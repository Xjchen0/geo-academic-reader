#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Environment doctor for geo-academic-reader.

Checks Python, dependencies, Chrome CDP, profile and VS Code Markdown setup.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.browser import chrome_launch_command, chrome_status, ensure_chrome, find_chrome
from scripts.config import PROFILE_PATH, PROJECT_ROOT, load_profile
from scripts.version import __version__

REQUIRED_PACKAGES = [
    ("requests", "requests"),
    ("bs4", "beautifulsoup4"),
    ("pypdf", "pypdf"),
    ("websockets", "websockets"),
]
OPTIONAL_PACKAGES = [
    ("fitz", "pymupdf (better PDF figure cropping)"),
]

USE_COLOR = platform.system() != "Windows" or os.environ.get("ANSICON") or os.environ.get("WT_SESSION")
GREEN = "\033[92m" if USE_COLOR else ""
YELLOW = "\033[93m" if USE_COLOR else ""
RED = "\033[91m" if USE_COLOR else ""
CYAN = "\033[96m" if USE_COLOR else ""
BOLD = "\033[1m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""


def _print_header(title):
    print("\n{}{}{}{}".format(BOLD, CYAN, "=" * 62, RESET))
    print("{}{}  {}{}".format(BOLD, CYAN, title, RESET))
    print("{}{}{}{}".format(BOLD, CYAN, "=" * 62, RESET))


def _ok(message):
    print(" {}[✓ OK]{} {}".format(GREEN, RESET, message))


def _warn(message):
    print(" {}[! WARN]{} {}".format(YELLOW, RESET, message))


def _fail(message):
    print(" {}[✗ FAIL]{} {}".format(RED, RESET, message))


def _info(message):
    print(" {}[i INFO]{} {}".format(CYAN, RESET, message))


def detect_package_manager():
    in_conda = "CONDA_PREFIX" in os.environ
    in_venv = sys.prefix != sys.base_prefix
    return {
        "in_conda": in_conda,
        "in_venv": in_venv,
        "has_uv": bool(shutil.which("uv")),
        "has_conda": bool(shutil.which("conda")),
        "has_pip": bool(shutil.which("pip") or shutil.which("pip3")),
        "summary": (
            "Active Conda Environment: {}".format(os.environ.get("CONDA_DEFAULT_ENV", "unknown"))
            if in_conda
            else ("Active Python venv / virtualenv" if in_venv else "Global / System Python")
        ),
    }


def check_packages(packages):
    installed, missing = [], []
    for import_name, display_name in packages:
        try:
            __import__(import_name)
            installed.append(display_name)
        except ImportError:
            missing.append(display_name)
    return installed, missing


def auto_install(missing, pm_info):
    if not missing:
        return
    # Map display names back to installable package names.
    install_names = []
    for name in missing:
        install_names.append(name.split(" ")[0])
    print("\n{}Attempting to install: {}{}".format(BOLD, ", ".join(install_names), RESET))
    if pm_info["has_uv"]:
        command = ["uv", "pip", "install"] + install_names
    elif pm_info["has_pip"]:
        command = [sys.executable, "-m", "pip", "install"] + install_names
    elif pm_info["has_conda"]:
        command = ["conda", "install", "-y"] + install_names
    else:
        _fail("No supported package manager found.")
        return
    _info("Running: {}".format(" ".join(command)))
    if subprocess.call(command) == 0:
        _ok("Installation complete.")
    else:
        _fail("Installation failed; run the command manually.")


def build_report(args):
    pm_info = detect_package_manager()
    installed, missing = check_packages(REQUIRED_PACKAGES)
    optional_installed, optional_missing = check_packages(OPTIONAL_PACKAGES)
    chrome_path = find_chrome()
    cdp = chrome_status() if chrome_path else None
    if args.launch_chrome and not cdp:
        try:
            cdp = ensure_chrome(launch=True)
        except Exception as exc:
            cdp = {"error": str(exc)}
    profile = load_profile()
    vscode_settings = PROJECT_ROOT / ".vscode" / "settings.json"
    return {
        "version": __version__,
        "os": "{} {} ({})".format(platform.system(), platform.release(), platform.machine()),
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "ok": sys.version_info >= (3, 9),
        },
        "package_manager": pm_info,
        "packages": {"installed": installed, "missing": missing},
        "optional_packages": {"installed": optional_installed, "missing": optional_missing},
        "chrome": {
            "executable": chrome_path,
            "cdp_running": bool(cdp and not cdp.get("error")),
            "browser": (cdp or {}).get("Browser", ""),
            "error": (cdp or {}).get("error", ""),
            "launch_command": chrome_launch_command(),
        },
        "profile": {
            "path": str(PROFILE_PATH),
            "exists": PROFILE_PATH.exists(),
            "values": profile,
        },
        "vscode": {
            "settings": str(vscode_settings),
            "exists": vscode_settings.exists(),
        },
        "workspace": {
            "root": str(PROJECT_ROOT),
            "papers": str(PROJECT_ROOT / "papers"),
            "assets": str(PROJECT_ROOT / "assets"),
            "raw": str(PROJECT_ROOT / ".raw"),
        },
    }


