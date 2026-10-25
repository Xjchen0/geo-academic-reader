#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo-academic-reader: One-Click Cross-Platform Uninstaller & Environment Cleaner
Version: 0.6.0 (MIT License)
Safely removes installed packages, entry point binaries, build artifacts, and caches.
"""

import sys
import os
import shutil
import subprocess
import argparse
from pathlib import Path

def print_banner():
    print(r"""
===================================================================
    geo-academic-reader | Uninstaller & Environment Cleaner
                 Version: 0.6.0 (MIT License)
===================================================================
    """)

def run_command(cmd, desc):
    print(f"[*] {desc}...")
    try:
        ret = subprocess.run(
            cmd, check=True, text=True, encoding="utf-8", errors="replace",
            capture_output=True,
        )
        print(f"    [OK] Success.")
        return True, ret.stdout
    except subprocess.CalledProcessError as e:
        # If not installed or already removed, treat gracefully
        print(f"    [i] Notice: {e.stderr.strip() or e.stdout.strip() or 'Already clean.'}")
        return False, e.stderr

def clean_build_artifacts(pkg_dir: Path):
    """Clean egg-info, build, dist, and __pycache__ folders."""
    print("[*] Cleaning build artifacts and bytecode caches...")
    count = 0
    # 1. Egg-info and build dirs
    for p in pkg_dir.glob("*.egg-info"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            print(f"    Removed: {p.name}")
            count += 1
    
    for d in ["build", ".pytest_cache"]:
        target = pkg_dir / d
        if target.exists() and target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            print(f"    Removed: {d}/")
            count += 1

    # 2. __pycache__
    for p in pkg_dir.rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            count += 1

    print(f"    [OK] Cleaned {count} cache / build artifact(s).")

def main():
    try:
        from scripts.console import configure_stdio

        configure_stdio()
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        description="Clean uninstall for geo-academic-reader and environment cleanup."
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompts and proceed automatically."
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Also uninstall dependencies (requests, beautifulsoup4, pypdf, websockets, pymupdf) and delete local .venv if present."
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Only clean local build caches and __pycache__ without uninstalling packages."
    )

    args = parser.parse_args()
    print_banner()

    pkg_dir = Path(__file__).parent.resolve()
    os.chdir(pkg_dir)

    # Clean local caches
    clean_build_artifacts(pkg_dir)

    if args.clean_only:
        print("\nCache cleanup complete.")
        return

    # Check package managers
    has_uv = bool(shutil.which("uv"))

    print("\n[*] Target package for uninstallation:")
    print("    - geo-academic-reader (CLI tools: geo-reader, geo-doctor)")
    if args.purge:
        print("    - Dependencies: beautifulsoup4, pypdf, websockets, pymupdf")
        print("    - Local virtualenv: .venv/ (if exists)")

    if not args.yes:
        try:
            confirm = input("\nAre you sure you want to proceed with uninstallation? [y/N]: ").strip().lower()
            if confirm not in ["y", "yes"]:
                print("[-] Uninstallation cancelled.")
                return
        except (KeyboardInterrupt, EOFError):
            print("\n[-] Cancelled by user.")
            return

    # 1. Uninstall the main package
    if has_uv:
        uninstall_cmd = ["uv", "pip", "uninstall", "-y", "geo-academic-reader"]
    else:
        uninstall_cmd = [sys.executable, "-m", "pip", "uninstall", "-y", "geo-academic-reader"]
    
    run_command(uninstall_cmd, "Uninstalling 'geo-academic-reader' package & CLI tools")

    # 2. If purge is requested, remove dependencies
    if args.purge:
        deps = ["beautifulsoup4", "pypdf", "websockets", "pymupdf"]
        print("\n[*] Purging dependencies...")
        for dep in deps:
            if has_uv:
                dep_cmd = ["uv", "pip", "uninstall", "-y", dep]
            else:
                dep_cmd = [sys.executable, "-m", "pip", "uninstall", "-y", dep]
            run_command(dep_cmd, f"Uninstalling dependency '{dep}'")

        # Check local .venv
        venv_dir = pkg_dir / ".venv"
        if venv_dir.exists() and venv_dir.is_dir():
            print(f"[*] Removing local virtual environment: {venv_dir}...")
            shutil.rmtree(venv_dir, ignore_errors=True)
            print("    [OK] Removed .venv directory.")

    print("\n" + "="*65)
    print("Uninstallation and environment cleanup completed successfully!")
    print("="*65 + "\n")

if __name__ == "__main__":
    main()
