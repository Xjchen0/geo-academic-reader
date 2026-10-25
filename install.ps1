# geo-academic-reader: Fast Windows PowerShell Installer
# Version: 0.5.1 (MIT License)

$ErrorActionPreference = "Stop"

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "  geo-academic-reader Installer (Windows)" -ForegroundColor Cyan
Write-Host "  Version: 0.5.1 (MIT License)" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan

# Force UTF-8 for console output
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

function Get-StoreStubInfo {
    <#
      A fresh Windows install resolves python / python3 to the Microsoft Store
      alias: a zero-byte reparse point that exits with code 49 and prints
      nothing. Return its path when one is found.
    #>
    $storeRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
    foreach ($name in @("python3", "python")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -and $cmd.Source.StartsWith($storeRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $cmd.Source
        }
    }
    return $null
}

# uv owns the project environment: it creates .venv/, resolves the
# dependencies from pyproject.toml and installs the project itself.
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCmd) {
    Write-Host "[*] 'uv' detected - creating the project environment." -ForegroundColor Green
    & $uvCmd.Source sync
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Environment ready in .venv/" -ForegroundColor Green
        Write-Host "     Run the workspace with: uv run python main.py --preflight"
        & $uvCmd.Source run python doctor.py
        exit 0
    }
    Write-Host "[!] 'uv sync' failed; falling back to a system Python." -ForegroundColor Yellow
}

$stub = Get-StoreStubInfo
if ($stub) {
    Write-Host "[FAIL] Python on PATH is the Microsoft Store alias stub:" -ForegroundColor Red
    Write-Host "       $stub" -ForegroundColor Red
    Write-Host "       It exits with code 49 and prints nothing - there is no real Python." -ForegroundColor Yellow
    Write-Host "       Fix: install Python from python.org and tick 'Add Python to PATH'," -ForegroundColor Yellow
    Write-Host "            or install 'uv' and re-run this script." -ForegroundColor Yellow
    exit 1
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Host "[FAIL] Python 3.9+ was not found in PATH." -ForegroundColor Red
    Write-Host "       Please install Python from python.org and enable 'Add to PATH'." -ForegroundColor Yellow
    exit 1
}

& $pythonCmd.Source install.py $args
