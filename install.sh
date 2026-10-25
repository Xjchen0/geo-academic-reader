#!/usr/bin/env bash
# geo-academic-reader: Fast Unix / macOS / Linux Installer
set -e

echo "==================================================================="
echo "  geo-academic-reader Installer (macOS / Linux)"
echo "  Version: 0.6.0 (MIT License)"
echo "==================================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# uv owns the project environment when it is available: it creates .venv/,
# resolves the dependencies from pyproject.toml and installs the project.
if command -v uv &>/dev/null; then
    echo "[*] 'uv' detected - creating the project environment."
    if uv sync; then
        echo "[OK] Environment ready in .venv/"
        echo "     Run the workspace with: uv run python main.py --preflight"
        uv run python doctor.py
        exit 0
    fi
    echo "[!] 'uv sync' failed; falling back to a system Python."
fi

# Check Python
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[FAIL] Error: Python 3.9+ is required but not found in PATH."
    exit 1
fi

echo "[*] Using Python: $($PYTHON_CMD --version)"

# Run Python installer
$PYTHON_CMD install.py "$@"
