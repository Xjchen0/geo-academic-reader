#!/usr/bin/env bash
# geo-academic-reader: Fast Unix / macOS / Linux Installer
set -e

echo "==================================================================="
echo "  🌍 geo-academic-reader Installer (macOS / Linux)"
echo "  Version: 0.4.0-pre (MIT License)"
echo "==================================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python 3.9+ is required but not found in PATH."
    exit 1
fi

echo "[*] Using Python: $($PYTHON_CMD --version)"

# Run Python installer
$PYTHON_CMD install.py "$@"
