---
name: geo-academic-reader
version: "0.2.1"
license: MIT
description: >-
  Browser-first evidence extraction and VS Code-ready literature notes for scientific
  papers (DOI, web URL, or local PDF). Produces an evidence pack (metadata, raw text,
  figure captions, provenance, downloaded images); the agent writes the review.
  Specialized for Earth Sciences, Geophysics, Geology, and general science.
compatibility: >-
  Requires: Python >= 3.9 (requests, beautifulsoup4, pypdf, websockets).
  Recommended: Google Chrome/Chromium/Edge for CDP 9222 browser extraction.
  Optional: pymupdf for better PDF figure cropping.
---

# geo-academic-reader (v0.2.1)

A workspace-level workflow, not a one-shot summarizer. The scripts extract evidence; the agent interprets it; a QA command verifies the note before delivery.

---

## ⚡ Quick Start

```bash
# 1. One-time environment setup and onboarding
./install.sh                 # Windows: .\install.ps1
python3 main.py --setup      # language, IDE, style, browser policy, depth, citation

# 2. Extract an evidence pack
python3 main.py --doi "10.1038/s41467-026-69772-8"
python3 main.py --url "https://www.nature.com/articles/s41467-026-69772-8"
python3 main.py --pdf "input_pdfs/paper.pdf"
python3 main.py --batch-pdfs

# 3. The agent writes papers/<slug>.md from .raw/<slug>/ using templates/paper_note.md

# 4. Validate and index
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"
```

Installed entry points: `geo-reader`, `geo-doctor`, `geo-setup`.

---

## 🎯 Input Matrix

| Input | Text strategy | Figure strategy | Browser needed? |
|:---|:---|:---|:---|
| **DOI** | Crossref metadata → rendered page → HTTP → OA PDF | Browser first; PDF only as fallback | Recommended; `auto` launches Chrome |
| **Article URL** | Rendered page → HTTP → OA PDF | Browser first; page-context fetch for 403s | Recommended |
| **Local PDF with DOI** | PDF text + Crossref, browser can top up text | Browser first; PDF embedded images as fallback | Recommended |
| **Local PDF without DOI** | PDF text only | PDF embedded images or PyMuPDF caption crops | No |
| **Open access (arXiv, bioRxiv, PMC)** | HTTP/PDF | Direct HTTP or OA PDF | Optional |

`paper.json` records the actual route, e.g. `text=browser; figures=browser` or `text=pdf; figures=pdf`. Never claim browser extraction if the manifest says otherwise.

---

## 📦 Evidence-Pack Contract

```text
.raw/<slug>/
├── paper.json              # metadata, APA, method, warnings, stats, file paths
├── fulltext.md             # raw extracted text with page markers (PDF)
├── figures/manifest.json   # captions, origin, source_url, page, dimensions, markdown_path
└── README.md               # human-readable summary of the pack
assets/<slug>/fig_01.png    # actual image bytes
```

The scripts **do not** write `papers/<slug>.md`. If the note is missing, the agent has not done its job yet.

Manifest fields that matter most: `caption`, `origin`, `source_url`, `page`, `width`, `height`, `is_body_figure`, and `markdown_path`. Treat the manifest as the sole authority for figure captions and paths.

---

## 📐 VS Code Markdown Specifications (P0 Rules)

1. **Native KaTeX**
   - Inline: `$E = mc^2$`, no spaces just inside the delimiters.
   - Display:
     ```markdown
     $$
     \frac{\partial \mathbf{u}}{\partial t} + (\mathbf{u} \cdot \nabla)\mathbf{u} = -\frac{1}{\rho}\nabla p + \nu \nabla^2 \mathbf{u}
     $$
     ```
   - No SVG/base64 formula images.
   - Only reproduce equations that appear in the source; no sample equations.

2. **Local figures**
   - Notes live in `papers/`, so the link is:
     ```markdown
     ![图 1：图注](../assets/<slug>/fig_01.png)
     *图 1：图注（来源：browser；原始链接：...）*
     ```
   - Never use `./assets/...`, absolute paths, or remote publisher URLs as the primary image.
   - Caption text comes from `figures/manifest.json`; if empty, say so.

3. **GFM alerts**
   - `> [!NOTE]` — core question and one-sentence conclusion.
   - `> [!IMPORTANT]` — parameters, assumptions, boundary conditions.
   - `> [!TIP]` — how to read a figure.
   - `> [!WARNING]` — limitations, sample boundaries, uncertainties.

4. **Academic neutrality**
   - Ban: `颠覆一切`, `彻底终结`, `空前重大突破`, `完美解决`, `前所未有`.
   - State what the evidence supports and what it does not; distinguish the authors' claims from your inference.

5. **Evidence anchors**
   - PDF: `（第 N 页）`.
   - Web: section or paragraph, e.g. `（Results, 第 3 段）`.
   - If the evidence pack does not contain a fact, write `原文未提供`.

---

## 🛠 Quality Gate

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --check-note --fix          # all papers/*.md
python3 main.py --check-note --strict       # warnings become errors
```

Checks: missing images, zero-byte files, invalid image magic bytes, files outside `assets/`, non-standard relative paths, leftover template markers, hyperbole, odd number of `$$`.

`--fix` rewrites a path only when the intended target is unambiguous. Do not delete a figure merely to make the report clean; report it.

Before delivery, also run:

```bash
python3 main.py --index "papers/<slug>.md"
```

This updates the 7-column row in `papers/INDEX.md`.

---

## 🛑 Common Errors & Recovery

| Symptom | Meaning | Action |
|:---|:---|:---|
| No Chrome found | Browser-first figures unavailable | Install Chrome, or accept `--browser off` and PDF fallback |
| CDP 9222 not running | Chrome not in debug mode | Use `--browser auto`, or `python3 doctor.py --launch-chrome` |
| Cloudflare challenge | Interactive check not passed | Complete it in the launched Chrome window, then retry with `--browser existing` |
| Zero figures | JS viewer, paywall, or selector mismatch | Read manifest warnings; retry with `--browser auto`; check the page manually |
| Text < 800 chars | Abstract page or paywall | Inspect `fulltext.md`; use OA PDF or `--url`; do not write a full review from an abstract |
| Image missing in preview | Wrong relative path | `--check-note --fix`; expected `../assets/<slug>/...` |
| Crossref 404 | New/preprint DOI | Use `--url`, or download the PDF and use `--pdf` |
| PDF text empty | Scanned PDF, no text layer | OCR is not included; obtain a text PDF or use the publisher page |

Detailed guide: [rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md). Publisher patterns: [rules/JOURNALS.md](rules/JOURNALS.md). Context strategy: [LESSONS.md](LESSONS.md). Copy-paste prompts: [PROMPTS.md](PROMPTS.md).
