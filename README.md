# geo-academic-reader

[![Version](https://img.shields.io/badge/version-0.5.0-blue.svg)](https://github.com/Xjchen0/geo-academic-reader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> Turn papers into a Markdown knowledge base you can still use years from now — not a chat transcript that disappears.

[English](README.md) | [简体中文](README.zh-CN.md)

geo-academic-reader is a **literature workspace for AI agents**. Scripts open the paper, capture the text, download high-resolution figures and record provenance. The agent reads that evidence and writes the note. One QA command checks figures, citations and Markdown before delivery. It is built for Earth Sciences, Geophysics and Geology, and works for general science.

**Good fit**: you want close readings that accumulate as files, citation networks, and figure quality you can verify.
**Poor fit**: you only want a paragraph of summary, or you do not want an agent reading and writing local files.

---

## 1. Install and deploy

### 1.1 Requirements

| Requirement | Version | Why | If missing |
| :--- | :--- | :--- | :--- |
| Python | ≥ 3.9 | Runs the CLI and the QA engine | Upgrade first; nothing else works below 3.9 |
| `requests`, `beautifulsoup4`, `pypdf`, `websockets` | latest | Fetch, parse, PDF text, Chrome DevTools Protocol | `pip install requests beautifulsoup4 pypdf websockets` |
| `pymupdf` | optional | Faster PDF image extraction | `pip install pymupdf` |
| Chrome / Chromium / Edge | any recent | **Browser-first figures** | Install a browser, or accept `--browser off` (lower-quality figures) |
| An AI agent | VS Code, Cursor, Claude Code, Antigravity, Windsurf, or a terminal agent | The agent reads the contract and writes the note | — |

`pymupdf` is the only optional package. Everything else is required.

### 1.2 Install

```bash
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader
./install.sh          # macOS / Linux
```

```powershell
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader
.\install.ps1         # Windows
```

Any platform, no shell differences:

```bash
python install.py
```

The installer checks Python, installs the required packages, reports the browser situation, and creates the empty `papers/` tree. **It never asks for a DOI, never writes a profile, and never creates reading data** — that happens in conversation, in step 2.

Optional: put the CLI on your `PATH`.

```bash
pip install -e .
geo-reader --preflight      # the same entry point as python3 main.py
geo-doctor                  # verbose diagnostics
```

### 1.3 Verify the installation

```bash
python3 main.py --preflight
```

It prints one checklist and writes `.geo-reader/preflight.json`:

| Check | Healthy | If missing |
| :--- | :--- | :--- |
| Contract docs | `AGENTS.md`, `MEMORY.md`, `LESSONS.md` present | Restore them from the release; never write empty placeholders |
| OS and Python | Python ≥ 3.9 | Give the upgrade path; do not continue |
| Packages | `requests`, `beautifulsoup4`, `pypdf`, `websockets` | Give the exact `pip install` line; **ask before installing** |
| Browser | Chrome / Chromium / Edge; CDP 9222 optional | Offer to install, or accept HTTP/PDF fallback with lower-quality figures |
| Editor | The profile's editor; `.vscode/settings.json` | Explain how to create it; do not change settings unasked |
| Workspace role | `code repository` or `test workspace` | Explain whether this folder carries local reading data |

The marker is valid for **24 hours and tied to this version**. `--doi`, `--url`, `--pdf`, `--batch-pdfs`, `--new-literature`, `--check-note` and `--index` require it; otherwise the CLI exits 2. The fix is to re-run the check — never to bypass it.

> **Why a gate**
>
> Agents tend to run commands first and read the contract later. The marker turns "skipped the check" into an explicit failure instead of a silent downgrade. It proves the check ran; it does not prove the documents were read — so the documents also say: never fabricate the marker.

### 1.4 Deploy as a reading workspace (recommended)

The same repository has two roles. `--preflight` detects which one and prints it on the `Role:` line:

| Role | Detected when | Carries | Does not carry |
| :--- | :--- | :--- | :--- |
| **Code repository** | No profile, no notes, no packs | Code, templates, docs, `journals.json`, empty `papers/` | Preferences, notes, figures, packs, PDFs |
| **Test / reading workspace** | Any of the above exists | Code + profile + notes + figures + packs + `input_pdfs/` | — |

- `papers/*.md`, `papers/assets/*`, `input_pdfs/*.pdf`, `reading_list_*.md`, `.raw/` and `.geo-reader/` are git-ignored.
- A code repository keeps only `papers/.gitkeep` and `papers/assets/.gitkeep`: the structure is visible, the data is absent.
- Updates replace code and docs only; they **never write** to `papers/`, `.raw/`, `.geo-reader/` or `input_pdfs/`.

**Recommended deployment**: clone the remote twice. Keep one checkout clean for commits and releases; use the other for daily reading. They share code history but never share local preferences, notes or evidence packs.

---

## 2. Quick start

Open the folder in your agent (VS Code, Cursor, Claude Code, Antigravity, Windsurf, or a terminal agent) and say:

```text
开始使用
```

(English is fine too: `Start`.) The agent will:

1. read `AGENTS.md`, `MEMORY.md` and `LESSONS.md` instead of guessing from flags;
2. run `python3 main.py --preflight` and confirm OS, Python, packages, Chrome, editor and workspace role with you, in plain language;
3. ask seven short preference questions and write `.geo-reader/profile.json`;
4. rerun preflight so literature commands unlock;
5. give a short tour of the tree and offer exactly one first exercise.

**No setup command, no wizard, and no files written before that conversation.** Say `重新设置偏好` / `Reconfigure` to change preferences later; they persist across sessions and across updates.

### 2.1 The preferences it asks for

| Option | Values | Effect |
| :--- | :--- | :--- |
| Language | `zh-CN`, `en`, `bilingual` | Note and reply language |
| Editor | VS Code, Cursor, Claude Code, Antigravity, Windsurf, terminal | Layout and preview advice |
| Instruction style | `guided`, `balanced`, `expert` | How often the agent stops to confirm |
| Browser policy | `auto`, `existing`, `off` | Launch/reuse Chrome, or HTTP/PDF only |
| Note depth | `brief`, `standard`, `deep` | One-page brief, IMRaD, per-figure reading |
| Citation format | `apa`, `nature`, `gbt7714` | Reference style |
| Journal list | Shipped 17 pages/sections, or custom | Which pages “find new papers” opens |

Defaults are `zh-CN`, VS Code, balanced, auto, deep, APA, and the shipped `journals.json`. “Use defaults” is a valid answer.

### 2.2 The loop

```text
python3 main.py --doi "<DOI>"            →  .raw/<slug>/  +  papers/assets/<slug>/
        ↓  the agent writes the note
papers/<slug>.md                          →  from templates/paper_note.md
        ↓
python3 main.py --check-note papers/<slug>.md --fix
python3 main.py --index papers/<slug>.md
```

First paper:

```text
精读 DOI 10.1038/s41467-026-69772-8
```

The agent extracts the evidence pack, writes the note, then runs `--check-note --fix` and `--index`. Copy-paste prompts for every task: [PROMPTS.md](PROMPTS.md).

### 2.3 What you end up with

```text
papers/
├── <slug>.md                 the note you read and cite
├── INDEX.md                  the catalogue (generated by --index)
└── assets/<slug>/fig_01.png  the figure library, inside papers/ so VS Code renders it
```

---

## 3. The two core functions

Both are triggered by **plain language**, not by a flag. The agent recognises the intent and drives the scripts.

### 3.1 New-paper briefing — “找新文献”

**Trigger:** say `找新文献` / `最近有什么新文章` / `看看期刊新文章` / “recommend some recent papers”.

```text
找新文献。
```

What happens:

1. The agent runs `python3 main.py --new-literature`, which opens **only the journal pages configured in `journals.json` / `.geo-reader/journals.json`** — Nature research-articles, Science First Release / Current, Science Advances, EPSL volumes, AGU journals, Geology current and early publication, GJI, PNAS Earth (17 pages/sections in the shipped list).
2. Each page is parsed for the entries the page itself lists; results are written to `.geo-reader/journal-scan/latest.md` and `latest.json`.
3. The agent presents **numbered candidates** — English title, a Chinese machine translation marked as such, journal, date, DOI — and **stops**.

```text
1. Nature — "Deep mantle convection beneath the Pacific"
   中文（机译）：太平洋之下的深部地幔对流
   2026-10-22 · https://doi.org/10.1038/s41586-026-00000-0
```

**It only lists.** No evidence pack, no note, no extraction until you reply with numbers or DOIs. Then the agent processes them one by one.

Hard rules the agent follows:

- Never search by topic, never guess from your notes or from the conversation. The journal list is the definition of what “new papers” means.
- The English title is authoritative; the Chinese line is machine translation for scanning only.
- A missing translation shows “暂缺” — never an invented title.
- Cloudflare / human-verification pages are handed to you: complete the check in the opened Chrome window and rerun the same command. The scan never auto-refreshes.

Tuning:

```bash
python3 main.py --journals-init                  # create your editable journal list
python3 main.py --new-literature --journal epsl --journal geology_early
python3 main.py --new-literature --days 3        # optional date filter; default 0 = page as-is
python3 main.py --new-literature --no-translate  # English-only list
```

### 3.2 Classic-paper reading — “经典文献分享”

**Trigger:** say `把 <DOI / URL / PDF> 当作一篇经典文献来读` / `经典文献分享` / “do a deep read of this classic”.

```text
把 10.1073/pnas.2510972122 当作一篇经典文献来读。
```

A classic-paper note is **not a summary of one PDF**. It is a citation network: what the paper inherited, what it argued against, and what later work did to it.

The agent will:

1. build the evidence pack (`--doi` / `--url` / `--pdf`);
2. find the paper's **prehistory** (who it answers), the **competing explanations of its time** (at least two, each with the criterion it depends on), and the **later tests or corrections**;
3. write `## 0. 文献坐标` with a `年份 | 工作 | 核心贡献 | 与本文的关系` table of at least 5 data rows;
4. cite at least **10 external works** for a deep read (**15** for a review), each with a DOI; unverifiable entries are marked “自动构造，需核对”;
5. state explicitly **which competing explanations the evidence rules out and which it does not** — “not discussed” is not “ruled out”;
6. say “这部分检索未覆盖” instead of padding the list with unread papers;
7. embed **original figures** from the evidence packs and give each one a `> **读图要点**` reading block;
8. finish with `--check-note --fix` and `--index`.

Minimum external works by depth:

| `note_depth` | Minimum external works | Typical use |
| :--- | :--- | :--- |
| `brief` | 3 | One-page brief |
| `standard` | 6 | Default single-paper note |
| `deep` | 10 | Classic-paper deep read |
| `note_type: 经典文献综述` | 15 | Multi-paper review |

Figures are not optional here either: a review must embed at least **3** original figures, a deep note at least **3**; `--check-note` reports `review_without_figures` as an error.

---

## 4. Why the route goes through the web

This is the part that makes the output different from “paste a PDF into a chat window”.

**The publisher's page is the only place where the figures, the caption, the supplementary material and the version of record coexist.** Everything else is a second-hand copy.

| | Straight from the web | PDF-only fallback |
| :--- | :--- | :--- |
| Figure resolution | Publisher's original asset (often 1000–2000 px wide) | Embedded bitmap, often ≤ 600 px, sometimes a page crop |
| Captions | Full caption, often with the panel explanation | Missing, or split across the page |
| Supplementary | Figures, tables and methods linked from the article page | Absent |
| Version of record | The published version, with corrections | Whatever you happened to download |
| Provenance | Recorded as `browser` or `http` in `figures/manifest.json` | Recorded as `pdf` — and said so in the note |

The pipeline therefore runs a strict fallback chain for every paper:

1. **Chrome/CDP first** (`--browser auto`, the default) — the agent opens the real article page and takes the publisher's own image assets.
2. **Direct HTTP second** — same assets, no browser, used when the browser fails.
3. **PDF-embedded images last** — only when both of the above fail. When this happens, the note says so explicitly and the manifest records `origin: pdf`.

A PDF page crop is never presented as a publisher figure, and the origin recorded in `figures/manifest.json` is the only thing the agent is allowed to report — never a guess.

**Why this matters for the reading itself:**

- A figure is usually the *evidence* for a claim. A low-resolution or cropped figure cannot support a claim about a panel's shape, a curve's inflection or an error bar's width — and a note that quotes such a figure is over-reading it.
- Figure captions carry the conditions: sample size, projection, age model, filter. A cropped panel loses the caption, so it loses the conditions.
- Browsing the live page also gets the *metadata of the discussion* — later versions, corrections, and the linked prior work that a citation network needs.

**What we ask of the agent, and what we ask of you:**

- The agent opens the browser for any paper that has a web version. If a page shows a human-verification challenge, it stops and asks you to click it — it never refreshes, never guesses, never silently switches to a lower-fidelity source. Only genuinely PDF-only papers use PDF cropping.
- If the text comes back shorter than 800 characters, or the figure list is empty, the agent reports that instead of writing a review anyway.

---

## 5. The other functions

All of these have copy-paste prompts in [PROMPTS.md](PROMPTS.md). Same trigger style, same contract.

| Task | Trigger | What you get |
| :--- | :--- | :--- |
| **Single paper, DOI** | `精读 DOI <doi>` | An IMRaD-style note with per-figure reading, evidence anchors, and the paper placed in its citation network |
| **Single paper, URL** | `精读这篇论文：<URL>` | The same, with a note on whether the page needed a login or a human check |
| **PDF only** | `精读 input_pdfs/<file>.pdf` | The DOI is extracted from the PDF; browser figures are still preferred if a DOI exists |
| **Batch PDFs** | `批量精读 input_pdfs/ 下的所有 PDF` | One note per PDF, processed one at a time, plus a summary table of title / year / journal / text source / figure source / figure count / failures |
| **Review (multi-paper)** | `围绕"<主题>"做一篇文献综述` | A structured review: search and inclusion criteria, consensus vs controversy vs evidence strength, DOI per paper, links to local notes, **at least 3 original figures** with reading blocks, and explicit “待补检索” markers where evidence is thin |
| **Reviewer-style re-read** | `按"审稿人"视角重读 papers/<slug>.md` | A critique list, not a rewrite: core claim, weakest link, assumptions and boundary conditions, whether the figures really support the text, and the three cheapest checks to run next |
| **Note health check** | `运行 --check-note --fix` | Every remaining error explained, image files verified by magic bytes, genuinely missing figures marked rather than deleted |
| **Index maintenance** | `检查 papers/ 下所有笔记` | Missing front matter reported, `--index` re-run, and duplicate or inconsistent rows in `papers/INDEX.md` listed |
| **Update** | `检查更新` / `更新` | `--check-update` (cached 6 h, exits 0 offline), then `--update` on your word. Preferences, notes, figures, packs and PDFs are preserved; a dirty or diverged tree is refused, never reset |
| **Reconfigure** | `重新设置偏好` | The seven questions again; `created_at` is kept, `updated_at` is refreshed |

Two structural rules apply to every task:

- **The scripts never write review prose.** A generator that fills every section makes a shallow note look like a close reading. The scripts produce evidence; the agent writes.
- **Every key claim carries an evidence anchor**: `（第 3 页）` for PDF, `（原文 §Results 第 2 段）` for web, `（图 2）` for a figure.

---

## 6. The Python code

The whole system is about 6,800 lines of dependency-light Python. It is deliberately split so that the evidence layer and the writing layer never mix.

### 6.1 Entry points

| File | Role |
| :--- | :--- |
| `main.py` | Thin wrapper around `scripts/cli.py` |
| `doctor.py` | Verbose environment diagnostics, `--json`, `--install`, `--launch-chrome` |
| `install.py` / `install.sh` / `install.ps1` | Cross-platform installer |
| `uninstall.py` | Removes the package and build caches; never touches `papers/` or `.raw/` |

### 6.2 Module map

| Module | Lines | Responsibility |
| :--- | :--- | :--- |
| `scripts/cli.py` | 588 | Argument parsing, command dispatch, human-readable output |
| `scripts/fetch_paper.py` | 635 | Crossref metadata, article-page text, DOI extraction from PDFs |
| `scripts/browser.py` | 599 | Chrome DevTools Protocol client: launch, navigate, wait, screenshot, fetch image assets |
| `scripts/figures.py` | 260 | Figure discovery, download, `image_magic` validation, manifest writing |
| `scripts/evidence.py` | 654 | Evidence-pack assembly: `paper.json`, `fulltext.md`, `figures/manifest.json`, `README.md` |
| `scripts/note_check.py` | 931 | The QA engine: figures, image paths, template residue, hype words, `$$` balance, GitHub alerts, citation network, `--fix` |
| `scripts/journal_watch.py` | 1131 | Journal page parsers (`nature`, `science_*`, `epsl`, `agu`, `geology_*`, `gji`, `pnas`), candidate listing |
| `scripts/translate.py` | 287 | Chinese machine translation of titles, with a cache and a geology term post-edit pass |
| `scripts/updater.py` | 749 | Release check, fast-forward update, sparse-clone fallback, backup and restore of the profile |
| `scripts/preflight.py` | 291 | The session marker: docs, environment, profile, workspace role |
| `scripts/onboarding.py` | 156 | Preference schema and the question set |
| `scripts/config.py` | 165 | Paths, profile choices, reference targets |
| `scripts/version.py` | 3 | Single source of truth for the version |

### 6.3 The evidence-pack contract

```text
.raw/<slug>/
├── paper.json           bibliographic metadata, APA string, extraction method, warnings, stats
├── fulltext.md          extracted text with page markers — evidence, not a summary
├── figures/manifest.json the sole authority for captions, origins and dimensions
└── README.md            human-readable summary and next steps
```

`figures/manifest.json` fields:

| Field | Meaning |
| :--- | :--- |
| `id` / `label` | Stable id (`fig_01`) and figure label (`Figure 2`) |
| `caption` | Caption from the page or PDF; if empty, the note must say so |
| `file` / `local_path` | Local file and workspace-relative path |
| `markdown_path` | Path used in notes: `assets/<slug>/fig_01.png` |
| `origin` / `download` | `browser`, `http` or `pdf`, plus how the bytes were fetched |
| `source_url` / `page` | Original image URL and applicable page |
| `width` / `height` / `bytes` | Dimensions and size |
| `is_body_figure` | Whether it looks like a body figure rather than page chrome |

### 6.4 The QA engine

`scripts/note_check.py` is the piece that makes the guarantees enforceable rather than aspirational.

| Check | Severity | What it enforces |
| :--- | :--- | :--- |
| `missing_image`, `broken_image` | error | Every referenced figure exists, is non-zero and has real image magic bytes |
| `invalid_image_path` | error | Only `assets/<slug>/...` inside `papers/` — never `../assets/`, absolute paths, `file://` or `<img>` |
| `placeholder_prose`, `hype_words` | error | No template residue and no unverifiable superlatives |
| `unbalanced_display_math`, `github_alert_syntax` | error | `$$` pairs; blockquotes instead of `> [!NOTE]`, which VS Code renders literally |
| `missing_related_context`, `missing_citation_table` | error | The 文献坐标 section and a ≥5-row citation table |
| `thin_reference_context`, `no_external_references` | error | External-work minimums: brief 3, standard 6, deep 10, review 15 |
| `references_without_doi`, `duplicate_reference_doi` | warning | Every external work needs a DOI; no duplicates |
| `review_without_figures` | error | A review embeds at least 3 usable original figures |
| `note_without_figures` | warning | A deep note embeds at least 3 |

`--fix` rewrites only unambiguous things: legacy figure libraries are migrated into `papers/assets/`, links are rewritten, and alert markers become labelled blockquotes. It never rewrites your prose.

### 6.5 Tests

```bash
python3 -m unittest discover tests -v
```

Five suites cover the parsers, the QA engine, the preflight gate, the translation cache and the updater:

```text
tests/test_journal_watch.py   tests/test_note_check.py
tests/test_preflight.py       tests/test_translate.py
tests/test_updater.py
```

### 6.6 Extending it

- **Add a journal**: add an entry to `.geo-reader/journals.json` — `key`, `name`, `parser`, `url` (or `url_template` + `volumes`), `enabled`. No code change unless the page layout is unusual.
- **Add a parser**: implement it in `scripts/journal_watch.py` and register the name in the parser table.
- **Add a QA rule**: extend `scripts/note_check.py` and add a case to `tests/test_note_check.py`. Rules are data, not prose: every issue has a code, a severity and a line.
- **Change the version**: edit `scripts/version.py` only; `pyproject.toml` and `setup.py` mirror it, and a release check compares all three.

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| Literature command exits 2 | Marker missing, stale or from another version | Run `python3 main.py --preflight`; do not bypass with `--no-preflight` |
| Marker says `profile_missing` | Preflight ran before the profile existed | Finish onboarding, write the profile, rerun preflight |
| Preflight reports a missing doc | `AGENTS.md` / `MEMORY.md` / `LESSONS.md` absent | Restore from the release; do not create empty files |
| Chrome not found | Browser-first figures unavailable | Install Chrome, or accept `--browser off` and PDF fallback |
| Cloudflare challenge | Human check required | Complete it in the opened Chrome window, then rerun; no auto-refresh |
| Zero figures | JS viewer, paywall or selector drift | Read manifest warnings; retry `--browser auto`; report the failure honestly |
| Text < 800 chars | Abstract page or paywall | Inspect `fulltext.md`; use an OA PDF or `--url`; never write a full review from an abstract |
| Image missing in preview | Path outside `papers/` | `--check-note --fix`; the valid form is `assets/<slug>/...` |
| `thin_reference_context` | The note summarises one paper only | Add prehistory, rivals and later tests, or lower `note_depth` |
| `review_without_figures` | The review has no original figures | Run `--doi` for the key works, embed `assets/<slug>/fig_XX.png`, add a `> **读图要点**` block per figure |
| `--check-update` says offline | GitHub unreachable | Not an error; retry with `--refresh`, or set `GEO_READER_NO_UPDATE_CHECK=1` |
| `--update` refuses | Dirty code tree or diverged history | Commit or `git stash`; never `reset --hard` |
| Journal list is empty | Page disabled, parser drift, or advanced volumes | Check `enabled` / `url`; update EPSL `volumes`; fix the parser |
| Chinese title shows “暂缺” | Translation rate limit or outage | Rerun `--new-literature`; cached titles are reused; never invent one |

More: [rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md), [rules/JOURNALS.md](rules/JOURNALS.md), [rules/MARKDOWN_SPEC.md](rules/MARKDOWN_SPEC.md), [LESSONS.md](LESSONS.md).

---

## 8. Diagnostics and cleanup

```bash
python3 main.py --preflight     # contract + environment + profile + role
python3 main.py --doctor        # verbose diagnostics
python3 doctor.py --json
python3 doctor.py --install
python3 doctor.py --launch-chrome

python3 uninstall.py            # remove the package and build caches
python3 uninstall.py --purge --yes
```

Uninstalling never deletes `papers/`, `papers/assets/` or `.raw/`.

---

## 9. License

[MIT](LICENSE)
