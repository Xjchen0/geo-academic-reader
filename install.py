#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo-academic-reader: One-Click Cross-Platform Installer & Setup Wizard
Version: 0.0.1-pre
Works seamlessly on Windows, macOS, and Linux.
"""

import sys
import os
import shutil
import subprocess
import platform
from pathlib import Path

def print_banner():
    print(r"""
===================================================================
    🌍 geo-academic-reader | Setup & Deployment Wizard
                 Version: 0.0.1-pre (MIT License)
===================================================================
    """)

def run_command(cmd, desc):
    print(f"[*] {desc}...")
    try:
        ret = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print(f"    [✓] Success.")
        return True, ret.stdout
    except subprocess.CalledProcessError as e:
        print(f"    [✗] Error: {e.stderr or e.stdout or str(e)}")
        return False, e.stderr

def main():
    print_banner()
    pkg_dir = Path(__file__).parent.resolve()
    os.chdir(pkg_dir)

    print(f"System: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})\n")

    # 1. Package manager detection
    has_uv = bool(shutil.which("uv"))
    has_conda = "CONDA_PREFIX" in os.environ or bool(shutil.which("conda"))
    in_venv = (sys.prefix != sys.base_prefix)

    print("[*] Detecting Python environment...")
    if "CONDA_PREFIX" in os.environ:
        print(f"    Active Conda environment: {os.environ.get('CONDA_DEFAULT_ENV', 'unknown')}")
    elif in_venv:
        print("    Active virtual environment (venv) detected.")
    elif has_uv:
        print("    Fast package manager 'uv' detected.")
    else:
        print("    System / Global Python detected.")

    # 2. Dependency installation
    req_file = pkg_dir / "requirements.txt"
    if req_file.exists():
        if has_uv:
            install_cmd = ["uv", "pip", "install", "-r", str(req_file)]
        else:
            install_cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        
        ok, _ = run_command(install_cmd, "Installing required dependencies")
        if not ok:
            print("\n[!] Retrying with user install flag...")
            run_command([sys.executable, "-m", "pip", "install", "--user", "-r", str(req_file)], "Installing dependencies (--user)")

    # 3. CLI Command Registration (Optional editable install)
    print("\n[*] Registering 'geo-reader' command line tool...")
    cli_ok, _ = run_command([sys.executable, "-m", "pip", "install", "-e", "."], "Registering 'geo-reader' console script")
    if cli_ok:
        print("    [✓] 'geo-reader' and 'geo-doctor' are now available directly in your terminal!")
    else:
        print("    [i] You can still run directly via: python scripts/run_pipeline.py")

    # 4. Run environment diagnostic & first-time wizard
    print("\n" + "="*65)
    print(" Running Environment Diagnostics & First-Time Guidance...")
    print("="*65)
    doctor_script = pkg_dir / "doctor.py"
    if doctor_script.exists():
        subprocess.run([sys.executable, str(doctor_script)])

    print("\n🎉 Deployment completed! Quick test:")
    print("   geo-reader --doi \"10.1126/science.adz2675\" --output ./output")
    print("   (or: python scripts/run_pipeline.py --doi \"10.1126/science.adz2675\")\n")

if __name__ == "__main__":
    main()
