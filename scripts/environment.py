#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find the Python environment this workspace should run in.

A user who clones the repository has *some* Python, but not necessarily
one with the dependencies, and not necessarily one on ``PATH``. The
Windows Store alias stub (``python3.exe`` that exits with code 49) is
the extreme case: it looks like Python and is not.

So the workspace scans a fixed order and reports what it found:

    uv  ->  conda  ->  venv  ->  plain python

The order is deliberate. ``uv`` owns the project environment when it is
available (``pyproject.toml`` + ``uv sync``), ``conda`` and ``venv``
come next because they are what most people already have activated,
and plain Python is the last resort that always exists. The scan never
installs anything; it only says which command to run and which command
would prepare that environment.

The *active* environment is preferred when it already has the
dependencies: if the user is sitting in a conda env or a venv, running
``python main.py`` beats asking them to build a second environment.
"""

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .config import PROJECT_ROOT

# The scan order. Everything downstream (doctor, preflight, the agent
# contract in AGENTS.md) refers to these names.
ENVIRONMENT_ORDER = ("uv", "conda", "venv", "python")

ENVIRONMENT_LABELS = {
    "uv": "uv 项目环境",
    "conda": "conda 环境",
    "venv": "venv / virtualenv",
    "python": "系统 Python",
    "current": "当前解释器",
}

REQUIRED_MODULES = ("requests", "bs4", "pypdf", "websockets")

OPTIONAL_MODULES = ("fitz",)

# A venv directory that a project may have created for itself.
VENV_DIR_NAMES = (".venv", "venv", "env", ".env")

# Windows PowerShell and cmd spell the virtualenv launcher differently.
WIN = platform.system() == "Windows"


def _which(name: str) -> Optional[str]:
    try:
        return shutil.which(name)
    except Exception:
        return None


def _is_store_alias(path: str) -> bool:
    """True for the WindowsApps stub that exits with code 49."""
    if not path:
        return False
    return "microsoft\\windowsapps" in os.path.normpath(path).lower()


def _run_version(command: List[str]) -> str:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except Exception:
        return ""
    out = (proc.stdout or "").strip()
    if not out:
        out = (proc.stderr or "").strip()
    return out.splitlines()[0].strip() if out else ""


def probe_modules(modules=REQUIRED_MODULES) -> Dict[str, object]:
    """Check which modules are importable, without importing them."""
    present, missing = [], []
    for name in modules:
        try:
            found = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            found = False
        (present if found else missing).append(name)
    return {"present": present, "missing": missing, "ok": not missing}


def _venv_executable(root: Path) -> Optional[str]:
    """Return the interpreter of a project-local virtualenv, if any."""
    for name in VENV_DIR_NAMES:
        base = root / name
        if not base.is_dir():
            continue
        candidates = (
            [base / "Scripts" / "python.exe", base / "Scripts" / "python"]
            if WIN
            else [base / "bin" / "python", base / "bin" / "python3"]
        )
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    return None


def _uv_candidate(root: Path) -> Dict[str, object]:
    path = _which("uv")
    project_venv = _venv_executable(root) if path else None
    detail = ""
    if path and project_venv:
        detail = "项目已有 .venv/，uv sync 会复用它"
    elif path:
        detail = "uv sync 会创建 .venv/ 并按 pyproject.toml 安装依赖"
    return {
        "kind": "uv",
        "label": ENVIRONMENT_LABELS["uv"],
        "available": bool(path),
        "active": False,
        "path": path or "",
        "version": _run_version([path, "--version"]) if path else "",
        "run_command": "uv run python main.py",
        "setup_command": "uv sync",
        "detail": detail,
    }


def _conda_candidate() -> Dict[str, object]:
    path = _which("conda")
    active_prefix = os.environ.get("CONDA_PREFIX", "")
    active_name = os.environ.get("CONDA_DEFAULT_ENV", "")
    if active_prefix:
        return {
            "kind": "conda",
            "label": ENVIRONMENT_LABELS["conda"],
            "available": True,
            "active": True,
            "path": path or "",
            "version": active_name,
            "run_command": "python main.py",
            "setup_command": "python -m pip install -r requirements.txt",
            "detail": "conda 环境 {} 已激活，python 就是该环境的解释器".format(
                active_name or active_prefix
            ),
        }
    if path:
        return {
            "kind": "conda",
            "label": ENVIRONMENT_LABELS["conda"],
            "available": True,
            "active": False,
            "path": path,
            "version": "",
            "run_command": "conda run -n base python main.py",
            "setup_command": "conda create -n geo-reader python=3.11 -y",
            "detail": "conda 已安装但没有激活环境；先 create/activate，再用 conda run",
        }
    return {
        "kind": "conda",
        "label": ENVIRONMENT_LABELS["conda"],
        "available": False,
        "active": False,
        "path": "",
        "version": "",
        "run_command": "",
        "setup_command": "",
        "detail": "没有找到 conda",
    }


def _venv_candidate(root: Path) -> Dict[str, object]:
    executable = _venv_executable(root)
    in_venv = sys.prefix != sys.base_prefix
    if executable:
        rel = os.path.relpath(executable, str(root))
        return {
            "kind": "venv",
            "label": ENVIRONMENT_LABELS["venv"],
            "available": True,
            "active": in_venv,
            "path": executable,
            "version": Path(rel).parent.name,
            "run_command": '"{}" main.py'.format(executable),
            "setup_command": "python -m venv .venv",
            "detail": "项目内已有虚拟环境 {}".format(rel),
        }
    if in_venv:
        return {
            "kind": "venv",
            "label": ENVIRONMENT_LABELS["venv"],
            "available": True,
            "active": True,
            "path": sys.executable,
            "version": Path(sys.prefix).name,
            "run_command": "python main.py",
            "setup_command": "python -m pip install -r requirements.txt",
            "detail": "当前已在虚拟环境 {} 中".format(sys.prefix),
        }
    return {
        "kind": "venv",
        "label": ENVIRONMENT_LABELS["venv"],
        "available": False,
        "active": False,
        "path": "",
        "version": "",
        "run_command": "",
        "setup_command": "python -m venv .venv",
        "detail": "没有找到项目内虚拟环境，也没有激活 venv",
    }


def _python_candidate() -> Dict[str, object]:
    python3 = _which("python3")
    python = _which("python")
    launcher = _which("py") if WIN else None
    usable = [p for p in (python3, python) if p and not _is_store_alias(p)]
    aliases = [p for p in (python3, python) if p and _is_store_alias(p)]
    if usable:
        chosen = usable[0]
        name = "python3" if chosen == python3 else "python"
        return {
            "kind": "python",
            "label": ENVIRONMENT_LABELS["python"],
            "available": True,
            "active": False,
            "path": chosen,
            "version": "",
            "run_command": "{} main.py".format(name),
            "setup_command": "{} -m pip install -r requirements.txt".format(name),
            "detail": "PATH 上有可用的 {}".format(name),
        }
    if aliases:
        return {
            "kind": "python",
            "label": ENVIRONMENT_LABELS["python"],
            "available": False,
            "active": False,
            "path": aliases[0],
            "version": "",
            "run_command": "python main.py",
            "setup_command": "",
            "detail": (
                "PATH 上的 python/python3 是 Microsoft Store 占位符"
                "（退出码 49，无输出），不是真正的解释器"
            ),
        }
    detail = "PATH 上没有 python"
    if launcher:
        detail += "，但有 Windows 的 py 启动器：py -3 main.py"
    return {
        "kind": "python",
        "label": ENVIRONMENT_LABELS["python"],
        "available": False,
        "active": False,
        "path": "",
        "version": "",
        "run_command": "py -3 main.py" if launcher else "python main.py",
        "setup_command": "",
        "detail": detail,
    }


def scan_environments(root: Optional[Path] = None) -> List[Dict[str, object]]:
    """Return the four environment candidates in the fixed scan order."""
    base = Path(root) if root else PROJECT_ROOT
    builders = {
        "uv": lambda: _uv_candidate(base),
        "conda": _conda_candidate,
        "venv": lambda: _venv_candidate(base),
        "python": _python_candidate,
    }
    return [builders[kind]() for kind in ENVIRONMENT_ORDER]


def active_environment() -> Dict[str, object]:
    """Describe the environment the running interpreter lives in."""
    conda_prefix = os.environ.get("CONDA_PREFIX", "")
    if conda_prefix:
        return {
            "kind": "conda",
            "name": os.environ.get("CONDA_DEFAULT_ENV", ""),
            "prefix": conda_prefix,
            "executable": sys.executable,
        }
    if sys.prefix != sys.base_prefix:
        name = os.path.basename(sys.prefix) or "venv"
        return {
            "kind": "venv",
            "name": name,
            "prefix": sys.prefix,
            "executable": sys.executable,
        }
    return {
        "kind": "system",
        "name": "",
        "prefix": sys.prefix,
        "executable": sys.executable,
    }


def detect_environment(root: Optional[Path] = None) -> Dict[str, object]:
    """Scan the environments and recommend one.

    Recommendation order:

    1. The environment we are already in, when it is a conda env or a
       venv **and** it already has the required packages. Running
       ``python main.py`` where you already are beats building a second
       environment.
    2. Otherwise the first available candidate in the fixed order
       uv -> conda -> venv -> plain python.
    """
    candidates = scan_environments(root)
    active = active_environment()
    packages = probe_modules()

    recommended: Optional[Dict[str, object]] = None
    reason = ""

    if active["kind"] in ("conda", "venv") and packages["ok"]:
        recommended = {
            "kind": active["kind"],
            "run_command": "python main.py",
            "executable": active["executable"],
            "setup_command": "",
            "reason": "当前已激活的{} {} 里依赖齐全，直接用".format(
                ENVIRONMENT_LABELS[active["kind"]], active["name"] or ""
            ).strip(),
        }
    else:
        for candidate in candidates:
            if not candidate.get("available"):
                continue
            recommended = {
                "kind": candidate["kind"],
                "run_command": candidate.get("run_command", ""),
                "executable": candidate.get("path", ""),
                "setup_command": candidate.get("setup_command", ""),
                "reason": candidate.get("detail", ""),
            }
            break

    if recommended is None:
        recommended = {
            "kind": "python",
            "run_command": "python main.py",
            "executable": "",
            "setup_command": "",
            "reason": "没有可用的环境；请先安装 uv、conda 或 Python",
        }

    if not packages["ok"] and recommended.get("setup_command"):
        reason = "缺少依赖：{}；先跑 setup".format(", ".join(packages["missing"]))

    return {
        "order": list(ENVIRONMENT_ORDER),
        "candidates": candidates,
        "active": active,
        "packages": packages,
        "recommended": recommended,
        "notes": [reason] if reason else [],
    }


def format_environment_report(detected: Dict[str, object]) -> str:
    """Render the scan for a console, in a compact few lines."""
    lines = ["环境扫描（顺序：uv -> conda -> venv -> 系统 Python）："]
    for candidate in detected.get("candidates", []):
        mark = "可用" if candidate.get("available") else "不可用"
        if candidate.get("active"):
            mark += " / 已激活"
        suffix = candidate.get("detail") or ""
        lines.append(
            "  - {:<10} {}  {}".format(
                candidate.get("kind", "?"), mark, suffix
            ).rstrip()
        )
    recommended = detected.get("recommended", {}) or {}
    lines.append(
        "推荐运行方式：{}（{}）".format(
            recommended.get("run_command", "?"), recommended.get("reason", "")
        )
    )
    setup = recommended.get("setup_command")
    if setup:
        lines.append("如需先准备环境：{}".format(setup))
    return "\n".join(lines)
