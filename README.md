# geo-academic-reader 🌍

[![Version](https://img.shields.io/badge/version-0.0.1--pre-blue.svg)](https://github.com/Xjchen0/geo-academic-reader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> **An AI Agent-first academic literature workspace template.** Designed for Earth Sciences, Geophysics, Geology, and general science. Clone or download this project folder, open it in VS Code with your favorite AI Agent (Cursor, Claude Code, Antigravity, Windsurf, Copilot), and let the agent organize, parse, and archive scientific publications into rich-media Markdown notes.

[English](README.md) | [简体中文](README.zh-CN.md)

---

## 🤖 AI Agent-First Architecture

This workspace is specifically designed for **AI Agents + VS Code pair research**:

- 🧠 **Pre-configured `AGENTS.md`**: Built-in instructions recognized by Antigravity, Cursor, Claude Code, Windsurf, and Copilot. The agent immediately knows how to parse papers, enforce KaTeX math rules, extract figures, and maintain catalogs.
- 📥 **`input_pdfs/` Drop-Zone**: Drop raw scientific papers here. Tell your agent: *"Summarize all PDFs in `input_pdfs/`"*.
- 📚 **`papers/` & `papers/INDEX.md` Knowledge Base**: Every analyzed paper generates a structured Markdown review in `papers/` and automatically logs a catalog entry in `papers/INDEX.md`.
- 🖼️ **`assets/` Figure Storage**: High-resolution figures are downloaded, locally saved, and linked via relative paths.
- ⚙️ **`.vscode/` Native Preview Ready**: Bundles settings that enable native KaTeX math (`$...$` and `$$...$$`), GFM callout alerts (`> [!NOTE]`), and word wrapping. **Zero Node.js / npm dependencies!**

---

## 📁 Workspace Directory Structure

```text
geo-academic-reader/                    # Project workspace root
├── AGENTS.md                           # AI Agent workspace guide & operational rules
├── .vscode/                            # VS Code workspace settings & recommended extensions
│   ├── settings.json                   # Native KaTeX, typographer & preview rules
│   └── extensions.json                 # Markdown extensions
├── input_pdfs/                         # Drop-zone for raw PDF papers
│   └── README.md
├── papers/                             # Your personal literature knowledge base
│   └── INDEX.md                        # Master literature catalog & archive index
├── assets/                             # Categorized high-resolution figure assets
├── main.py                             # Unified workspace CLI & interactive runner
├── doctor.py                           # Cross-platform environment diagnostic tool
├── install.py / install.sh / .ps1      # One-click environment installers
├── uninstall.py / uninstall.sh / .ps1  # One-click environment cleaners
├── rules/                              # Modular scraper, KaTeX & troubleshooting rules
│   ├── JOURNALS.md                     # 15+ journal scraping & high-res figure CDN rules
│   ├── MARKDOWN_SPEC.md                # VS Code GFM & KaTeX layout rules
│   └── TROUBLESHOOTING.md              # Troubleshooting & recovery guide
├── LESSONS.md                          # Token budgeting & long paper context management
├── requirements.txt                    # Lightweight Python dependencies
├── SKILL.md                            # Agent Skill definition (for skill-based runtimes)
└── scripts/                            # Core engine scripts
```

---

## 🚀 Quick Start (Human & Agent)

### 1. Initialize Workspace Environment

```bash
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader

# Run one-click setup (macOS / Linux):
./install.sh
# (Windows PowerShell: .\install.ps1, or: python install.py)
```

---

### 2. Working in the Workspace

You can operate this workspace either via **AI Agent Prompts** or via **Terminal CLI**:

#### 💬 Method A: Talk to your AI Agent (Cursor / Claude Code / Antigravity)
Open this folder in your AI IDE (`code .`), and chat naturally:
- *"Read paper DOI `10.1126/science.adz2675` and generate an in-depth review into `papers/`."*
- *"Parse the PDF file in `input_pdfs/` and extract all figures."*
- *"Check our `papers/INDEX.md` and summarize what we have reviewed so far."*

#### 💻 Method B: Command Line (CLI & Interactive Menu)
```bash
# 1. Interactive terminal menu:
python main.py

# 2. Parse by DOI:
python main.py --doi "10.1126/science.adz2675"

# 3. Parse by direct URL:
python main.py --url "https://www.nature.com/articles/s41586-026-10999-2"

# 4. Batch parse all PDFs in input_pdfs/:
python main.py --batch-pdfs

# 5. Parse a specific local PDF:
python main.py --pdf "input_pdfs/my_paper.pdf"
```

---

### 3. Reading in VS Code

1. Open any generated note: `code papers/<paper_name>.md`
2. Open Markdown Preview:
   - **Windows / Linux**: `Ctrl + Shift + V` (or `Ctrl + K` then `V`)
   - **macOS**: `Cmd + Shift + V` (or `Cmd + K` then `V`)
3. Enjoy sharp KaTeX equations, high-res figures, and GFM alerts!

---

## 🧹 Clean Up & Uninstallation

```bash
# Quick uninstall (removes package & cleans build caches):
python uninstall.py

# Complete purge (removes package, dependencies, and local .venv):
python uninstall.py --purge --yes
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
