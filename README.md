# geo-academic-reader 🌍

[![Version](https://img.shields.io/badge/version-0.2.1-blue.svg)](https://github.com/Xjchen0/geo-academic-reader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> **A browser-first literature workspace for AI agents.** The scripts collect evidence; the agent writes the review; a built-in QA step catches broken figures and fabricated filler before you cite anything.

[English](README.md) | [简体中文](README.zh-CN.md)

---

## Why this exists

Two failure modes are common in "AI reads papers" workflows:

1. **The script writes the review.** A generic Markdown generator produces plausible-sounding paragraphs and sample equations that have nothing to do with the paper, so every note looks "deep" while saying very little.
2. **The PDF becomes the source of figures.** Embedded bitmaps are often low-resolution, split across pages, or missing captions — even when the publisher page has a clean, high-resolution figure.

Version 0.2.1 fixes both by separating responsibilities:

- **Scripts extract.** They produce an evidence pack with raw text, metadata, figure captions, figure provenance, and downloaded images. They never write a literature review.
- **Agents interpret.** The agent reads the evidence pack and writes `papers/<slug>.md` using `templates/paper_note.md`, with an evidence anchor for every important claim.
- **QA verifies.** `--check-note` checks image paths, empty or corrupt files, template leftovers, hyperbole, and unbalanced display math before delivery.

For a DOI, a web URL, or a PDF that contains a DOI, the pipeline tries **Chrome first** so the figures come from the rendered publisher page at the highest available resolution. PDF figures are a fallback, and the manifest records which path was used.

---

## Pipeline

```text
DOI / URL / PDF
      │
      ▼
Chrome DevTools Protocol (CDP 9222)  ──►  rendered page, high-res figure URLs
      │                                      (in-page fetch for CDN 403s)
      ▼
.raw/<slug>/paper.json
.raw/<slug>/fulltext.md
.raw/<slug>/figures/manifest.json
assets/<slug>/fig_01.png ...
      │
      ▼
Agent (AGENTS.md + templates/paper_note.md)
      │
      ▼
papers/<slug>.md  ──►  --check-note --fix  ──►  --index  ──►  papers/INDEX.md
```

---

## What is new in 0.2.1

- **Browser-first extraction.** `--browser auto` launches Chrome with a dedicated profile on port 9222, waits for JavaScript rendering, upgrades thumbnail URLs, and downloads images from the page context when direct HTTP is blocked.
- **Evidence packs instead of generated prose.** `main.py` writes only `.raw/<slug>/` and `assets/<slug>/`. It does not create `papers/<slug>.md`.
- **Note QA.** `--check-note --fix` repairs common image problems, including paths that preview fine on one machine but break after moving the workspace.
- **First-run onboarding.** `--setup` asks about language, IDE, agent style, browser policy, note depth, and citation format, then stores the answers in `.geo-reader/profile.json` for `AGENTS.md` to follow.
- **Packaging.** `scripts/` is now a real package, with `geo-reader`, `geo-doctor`, and `geo-setup` entry points.

---

## Requirements

- Python **3.9+**
- `requests`, `beautifulsoup4`, `pypdf`, `websockets` (installed by the setup script)
- **Google Chrome, Chromium, or Microsoft Edge** — strongly recommended for high-resolution figures and JavaScript-rendered pages
- Optional: `pymupdf` (`pip install -r requirements-optional.txt`) for better PDF figure cropping and caption matching

No Node.js, npm, or headless-browser download is required.

---

## Quick start

```bash
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader

# macOS / Linux
./install.sh

# Windows PowerShell
.\install.ps1

# Any platform, equivalent
python install.py
```

Then run the one-minute onboarding:

```bash
python3 main.py --setup
```

On Windows, use `python` if `python3` is not on `PATH`.

The wizard asks for:

| Choice | Options | Effect |
| :--- | :--- | :--- |
| Output language | `zh-CN`, `en`, `bilingual` | Language the agent uses for notes |
| Main environment | VS Code, Cursor, Claude Code, Antigravity, Windsurf, CLI | Recorded in the profile and welcome guide |
| Agent instruction style | `guided`, `balanced`, `expert` | How often the agent stops for confirmation |
| Browser policy | `auto`, `existing`, `off` | Whether to launch Chrome, reuse port 9222, or skip the browser |
| Note depth | `brief`, `standard`, `deep` | Length and figure-by-figure detail |
| Citation format | APA, Nature, GB/T 7714 | Preferred reference style |

Your answers are saved to `.geo-reader/profile.json`, and a local summary is written to `.geo-reader/WELCOME.md`. Both files are git-ignored. `AGENTS.md` tells the agent to read the profile at the start of every task. Re-run the wizard at any time with `--reconfigure`.

---

## Daily workflow

### 1. Extract an evidence pack

```bash
# DOI
python3 main.py --doi "10.1038/s41467-026-69772-8"

# Publisher page
python3 main.py --url "https://www.nature.com/articles/s41467-026-69772-8"

# Local PDF (uses its DOI to find the publisher page when possible)
python3 main.py --pdf "input_pdfs/my_paper.pdf"

# Every PDF in input_pdfs/
python3 main.py --batch-pdfs
```

Useful options:

```bash
--browser auto       # launch/reuse Chrome, browser first (default)
--browser existing   # only use an already-running Chrome on port 9222
--browser off        # no browser; HTTP/PDF only
--wait 6             # wait longer after page load
--max-figures 20     # cap downloaded figures
--json               # machine-readable summary
--quiet              # less progress output
```

The command prints the slug, evidence-pack paths, figure count, extraction method (for example `text=browser; figures=browser`), and any warnings.

### 2. Let the agent write the note

Tell your agent something like:

> Read the evidence pack in `.raw/<slug>/`, then write `papers/<slug>.md` using `templates/paper_note.md`. Use only the extracted text and manifest captions; do not invent formulas or conclusions. Link figures as `../assets/<slug>/fig_XX.png`. Finish with `--check-note --fix` and `--index`.

More ready-to-use prompts are in [PROMPTS.md](PROMPTS.md).

### 3. Validate and index

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"
python3 main.py --list
```

`--check-note` reports missing images, zero-byte files, files that are not valid images, paths outside `assets/`, non-standard relative paths, leftover placeholder text, hyperbolic wording, and unbalanced `$$` blocks. `--fix` repairs image paths when the target can be determined safely. Add `--strict` to treat warnings as errors.

### 4. Preview in VS Code

- macOS: `Cmd + Shift + V`
- Windows / Linux: `Ctrl + Shift + V`

The workspace's `.vscode/settings.json` enables native KaTeX and GFM alerts. No extension is required for math, although [`.vscode/extensions.json`](.vscode/extensions.json) recommends a few Markdown helpers.

---

## CLI reference

```text
python3 main.py --setup                 First-run onboarding
python3 main.py --reconfigure           Change preferences
python3 main.py --doi DOI               Extract by DOI
python3 main.py --url URL               Extract by article URL
python3 main.py --pdf PATH              Extract from a local PDF
python3 main.py --batch-pdfs            Process all PDFs in input_pdfs/
python3 main.py --check-note [NOTE]     Check one note, or all papers/*.md
python3 main.py --index NOTE            Add/update a row in papers/INDEX.md
python3 main.py --list                  List evidence packs and notes
python3 main.py --guide                 Print the quick-start guide
python3 main.py --doctor                Run environment diagnostics
python3 main.py                         Interactive menu (in a terminal)
```

With `pip install -e .`, the same commands are available as `geo-reader`, `geo-doctor`, and `geo-setup`.

---

## Workspace layout

```text
geo-academic-reader/
├── AGENTS.md                     Agent contract, SOP, and writing rules
├── PROMPTS.md                    Copy-paste prompts for common tasks
├── README.md / README.zh-CN.md
├── input_pdfs/                   Drop-zone for raw PDFs
├── papers/
│   ├── INDEX.md                  Human-facing literature index
│   └── <slug>.md                 Agent-written notes
├── assets/<slug>/fig_XX.png      Local figures referenced by notes
├── .raw/<slug>/                  Evidence packs (git-ignored)
│   ├── paper.json
│   ├── fulltext.md
│   ├── figures/manifest.json
│   └── README.md
├── .geo-reader/                  Local profile and Chrome profile (git-ignored)
├── templates/
│   ├── paper_note.md
│   └── literature_review.md
├── rules/                        Journal, Markdown, and troubleshooting references
├── scripts/                      Extraction, QA, onboarding, CLI
├── main.py                       Workspace entry point
├── doctor.py                     Environment diagnostics
├── install.py / install.sh / .ps1
└── uninstall.py / uninstall.sh / .ps1
```

### Evidence-pack contract

`paper.json` contains bibliographic metadata, the APA citation and its source, the extraction method, open-access information, warnings, statistics, and relative paths to the other files.

`fulltext.md` is raw extracted text with page markers when the source is a PDF. It is deliberately unpolished; it is evidence, not a summary.

`figures/manifest.json` is the single source of truth for figures:

| Field | Meaning |
| :--- | :--- |
| `id` | Stable identifier such as `fig_01` |
| `label` | Caption label such as `Figure 2` when detectable |
| `caption` | Caption text from the page or PDF |
| `file` | Local filename in `assets/<slug>/` |
| `local_path` | Workspace-relative path |
| `markdown_path` | Path to use in a note: `../assets/<slug>/fig_01.png` |
| `origin` / `download` | `browser`, `http`, or `pdf`, and how the bytes were obtained |
| `method` | Extraction method recorded per figure |
| `source_url` | Original image URL, when known |
| `page` | PDF page number, when applicable |
| `width`, `height`, `bytes` | Image dimensions and size |
| `is_body_figure` | Whether the image looked like article content rather than page chrome |

Treat the manifest as authoritative. If a caption is empty, the note should say so rather than inventing a title.

---

## Figures and VS Code troubleshooting

The most common cause of "the image does not show in VS Code preview" is a path that is valid for one file but not for another, for example `./assets/...` or `/Users/you/...` inside `papers/<slug>.md`. Notes live in `papers/`, so the correct link is:

```markdown
![Figure 1: caption](../assets/<slug>/fig_01.png)
```

Run:

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
```

This checks that the file exists, is non-empty, has valid image magic bytes, and resolves to `../assets/<slug>/...`. If an image is missing but exactly one file with the same name exists under `assets/`, `--fix` rewrites the link. It will not guess when multiple candidates exist.

Other checks:

- Confirm `assets/<slug>/fig_01.png` is a real image, not an HTML error page saved with a `.png` extension.
- In VS Code, run **Markdown: Refresh Preview** from the Command Palette if the preview is stale.
- Open the note from the workspace root so relative paths resolve consistently.

---

## Scope and limitations

- **Access, not circumvention.** Browser-first extraction uses the Chrome session available on your machine to render pages and fetch images that your session can already access. It does not bypass paywalls or access controls. Respect publisher terms and your institution's licences.
- **Cloudflare and bot challenges.** The pipeline waits and retries, but cannot always pass an interactive challenge. If a page is blocked, open it manually in the launched Chrome window, complete the challenge, then retry with `--browser existing`.
- **Not every figure is recoverable.** Some publishers load figures through proprietary viewers, deliver them only in supplementary archives, or label them in ways that defeat caption matching. The manifest warnings tell you what failed.
- **PDF fallback is a fallback.** With `pypdf`, embedded images may be low-resolution or lack captions. Install `pymupdf` for caption-aware cropping at higher resolution. Scanned PDFs without a text layer are not OCR'd.
- **Metadata can be incomplete.** Crossref may not have a brand-new DOI, and constructed APA strings are marked as such in `paper.json`.
- **Scripts do not write reviews.** If `papers/<slug>.md` is missing, that is expected: the agent has not written it yet.

For publisher-specific patterns, see [rules/JOURNALS.md](rules/JOURNALS.md). For failure recovery, see [rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md).

---

## Environment diagnosis

```bash
python3 main.py --doctor
# or
python3 doctor.py
python3 doctor.py --json
python3 doctor.py --install
python3 doctor.py --launch-chrome
```

The doctor checks Python, required and optional packages, Chrome and CDP 9222, the saved profile, `.vscode/settings.json`, and workspace directories.

---

## Cleanup and uninstallation

```bash
# Remove the package and local build caches
python3 uninstall.py

# Also remove dependencies and .venv (if present)
python3 uninstall.py --purge --yes
```

Your `papers/`, `assets/`, and `.raw/` content is not deleted by the uninstaller.

---

## License

This project is licensed under the [MIT License](LICENSE).
