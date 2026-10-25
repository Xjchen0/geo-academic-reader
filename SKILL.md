---
name: geo-academic-reader
version: "0.6.0"
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

# geo-academic-reader (v0.6.0)

A workspace-level workflow, not a one-shot summarizer. The scripts extract evidence; the agent interprets it; a QA command verifies the note before delivery.

---

## 🔐 Session Contract (P0)

Every session, before any literature command:

1. Read `AGENTS.md` → `MEMORY.md` → `LESSONS.md`.
2. Run `python3 main.py --preflight`; confirm OS, Python, packages, Chrome/CDP, editor and workspace role with the user.
3. Literature commands (`--doi`, `--url`, `--pdf`, `--batch-pdfs`, `--new-literature`, `--check-note`, `--index`) require a marker < 24 h old, from this version, `ok`, written after the profile existed. Otherwise the CLI exits 2.
4. `--no-preflight` / `GEO_READER_SKIP_PREFLIGHT=1` are emergency escapes; use them only when the user explicitly asks and say what was skipped.

The marker is not proof that you read the documents. Never fabricate it.

**Two roles, one tree.** A *code repository* has no profile, notes or packs, and ships an empty `papers/`. A *test workspace* has local `.geo-reader/profile.json`, `papers/*.md`, `papers/assets/`, `.raw/` and `input_pdfs/`; those are git-ignored and never published. `--preflight` prints the detected role.

---

## 🚀 First Run

Open the workspace in an agent (VS Code, Cursor, Claude Code, Antigravity, Windsurf, or a terminal agent) and say:

```text
开始使用
```

The agent follows `AGENTS.md` §0: it reads the contract documents, runs `--preflight`, confirms the environment with you, asks about language, editor, instruction style, browser policy, note depth, citation format, and the journal list for “find new papers”, writes `.geo-reader/profile.json`, reruns `--preflight`, and gives a short tour of the tree. **There is no setup command and no wizard.** No `.geo-reader/` directory is created until that conversation happens, so a fresh clone carries no usage trace. Preferences persist across sessions; say `重新设置偏好` to change them.

Load the skill only after the profile exists. If the profile is missing, onboarding comes first, even when the first message already contains a DOI.

---

## ⚡ Quick Start

```bash
# 1. Install dependencies (once)
./install.sh                 # Windows: .\install.ps1
uv sync                      # if you use uv: creates .venv/ and installs the project
python3 main.py --preflight  # contract docs, environment, profile, workspace role
python3 doctor.py            # optional verbose diagnostics

# Use `uv run python main.py ...` instead of `python3 main.py ...` when the
# project owns a uv environment (every `python` on PATH exits with code 49 on
# a fresh Windows install — that is the Microsoft Store alias stub).

# 2. Extract an evidence pack
python3 main.py --doi "10.1038/s41467-026-69772-8"
python3 main.py --url "https://www.nature.com/articles/s41467-026-69772-8"
python3 main.py --pdf "input_pdfs/paper.pdf"
python3 main.py --batch-pdfs

# 3. The agent writes papers/<slug>.md from .raw/<slug>/ using templates/paper_note.md

# 4. Validate and index
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"

# 5. Keep the workspace current (profile, notes and packs are preserved)
python3 main.py --check-update
python3 main.py --update
```

Installed entry points: `geo-reader`, `geo-doctor`.

---

## 🔎 New-Literature Watch (list first, P0)

```bash
python3 main.py --new-literature
python3 main.py --new-literature --journal epsl --journal geology_early
python3 main.py --new-literature --no-translate   # English-only list
python3 main.py --journals-init      # create and edit .geo-reader/journals.json
```

The scan reads `journals.json` (user copy `.geo-reader/journals.json` first) and opens each configured page in Chrome/CDP: Nature research-articles, Science First Release and Current, Science Advances, EPSL volumes, AGU journals, Geology current and early publication, GJI, and PNAS Earth. It parses the entries each page lists, adds a cached Chinese machine translation for every title, and writes `.geo-reader/journal-scan/latest.md` with numbered candidates. `--days 0` (the default) takes the page as-is.

Each candidate carries the English title plus a `中文（机译）：` line. The translation is for scanning only — the English title is authoritative. Cache: `.geo-reader/journal-scan/translations.json`; geoscience terms are post-edited on read (fugacity→逸度, sub-arc→弧下). If a title shows “暂缺”, rerun to fill it; never invent one.

**Stop after listing.** Present the English title with its Chinese line, journal, date and DOI; do not run `--doi`, create `.raw/`, or write a note until the user names numbers or DOIs. Never replace the scan with an OpenAlex or web topic search, and never infer the topic from existing notes or the conversation. If a page is empty or reports a challenge, name the page and error; complete Cloudflare checks in the opened Chrome window and rerun the same command. Do not auto-refresh.

---

## 🧭 Thematic Review (verify first, write second, P0)

```bash
python3 main.py --thematic-review "<topic>" --anchor-doi "10.xxxx/yyyy"
python3 main.py --thematic-review "<topic>" --refs "10.x/yyy,10.z/www" --from-year 1990
python3 main.py --thematic-review "<topic>" --anchor-doi <DOI> --max-refs 30 --no-forward
```

