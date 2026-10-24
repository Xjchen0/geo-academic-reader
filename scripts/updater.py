#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check for and apply workspace updates while preserving user data.

Design rules
------------
1. The updater never writes to ``papers/``, ``.raw/``, ``.geo-reader/`` or
   ``input_pdfs/``. Local notes, figures, evidence packs and preferences are
   the user's work, not part of the code payload.
2. A git checkout is updated with ``git merge --ff-only <tag>``; a dirty
   tracked tree or a diverged history is reported, never reset.
3. A non-git copy is updated from the GitHub release tarball, copying only
   code/documentation paths from ``UPGRADE_PATHS``.
4. Network failure is not an error for a reading task: ``--check-update``
   exits 0 and says the check was skipped.
"""

import datetime
import io
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import GUIDE_DIR, PROJECT_ROOT, PROFILE_PATH
from .version import __version__

GITHUB_REPO = "Xjchen0/geo-academic-reader"
RELEASES_API = "https://api.github.com/repos/{}/releases?per_page=30".format(GITHUB_REPO)
RELEASE_URL = "https://github.com/{}/releases/tag/{}"
TARBALL_URLS = (
    "https://codeload.github.com/{repo}/tar.gz/refs/tags/{tag}",
    "https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz",
)
CACHE_PATH = GUIDE_DIR / "update-check.json"
CACHE_TTL_SECONDS = 6 * 60 * 60
OFFLINE_TTL_SECONDS = 30 * 60

# Only these paths may be replaced by an update. Everything else belongs to
# the user (notes, figures, evidence packs, preferences, dropped PDFs).
UPGRADE_PATHS = (
    "main.py",
    "doctor.py",
    "install.py",
    "install.sh",
    "install.ps1",
    "uninstall.py",
    "uninstall.sh",
    "uninstall.ps1",
    "pyproject.toml",
    "setup.py",
    "requirements.txt",
    "requirements-optional.txt",
    "geo-academic-reader.yaml",
    "AGENTS.md",
    "SKILL.md",
    "PROMPTS.md",
    "LESSONS.md",
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "scripts",
    "templates",
    "rules",
    "tests",
)

# Cone-mode sparse checkout accepts directories only; root files are included
# automatically.
SPARSE_DIRS = ("scripts", "templates", "rules", "tests")

_VERSION_RE = re.compile(
    r"^v?(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.(?P<patch>\d+))?"
    r"(?:[-._]?(?P<phase>dev|alpha|a|beta|b|pre|preview|rc)\.?(?P<phase_num>\d+)?)?"
    r"(?:[-._]?(?P<post>post|rev|r)\.?(?P<post_num>\d+)?)?"
    r"(?:\+[0-9A-Za-z.\-]+)?$",
    re.I,
)

_PHASE_RANK = {
    "dev": 0,
    "alpha": 1,
    "a": 1,
    "beta": 2,
    "b": 2,
    "pre": 3,
    "preview": 3,
    "rc": 3,
}


def parse_version(text: str) -> Tuple[int, int, int, int, int, int]:
    """Parse a version into a comparable key.

    PEP 440-ish ordering, without requiring ``packaging``:
    ``0.3.0-pre.1`` < ``0.3.0`` < ``0.3.1`` < ``0.10.0``.
    """
    raw = str(text or "").strip()
    match = _VERSION_RE.match(raw)
    if not match:
        raise ValueError("无法解析版本号: {!r}".format(text))
    phase = (match.group("phase") or "").lower()
    if phase:
        # A release candidate sorts before the final release of the same number.
        phase_rank = _PHASE_RANK.get(phase, 3)
        phase_num = int(match.group("phase_num") or 0)
    else:
        phase_rank = 4
        phase_num = 0
    post = (match.group("post") or "").lower()
    post_num = int(match.group("post_num") or 0) if post else 0
    return (
        int(match.group("major")),
        int(match.group("minor") or 0),
        int(match.group("patch") or 0),
        phase_rank,
        phase_num,
        post_num,
    )


def compare_versions(left: str, right: str) -> int:
    """Return 1 if left > right, -1 if left < right, 0 if equal."""
    a, b = parse_version(left), parse_version(right)
    return (a > b) - (a < b)


def is_newer(candidate: Optional[str], current: str) -> bool:
    if not candidate:
        return False
    try:
        return compare_versions(candidate, current) > 0
    except ValueError:
        return False


def bump_patch(version: str) -> str:
    """0.3.0 -> 0.3.1; prerelease suffixes are dropped."""
    major, minor, patch, _, _, _ = parse_version(version)
    return "{}.{}.{}".format(major, minor, patch + 1)


# ---------------------------------------------------------------------------
# GitHub release lookup


def _http_json(url: str, timeout: float) -> list:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "geo-academic-reader/{}".format(__version__),
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_releases(timeout: float = 8.0) -> List[dict]:
    payload = _http_json(RELEASES_API, timeout=timeout)
    if not isinstance(payload, list):
        raise ValueError("GitHub releases API 返回了非列表响应")
    return payload


def select_release(releases: List[dict], include_prerelease: bool = False) -> Optional[dict]:
    """Pick the highest published release, optionally allowing prereleases."""
    best = None
    best_key = None
    for release in releases or []:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        if release.get("prerelease") and not include_prerelease:
            continue
        tag = str(release.get("tag_name") or "")
        try:
            key = parse_version(tag)
        except ValueError:
            continue
        if best_key is None or key > best_key:
            best_key = key
            best = release
    return best


def _release_summary(release: dict) -> dict:
    tag = str(release.get("tag_name") or "")
    try:
        version = re.sub(r"^v", "", tag, flags=re.I)
        parse_version(version)
    except ValueError:
        version = tag
    return {
        "tag": tag,
        "version": version,
        "name": release.get("name") or tag,
        "url": release.get("html_url") or RELEASE_URL.format(GITHUB_REPO, tag),
        "published_at": release.get("published_at") or "",
        "prerelease": bool(release.get("prerelease")),
        "body": (release.get("body") or "").strip(),
    }


# ---------------------------------------------------------------------------
# Cache


def _now() -> datetime.datetime:
    return datetime.datetime.now().astimezone()


def _read_cache() -> Optional[dict]:
    try:
        if CACHE_PATH.is_file():
            data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        return None
    return None


def _write_cache(payload: dict) -> None:
    # Never create .geo-reader/ before onboarding; the cache is optional.
    try:
        if not GUIDE_DIR.exists():
            return
        CACHE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except Exception:
        pass


def _clear_cache() -> None:
    """Drop a stale 'update available' hint after a successful upgrade."""
    try:
        CACHE_PATH.unlink()
    except OSError:
        pass


def _cache_fresh(cached: dict, include_prerelease: bool) -> bool:
    if bool(cached.get("include_prerelease")) != bool(include_prerelease):
        return False
    try:
        checked = datetime.datetime.fromisoformat(str(cached.get("checked_at") or ""))
    except ValueError:
        return False
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=datetime.timezone.utc)
    ttl = CACHE_TTL_SECONDS if cached.get("reachable") else OFFLINE_TTL_SECONDS
    return (_now() - checked).total_seconds() < ttl


# ---------------------------------------------------------------------------
# Public check


def check_for_update(
    current: Optional[str] = None,
    include_prerelease: bool = False,
    refresh: bool = False,
    timeout: float = 8.0,
) -> dict:
    """Return a structured update check. Never raises for network failure."""
    current = current or __version__
    cached = _read_cache()
    if cached and not refresh and _cache_fresh(cached, include_prerelease):
        payload = dict(cached)
        payload["source"] = "cache"
        payload["current"] = current
        payload["has_update"] = is_newer(payload.get("latest_version"), current)
        return payload

    checked_at = _now().isoformat(timespec="seconds")
    try:
        releases = fetch_releases(timeout=timeout)
        release = select_release(releases, include_prerelease)
        if release is None:
            preview = None if include_prerelease else select_release(
                releases, include_prerelease=True
            )
            payload = {
                "reachable": True,
                "latest_version": None,
                "has_update": False,
                "current": current,
                "prerelease_only": bool(preview),
                "prerelease_latest": _release_summary(preview) if preview else None,
                "error": "未找到已发布的版本（release）",
                "checked_at": checked_at,
                "include_prerelease": include_prerelease,
            }
        else:
            summary = _release_summary(release)
            payload = {
                "reachable": True,
                "current": current,
                "latest_version": summary["version"],
                "latest_tag": summary["tag"],
                "name": summary["name"],
                "url": summary["url"],
                "published_at": summary["published_at"],
                "prerelease": summary["prerelease"],
                "notes": summary["body"],
                "has_update": is_newer(summary["version"], current),
                "prerelease_only": False,
                "error": None,
                "checked_at": checked_at,
                "include_prerelease": include_prerelease,
            }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        previous = cached or {}
        payload = {
            "reachable": False,
            "current": current,
            "latest_version": previous.get("latest_version"),
            "latest_tag": previous.get("latest_tag"),
            "name": previous.get("name"),
            "url": previous.get("url"),
            "published_at": previous.get("published_at"),
            "prerelease": previous.get("prerelease"),
            "notes": previous.get("notes"),
            "has_update": False,
            "error": "{}: {}".format(type(exc).__name__, exc),
            "checked_at": checked_at,
            "include_prerelease": include_prerelease,
        }
    payload["source"] = "network"
    _write_cache(payload)
    return payload


# ---------------------------------------------------------------------------
# Applying an update


def _run_git(args: List[str], timeout: float = 120.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _git_available() -> bool:
    """True only when the workspace itself is the git repository root.

    A workspace nested inside a larger git repo must not be updated by
    fast-forwarding the parent repository.
    """
    try:
        inside = _run_git(["rev-parse", "--is-inside-work-tree"], timeout=10)
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return False
        top = _run_git(["rev-parse", "--show-toplevel"], timeout=10)
        if top.returncode != 0:
            return False
        return Path(top.stdout.strip()).resolve() == PROJECT_ROOT.resolve()
    except (OSError, subprocess.SubprocessError):
        return False


def _git_tracked_changes() -> str:
    result = _run_git(["status", "--porcelain", "--untracked-files=no"], timeout=30)
    return result.stdout.strip() if result.returncode == 0 else ""


def _backup_profile() -> Optional[Path]:
    if not PROFILE_PATH.is_file():
        return None
    backup_dir = GUIDE_DIR / "backups"
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = _now().strftime("%Y%m%d-%H%M%S")
        target = backup_dir / "profile-{}.json".format(stamp)
        shutil.copy2(str(PROFILE_PATH), str(target))
        return target
    except Exception:
        return None


def _clone_payload(tag: str, timeout: float, log) -> List[str]:
    """Copy the code payload from a shallow, sparse clone of the release tag.

    Used when the workspace is not itself a git checkout but git is
    available. Sparse checkout keeps the user's notes and figures out of the
    download.
    """
    url = "https://github.com/{}.git".format(GITHUB_REPO)
    with tempfile.TemporaryDirectory(prefix="geo-reader-clone-") as temp:
        destination = Path(temp) / "src"
        log("克隆 {} ({}) ...".format(url, tag))
        base = [
            "git", "clone", "--depth", "1", "--branch", tag,
            "--single-branch", url, str(destination),
        ]
        sparse_cmd = [
            "git", "clone", "--depth", "1", "--branch", tag,
            "--single-branch", "--filter=blob:none", "--sparse",
            url, str(destination),
        ]
        sparse = subprocess.run(
            sparse_cmd, text=True, capture_output=True, timeout=timeout,
        )
        if sparse.returncode == 0:
            checkout = subprocess.run(
                ["git", "-C", str(destination), "sparse-checkout", "set"] + list(SPARSE_DIRS),
                text=True, capture_output=True, timeout=timeout,
            )
            if checkout.returncode != 0:
                raise OSError("sparse checkout 失败: {}".format(
                    (checkout.stderr or checkout.stdout or "").strip()
                ))
        else:
            shutil.rmtree(str(destination), ignore_errors=True)
            full = subprocess.run(
                base, text=True, capture_output=True, timeout=timeout
            )
            if full.returncode != 0:
                raise OSError("git clone 失败: {}".format(
                    (full.stderr or full.stdout or "").strip()
                ))
        return _copy_payload(destination, log)


def _download_tarball(urls, timeout: float, log) -> bytes:
    errors = []
    for url in urls:
        request = urllib.request.Request(
            url, headers={"User-Agent": "geo-academic-reader/{}".format(__version__)}
        )
        log("下载 {}".format(url))
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append("{}: {}".format(url, exc))
            log("下载失败，尝试下一个地址 ...")
    raise OSError("；".join(errors) or "没有可用的下载地址")


def _safe_extract(data: bytes, destination: Path) -> Path:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            name = member.name.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/"):
                raise ValueError("压缩包包含不安全路径: {}".format(member.name))
            if not (member.isfile() or member.isdir()):
                raise ValueError("压缩包包含非普通文件: {}".format(member.name))
        try:
            archive.extractall(str(destination), filter="data")
        except TypeError:  # Python < 3.12
            archive.extractall(str(destination))
    roots = [item for item in destination.iterdir() if item.is_dir()]
    if not roots:
        raise ValueError("压缩包结构异常：找不到顶层目录")
    return roots[0]


def _copy_payload(source_root: Path, log) -> List[str]:
    copied = []
    for relative in UPGRADE_PATHS:
        source = source_root / relative
        if not source.exists():
            continue
        target = PROJECT_ROOT / relative
        if source.is_dir():
            shutil.copytree(str(source), str(target), dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source), str(target))
        copied.append(relative)
    return copied


def _data_snapshot() -> dict:
    def count(directory: Path, pattern: str) -> int:
        try:
            return sum(1 for _ in directory.glob(pattern))
        except Exception:
            return 0

    return {
        "notes": count(PROJECT_ROOT / "papers", "*.md"),
        "packs": count(PROJECT_ROOT / ".raw", "*"),
        "pdfs": count(PROJECT_ROOT / "input_pdfs", "*.pdf"),
    }


def update_workspace(
    include_prerelease: bool = False,
    force: bool = False,
    dry_run: bool = False,
    timeout: float = 60.0,
    log=print,
) -> dict:
    """Update the code payload; keep notes, packs and preferences untouched."""
    current = __version__
    check = check_for_update(
        current=current, include_prerelease=include_prerelease, refresh=True, timeout=8.0
    )
    result = {
        "current": current,
        "target": check.get("latest_version"),
        "tag": check.get("latest_tag"),
        "updated": False,
        "method": None,
        "preserved": {"profile": PROFILE_PATH.is_file(), "data": _data_snapshot()},
        "profile_backup": None,
        "check": check,
        "warnings": [],
    }

    if not check.get("reachable"):
        result["error"] = "无法访问 GitHub，已保留当前版本。{}".format(check.get("error") or "")
        return result

    if not check.get("has_update") and not force:
        result["message"] = "已是最新版本 {}（或本地版本更高）。".format(current)
        return result

    tag = check.get("latest_tag")
    if not tag:
        result["error"] = (
            "GitHub 上没有可用的版本标签；如果只存在预发布版本，请加 --prerelease。"
        )
        return result

    if dry_run:
        result["message"] = "预览：将更新 {} → {}（未执行）。".format(current, check.get("latest_version"))
        result["method"] = "dry-run"
        return result

    backup = None
    profile_before = None

    # --- git checkout -----------------------------------------------------
    if _git_available():
        dirty = _git_tracked_changes()
        if dirty:
            result["error"] = (
                "本地有未提交的代码改动，未执行更新。请先 commit 或 stash 后再试；"
                "笔记与 .raw/ 不受影响。"
            )
            return result
        backup = _backup_profile()
        result["profile_backup"] = str(backup) if backup else None
        if PROFILE_PATH.is_file():
            try:
                profile_before = PROFILE_PATH.read_text(encoding="utf-8")
            except Exception:
                profile_before = None
        log("发现 git 仓库，尝试快进到 {} ...".format(tag))
        fetch = _run_git(["fetch", "--tags", "--prune", "origin"])
        if fetch.returncode != 0:
            log("git fetch 失败：{}".format((fetch.stderr or "").strip()))
        verify = _run_git(["rev-parse", "--verify", "refs/tags/{}^{{commit}}".format(tag)])
        if verify.returncode != 0:
            result["error"] = "找不到标签 {}，请确认网络与仓库状态。".format(tag)
            return result
        merge = _run_git(["merge", "--ff-only", tag])
        if merge.returncode != 0:
            result["error"] = (
                "无法快进到 {}：本地提交与上游历史分叉。未做任何覆盖。\n{}"
            ).format(tag, (merge.stderr or merge.stdout or "").strip())
            return result
        result["updated"] = True
        result["method"] = "git"
        result["detail"] = (merge.stdout or "").strip()
    # --- tarball fallback -------------------------------------------------
    else:
        backup = _backup_profile()
        result["profile_backup"] = str(backup) if backup else None
        if PROFILE_PATH.is_file():
            try:
                profile_before = PROFILE_PATH.read_text(encoding="utf-8")
            except Exception:
                profile_before = None
        urls = [pattern.format(repo=GITHUB_REPO, tag=tag) for pattern in TARBALL_URLS]
        copied = None
        method = None
        errors = []
        if shutil.which("git"):
            try:
                copied = _clone_payload(tag, timeout=timeout, log=log)
                method = "clone"
            except Exception as exc:
                errors.append("git clone: {}".format(exc))
                log("git clone 失败（{}），改用源码包 ...".format(exc))
        if copied is None:
            try:
                data = _download_tarball(urls, timeout=timeout, log=log)
                with tempfile.TemporaryDirectory(prefix="geo-reader-update-") as temp:
                    root = _safe_extract(data, Path(temp))
                    copied = _copy_payload(root, log)
                method = "tarball"
            except Exception as exc:
                errors.append("源码包: {}".format(exc))
        if copied is None:
            result["error"] = (
                "下载更新包失败：{}\n"
                "  手动更新：从 {} 下载源码包，解压后覆盖代码与文档；"
                "不要删除 papers/、.raw/、.geo-reader/、input_pdfs/。"
            ).format("；".join(errors), check.get("url") or RELEASE_URL.format(GITHUB_REPO, tag))
            return result
        result["updated"] = True
        result["method"] = method
        result["copied"] = copied

    # --- verify that the user's data survived ----------------------------
    if profile_before is not None:
        try:
            profile_after = PROFILE_PATH.read_text(encoding="utf-8")
        except Exception:
            profile_after = None
        if profile_after is None:
            if backup:
                shutil.copy2(str(backup), str(PROFILE_PATH))
                result["warnings"].append("偏好文件在更新中缺失，已从备份恢复。")
            else:
                result["warnings"].append("偏好文件在更新中缺失，且没有可用备份。")
        elif profile_after != profile_before:
            PROFILE_PATH.write_text(profile_before, encoding="utf-8")
            result["warnings"].append("偏好文件内容发生变化，已恢复为更新前的版本。")
        result["preserved"]["profile"] = PROFILE_PATH.is_file()

    result["preserved"]["data_after"] = _data_snapshot()
    _clear_cache()
    result["message"] = "更新完成：{} → {}（{}）".format(
        current, check.get("latest_version"), result["method"]
    )
    return result


# ---------------------------------------------------------------------------
# Formatting


def format_check(payload: dict) -> str:
    current = payload.get("current") or __version__
    if not payload.get("reachable"):
        return (
            "无法访问 GitHub，已跳过更新检查（不影响本地使用）。\n"
            "  原因: {}\n"
            "  稍后可重试: python3 main.py --check-update --refresh"
        ).format(payload.get("error") or "network error")

    latest = payload.get("latest_version")
    if not latest:
        if payload.get("prerelease_only"):
            preview = payload.get("prerelease_latest") or {}
            return (
                "没有稳定版本更新；当前只有预发布版本 {}。\n"
                "  如要使用：python3 main.py --check-update --prerelease\n"
                "  当前版本: {}"
            ).format(preview.get("version") or "—", current)
        return "已是最新版本 {}（GitHub 上没有可用 release）。".format(current)
    if payload.get("has_update"):
        lines = [
            "发现新版本：{} → {}".format(current, latest),
            "  发布页: {}".format(payload.get("url") or ""),
            "  更新: python3 main.py --update",
            "  偏好、笔记、证据包会保留。",
        ]
        if payload.get("prerelease"):
            lines.insert(1, "  （预发布版本，可用 --prerelease 指定通道）")
        return "\n".join(lines)
    return "已是最新版本：{}（远端最新 {}）。".format(current, latest)


def format_update(payload: dict) -> str:
    if payload.get("error"):
        return "更新未执行：{}".format(payload["error"])
    lines = [payload.get("message") or "无需更新。"]
    if payload.get("updated"):
        lines.append("  方式: {}".format(payload.get("method")))
        preserved = payload.get("preserved") or {}
        lines.append("  偏好: {}".format("已保留" if preserved.get("profile") else "尚未建立"))
        if payload.get("profile_backup"):
            lines.append("  备份: {}".format(payload["profile_backup"]))
        before = preserved.get("data") or {}
        after = preserved.get("data_after") or before
        lines.append(
            "  数据: notes={}→{}  packs={}→{}  pdfs={}→{}".format(
                before.get("notes", 0), after.get("notes", 0),
                before.get("packs", 0), after.get("packs", 0),
                before.get("pdfs", 0), after.get("pdfs", 0),
            )
        )
        lines.append("  建议: python3 main.py --doctor && python3 main.py --check-note --fix")
    for warning in payload.get("warnings") or []:
        lines.append("  警告: {}".format(warning))
    return "\n".join(lines)
