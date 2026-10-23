# geo-academic-reader 🌍

[![Version](https://img.shields.io/badge/version-0.0.1--pre-blue.svg)](https://github.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> Transform scientific research publications into rich-media, publication-grade Markdown documents optimized for **VS Code Native Markdown Preview**. Designed for Earth Sciences, Geophysics, Geology, and general science.

[English](README.md) | [简体中文](README.zh-CN.md)

---

## ✨ Features

- 🎯 **VS Code Native Experience**:
  - Delivers mathematical equations in standard KaTeX syntax (`$...$` and `$$...$$`), rendered natively by VS Code.
  - **Zero Node.js or npm dependencies** required!
  - GitHub-Flavored Markdown (GFM) callout alerts (`> [!NOTE]`, `> [!IMPORTANT]`, `> [!WARNING]`).
- 🖼️ **High-Resolution Asset Management**:
  - Automatically fetches and rewrites high-resolution figure URLs from publisher CDNs (Nature, Science, AGU, Wiley, bioRxiv).
  - Organizes figures into local relative paths (`./assets/<paper_slug>/fig_N.png`).
- ⚖️ **Academic Objectivity & Anti-Hyperbole**:
  - Eliminates sensationalist marketing jargon; enforces objective presentation of physical models, parameter sensitivities, and experimental limitations.
  - Automatically queries Crossref for official APA references and DOI links.
- 🩺 **Intelligent Environment Doctor**:
  - Built-in `doctor.py` detects Windows, macOS, and Linux.
  - Seamlessly adapts to **Conda**, **uv**, **pip**, or Python virtual environments (`venv`).
- ⚡ **One-Click Agent & CLI Deployment**:
  - Can be invoked as an AI Agent Skill (Antigravity, Claude, VoltAgent, Cursor) or directly via the terminal command `geo-reader`.

---

## 🚀 Fast Installation & First-Time Setup

### Option 1: One-Click Installer (Recommended)

Clone the repository and run the setup wizard:

```bash
git clone https://github.com/your-username/geo-academic-reader.git
cd geo-academic-reader

# On macOS / Linux:
./install.sh
# (or: python3 install.py)

# On Windows (PowerShell):
.\install.ps1
# (or: python install.py)
```

The installer will:
1. Detect your active Python environment (Conda, uv, or venv).
2. Install minimal dependencies (`requests`, `beautifulsoup4`, `pypdf`, `websockets`).
3. Register the `geo-reader` and `geo-doctor` commands on your PATH.
4. Run the diagnostic wizard.

---

### Option 2: Manual Install

```bash
# If using uv (fastest):
uv pip install -r requirements.txt
uv pip install -e .

# If using Conda:
conda activate your_env
pip install -r requirements.txt
pip install -e .

# If using standard venv:
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

---

## 🧹 Uninstallation & Environment Cleanup

When you need to remove the tool or completely clean up the environment:

```bash
# 1. Quick uninstall (removes package, CLI binaries, build artifacts & caches):
python uninstall.py
# (or: ./uninstall.sh on macOS/Linux, .\uninstall.ps1 on Windows)

# 2. Complete purge (removes package, dependencies, and local .venv):
python uninstall.py --purge --yes

# 3. Clean only local build/bytecode caches without uninstalling:
python uninstall.py --clean-only
```

---

## 📖 Usage

### Command Line Interface (CLI)

```bash
# 1. Parse via DOI (Nature, Science, AGU, Wiley, etc.)
geo-reader --doi "10.1126/science.adz2675" --output ./output

# 2. Parse via direct Paper URL
geo-reader --url "https://www.nature.com/articles/s41586-026-10999-2" --output ./output

# 3. Parse via local PDF file
geo-reader --pdf "/path/to/paper.pdf" --output ./output

# 4. Run environment diagnostics
geo-doctor
```

Output directory layout:
```text
output/
├── Science_10.1126_science.adz2675.md    # Beautifully rendered Markdown article
└── assets/
    └── Science_10.1126_science.adz2675/  # Extracted high-resolution figures
        ├── fig_1.png
        └── fig_2.png
```

---

### 🔍 Viewing in VS Code

1. Open the generated Markdown file in VS Code:
   ```bash
   code ./output/<filename>.md
   ```
2. Open the Markdown Preview:
   - **Windows / Linux**: `Ctrl + Shift + V` (or `Ctrl + K` then `V` for side-by-side)
   - **macOS**: `Cmd + Shift + V` (or `Cmd + K` then `V` for side-by-side)
3. Enjoy sharp KaTeX mathematical formulas, embedded local figures, and styled GFM alerts!

---

## 🤖 Using as an AI Agent Skill

Copy or link `geo-academic-reader` into your agent's skills directory:
- **Antigravity / Cursor / Claude Code**: Add to `.agent/skills/geo-academic-reader` or `~/.gemini/antigravity/skills/geo-academic-reader`.
- The Agent will automatically detect `SKILL.md` and activate `geo-academic-reader` when asked to read papers, parse DOIs, or produce rich Markdown for VS Code.

---

## 🌐 Chrome DevTools Protocol (CDP) Mode (Optional)

- **When Chrome is NOT needed**:
  - Open Access papers (bioRxiv, medRxiv, arXiv, PMC);
  - Direct local PDF extraction.
- **When Chrome 9222 is recommended**:
  - Paywalled publisher pages with aggressive Cloudflare verification (Science, Nature paywall).
- **Starting Chrome with remote debugging**:
  Run `geo-doctor` in terminal; it will output the exact command tailored for your operating system.

---

## 📁 Repository Structure

```text
geo-academic-reader/
├── SKILL.md                 # Agent Skill definition & trigger guidelines
├── README.md                # English documentation
├── README.zh-CN.md          # 简体中文文档
├── LICENSE                  # MIT License
├── pyproject.toml           # Python packaging specification
├── setup.py                 # Legacy build script
├── requirements.txt         # Lightweight dependencies
├── doctor.py                # Multi-platform environment diagnostic tool
├── install.py               # Cross-platform installer
├── install.sh               # Unix/macOS one-click installer
├── install.ps1              # Windows PowerShell one-click installer
├── uninstall.py             # Cross-platform uninstaller & environment cleaner
├── uninstall.sh             # Unix/macOS one-click uninstaller
├── uninstall.ps1            # Windows PowerShell one-click uninstaller
├── geo-academic-reader.yaml # Sandbox network policy manifest
├── LESSONS.md               # Agent runtime lessons & token budgeting
├── rules/                   # Modular reference rules
│   ├── JOURNALS.md          # 15+ journal scraping & high-res figure rules
│   ├── MARKDOWN_SPEC.md     # VS Code GFM & KaTeX layout rules
│   └── TROUBLESHOOTING.md   # Troubleshooting & recovery guide
└── scripts/
    ├── config.py            # Global configuration & headers
    ├── fetch_paper.py       # Paper text and figure extractor
    ├── generate_markdown.py # VS Code Markdown synthesis engine
    └── run_pipeline.py      # Core CLI pipeline runner
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
