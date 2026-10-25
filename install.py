#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-click installer for geo-academic-reader v0.5.0."""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.version import __version__


def print_banner():
    print(r"""
===================================================================
    geo-academic-reader | Setup Wizard
                 Version: {version} (MIT License)
===================================================================
    """.format(version=__version__))


def run_command(command, description):
    print("[*] {}...".format(description))
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print("    [✓] Success.")
        return True, result.stdout
    except subprocess.CalledProcessError as exc:
        print("    [✗] Error: {}".format(exc.stderr or exc.stdout or str(exc)))
        return False, exc.stderr


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install geo-academic-reader")
    parser.add_argument("--with-pdf-figures", action="store_true",
                        help="Also install PyMuPDF for caption-aware PDF figure cropping")
    parser.add_argument("--skip-doctor", action="store_true", help="Skip the environment diagnostic")
    args = parser.parse_args(argv)

    print_banner()
    package_dir = Path(__file__).resolve().parent
    os.chdir(package_dir)

    print("System: {} {} ({})".format(platform.system(), platform.release(), platform.machine()))
    print("Python: {} ({})\n".format(sys.version.split()[0], sys.executable))

    has_uv = bool(shutil.which("uv"))
    print("[*] Detecting Python environment...")
    if "CONDA_PREFIX" in os.environ:
        print("    Active Conda environment: {}".format(os.environ.get("CONDA_DEFAULT_ENV", "unknown")))
    elif sys.prefix != sys.base_prefix:
        print("    Active virtual environment (venv) detected.")
    elif has_uv:
        print("    Fast package manager 'uv' detected.")
    else:
        print("    System / Global Python detected.")

    requirements = package_dir / "requirements.txt"
    if requirements.exists():
        command = (["uv", "pip", "install", "-r", str(requirements)]
                   if has_uv else [sys.executable, "-m", "pip", "install", "-r", str(requirements)])
        ok, _ = run_command(command, "Installing core dependencies")
        if not ok:
            print("\n[!] Retrying with --user ...")
            run_command([sys.executable, "-m", "pip", "install", "--user", "-r", str(requirements)],
                        "Installing core dependencies (--user)")

    if args.with_pdf_figures:
        command = (["uv", "pip", "install", "pymupdf>=1.23"]
                   if has_uv else [sys.executable, "-m", "pip", "install", "pymupdf>=1.23"])
        run_command(command, "Installing optional PyMuPDF")

    print("\n[*] Registering CLI tools (geo-reader, geo-doctor)...")
    if has_uv:
        editable_command = ["uv", "pip", "install", "-e", "."]
    else:
        editable_command = [sys.executable, "-m", "pip", "install", "-e", "."]
    ok, _ = run_command(editable_command, "Editable install")
    if ok:
        print("    [✓] CLI tools registered.")
    else:
        print("    [i] You can still run: python3 main.py ...")

    if not args.skip_doctor:
        print("\n" + "=" * 65)
        print(" Running environment diagnostics...")
        print("=" * 65)
        subprocess.run([sys.executable, str(package_dir / "doctor.py")])

    print("\nInstallation complete. Next steps:")
    print("  1. Open this folder in your agent and say: 开始使用 (or Start)")
    print("  2. python3 main.py --doi \"10.1038/s41467-026-69772-8\"")
    print("  3. Ask your agent to write papers/<slug>.md from .raw/<slug>/")
    print("  4. python3 main.py --check-note papers/<slug>.md --fix")
    print("  5. python3 main.py --index papers/<slug>.md\n")


if __name__ == "__main__":
    main()
