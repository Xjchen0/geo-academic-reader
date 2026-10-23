#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workspace paths, HTTP defaults, profile storage and naming helpers."""

import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from .version import __version__

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPERS_DIR = PROJECT_ROOT / "papers"
# Figures live beside the notes so that the Markdown preview works no matter
# whether the user opens the project root, papers/, or a single note file.
# VS Code only allows local images under the current workspace root (or the
# note's own directory for single-file windows); a sibling assets/ folder at
# the project root breaks in the latter two cases.
ASSETS_DIR = PAPERS_DIR / "assets"
# Pre-0.2.2 location, kept for one-command migration in --check-note --fix.
LEGACY_ASSETS_DIR = PROJECT_ROOT / "assets"
INPUT_PDFS_DIR = PROJECT_ROOT / "input_pdfs"
RAW_DIR = PROJECT_ROOT / ".raw"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
GUIDE_DIR = PROJECT_ROOT / ".geo-reader"
INDEX_FILE = PAPERS_DIR / "INDEX.md"
RAW_INDEX_FILE = RAW_DIR / "INDEX.md"

# Allow tests and advanced users to keep the profile elsewhere.
PROFILE_PATH = Path(
    os.environ.get("GEO_READER_PROFILE", str(GUIDE_DIR / "profile.json"))
).expanduser()
if not PROFILE_PATH.is_absolute():
    PROFILE_PATH = (PROJECT_ROOT / PROFILE_PATH).resolve()

DEFAULT_HEADERS = {
    "User-Agent": (
        "geo-academic-reader/{version} "
        "(+https://github.com/Xjchen0/geo-academic-reader)"
    ).format(version=__version__),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}

CROSSREF_API_URL = "https://api.crossref.org/works/"
OPENALEX_API_URL = "https://api.openalex.org/works/doi:"
CHROME_CDP_HTTP = "http://127.0.0.1:9222"

DEFAULT_PROFILE = {
    "version": 1,
    "language": "zh-CN",
    "ide": "vscode",
    "agent": "qoder",
    "style": "balanced",      # guided | balanced | expert
    "browser": "auto",        # auto | existing | off
    "note_depth": "deep",     # brief | standard | deep
    "citation": "apa",        # apa | nature | gbt7714
    "created_at": "",
    "updated_at": "",
}

PROFILE_CHOICES = {
    "language": ["zh-CN", "en", "bilingual"],
    "ide": ["vscode", "cursor", "claude-code", "antigravity", "windsurf", "cli"],
    "style": ["guided", "balanced", "expert"],
    "browser": ["auto", "existing", "off"],
    "note_depth": ["brief", "standard", "deep"],
    "citation": ["apa", "nature", "gbt7714"],
}


def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    return datetime.date.today().isoformat()


def ensure_workspace_dirs() -> None:
    # Do not create GUIDE_DIR here: a first-time user should leave no trace
    # until the conversational onboarding writes .geo-reader/profile.json.
    for directory in (PAPERS_DIR, ASSETS_DIR, INPUT_PDFS_DIR, RAW_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def profile_exists() -> bool:
    return PROFILE_PATH.is_file()


def is_tty() -> bool:
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except Exception:
        return False


def slugify(value: str) -> str:
    """Convert a DOI, title or filename into a stable, portable folder name."""
    value = str(value or "").strip()
    value = re.sub(r"[^\w\s.-]", "_", value, flags=re.UNICODE)
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"_+", "_", value)
    value = value.strip("._-")
    return (value or "paper")[:100]


def doi_to_slug(doi: str) -> str:
    """Stable slug that keeps the registrant prefix, e.g. 10.1038_s41467-... ."""
    doi = (doi or "").strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return slugify(doi.replace("/", "_"))


def url_to_slug(url: str, title: str = "") -> str:
    digest = hashlib.sha1((url or "").encode("utf-8")).hexdigest()[:8]
    if title:
        return "{}_{}".format(slugify(title)[:64], digest)
    return "web_{}".format(digest)


def extract_doi(text: str):
    """Return the first DOI found in a string, with trailing punctuation removed."""
    if not text:
        return None
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text)
    if not match:
        return None
    doi = match.group(0).rstrip(".,;:)]}>'\"")
    return doi or None


def load_profile() -> dict:
    profile = dict(DEFAULT_PROFILE)
    try:
        if PROFILE_PATH.exists():
            loaded = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                profile.update(loaded)
    except Exception:
        pass
    return profile


def save_profile(profile: dict) -> Path:
    profile = dict(profile or {})
    merged = dict(DEFAULT_PROFILE)
    merged.update(profile)
    merged["updated_at"] = now_iso()
    if not merged.get("created_at"):
        merged["created_at"] = merged["updated_at"]
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return PROFILE_PATH


def relative_posix(path: Path, start: Path) -> str:
    """Relative path with forward slashes, suitable for Markdown on all platforms."""
    return os.path.relpath(str(path), str(start)).replace(os.sep, "/")
