# geo-academic-reader

[![Version](https://img.shields.io/badge/version-0.3.3-blue.svg)](https://github.com/Xjchen0/geo-academic-reader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> A literature workspace for AI agents: **browser-first evidence extraction**, **agent-written notes**, and **preview-safe Markdown** that renders in VS Code.

[English](README.md) | [简体中文](README.zh-CN.md)

---

## What it does

Point it at a DOI, a publisher URL, or a local PDF. It returns an **evidence pack** — metadata, extracted text with page anchors, figure captions with provenance, and downloaded images. Your agent reads that pack and writes a literature note. You get a durable Markdown knowledge base instead of a chat transcript.

The design separates three responsibilities:

| Layer | Responsibility | Output |
| :--- | :--- | :--- |
| Scripts | Fetch, render, download, record provenance | `.raw/<slug>/`, `papers/assets/<slug>/` |
| Agent | Interpret the evidence, write the note | `papers/<slug>.md` |
| QA | Verify paths, images, callouts, citation network, tone, math, placeholders | `--check-note`, `--index` |

The scripts never write review prose. That is deliberate: a generator that fills every section with plausible text makes a shallow note look thorough.

---

## Why browser-first

- Publisher pages give figure order, captions, and panel structure; PDF extraction often splits multi-panel figures or loses captions.
- Thumbnail URLs in the initial DOM (`/w400/`, `.medium.gif`) are rewritten to `full`, `w1200`, or `large` variants before download.
- When a CDN rejects direct HTTP with a 403, the image is fetched in the page context, reusing the browser session and referer.
- PDF-embedded images remain a fallback. When they are used, the manifest and the note say so.

Access is not circumvention. The pipeline uses the browser session you already have; it does not bypass paywalls or bot checks.

---

## Requirements

- Python **3.9+**
- `requests`, `beautifulsoup4`, `pypdf`, `websockets`
- **Google Chrome, Chromium, or Microsoft Edge** — strongly recommended for JavaScript-rendered pages and high-resolution figures
- Optional: `pymupdf` for caption-aware PDF figure cropping

No Node.js or headless-browser download is required.

---

## Quick start

```bash
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader
./install.sh          # Windows: .\install.ps1   |   any platform: python install.py
```

Open the folder in your agent (VS Code, Cursor, Claude Code, Antigravity, Windsurf, or a terminal agent) and say:

```text
开始使用
```

That is the whole onboarding. The agent follows `AGENTS.md` §0: it asks a few short questions, writes `.geo-reader/profile.json`, and remembers the answers for later sessions. **There is no setup command, no wizard, and no files written before the conversation** — a fresh clone carries no usage trace. Say `重新设置偏好` at any time to change your choices.

Then extract your first paper:

```bash
python3 main.py --doi "10.1038/s41467-026-69772-8"
```

Ask the agent to write the note from the evidence pack, and finish with:

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"
```

Ready-to-use prompts are in [PROMPTS.md](PROMPTS.md).

---

## First conversation

The agent asks, in one or two batches:

| Choice | Options | What it changes |
| :--- | :--- | :--- |
| Language | `zh-CN`, `en`, `bilingual` | Language of notes and replies |
| Editor | VS Code, Cursor, Claude Code, Antigravity, Windsurf, terminal | Formatting conventions and preview advice |
| Instruction style | `guided`, `balanced`, `expert` | How often the agent stops to confirm |
| Browser policy | `auto`, `existing`, `off` | Whether it may launch Chrome, reuse port 9222, or stay on HTTP/PDF |
| Note depth | `brief`, `standard`, `deep` | One-page brief, standard IMRaD, or per-figure deep read |
| Citation format | `apa`, `nature`, `gbt7714` | Reference section style |
| Journal list | the shipped 30 journals, or custom | Which journals “find new papers” scans |

Defaults are `zh-CN`, VS Code, balanced, browser auto, deep, APA, and the shipped journal list. Saying “use defaults” is enough. The profile is local and git-ignored; the agent checks it with `python3 main.py --profile --json` before each task and never re-onboards once it exists.

---

## Daily workflow

### 0. Find new papers (list first)

```bash
python3 main.py --new-literature --days 7
python3 main.py --new-literature --days 14 --journal epsl --journal gca
python3 main.py --journals-init   # create the editable user list
```

The scan uses the ISSNs in `journals.json` (the user copy `.geo-reader/journals.json` takes precedence), queries Crossref for records published or deposited in the window, deduplicates them, and drops corrections, errata, editorials, retractions, and society front matter. It writes `.geo-reader/journal-scan/latest.md` and prints a numbered list.

This step **only lists candidates**. No evidence pack is created, and the agent must wait for your numbers or DOIs before reading anything. Edit `enabled`, `keywords`, and `defaults.days` in the list to change scope; keywords are static configuration, never inferred from the conversation.

### 1. Extract

```bash
python3 main.py --doi "10.1038/s41467-026-69772-8"
python3 main.py --url "https://www.nature.com/articles/s41467-026-69772-8"
python3 main.py --pdf "input_pdfs/my_paper.pdf"
python3 main.py --batch-pdfs
```

Useful flags:

```bash
--browser auto       # launch/reuse Chrome, browser first (default)
--browser existing   # only reuse a Chrome already listening on 9222
--browser off        # HTTP/PDF only
--wait 6             # extra wait for JavaScript or bot checks
--max-figures 20     # cap downloaded figures
--json               # machine-readable summary
```

The command prints the slug, evidence paths, figure count, extraction route (`text=browser; figures=browser`), and warnings. It does not create the note.

### 2. Write

Give the agent the evidence-pack paths and `templates/paper_note.md`. A typical instruction:

> Read `.raw/<slug>/` and write `papers/<slug>.md` from `templates/paper_note.md`. Use only the extracted text and manifest captions; never invent formulas or conclusions. Link figures as `assets/<slug>/fig_XX.png`. Anchor key claims to a page or section. Place the paper in its citation network — prehistory, competing explanations, later tests — with a DOI for every external work. Finish with `--check-note --fix` and `--index`.

### 3. Verify

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"
python3 main.py --list
```

`--check-note` verifies image existence, non-zero size, image magic bytes, the canonical figure layout, leftover template text, hyperbolic wording, balanced `$$`, and the citation network: a 文献坐标 section, a ≥5-row citation table, a 参考文献 section with DOIs, and the external-reference target for the declared `note_depth` (3 / 6 / 10, or 15 for a review). It also rejects GitHub alert syntax, which VS Code renders as literal text. `--fix` rewrites paths, migrates legacy figures, and converts alert markers to labelled blockquotes. Add `--strict` to turn warnings into errors.

---

## Updates

After a task, run `--check-update` once. It reads the GitHub releases API, caches the answer for six hours, and exits 0 when GitHub is unreachable, so it never fails an offline session.

```bash
python3 main.py --check-update              # 0.3.2 → 0.3.3, or "up to date"
python3 main.py --update --dry-run          # show the target
python3 main.py --update                    # update, keep your work
```

`--update` uses `git merge --ff-only <tag>` in a git checkout. A copy without `.git` is updated from a shallow sparse clone of the tag, falling back to the release tarball. It never writes `papers/`, `.raw/`, `.geo-reader/` or `input_pdfs/`; `.geo-reader/profile.json` is backed up to `.geo-reader/backups/` and restored if anything goes wrong. A dirty tracked tree or diverged history is refused rather than reset. Use `--prerelease` only if you deliberately track prereleases.

Versioning is patch-first: a fix, a docs change or a small local improvement bumps `0.3.0 → 0.3.1`; a new capability bumps the minor unless requested otherwise.

> **One-time note**
>
> The updater itself ships from 0.3.1 onward. A copy older than 0.3.1 needs one manual upgrade (`git pull --ff-only` or a fresh download); after that, `--update` handles later releases.

### 4. Preview

Open `papers/<slug>.md` and press `Cmd+Shift+V` (macOS) or `Ctrl+Shift+V`. Native KaTeX works without extensions. Callouts use plain blockquotes with a bold label (`> **一句话结论**`), because VS Code's built-in preview does not render GitHub alert syntax.

---

## Classic papers are citation networks

A classic-paper note that only restates one PDF is not a literature review — it is a book report. Every note therefore carries a `## 0. 文献坐标` section with a citation table (`年份 | 工作 | 核心贡献 | 与本文的关系`), an explicit **竞争解释** paragraph, and a **后续检验** paragraph. `--check-note` requires:

| `note_depth` | Minimum external works | Typical use |
| :--- | :--- | :--- |
| `brief` | 3 | one-page briefing |
| `standard` | 6 | default note |
| `deep` | 10 | classic-paper deep read |
| `note_type: 经典文献综述` | 15 | multi-paper review |

The anchor paper is excluded from the count. Only entries under `## 参考文献` count, and each external work should carry a DOI. If the literature cannot be reached, the note says what is missing; padding the bibliography with unread papers is exactly the failure mode this check exists to prevent.

---

## Figure paths and VS Code preview

VS Code's built-in Markdown preview loads local images only from the workspace folder. In a single-file window it allows only the note's own folder. A project-root `assets/` therefore fails whenever the user opens `papers/` or the note alone — while hovering the link in the editor can still show a thumbnail, because hover resolves the file on disk through a different path. That mismatch is why “the image link works but the preview is broken” happens.

This workspace keeps figures **inside the note tree**:

```text
papers/
├── INDEX.md
├── <slug>.md
└── assets/
    └── <slug>/
        ├── fig_01.png
        └── fig_02.png
```

The note links them relatively:

```markdown
![图 1：图注](assets/<slug>/fig_01.png)
*图 1：图注（来源：browser；原始链接：https://...）*
```

This renders whether the workspace root is the project root, `papers/`, or the single note file. `../assets/...`, `./assets/...`, absolute paths, `file://`, and `<img>` tags are rejected by QA.

### Upgrading from 0.2.1

Older workspaces stored figures in a root-level `assets/` and used `../assets/...` links. Run:

```bash
python3 main.py --check-note --fix
```

`--fix` copies each figure into `papers/assets/<slug>/`, rewrites the note links, and updates `figures/manifest.json` and `paper.json`. The legacy folder is left in place, so nothing is lost; delete it yourself once the preview is confirmed.

---

## CLI reference

```text
python3 main.py --doi DOI               Extract an evidence pack by DOI
python3 main.py --url URL               Extract by article URL
python3 main.py --pdf PATH              Extract from a local PDF
python3 main.py --batch-pdfs            Process every PDF in input_pdfs/
python3 main.py --new-literature        List candidates from journals.json (no extraction)
python3 main.py --journals-init         Create .geo-reader/journals.json
python3 main.py --check-note [NOTE]     Check one note, or all papers/*.md
python3 main.py --index NOTE            Add/update a row in papers/INDEX.md
python3 main.py --list                  List evidence packs and notes
python3 main.py --profile [--json]      Show the saved preferences
python3 main.py --guide                 Print the quick-start guide
python3 main.py --check-update          Check GitHub for a newer release (cached 6 h)
python3 main.py --update                Update code; profile, notes and packs preserved
python3 main.py --doctor                Environment diagnostics
python3 main.py                         Interactive menu (terminal only)
```

With `pip install -e .`, `geo-reader` and `geo-doctor` expose the same commands.

---

## Workspace layout

```text
geo-academic-reader/
├── AGENTS.md                     Agent contract, onboarding, SOP
├── PROMPTS.md                    Copy-paste task prompts
├── SKILL.md                      Skill manifest and condensed contract
├── journals.json                 Shipped journal list (ISSN, flags, keywords)
├── input_pdfs/                   Drop-zone for raw PDFs
├── papers/
│   ├── INDEX.md                  Literature catalog
│   ├── <slug>.md                 Agent-written notes
│   └── assets/<slug>/fig_XX.png  Figures, inside the note tree
├── .raw/<slug>/                  Evidence packs (git-ignored)
│   ├── paper.json
│   ├── fulltext.md
│   ├── figures/manifest.json
│   └── README.md
├── .geo-reader/                  Local profile, journal list and scan output (git-ignored)
├── templates/                    Note and review templates
├── rules/                        Markdown, journal, troubleshooting references
├── scripts/                      Extraction, QA, onboarding schema, CLI
├── main.py                       Workspace entry point
├── doctor.py                     Environment diagnostics
└── install.* / uninstall.*
```

### Evidence-pack contract

`paper.json` holds bibliographic metadata, the APA string and whether it was constructed, the extraction method, open-access information, warnings, statistics, and relative paths.

`fulltext.md` is raw extracted text with page markers for PDFs. It is evidence, not a summary.

`figures/manifest.json` is the sole authority for figures:

| Field | Meaning |
| :--- | :--- |
| `id` | Stable identifier such as `fig_01` |
| `label` | Caption label such as `Figure 2`, when detectable |
| `caption` | Caption text from the page or PDF |
| `file` | Filename under `papers/assets/<slug>/` |
| `local_path` | Workspace-relative path |
| `markdown_path` | Path to use in a note: `assets/<slug>/fig_01.png` |
| `origin` / `download` | `browser`, `http`, or `pdf`, and how the bytes were obtained |
| `source_url` | Original image URL |
| `page` | PDF page number, when applicable |
| `width`, `height`, `bytes` | Image dimensions and size |
| `is_body_figure` | Whether the image looked like article content |

If a caption is empty, the note must say so rather than invent one.

---

## Scope and limitations

- **Paywalls stay paywalls.** Browser-first extraction renders what your session can already access.
- **Bot checks are interactive.** The pipeline waits and retries; if a challenge appears, complete it in the launched Chrome window and retry with `--browser existing`.
- **Not every figure is recoverable.** Proprietary viewers, supplementary-only figures, and unusual caption markup can defeat extraction. The manifest records what failed rather than hiding it.
- **PDF fallback is lower quality.** Embedded bitmaps may be split or captionless; `pymupdf` improves cropping. Scanned PDFs are not OCR'd.
- **Metadata can be incomplete.** New DOIs may not be in Crossref, and constructed citations are marked in `paper.json`.
- **No review prose from scripts.** A missing `papers/<slug>.md` means the agent has not written it yet, not that extraction failed.

Publisher-specific notes: [rules/JOURNALS.md](rules/JOURNALS.md). Recovery: [rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md). Operational lessons: [LESSONS.md](LESSONS.md).

---

## Diagnostics and cleanup

```bash
python3 main.py --doctor        # Python, packages, Chrome, CDP 9222, profile, VS Code settings
python3 doctor.py --json
python3 doctor.py --install
python3 doctor.py --launch-chrome

python3 uninstall.py            # remove the package and build caches
python3 uninstall.py --purge --yes
```

Your `papers/`, `papers/assets/`, and `.raw/` content is not deleted by the uninstaller.

---

## License

[MIT](LICENSE)
