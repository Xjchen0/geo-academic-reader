#!/usr/bin/env bash
# geo-academic-reader: Fast Unix / macOS / Linux Uninstaller
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python is not found."
    exit 1
fi

$PYTHON_CMD uninstall.py "$@"
