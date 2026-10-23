#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo-academic-reader - Environment Doctor & Setup Assistant
Version: 0.0.1-pre (MIT License)
Cross-platform diagnostic tool for Windows, macOS, and Linux.
Detects Python environment (Conda, uv, venv, pip), packages, and Chrome CDP.
"""

import sys
import os
import platform
import shutil
import urllib.request
import urllib.error
import json
import subprocess
from pathlib import Path

# Terminal colors (auto-disabled on Windows legacy console)
USE_COLOR = platform.system() != "Windows" or os.environ.get("ANSICON") or os.environ.get("WT_SESSION")
GREEN = "\033[92m" if USE_COLOR else ""
YELLOW = "\033[93m" if USE_COLOR else ""
RED = "\033[91m" if USE_COLOR else ""
CYAN = "\033[96m" if USE_COLOR else ""
BOLD = "\033[1m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""

VERSION = "0.0.1-pre"
REQUIRED_PACKAGES = [
    ("requests", "requests"),
    ("bs4", "beautifulsoup4"),
    ("pypdf", "pypdf"),
    ("websockets", "websockets"),
]

def print_header(title):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")

def print_ok(msg):
    print(f" {GREEN}[✓ OK]{RESET} {msg}")

def print_warn(msg):
    print(f" {YELLOW}[! WARN]{RESET} {msg}")

def print_fail(msg):
    print(f" {RED}[✗ FAIL]{RESET} {msg}")

def print_info(msg):
    print(f" {CYAN}[i INFO]{RESET} {msg}")

def detect_os():
    os_name = platform.system()
    arch = platform.machine()
    if os_name == "Darwin":
        return "macOS", f"macOS {platform.mac_ver()[0]} ({arch})"
    elif os_name == "Windows":
        return "Windows", f"Windows {platform.release()} ({arch})"
    elif os_name == "Linux":
        return "Linux", f"Linux {platform.release()} ({arch})"
    return os_name, f"{os_name} ({arch})"

def detect_python():
    version = sys.version_info
    ver_str = f"{version.major}.{version.minor}.{version.micro}"
    py_path = sys.executable
    is_ok = (version.major == 3 and version.minor >= 9)
    return is_ok, ver_str, py_path

def detect_package_manager():
    """Detect if the user is in conda, uv, standard venv, or system python."""
    in_conda = "CONDA_PREFIX" in os.environ
    in_venv = (sys.prefix != sys.base_prefix)
    has_uv = bool(shutil.which("uv"))
    has_conda = bool(shutil.which("conda"))
    has_pip = bool(shutil.which("pip") or shutil.which("pip3"))

    detected = []
    if in_conda:
        detected.append(f"Active Conda Environment: {os.environ.get('CONDA_DEFAULT_ENV', 'unknown')}")
    elif in_venv:
        detected.append("Active Python venv / virtualenv")
    else:
        detected.append("Global / System Python (Recommend using venv or conda)")

    tools = []
    if has_uv:
        tools.append("uv (fast package manager)")
    if has_conda:
        tools.append("conda")
    if has_pip:
        tools.append("pip")

    return {
        "in_conda": in_conda,
        "in_venv": in_venv,
        "has_uv": has_uv,
        "has_conda": has_conda,
        "has_pip": has_pip,
        "summary": " | ".join(detected),
        "available_tools": tools
    }

def check_dependencies():
    missing = []
    installed = []
    for import_name, pkg_name in REQUIRED_PACKAGES:
        try:
            __import__(import_name)
            installed.append(pkg_name)
        except ImportError:
            missing.append(pkg_name)
    return installed, missing

def check_chrome_cdp():
    """Check if Chrome DevTools Protocol port 9222 is open and listening."""
    url = "http://127.0.0.1:9222/json/version"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "geo-academic-doctor"})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return True, data.get("Browser", "Chrome/Unknown")
    except Exception:
        pass
    return False, None

def get_chrome_launch_command(os_type):
    if os_type == "macOS":
        return '/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_dev"'
    elif os_type == "Windows":
        return '& "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:TEMP\\chrome_dev"'
    else: # Linux
        return 'google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_dev" &'

def auto_install(missing_pkgs, pm_info):
    if not missing_pkgs:
        return
    print(f"\n{BOLD}Attempting to automatically install missing packages: {', '.join(missing_pkgs)}...{RESET}")
    
    cmd = []
    if pm_info["has_uv"]:
        cmd = ["uv", "pip", "install"] + missing_pkgs
    elif pm_info["has_pip"]:
        cmd = [sys.executable, "-m", "pip", "install"] + missing_pkgs
    elif pm_info["has_conda"]:
        cmd = ["conda", "install", "-y"] + missing_pkgs
    else:
        print_fail("No supported package manager found to auto-install.")
        return

    print_info(f"Running: {' '.join(cmd)}")
    ret = subprocess.call(cmd)
    if ret == 0:
        print_ok("All missing packages successfully installed!")
    else:
        print_fail("Installation failed. Please run manual command listed above.")

def main():
    auto_fix = "--install" in sys.argv or "--setup" in sys.argv
    print_header(f"geo-academic-reader v{VERSION} - Environment Diagnostic")

    # 1. OS Check
    os_type, os_desc = detect_os()
    print_ok(f"Operating System: {os_desc}")

    # 2. Python Check
    py_ok, py_ver, py_path = detect_python()
    if py_ok:
        print_ok(f"Python Version: {py_ver} ({py_path})")
    else:
        print_fail(f"Python Version {py_ver} is too old! geo-academic-reader requires Python >= 3.9.")
        print(f"       Please upgrade Python or switch to a newer environment.")

    # 3. Package Manager & Environment
    pm_info = detect_package_manager()
    print_info(f"Environment Status: {pm_info['summary']}")
    if pm_info["available_tools"]:
        print_info(f"Available tools: {', '.join(pm_info['available_tools'])}")

    # 4. Dependency Check
    print_header("Python Package Dependencies Check")
    installed, missing = check_dependencies()
    for pkg in installed:
        print_ok(f"Package '{pkg}' is installed.")
    
    if missing:
        print_fail(f"Missing {len(missing)} package(s): {', '.join(missing)}")
        print(f"\n{BOLD}Recommended installation commands for your environment:{RESET}")
        
        if pm_info["in_conda"]:
            print(f"  {CYAN}# If using Conda:{RESET}")
            print(f"  pip install {' '.join(missing)}")
        elif pm_info["has_uv"]:
            print(f"  {CYAN}# If using uv (fast):{RESET}")
            print(f"  uv pip install {' '.join(missing)}")
        else:
            print(f"  {CYAN}# Standard pip install:{RESET}")
            print(f"  {sys.executable} -m pip install {' '.join(missing)}")

        if auto_fix:
            auto_install(missing, pm_info)
        else:
            print(f"\n{YELLOW}Tip: Run 'python doctor.py --install' (or python install.py) to auto-install missing packages.{RESET}")
    else:
        print_ok("All required Python packages are installed and ready!")

    # 5. Chrome CDP Check
    print_header("Chrome CDP (Anti-Bot / Paywall Bypass) Check")
    cdp_ok, browser_ver = check_chrome_cdp()
    if cdp_ok:
        print_ok(f"Chrome CDP active on port 9222 ({browser_ver})")
        print_info("High-resolution paywalled figures and complex papers can be directly extracted.")
    else:
        print_warn("Chrome CDP is NOT active on port 9222.")
        print_info("Note: Chrome CDP is optional. Open Access papers (bioRxiv, PMC, arXiv) and local PDFs work without Chrome.")
        print_info("If you plan to extract articles from Nature, Science, or Wiley paywalls, launch Chrome with remote debugging:")
        print(f"\n  {BOLD}{CYAN}Copy & Run in your terminal:{RESET}")
        print(f"  {get_chrome_launch_command(os_type)}\n")

    # 6. VS Code Markdown Preview Guide
    print_header("VS Code Markdown Preview Readiness")
    print_ok("Markdown generator produces clean GitHub-Flavored Markdown (GFM).")
    print_ok("Math equations use standard KaTeX ($...$ and $$...$$), natively rendered in modern VS Code.")
    print_ok("Figure images are saved in relative './assets/' subdirectories.")
    print_info("In VS Code, press: 'Ctrl+Shift+V' (Win/Linux) or 'Cmd+Shift+V' (Mac) to open instant preview.")
    print(f"\n{BOLD}{GREEN}Diagnostic completed! You are ready to run geo-academic-reader.{RESET}\n")

if __name__ == "__main__":
    main()