**A thematic review is not the journal scan.** The scan answers "what did these journals publish lately"; a thematic review answers "what does the evidence say about this question". Never substitute one for the other.

The command does three things and writes no prose:

1. **Topic search** — Crossref `query.bibliographic`, relevance-ranked, `type:journal-article`, optionally bounded by `--from-year` / `--to-year`.
2. **Per-item verification** — every anchor, user-supplied DOI and topic candidate is checked against Crossref for title, authors, year, journal and type, and its abstract is pulled when the publisher deposited one. Entries that fail verification stay “待核验” and must not be cited as fact.
3. **Citation network** — predecessors from the anchor's Crossref reference list, later tests from OpenAlex forward citations. OpenAlex only *finds* them; every candidate still passes through Crossref.

Output: `.raw/reviews/<slug>/` with `candidates.md` (numbered list + abstracts), `references.json` (structured verification) and `factcheck.md` (the human fact-check sheet).

Then write the note from `templates/thematic_review.md`: an anchor paper (front matter `anchor_doi`, and the anchor must also appear in the reference list), a citation-network table covering prehistory, rivals and later tests, at least two competing explanations with the criterion each one relies on, a later-tests section (“检索未覆盖” when nothing was searched), evidence tiers on every key claim, and a human fact-check section.

**Evidence tiers** — `【直证】` direct from the source, `【转述】` second-hand and not re-checked, `【推断】` author inference or an extrapolation, `【评估】` the writer's own assessment, `【未核实】` not verified and must be flagged. Use at least three; never let a tier go unmarked. Do not write “系统综述” unless the search string, database, date window and inclusion/exclusion rules are actually recorded.

`--check-note` enforces the thematic rules on any note whose `note_type` contains 主题: `missing_anchor_paper`, `anchor_not_in_references`, `missing_competing_explanations`, `missing_later_tests`, `missing_evidence_tiers`, `missing_factcheck_section`.

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
papers/assets/<slug>/fig_01.png   # actual image bytes, next to the notes
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
   - Figures live in `papers/assets/<slug>/`, inside the same `papers/` tree as the note. The only correct link is:
     ```markdown
     ![图 1：图注](assets/<slug>/fig_01.png)
     *图 1：图注（来源：browser；原始链接：...）*
     ```
   - VS Code's Markdown preview only loads local images under the workspace folder (or, in a single-file window, under the note's own folder). Keeping figures in `papers/assets/` makes the note render whether the user opens the project root, `papers/`, or the note alone.
   - Never use `../assets/...`, `./assets/...`, absolute paths, `file://`, or remote publisher URLs as the primary image.
   - Caption text comes from `figures/manifest.json`; if empty, say so.

3. **Labelled blockquotes** (not GitHub alerts)
   - `> **一句话结论**` — core question and one-sentence conclusion.
   - `> **关键前提**` — parameters, assumptions, boundary conditions.
   - `> **读图要点**` — how to read a figure.
   - `> **边界条件与未解问题**` — limitations, sample boundaries, uncertainties.

4. **Academic neutrality**
   - Ban: `颠覆一切`, `彻底终结`, `空前重大突破`, `完美解决`, `前所未有`.
   - State what the evidence supports and what it does not; distinguish the authors' claims from your inference.

5. **Evidence anchors**
   - PDF: `（第 N 页）`.
   - Web: section or paragraph, e.g. `（Results, 第 3 段）`.
   - If the evidence pack does not contain a fact, write `原文未提供`.

---

## 🕸 Classic-Paper Citation Network (P0)

A classic-paper note is a position in a literature, not a summary of one PDF. The note must contain a `## 0. 文献坐标` section with:

- a citation table of at least 5 rows: `年份 | 工作 | 核心贡献 | 与本文的关系`;
- one paragraph on **竞争解释** (at least two rivals and the criterion each depends on);
- one paragraph on **后续检验** (what later work supported, limited or overturned).

Minimum external works, excluding the anchor:

| `note_depth` | Target |
| :--- | :--- |
| `brief` | 3 |
| `standard` | 6 |
| `deep` | 10 |
| `note_type: 经典文献综述` | 15 |

Every external work needs a DOI. Never pad the list with unread papers; if the target cannot be met, say what is missing.

### Figures are not optional

| Note kind | Minimum embedded publisher figures | Check |
| :--- | :--- | :--- |
| `note_type` contains `综述` / `review` | 3 | `review_without_figures` — error |
| `note_depth: deep` | 3 | `note_without_figures` — warning |
| `note_depth: standard` | 1 | `note_without_figures` — warning |
| `note_depth: brief` | 0 | — |

A review without figures is a digest. Run `--doi` on the works whose figures carry the argument, copy `papers/assets/<slug>/fig_XX.*` into the note, take the caption verbatim from `figures/manifest.json`, and add a `> **读图要点**` blockquote under each figure. Never embed a cover image or a page icon (`is_body_figure: false`). A broken link does not count towards the quota.

---

