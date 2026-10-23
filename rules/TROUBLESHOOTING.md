# Troubleshooting & Error Recovery

This document provides error diagnosis, fallback procedures, and quick fixes.

---

## Common Error Codes & Handling

| Symptom / Error | Cause | Recommended Solution |
|:---|:---|:---|
| **404 Not Found (Crossref)** | DOI is newly minted, preprint, or not yet indexed by Crossref. | 1. Use the direct web URL via `--url` instead of `--doi`.<br>2. Or download the paper PDF and use `--pdf`. |
| **403 Forbidden on Figures** | Publisher CDN blocks headless curl or non-browser HTTP clients. | 1. Ensure Chrome CDP is active (`python doctor.py`).<br>2. The script will automatically fetch image data within the active browser session. |
| **NotOpenSSLWarning / SSL Error** | Legacy system python on macOS (`LibreSSL 2.8.3`). | Install and run inside a fresh virtual environment or conda: `uv pip install requests` or `conda install requests`. |
| **UnicodeDecodeError on Windows** | Windows terminal defaulting to GBK (CP936) encoding. | Set environment variable `PYTHONUTF8=1` in PowerShell before running, or pass `--utf8`. All pipeline scripts enforce `utf-8` file I/O. |
| **Images Not Rendering in VS Code** | Broken relative paths or markdown preview cache. | 1. Ensure the generated `.md` file and `assets/` folder maintain their relative layout.<br>2. In VS Code, run `Ctrl+Shift+P` -> `Markdown: Refresh Preview`. |

---

## Diagnostic Checklist

Whenever unexpected behavior occurs, run:
```bash
python doctor.py
```
This inspects OS capabilities, available package managers, dependencies, and Chrome port 9222 status.
