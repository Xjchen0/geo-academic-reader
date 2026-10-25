#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-click installer for geo-academic-reader v0.6.0."""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

from scripts.console import FAIL, OK, configure_stdio
from scripts.environment import detect_environment
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
        result = subprocess.run(
            command, check=True, text=True, encoding="utf-8", errors="replace",
            capture_output=True,
        )
        print("    [{}] Success.".format(OK))
        return True, result.stdout
    except subprocess.CalledProcessError as exc:
        print("    [{}] Error: {}".format(FAIL, exc.stderr or exc.stdout or str(exc)))
        return False, exc.stderr
    except FileNotFoundError as exc:
        print("    [{}] Error: {}".format(FAIL, exc))
        return False, str(exc)


def main(argv=None):
    configure_stdio()
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

    # The same ordered scan the agent uses in conversation: uv -> conda ->
    # venv -> plain Python. Installing into the environment the user already
    # has is friendlier than building a second one.
    environment = detect_environment()
    recommended = environment.get("recommended", {}) or {}
    kind = recommended.get("kind", "python")
    print("[*] Environment scan (uv -> conda -> venv -> system Python):")
    for candidate in environment.get("candidates", []):
        mark = "available" if candidate.get("available") else "not found"
        if candidate.get("active"):
            mark += " / active"
        print("    - {:<8} {:<20} {}".format(
            candidate.get("kind", "?"), mark, candidate.get("detail", "")
        ).rstrip())
    print("    Using: {} ({})".format(kind, recommended.get("reason", "")))
    print()

    requirements = package_dir / "requirements.txt"
    pyproject = package_dir / "pyproject.toml"
    used_uv = False

    if kind == "uv" and pyproject.exists():
        # uv owns the project environment: it creates .venv/, resolves the
        # dependencies declared in pyproject.toml and installs the package
        # itself, so `uv run python main.py ...` works out of the box.
        print("    Using 'uv sync' to create .venv/ and install the project.")
        ok, _ = run_command(["uv", "sync"], "Creating the uv environment and installing dependencies")
        used_uv = ok
        if not ok:
            print("\n[!] uv sync failed, falling back to pip ...")

    if not used_uv and requirements.exists():
        command = [sys.executable, "-m", "pip", "install", "-r", str(requirements)]
        ok, _ = run_command(command, "Installing core dependencies")
        if not ok:
            print("\n[!] Retrying with --user ...")
            run_command([sys.executable, "-m", "pip", "install", "--user", "-r", str(requirements)],
                        "Installing core dependencies (--user)")

    if args.with_pdf_figures:
        if used_uv:
            command = ["uv", "pip", "install", "pymupdf>=1.23"]
        else:
            command = [sys.executable, "-m", "pip", "install", "pymupdf>=1.23"]
        run_command(command, "Installing optional PyMuPDF")

    if used_uv:
        print("\n[*] The project is installed in .venv/ (uv).")
        print("    Run everything through: uv run python main.py ...")
    else:
        print("\n[*] Registering CLI tools (geo-reader, geo-doctor)...")
        editable_command = [sys.executable, "-m", "pip", "install", "-e", "."]
        ok, _ = run_command(editable_command, "Editable install")
        if ok:
            print("    [{}] CLI tools registered.".format(OK))
        else:
            print("    [i] You can still run: python3 main.py ...")

    if not args.skip_doctor:
        print("\n" + "=" * 65)
        print(" Running environment diagnostics...")
        print("=" * 65)
        doctor_python = ["uv", "run", "python"] if used_uv else [sys.executable]
        subprocess.run(doctor_python + [str(package_dir / "doctor.py")])

    runner = "uv run python main.py" if used_uv else recommended.get(
        "run_command", "python3 main.py"
    )
    if used_uv:
        runner = "uv run python main.py"
    print("\nInstallation complete. Next steps:")
    print("  1. Open this folder in your agent and say: 开始使用 (or Start)")
    print("  2. {} --doi \"10.1038/s41467-026-69772-8\"".format(runner))
    print("  3. Ask your agent to write papers/<slug>.md from .raw/<slug>/")
    print("  4. {} --check-note papers/<slug>.md --fix".format(runner))
    print("  5. {} --index papers/<slug>.md\n".format(runner))


if __name__ == "__main__":
    main()