## 🛠 Quality Gate

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --check-note --fix          # all papers/*.md
python3 main.py --check-note --strict       # warnings become errors
```

Checks: missing images, zero-byte files, invalid image magic bytes, files outside `papers/assets/`, legacy root-level assets, non-standard relative paths, leftover template markers, hyperbole, odd number of `$$`, GitHub alert syntax, missing 文献坐标 / 参考文献 sections, too few external works, missing citation table, references without DOI, duplicate DOIs, reviews without figures.

`--fix` rewrites a path only when the intended target is unambiguous, migrates figures from a legacy root `assets/` folder into `papers/assets/` (updating the note, manifest, and `paper.json`), and converts `> [!NOTE]`-style markers into labelled blockquotes. It does not invent citations. Do not delete a figure merely to make the report clean; report it.

Before delivery, also run:

```bash
python3 main.py --index "papers/<slug>.md"
```

This updates the 7-column row in `papers/INDEX.md`.

---

## 🔄 Updates

After a task, run `python3 main.py --check-update` once. It caches for 6 hours and exits 0 when GitHub is unreachable, so offline use is unaffected.

| Command | Behaviour |
|:---|:---|
| `--check-update` | Compare the local version with the latest GitHub release |
| `--check-update --refresh` | Ignore the cache |
| `--check-update --prerelease` | Include prereleases |
| `--update --dry-run` | Show the target version without changing files |
| `--update` | Fast-forward a git checkout to the release tag, or copy the release payload from a shallow sparse clone / tarball for a non-git copy |

Guarantees: `.geo-reader/profile.json` is backed up and restored if needed; `papers/`, `.raw/` and `input_pdfs/` are never written. A dirty tracked tree or diverged history is refused, never reset. Tell the user about a new release in one line; do not update without consent.

---

## 🛑 Common Errors & Recovery

| Symptom | Meaning | Action |
|:---|:---|:---|
| Literature command exits 2 | No fresh preflight marker, or the marker predates the profile | Run `python3 main.py --preflight`; do not bypass unless the user explicitly asks |
| `preflight` says a contract doc is missing | `AGENTS.md`, `MEMORY.md` or `LESSONS.md` is absent | Restore it from the release; do not create an empty placeholder |
| `preflight` reports missing packages | Required dependency absent | Give the `pip install` line and ask before installing |
| No profile yet | First run | Say `开始使用` in the agent chat; do not run a setup script |
| No Chrome found | Browser-first figures unavailable | Install Chrome, or accept `--browser off` and PDF fallback |
| CDP 9222 not running | Chrome not in debug mode | Use `--browser auto`, or `python3 doctor.py --launch-chrome` |
| Cloudflare challenge | Interactive check not passed | Complete it in the launched Chrome window, then retry with `--browser existing` |
| Zero figures | JS viewer, paywall, or selector mismatch | Read manifest warnings; retry with `--browser auto`; check the page manually |
| Text < 800 chars | Abstract page or paywall | Inspect `fulltext.md`; use OA PDF or `--url`; do not write a full review from an abstract |
| Image missing in preview | Wrong relative path or legacy layout | `--check-note --fix`; expected `assets/<slug>/...` under `papers/` |
| `github_alert_syntax` | VS Code does not render `> [!NOTE]` | `--check-note --fix`, then reword the generated label |
| `thin_reference_context` | The note summarises one paper only | Add prehistory, rival explanations and later tests, or set a lower `note_depth` |
| `--check-update` says offline | GitHub unreachable or rate-limited | Not an error; retry with `--refresh`, or set `GEO_READER_NO_UPDATE_CHECK=1` |
| `--update` refuses on a dirty tree | Local tracked code changes | Commit or `git stash`; never `reset --hard`. Notes and packs are untouched |
| Profile missing after update | Rare partial restore | Restore `.geo-reader/backups/profile-<timestamp>.json`; `--update` also restores automatically |
| Crossref 404 | New/preprint DOI | Use `--url`, or download the PDF and use `--pdf` |
| `--new-literature` returns 0 | No entries parsed, page disabled, or markup changed | Check `enabled` and the page URL; confirm the `parser` still matches the page |
| A journal page hits Cloudflare | Human check required | Complete it in the opened Chrome window, then rerun; the scan does not auto-refresh |
| EPSL list is stale or short | Volume numbers advanced | Update `volumes` in `.geo-reader/journals.json` |
| A candidate shows “暂缺” for the Chinese title | Translation rate limit or service outage | Rerun `--new-literature`; cached titles are reused and only missing ones are retried. Never invent a title |
| Chinese term is mistranslated | Machine translation, not a definitive rendering | Add a rule to `TERM_FIXES` in `scripts/translate.py`; the cache stores raw output, so fixes apply on read |
| Journal list missing or invalid JSON | `journals.json` deleted/edited badly | `python3 main.py --journals-init --force` (overwrites the user copy) or restore the file |
| PDF text empty | Scanned PDF, no text layer | OCR is not included; obtain a text PDF or use the publisher page |

Detailed guide: [rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md). Publisher patterns: [rules/JOURNALS.md](rules/JOURNALS.md). Context strategy: [LESSONS.md](LESSONS.md). Copy-paste prompts: [PROMPTS.md](PROMPTS.md).