def print_report(report):
    _print_header("geo-academic-reader v{} | Environment Diagnostic".format(report["version"]))
    _ok("OS: {}".format(report["os"]))
    python = report["python"]
    if python["ok"]:
        _ok("Python: {} ({})".format(python["version"], python["executable"]))
    else:
        _fail("Python {} is too old; require >= 3.9".format(python["version"]))

    _info("Environment: {}".format(report["package_manager"]["summary"]))

    _print_header("Python Dependencies")
    for package in report["packages"]["installed"]:
        _ok("{} installed".format(package))
    for package in report["packages"]["missing"]:
        _fail("{} missing".format(package))
    if report["packages"]["missing"]:
        _info("Run: python3 doctor.py --install")

    for package in report["optional_packages"]["installed"]:
        _ok("Optional: {} installed".format(package))
    for package in report["optional_packages"]["missing"]:
        _warn("Optional: {} missing (PDF fallback will use embedded images)".format(package))

    _print_header("Chrome / Browser-first Extraction")
    chrome = report["chrome"]
    if chrome["executable"]:
        _ok("Chrome executable: {}".format(chrome["executable"]))
    else:
        _warn("Chrome/Chromium/Edge not found; browser-first figures unavailable.")
    if chrome["cdp_running"]:
        _ok("CDP 9222 active: {}".format(chrome["browser"]))
    else:
        _warn("CDP 9222 not running. Start it with:")
        print("   {}".format(chrome["launch_command"]))
        _info("Or let the pipeline launch it: python3 main.py --doi ... --browser auto")

    _print_header("Workspace Profile & VS Code")
    profile = report["profile"]
    if profile["exists"]:
        values = profile["values"]
        _ok("Profile: {}".format(profile["path"]))
        _info("style={style} | language={language} | browser={browser} | depth={depth}".format(
            style=values.get("style"), language=values.get("language"),
            browser=values.get("browser"), depth=values.get("note_depth")
        ))
    else:
        _warn("No profile yet. Run: python3 main.py --setup")
    if report["vscode"]["exists"]:
        _ok("VS Code settings: {}".format(report["vscode"]["settings"]))
    else:
        _warn("Missing .vscode/settings.json; Markdown preview may not be tuned.")

    _print_header("Workspace Directories")
    for name in ("root", "papers", "assets", "raw"):
        _info("{}: {}".format(name, report["workspace"][name]))

    _print_header("Next Steps")
    print("  1. python3 main.py --setup")
    print("  2. python3 main.py --doi \"10.1038/s41467-026-69772-8\"")
    print("  3. Agent writes papers/<slug>.md from .raw/<slug>/")
    print("  4. python3 main.py --check-note papers/<slug>.md --fix")
    print("  5. python3 main.py --index papers/<slug>.md")
    if report["packages"]["missing"] and not report["python"]["ok"]:
        print("\n{}Diagnostic completed with blocking issues.{}".format(RED, RESET))
    else:
        print("\n{}Diagnostic completed.{}".format(GREEN, RESET))


def main(argv=None):
    parser = argparse.ArgumentParser(description="geo-academic-reader environment doctor")
    parser.add_argument("--install", "--setup", action="store_true", dest="install", help="Install missing packages")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--launch-chrome", action="store_true", help="Launch Chrome with CDP 9222")
    args = parser.parse_args(argv)

    report = build_report(args)
    if args.install:
        auto_install(report["packages"]["missing"], report["package_manager"])
        report = build_report(args)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)

    blocking = bool(report["packages"]["missing"]) or not report["python"]["ok"]
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
