# geo-academic-reader: Fast Windows PowerShell Installer
# Version: 0.2.1 (MIT License)

$ErrorActionPreference = "Stop"

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "  🌍 geo-academic-reader Installer (Windows)" -ForegroundColor Cyan
Write-Host "  Version: 0.2.1 (MIT License)" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan

# Force UTF-8 for console output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Host "❌ Error: Python 3.9+ was not found in PATH." -ForegroundColor Red
    Write-Host "   Please install Python from python.org or Microsoft Store and enable 'Add to PATH'." -ForegroundColor Yellow
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

& $pythonCmd.Source install.py $args
