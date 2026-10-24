#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Session preflight for the literature workspace.

An agent must load the operating contract before it touches a paper. This
module verifies that the contract documents exist, runs the environment
doctor, checks the profile and records a short-lived marker that the CLI
requires for literature commands.

It cannot prove that an agent read a file. It can make skipping the check
visible, and it gives the agent a concrete checklist to walk the user through.
"""

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from .config import (
    ASSETS_DIR,
    GUIDE_DIR,
    INDEX_FILE,
    INPUT_PDFS_DIR,
    PAPERS_DIR,
    PROFILE_PATH,
    PROJECT_ROOT,
    RAW_DIR,
    load_profile,
    profile_exists,
)
from .version import __version__

CONTRACT_DOCS = ("AGENTS.md", "MEMORY.md", "LESSONS.md")
MARKER_PATH = GUIDE_DIR / "preflight.json"
MARKER_MAX_AGE_HOURS = 24
GATE_SKIP_ENV = "GEO_READER_SKIP_PREFLIGHT"


def _now() -> datetime.datetime:
    return datetime.datetime.now().astimezone()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def document_status(root: Optional[Path] = None) -> Dict[str, dict]:
    """Return exists/size for the files an agent must read before working."""
    base = Path(root) if root else PROJECT_ROOT
    result = {}
    for name in CONTRACT_DOCS:
        path = base / name
        try:
            size = path.stat().st_size
            exists = path.is_file()
        except OSError:
            size, exists = 0, False
        result[name] = {"path": str(path), "exists": exists, "bytes": size}
    return result


def classify_role(has_profile: bool, note_count: int, raw_count: int) -> str:
    """Separate the clean code repository from a workspace holding user data."""
    if has_profile or note_count > 0 or raw_count > 0:
        return "test"
    return "code"


def workspace_role() -> Dict[str, object]:
    notes = [
        path for path in PAPERS_DIR.glob("*.md")
        if path.name.lower() != "index.md"
    ]
    raw_packs = 0
    if RAW_DIR.is_dir():
        raw_packs = sum(1 for path in RAW_DIR.iterdir() if path.is_dir())
    role = classify_role(profile_exists(), len(notes), raw_packs)
    return {
        "role": role,
        "label": (
            "test workspace — local profile, notes or evidence packs present"
            if role == "test"
            else "code repository — clean template, no local reading data"
        ),
        "notes": len(notes),
        "evidence_packs": raw_packs,
        "profile": profile_exists(),
    }


def _run_doctor() -> Dict[str, object]:
    """Run doctor.py in a subprocess so preflight stays import-light."""
    command = [sys.executable, str(PROJECT_ROOT / "doctor.py"), "--json"]
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(PROJECT_ROOT),
        )
        data = json.loads(proc.stdout or "{}")
        return data if isinstance(data, dict) else {"error": "doctor output is not a JSON object"}
    except Exception as exc:  # doctor is an external process; never crash preflight
        return {"error": "{}: {}".format(type(exc).__name__, exc)}


def build_preflight() -> Dict[str, object]:
    docs = document_status()
    env = _run_doctor()
    profile = load_profile() if profile_exists() else {}
    role = workspace_role()

    blockers = []
    missing_docs = [name for name, info in docs.items() if not info["exists"]]
    if missing_docs:
        blockers.append("缺少契约文档：{}".format(", ".join(missing_docs)))

    if env.get("error"):
        blockers.append("环境自检失败：{}".format(env["error"]))
    elif env:
        if not env.get("python", {}).get("ok", False):
            blockers.append("Python 版本低于 3.9")
        missing_packages = env.get("packages", {}).get("missing") or []
        if missing_packages:
            blockers.append("缺少依赖：{}".format(", ".join(missing_packages)))
    else:
        blockers.append("环境自检没有返回结果")

    chrome = env.get("chrome", {}) if env else {}
    return {
        "version": __version__,
        "checked_at": _now().isoformat(timespec="seconds"),
        "ok": not blockers,
        "blockers": blockers,
        "documents": docs,
        "environment": {
            "os": env.get("os", ""),
            "python": env.get("python", {}),
            "packages": env.get("packages", {}),
            "optional_packages": env.get("optional_packages", {}),
            "chrome": {
                "executable": chrome.get("executable", ""),
                "cdp_running": bool(chrome.get("cdp_running")),
                "error": chrome.get("error", ""),
                "launch_command": chrome.get("launch_command", ""),
            },
            "vscode": env.get("vscode", {}),
        },
        "profile": {
            "path": str(PROFILE_PATH),
            "exists": profile_exists(),
            "values": profile,
        },
        "workspace": {
            "root": str(PROJECT_ROOT),
            "role": role["role"],
            "label": role["label"],
            "notes": role["notes"],
            "evidence_packs": role["evidence_packs"],
            "papers": str(PAPERS_DIR),
            "assets": str(ASSETS_DIR),
            "raw": str(RAW_DIR),
            "input_pdfs": str(INPUT_PDFS_DIR),
            "profile": str(PROFILE_PATH),
            "index": str(INDEX_FILE),
        },
    }


def write_marker(report: Dict[str, object]) -> Path:
    _atomic_write(MARKER_PATH, json.dumps(report, ensure_ascii=False, indent=2))
    return MARKER_PATH


def read_marker() -> Optional[dict]:
    try:
        return json.loads(MARKER_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def marker_is_fresh(
    marker: Optional[dict],
    now: Optional[datetime.datetime] = None,
    max_age_hours: int = MARKER_MAX_AGE_HOURS,
    version: str = __version__,
) -> bool:
    if not marker:
        return False
    if marker.get("version") != version:
        return False
    if not marker.get("ok"):
        return False
    try:
        checked = datetime.datetime.fromisoformat(str(marker.get("checked_at")))
    except ValueError:
        return False
    if checked.tzinfo is None:
        checked = checked.astimezone()
    reference = now or _now()
    age = reference - checked
    return datetime.timedelta(0) <= age <= datetime.timedelta(hours=max_age_hours)


def gate_status() -> Dict[str, object]:
    """Decide whether a literature command may run."""
    marker = read_marker()
    if not marker_is_fresh(marker):
        return {
            "allowed": False,
            "reason": "preflight_missing",
            "message": (
                "会话前置检查缺失或已过期（超过 {} 小时/版本变化）。".format(MARKER_MAX_AGE_HOURS)
            ),
        }
    if not marker.get("profile", {}).get("exists"):
        return {
            "allowed": False,
            "reason": "profile_missing",
            "message": "尚未完成对话式引导：.geo-reader/profile.json 不存在。",
        }
    return {"allowed": True, "reason": "ok", "message": ""}


def format_report(report: Dict[str, object]) -> str:
    env = report.get("environment", {}) or {}
    python = env.get("python", {}) or {}
    packages = env.get("packages", {}) or {}
    chrome = env.get("chrome", {}) or {}
    profile = report.get("profile", {}) or {}
    workspace = report.get("workspace", {}) or {}
    docs = report.get("documents", {}) or {}

    lines = [
        "geo-academic-reader v{} | Preflight".format(report.get("version", "")),
        "=" * 62,
        "Workspace : {}".format(workspace.get("root", "")),
        "Role      : {}".format(workspace.get("label", "")),
        "Docs      : " + " | ".join(
            "{} {}".format(name, "OK" if info.get("exists") else "MISSING")
            for name, info in docs.items()
        ),
        "System    : {}".format(env.get("os", "unknown")),
        "Python    : {} {}".format(
            python.get("version", "?"), "OK" if python.get("ok") else "TOO OLD"
        ),
        "Packages  : {}".format(
            "OK" if not packages.get("missing") else "missing " + ", ".join(packages.get("missing", []))
        ),
        "Chrome    : {}".format(
            "OK" + (" + CDP 9222" if chrome.get("cdp_running") else " (CDP not running)")
            if chrome.get("executable") else "not found (HTTP/PDF fallback only)"
        ),
        "Profile   : {}".format(
            "found ({})".format(
                ", ".join(
                    "{}={}".format(key, (profile.get("values") or {}).get(key, "?"))
                    for key in ("language", "style", "browser", "note_depth", "citation")
                )
            )
            if profile.get("exists") else "missing — conversational onboarding required"
        ),
        "Data      : {} note(s), {} evidence pack(s), {}".format(
            workspace.get("notes", 0),
            workspace.get("evidence_packs", 0),
            "profile local" if workspace.get("role") == "test" else "clean",
        ),
    ]
    if report.get("blockers"):
        lines.append("Blockers  : " + "; ".join(report["blockers"]))
    else:
        lines.append("Blockers  : none")
    if report.get("ok"):
        lines.append("Gate      : READY (marker valid for {} h)".format(MARKER_MAX_AGE_HOURS))
    else:
        lines.append("Gate      : BLOCKED")
    lines.append("")
    if profile.get("exists"):
        lines.append("Next: run a literature command, or --guide for the workflow.")
    else:
        lines.append("Next: in the agent chat, say 开始使用 / Start. Do not run a setup script.")
    return "\n".join(lines)
