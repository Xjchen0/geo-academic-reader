# geo-academic-reader

[![Version](https://img.shields.io/badge/version-0.4.0--pre-blue.svg)](https://github.com/Xjchen0/geo-academic-reader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> Turn papers into a Markdown knowledge base you can still use years from now — not a chat transcript that disappears.

[English](README.md) | [简体中文](README.zh-CN.md)

geo-academic-reader is a **literature workspace for AI agents**. Scripts open the paper, capture the text, download high-resolution figures and record provenance. The agent reads that evidence and writes the note. One QA command checks figures, citations and Markdown before delivery. It is built for Earth Sciences, Geophysics and Geology, and works for general science.

**Good fit**: you want close readings that accumulate as files, citation networks, and figure quality you can verify.
**Poor fit**: you only want a paragraph of summary, or you do not want an agent reading and writing local files.

---

## In 30 seconds

| Step | Who | Output |
| :--- | :--- | :--- |
| Capture | Scripts | `.raw/<slug>/`: metadata, page-anchored text, figure manifest, provenance |
| Interpret | Agent | `papers/<slug>.md`: a note with evidence anchors |
| Verify | Scripts | `--check-note --fix`: figures, template residue, citation network, Markdown compatibility |
| Keep | Scripts | `papers/assets/<slug>/` + `papers/INDEX.md`: self-contained, previewable, searchable |

The scripts **never write review prose**. That is deliberate: a generator that fills every section makes a shallow note look like a close reading.

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

(English is fine too: `Start`.) The agent will:

1. read `AGENTS.md`, `MEMORY.md` and `LESSONS.md` instead of guessing from flags;
2. run `python3 main.py --preflight` and confirm OS, Python, packages, Chrome and editor with you;
3. ask a few preference questions and write `.geo-reader/profile.json`;
4. rerun preflight so literature commands unlock;
5. give a short tour of the tree and one optional first exercise.

**No setup command, no wizard, and no files written before that conversation.** Say `重新设置偏好` / `Reconfigure` to change preferences later.

First paper:

```text
Read DOI 10.1038/s41467-026-69772-8
```

The agent extracts the evidence pack, writes the note, then runs `--check-note --fix` and `--index`. Copy-paste prompts: [PROMPTS.md](PROMPTS.md).

---

## First run: what the agent confirms

### 1. Environment first

`python3 main.py --preflight` prints a checklist; the agent walks through it with you in plain language:

| Check | Healthy | If missing |
| :--- | :--- | :--- |
| Contract docs | `AGENTS.md`, `MEMORY.md`, `LESSONS.md` present | Stop and restore them from the release; never write empty placeholders |
| OS and Python | Python ≥ 3.9 | Give the upgrade path; do not continue |
| Packages | `requests`, `beautifulsoup4`, `pypdf`, `websockets` | Give the exact `pip install` line; **ask before installing** |
| Browser | Chrome / Chromium / Edge; CDP 9222 optional | Offer to install, or accept HTTP/PDF fallback with lower-quality figures |
| Editor | The profile's editor; `.vscode/settings.json` | Explain how to create it; do not change settings unasked |
| Workspace role | `code repository` or `test workspace` | Explain whether this folder carries local reading data |

Preflight writes `.geo-reader/preflight.json`: valid for **24 hours, tied to the version**. `--doi`, `--url`, `--pdf`, `--batch-pdfs`, `--new-literature`, `--check-note` and `--index` require it; otherwise the CLI exits 2. The fix is to re-run the check, not to bypass it.

> **Why a gate**
>
> Agents tend to run commands first and read the contract later. The marker turns "skipped the check" into an explicit failure instead of a silent downgrade. It proves the check ran; it does not prove the documents were read — so the documents also say: never fabricate the marker.

### 2. Preferences: seven questions

| Option | Values | Effect |
| :--- | :--- | :--- |
| Language | `zh-CN`, `en`, `bilingual` | Note and reply language |
| Editor | VS Code, Cursor, Claude Code, Antigravity, Windsurf, terminal | Layout and preview advice |
| Instruction style | `guided`, `balanced`, `expert` | How often the agent stops to confirm |
| Browser policy | `auto`, `existing`, `off` | Launch/reuse Chrome, or HTTP/PDF only |
| Note depth | `brief`, `standard`, `deep` | One-page brief, IMRaD, per-figure reading |
| Citation format | `apa`, `nature`, `gbt7714` | Reference style |
| Journal list | Shipped 17 pages/sections, or custom | Which pages “find new papers” opens |

Defaults are `zh-CN`, VS Code, balanced, auto, deep, APA, and the shipped `journals.json`. “Use defaults” is a valid answer. Preferences live locally, are git-ignored, and survive sessions and updates.

### 3. A tour of the tree

| Path | Purpose | Do you need it? |
| :--- | :--- | :--- |
| `papers/<slug>.md` | The note you read and cite | Yes |
| `papers/assets/<slug>/` | Its figure library, inside `papers/` | Loaded automatically |
| `.raw/<slug>/` | Evidence pack: metadata, text, captions, provenance | When checking a claim |
| `.geo-reader/profile.json` | Your preferences | Only when changing them |
| `.geo-reader/journal-scan/latest.md` | The last candidate list | Yes |
| `templates/paper_note.md` | Note template and writing rules | When customising structure |
| `journals.json` | Shipped journal pages | Rarely |
| `MEMORY.md` / `LESSONS.md` | Durable decisions and failure modes | The agent reads them every session |

### 4. One first exercise

- **Find new papers**: open the configured journal pages, list numbered candidates (English title + Chinese machine translation), then wait for your choice.
- **Read one paper**: give a DOI, URL or PDF; get an evidence pack and a note.
- **Look around**: `python3 main.py --list` shows existing packs and notes.

---

## Two folders: code repository vs test workspace

The same repository can exist in two roles. `--preflight` detects which one and prints it on the `Role:` line:

| Role | Detected when | Carries | Does not carry |
| :--- | :--- | :--- | :--- |
| **Code repository** | No profile, no notes, no packs | Code, templates, docs, `journals.json`, empty `papers/` | Preferences, notes, figures, packs, PDFs |
| **Test / reading workspace** | Any of the above exists | Code + profile + notes + figures + packs + `input_pdfs/` | — |

- `papers/*.md`, `papers/assets/*`, `input_pdfs/*.pdf`, `reading_list_*.md`, `.raw/` and `.geo-reader/` are git-ignored.
- A code repository keeps only `papers/.gitkeep` and `papers/assets/.gitkeep`: the structure is visible, the data is absent.
- Check `Role:` before publishing. Committing from a test workspace mixes your reading data into the release.
- Updates replace code and docs only; they **never write** to `papers/`, `.raw/`, `.geo-reader/` or `input_pdfs/`.

**Recommended setup**: clone the remote twice. Keep one checkout clean for commits and releases; use the other for daily reading and testing. They share code history but never share local preferences, notes or evidence packs.

---

## Daily workflow

### 0. Find new papers: list first, then stop

```bash
python3 main.py --new-literature
python3 main.py --new-literature --journal epsl --journal geology_early
python3 main.py --new-literature --days 3          # optional date filter
python3 main.py --new-literature --no-translate    # English-only list
python3 main.py --journals-init                    # create an editable journal list
```

The scan opens each configured page in Chrome/CDP — Nature research-articles, Science First Release / Current, Science Advances, EPSL volumes, AGU journals, Geology current and early publication, GJI, PNAS Earth — parses the entries the page itself lists, writes `.geo-reader/journal-scan/latest.md`, and prints numbered candidates.

Each candidate has a **Chinese machine translation** marked “machine translation, for scanning only”; the English title is authoritative. Translations are cached by English title and only new entries are requested. A failed translation shows “暂缺” rather than an invented title.

This step **only lists**. The agent must not extract or write a note until you reply with numbers or DOIs. If a page hits Cloudflare, complete the check in the opened Chrome window and rerun the same command; the scan does not auto-refresh.

### 1. Extract an evidence pack

```bash
python3 main.py --doi "10.1038/s41467-026-69772-8"
python3 main.py --url "https://www.nature.com/articles/s41467-026-69772-8"
python3 main.py --pdf "input_pdfs/my_paper.pdf"
python3 main.py --batch-pdfs
```

Useful options: `--browser auto|existing|off`, `--wait 6`, `--max-figures 20`, `--json`. The command prints the slug, paths, figure count, actual route (e.g. `text=browser; figures=browser`) and warnings. It **does not create the note**.

### 2. Write the note

Hand the evidence pack and `templates/paper_note.md` to the agent. A typical instruction:

> Read `.raw/<slug>/` and write `papers/<slug>.md` using `templates/paper_note.md`. Use only the extracted text and manifest captions; invent no equations or conclusions. Link figures as `assets/<slug>/fig_XX.png`. Anchor each key claim to a page or section. Place the paper in its citation network: prehistory, competing explanations, later tests, with a DOI for every external work. Finish with `--check-note --fix` and `--index`.

### 3. Verify and index

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"
python3 main.py --list
```

`--check-note` verifies that figures exist, are non-zero and are real images, live under `papers/assets/`, and that the note has no template residue, hyperbole, unbalanced `$$` or GitHub alert syntax. It also checks the citation network: 文献坐标 section, a ≥5-row citation table, external-work count, DOI coverage and duplicate DOIs. `--fix` rewrites only unambiguous paths, migrates a legacy figure library, and converts alert markers to labelled blockquotes. `--strict` treats warnings as errors.

### 4. Check for updates

```bash
python3 main.py --check-update        # e.g. 0.3.3 → 0.4.0, or “up to date”
python3 main.py --update --dry-run    # preview the target
python3 main.py --update              # update; keep profile, notes and packs
```

Checks are cached for 6 hours and exit 0 when GitHub is unreachable, so an offline reading task never fails. Git checkouts use `git merge --ff-only <tag>`; a copy without `.git` uses a shallow sparse clone, then the release tarball. A dirty **code** tree or diverged history is refused, never reset. Use `--prerelease` only when deliberately tracking prereleases.

---

## Command reference

```text
python3 main.py --preflight              contract docs + environment + profile + role (24 h marker)
python3 main.py --no-preflight ...       skip the gate for this command (explicit user consent only)
python3 main.py --doi DOI                extract an evidence pack by DOI
python3 main.py --url URL                extract from an article URL
python3 main.py --pdf PATH               extract from a local PDF
python3 main.py --batch-pdfs             process every PDF in input_pdfs/
python3 main.py --new-literature         open configured journal pages; list only
python3 main.py --journals-init          create .geo-reader/journals.json
python3 main.py --check-note [NOTE]      check one note or all notes
python3 main.py --index NOTE             add/update a row in papers/INDEX.md
python3 main.py --list                   list evidence packs and notes
python3 main.py --profile [--json]       show current preferences
python3 main.py --guide                  print the quick-start guide
python3 main.py --check-update           check GitHub for a newer release
python3 main.py --update                 update code; keep preferences, notes and packs
python3 main.py --doctor                 verbose environment diagnostics
python3 main.py                          interactive menu (terminal only)
```

After `pip install -e .`, `geo-reader` and `geo-doctor` are also available.

---

## Directory layout

```text
geo-academic-reader/
├── AGENTS.md                    Session contract, onboarding, SOP
├── MEMORY.md                    Durable decisions that survive versions
├── LESSONS.md                   Failure modes and what they changed
├── PROMPTS.md                   Copy-paste task prompts
├── SKILL.md                     Skill manifest and condensed contract
├── journals.json                Shipped journal pages (parser, URL, volumes)
├── input_pdfs/                  PDF drop-zone (local, git-ignored)
├── papers/                      Self-contained knowledge base
│   ├── INDEX.md                 Note catalogue (generated locally)
│   ├── <slug>.md                Agent-written note
│   └── assets/<slug>/fig_XX.png Figure library, same tree as the note
├── .raw/<slug>/                 Evidence pack (local, git-ignored)
│   ├── paper.json
│   ├── fulltext.md
│   ├── figures/manifest.json
│   └── README.md
├── .geo-reader/                 Local state (git-ignored)
│   ├── profile.json             Preferences
│   ├── preflight.json           24 h session marker
│   ├── journals.json            User journal list (preferred over the shipped one)
│   └── journal-scan/
│       ├── latest.md            Latest numbered candidate list
│       └── translations.json    Chinese-title cache
├── templates/                   Note and review templates
├── rules/                       Markdown, journal and troubleshooting rules
├── scripts/                     Extraction, QA, preflight, CLI
├── main.py / doctor.py          Entry point / environment diagnostics
└── install.* / uninstall.*
```

### Evidence-pack contract

`paper.json`: bibliographic metadata, APA string and whether it was constructed, extraction method, open-access status, warnings, stats and relative paths.
`fulltext.md`: raw extracted text with page markers — evidence, not a summary.
`figures/manifest.json`: the sole authority for captions and figures.

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

---

## A classic paper is a citation network

A “classic-paper read” that only restates one PDF is a book report. Every note needs `## 0. 文献坐标` with a `年份 | 工作 | 核心贡献 | 与本文的关系` table, an explicit **competing explanations** paragraph and an explicit **later tests** paragraph.

| `note_depth` | Minimum external works | Typical use |
| :--- | :--- | :--- |
| `brief` | 3 | One-page brief |
| `standard` | 6 | Default single-paper note |
| `deep` | 10 | Classic-paper deep read |
| `note_type: 经典文献综述` | 15 | Multi-paper review |

The anchor paper does not count as an external work. Only entries under `## 参考文献` count, and each external work should have a DOI. If the literature was not read, say which part is missing instead of padding the list.

---

## Figures and VS Code preview

VS Code's built-in Markdown preview only loads local images under the workspace folder (or, in a single-file window, under the note's own folder). The figure library therefore lives inside `papers/`:

```markdown
![Figure 1: caption](assets/<slug>/fig_01.png)
*Figure 1: caption (source: browser; original: https://...)*
```

QA rejects `../assets/...`, `./assets/...`, absolute paths, `file://` and `<img>`. Callouts use labelled blockquotes such as `> **一句话结论**`, because VS Code does not render GitHub's `> [!NOTE]` syntax.

---

## Troubleshooting

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
| `--check-update` says offline | GitHub unreachable | Not an error; retry with `--refresh`, or set `GEO_READER_NO_UPDATE_CHECK=1` |
| `--update` refuses | Dirty code tree or diverged history | Commit or `git stash`; never `reset --hard` |
| Journal list is empty | Page disabled, parser drift, or advanced volumes | Check `enabled` / `url`; update EPSL `volumes`; fix the parser |
| Chinese title shows “暂缺” | Translation rate limit or outage | Rerun `--new-literature`; cached titles are reused; never invent one |

More: [rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md), [rules/JOURNALS.md](rules/JOURNALS.md), [LESSONS.md](LESSONS.md).

---

## Diagnostics and cleanup

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

## License

[MIT](LICENSE)
