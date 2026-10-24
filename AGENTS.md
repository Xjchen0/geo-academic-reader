# AGENTS.md — geo-academic-reader v0.4.0

> **Read this file before doing any literature task in this workspace.**
> The workspace turns papers (DOI / URL / PDF) into a **raw evidence pack**, then the agent writes a **VS Code-ready literature note** from that evidence. The Python pipeline never writes review prose.

---

## 0. First run: conversational onboarding (mandatory)

There is **no setup script and no wizard**. A first-time user must leave no trace until the agent has talked to them. The trigger instructions live here and in `PROMPTS.md`.

### 0.1 Check for a profile

At the start of every session, read `.geo-reader/profile.json`:

```bash
python3 main.py --profile --json
```

- `"exists": true` → load the values and continue. **Never re-onboard** a returning user.
- `"exists": false` → run the onboarding below **before** extracting any paper, even if the user's first message already contains a DOI, URL or PDF. Do not ask the user to run a command. Do not create `.geo-reader/` yet.

### 0.2 Ask, in conversation

Use the agent's question UI when available (Qoder `AskUserQuestion`, Claude Code choices, etc.). Otherwise ask in two compact numbered batches. Accept short answers such as `1A 2B 3A ...`.

**Batch 1 — how to work**
1. **Language** for notes and replies: `zh-CN` (中文) / `en` / `bilingual`.
2. **Editor** where Markdown is read: `vscode` / `cursor` / `claude-code` / `antigravity` / `windsurf` / `cli`.
3. **Instruction style**:
   - `guided` — one stage at a time, outline first, confirm key claims.
   - `balanced` — autonomous extraction + writing, ask only about scope, paywalls or ambiguity.
   - `expert` — batch work, minimal narration, final report.

**Batch 2 — extraction defaults**
4. **Browser policy**: `auto` (reuse/launch Chrome, high-resolution figures first) / `existing` (only reuse CDP 9222) / `off` (HTTP/PDF fallback).
5. **Note depth**: `brief` (1-page brief) / `standard` (IMRaD) / `deep` (per-figure reading).
6. **Citation format**: `apa` / `nature` / `gbt7714`.
7. **Journal list** for “找新文献”: `default` (the shipped `journals.json`, 17 journal pages / sections) / `custom` (the user will supply page URLs or volume numbers later).
   - For `custom`, do not guess: run `python3 main.py --journals-init`, ask the user to edit `.geo-reader/journals.json`, and scan on a later turn.
8. Optional: **agent name** and a **contact email** for polite API requests. Both may be skipped.

If the user says “use defaults”, take `zh-CN`, `vscode`, `balanced`, `auto`, `deep`, `apa` and the shipped journal list. Say which defaults were used.

### 0.3 Persist the answers

Write `.geo-reader/profile.json` yourself (create the directory). Use this schema:

```json
{
  "version": 1,
  "language": "zh-CN",
  "ide": "vscode",
  "agent": "qoder",
  "style": "balanced",
  "browser": "auto",
  "note_depth": "deep",
  "citation": "apa",
  "citation_contact": "",
  "created_at": "2026-10-24T10:00:00+08:00",
  "updated_at": "2026-10-24T10:00:00+08:00"
}
```

- Allowed values are enforced by `scripts/config.py:PROFILE_CHOICES`.
- Keep `created_at` when updating; refresh `updated_at`.
- Tell the user one line: “偏好已保存；以后直接给我 DOI / URL / PDF 即可。”
- Then show the working loop in three short lines so a first-time user learns the commands without reading the README:
  1. `python3 main.py --doi "<DOI>"` produces `.raw/<slug>/` and `papers/assets/<slug>/`.
  2. You write `papers/<slug>.md` from `templates/paper_note.md`; figures use `assets/<slug>/fig_XX.png`.
  3. `python3 main.py --check-note papers/<slug>.md --fix` then `--index` closes the loop.
  Mention that copy-paste prompts are in `PROMPTS.md` and that `重新设置偏好` changes the profile.
- `.geo-reader/` is git-ignored and stays local.
- The journal list is **not** stored in the profile: `journals.json` is the shipped default, and `.geo-reader/journals.json` is the user copy (preferred, preserved by updates). Never infer a journal list from the conversation; create the user copy with `--journals-init` and let the user edit it.

### 0.4 Reconfigure and persistence

- Trigger phrases: `开始使用`, `首次使用`, `Start`, `Set up`, or any first literature request while the profile is missing.
- `重新设置偏好` / `Reconfigure` → ask the questions again, update the existing profile, keep `created_at`.
- Preferences persist across sessions and across repeated tests. Never delete or reset `.geo-reader/profile.json` just because the code was updated.
- If the profile is corrupted, back it up to `.geo-reader/profile.json.bak`, ask the questions again, then rewrite it.

### 0.5 Adapt to the profile

| Profile field | Values | Agent behaviour |
| :--- | :--- | :--- |
| `language` | `zh-CN` / `en` / `bilingual` | Write notes and replies in this language. |
| `style` | `guided` | One stage at a time; show the outline before writing; confirm key claims. |
| `style` | `balanced` | Complete extraction and note autonomously; ask only about scope, paywalls or ambiguity. |
| `style` | `expert` | Batch work, minimal narration, final report with files and open issues. |
| `browser` | `auto` | Launch/reuse Chrome and prefer browser figures. |
| `browser` | `existing` | Only reuse an already-running CDP 9222 session. |
| `browser` | `off` | Use HTTP/PDF fallback and state that figures may be lower quality. |
| `note_depth` | `brief` / `standard` / `deep` | 1-page brief / standard IMRaD / per-figure deep read. |
| `citation` | `apa` / `nature` / `gbt7714` | Citation format for the reference section. |

`python3 main.py --guide` prints the same choices for the user.

### 0.6 Updates: check after a task, upgrade only with consent

- After finishing a literature task, run `python3 main.py --check-update` once. It uses a 6-hour cache and exits 0 when GitHub is unreachable, so it never turns a successful task into a failure. The CLI also prints a one-line hint after extraction/QA when a newer release is known.
- If a newer version exists, report it in one line (`current → latest`, release URL) and offer `python3 main.py --update`. Never upgrade without the user's consent.
- `--update` preserves `.geo-reader/profile.json` (with a timestamped backup under `.geo-reader/backups/`), `papers/`, `.raw/` and `input_pdfs/`. Git checkouts fast-forward to the release tag; a copy without `.git` uses a shallow sparse clone, then the release tarball. A dirty tracked tree or diverged history is refused, never reset.
- `GEO_READER_NO_UPDATE_CHECK=1` disables the automatic hint for offline or metered use.

Version policy: a small change (fix, docs, local improvement) bumps the patch (`0.3.0 → 0.3.1`); a new capability bumps the minor unless the user asks otherwise. Tags are never reused; release notes live in the GitHub release body. The updater itself ships from 0.3.1 onward, so an older copy needs one manual `git pull --ff-only` (or a fresh download) before `--update` exists.

---

## 1. Non-negotiable rules

### 1.1 No fabricated content (P0)

- **Never** write generic paragraphs, placeholder equations, or template conclusions that are not supported by the evidence pack.
- **Never** invent a formula, sample size, location, parameter, citation, DOI, or figure caption.
- If the evidence is missing, write **“原文未提供”** and explain what is missing.
- Do not use the old pathology of filling a note with “本研究关注的科学核心问题在于……” or a generic \(\mathcal{F}(x,t)=\sum\alpha_k e^{-\lambda_k t}\Phi_k(x)\). Such placeholder content is detected by `--check-note` and must be deleted.
- Do not write a review from web-search snippets alone. Use the local evidence pack; if you must use an external source, label it as unverified and give the link.

### 1.2 Browser-first figures (P0)

For **DOI**, **URL**, and **PDF that contains a DOI**:

1. First try Chrome/CDP (`--browser auto`). This is the default.
2. Only if the browser fails (no Chrome, Cloudflare challenge, empty figure list) may you fall back to direct HTTP.
3. Only if both fail may you use PDF-embedded images. When you do, state it explicitly and mark the figure origin as `pdf` in the note.
4. Never present a PDF-page crop as if it were the publisher's high-resolution figure.

The pipeline writes the actual origin into `figures/manifest.json` (`browser`, `http`, or `pdf`). Read it; do not guess.

### 1.3 Image paths must render in VS Code (P0)

The figure library lives **inside `papers/`**, next to the notes:

```text
papers/
├── <slug>.md
├── INDEX.md
└── assets/
    └── <slug>/
        └── fig_01.png
```

The only valid form is note-relative and never leaves `papers/`:

```markdown
![图 1：图注](assets/<slug>/fig_01.png)
```

- **Never** use `../assets/...`, `./assets/...`, `/Users/.../assets/...`, `file://...`, or HTML `<img>`.
- Why: VS Code's Markdown preview only loads local images under the current workspace root (or the note's own folder for single-file windows). A project-root `assets/` directory breaks when the user opens `papers/` or a single note — the link hovers still work, which makes the failure look inconsistent.
- Before claiming completion, run:
  ```bash
  python3 main.py --check-note papers/<slug>.md --fix
  ```
  This verifies file existence, non-zero size, image magic bytes, note-relative paths, placeholder content, unbalanced `$$`, GitHub alert syntax (§4), and the citation network of §1.5 (related-works section, reference section, external count, citation table, DOI coverage, duplicate DOIs). With `--fix` it also migrates legacy root-level `assets/` into `papers/assets/`, rewrites the links, and converts alert markers into blockquotes.

### 1.4 Academic neutrality

- Forbidden: “颠覆一切”, “彻底终结”, “空前重大突破”, “完美解决”, “前所未有”.
- Required: state boundary conditions, sample limits, parameter sensitivity and model assumptions.
- Distinguish **direct evidence**, **author inference**, and **your own assessment**.

### 1.5 A classic-paper note is a citation network (P0)

A “经典文献精读” is not a summary of one PDF. It has to show what the paper inherited, what it argued against, and what later work did to it. `--check-note` enforces the mechanical part:

| `note_depth` | Minimum external works | Typical use |
| :--- | :--- | :--- |
| `brief` | 3 | one-page briefing |
| `standard` | 6 | default single-paper note |
| `deep` | 10 | classic-paper deep read |
| any + `note_type: 经典文献综述` | 15 | multi-paper review |

Required structure:

- A `## 0. 文献坐标` (or 文献脉络 / 研究脉络 / 时间线) section, with a table of at least 5 data rows: `年份 | 工作 | 核心贡献 | 与本文的关系`. Cover **prehistory, competing explanations, and later tests** — not only papers that support the anchor.
- An explicit **竞争解释** paragraph with at least two rivals and the criterion each one depends on. If the anchor cannot exclude a rival, say so.
- An explicit **后续检验** paragraph. If you did not search for later work, write “检索未覆盖” rather than implying none exists.
- A `## 参考文献` section. Every external work gets a DOI or a stable link. Entries you could not verify must be marked “自动构造，需核对”.

Counting and verification rules:

- Only entries under the reference heading count; inline mentions in the body do not.
- The anchor paper itself is excluded from the external count.
- Duplicate DOIs, entries without a DOI, a missing reference section and a missing 文献坐标 section are reported by `--check-note`.
- Do not pad the list with papers you did not read. Three well-understood rivals are worth more than ten decorative citations; if the count is below target, say what is missing instead of inventing entries.

### 1.6 “找新文献” = 打开期刊官网，只列候选，等待选择（P0）

当用户说“找新文献”“最近有什么新文章”“推荐文献”“看看期刊新文章”时：

1. **只打开配置好的期刊页面**。不要用 OpenAlex / WebSearch 按主题检索，不要从现有笔记、`INDEX.md` 或对话上下文推断用户“可能想看什么”。
2. 运行 `python3 main.py --new-literature`。它读取 `journals.json`（个人副本 `.geo-reader/journals.json` 优先），用 Chrome/CDP 逐页打开每本期刊的 research-articles、current issue、early publication 或最近卷期页面，按页面自己的条目解析标题、DOI 和日期，写入 `.geo-reader/journal-scan/latest.md` 与 `latest.json`。
3. 默认 `--days 0`：页面列出什么就列什么，不加日期窗口。需要只看最近几天时再传 `--days N`；无日期的条目（例如 EPSL 卷期页）仍保留。
4. 把编号候选（**英文原题 + 中文机译标题**、期刊、日期、DOI）呈现给用户，然后**停止**。本轮不要运行 `--doi`，不要创建 `.raw/<slug>/`，不要写 `papers/*.md`。
5. 只有用户明确给出编号或 DOI 后，才逐篇执行 `--doi` 并进入精读流程。用户选了多篇时，一篇一篇建证据包；`papers/INDEX.md` 由父 Agent 串行更新。

**中文标题**：扫描默认调用 Bing 翻译，为每条候选补 `title_zh`，写入 `latest.md` 的“中文（机译）：…”一行和 `latest.json` 的 `title_zh` 字段。约定如下：

- 中文标题是**机器翻译，仅供检索**；英文原题才是准据。向用户呈现时保留英文原题，不要把机译标题当成论文正式标题。
- 翻译结果缓存在 `.geo-reader/journal-scan/translations.json`（按英文原题去重），重跑只翻译新条目。地学术语在读取时做后编辑（如 fugacity→逸度、sub-arc→弧下、large igneous province→大火成岩省）。
- 少数条目可能因限流或服务不可用而显示“暂缺”；如实说明并建议重跑，**不得**自行编造中文标题。
- 需要纯英文清单时传 `--no-translate`。

扫描为空或部分期刊报错时，报告扫描过的页面和错误原因，并建议检查清单；**不得**改用主题搜索来“补”一个列表。用户明确要求“找某个主题的新文献”时，说明这是主题检索（不是期刊清单扫描），先确认口径再动手。

`journals.json` v2 的每一项是一个页面：`key`、`name`、`parser`、`url`（或 `url_template` + `volumes`）、`enabled`，可选 `wait`、`scroll`、`ready`、`challenge_timeout`。`parser` 决定用哪个解析器，当前支持 `nature`、`science_first`、`science_current`、`science_advances`、`epsl`、`agu`、`geology_current`、`geology_early`、`gji`、`pnas`。默认清单对应 17 个区块（Nature 系列 4 个页面、Science First Release / Current、Science Advances、EPSL 4 个卷、AGU 5 本、Geology 2 个页面、GJI、PNAS）。

- **Cloudflare / 人机验证**：浏览器停在验证页时，脚本只等待并报告，不自动刷新。让用户在打开的 Chrome 窗口完成验证，然后重跑同一条命令。
- **EPSL 卷号会前进**：清单用 `vol/699/suppl/C` 这类卷期页；结果异常少时先更新 `volumes`。
- **不按关键词过滤**：页面列出的就是候选。Nature / Science 这类综合刊会包含非地学论文，这是清单本身的定义，不要临时加主题过滤。

---

## 2. Directory contract

| Path | Role |
| :--- | :--- |
| `input_pdfs/` | Drop-zone for raw PDFs. |
| `.raw/<slug>/paper.json` | Metadata + extraction provenance (no full text). |
| `.raw/<slug>/fulltext.md` | Extracted text with page / section markers. |
| `.raw/<slug>/figures/manifest.json` | Figure captions, origin, dimensions, local paths. |
| `.raw/<slug>/README.md` | Human-readable evidence summary + next steps. |
| `papers/assets/<slug>/fig_01.png` | Final figure files referenced by notes. |
| `papers/<slug>.md` | Agent-written literature note (the only review artifact). |
| `papers/INDEX.md` | Note catalog, maintained by `--index`. |
| `templates/paper_note.md` | Mandatory single-paper note template. |
| `templates/literature_review.md` | Multi-paper review template. |
| `journals.json` | Shipped journal page list (parser, URL or volume template, enabled flag, per-page waits). |
| `.geo-reader/journals.json` | User copy, preferred over the shipped list; created by `--journals-init`. |
| `.geo-reader/journal-scan/latest.md` | Latest numbered candidate list; the agent reads this, then waits. |
| `.geo-reader/journal-scan/scan-<date>.json` | Machine-readable result of the same scan (per-page status and errors). |
| `.geo-reader/journal-scan/translations.json` | Chinese-title cache (English title → machine translation); git-ignored. |
| `PROMPTS.md` | Copy-paste prompts for users, including first-run triggers. |
| `rules/` | Scraping, KaTeX, troubleshooting details. |

`.raw/` and `.geo-reader/` are local and git-ignored. `papers/` (notes **and** their assets) is the durable, self-contained knowledge base.

---

## 3. Standard operating procedure

### Step 0 — “找新文献”：open the journal pages, list only, then stop (P0)

```bash
python3 main.py --new-literature
# Optional date filter (0 or omitted = page as-is): --days 3
# Scan only a few pages: --journal epsl --journal geology_early
# English-only list: --no-translate
# Create the editable user copy: python3 main.py --journals-init
```

The scan opens each configured page in Chrome/CDP, parses the page's own entries, adds a cached Chinese machine translation of each title, and writes `.geo-reader/journal-scan/latest.md`. Read that file, present the numbered candidates — English title with the Chinese line beneath it, journal, date, DOI — to the user, and **end the turn**. Do not call `--doi`, do not create `.raw/`, and do not write a note until the user replies with numbers or DOIs. Never invent a Chinese title when translation failed; say it is missing. Details and edge cases: §1.6.

### Step 1 — Environment check

```bash
python3 doctor.py
```

If Chrome or a package is missing, tell the user the exact command. Do not silently downgrade to PDF figures.

### Step 2 — Extract the evidence pack

```bash
# DOI
python3 main.py --doi "10.1038/s41467-026-69772-8"

# URL
python3 main.py --url "https://www.nature.com/articles/s41467-026-69772-8"

# Local PDF (the pipeline extracts the DOI and then prefers browser figures)
python3 main.py --pdf "input_pdfs/paper.pdf"

# Batch
python3 main.py --batch-pdfs
```

Useful options:
- `--browser auto|existing|off`
- `--wait 6` (longer wait for Cloudflare/JS pages)
- `--max-figures 40`
- `--json` (machine-readable summary)

The command **does not** create `papers/<slug>.md`. It prints the slug and paths.

### Step 3 — Read the evidence pack

Read in this order:

1. `.raw/<slug>/paper.json` — metadata, DOI, journal, year, APA citation, warnings, stats.
2. `.raw/<slug>/fulltext.md` — text with page markers (PDF) or clean article text (web).
3. `.raw/<slug>/figures/manifest.json` — each figure's caption, origin, page, dimensions and `markdown_path`.

If `warnings` contains “正文少于 800 字符”, treat the text as insufficient. Tell the user; do not fabricate a full review. Try `--browser auto --wait 8`, an OA PDF, or ask for a PDF.

### Step 4 — Write the note

Use `templates/paper_note.md`. Fill every `{{PLACEHOLDER}}`; delete unused figure sections.

Required content:
- Front matter: `title`, `journal`, `year`, `doi`, `source`, `raw`, `status`, `note_type`, `note_depth`, `reviewed_at`, `tags`. `note_depth` drives the reference target; set it to `brief`, `standard` or `deep` rather than leaving the placeholder.
- One-sentence conclusion in a blockquote with a bold label, `> **一句话结论**`.
- `## 0. 文献坐标` with a citation-network table (≥5 rows) plus **竞争解释** and **后续检验** paragraphs, per §1.5.
- Research question and explicit hypotheses (or “作者未显式提出假说”).
- Data, methods, boundary conditions, reproducibility.
- Per-figure reading: axes, variables, controls, inflection points, what the figure supports/does not support.
- Mechanism/discussion, separating evidence from inference.
- Limitations in a blockquote labelled `> **边界条件与未解问题**`, including author-stated and reader-identified limits.
- `## 参考文献` with the anchor plus every external work; each external work needs a DOI. Mark constructed citations as “自动构造，需核对”.

**Evidence anchors** are mandatory for key claims:
- PDF: `（第 3 页）`
- Web: `（原文 §Results 第 2 段）`
- Figure: `（图 2）`

### Step 5 — QA before delivery

```bash
python3 main.py --check-note papers/<slug>.md --fix
python3 main.py --index papers/<slug>.md
```

If `--check-note` reports errors that cannot be fixed automatically (missing figures, placeholder prose, a missing 文献坐标 section, too few external works), fix them manually or re-run extraction with browser enabled. `--fix` rewrites GitHub alert markers into renderable blockquotes; review the generated labels because it cannot infer the right wording.

### Step 6 — Report to the user

Report:
- Note path and evidence-pack path.
- Figure count and origin (`browser` / `http` / `pdf`).
- Any warnings or unverified claims.
- The exact next command the user may want.

Do not claim completion if images are missing or the note still contains placeholders.

### Step 7 — Check for updates (after the task)

```bash
python3 main.py --check-update          # cached for 6 h; exit 0 when offline
python3 main.py --update --dry-run      # show the target without changing files
python3 main.py --update                # apply; profile, notes and packs are kept
```

Report the result only when an update exists, or when the user asked for a check. Use `--prerelease` only if the user is deliberately tracking prereleases.

---

## 4. Math and Markdown standards

- Inline math: `$E = mc^2$` — no space immediately inside `$`.
- Display math:
  ```markdown
  $$
  \frac{\partial \mathbf{u}}{\partial t} + (\mathbf{u}\cdot\nabla)\mathbf{u} = -\frac{1}{\rho}\nabla p + \nu\nabla^2\mathbf{u}
  $$
  ```
- Only include equations that appear in the paper or are explicitly labelled as your derivation.
- Callouts use plain blockquotes with a bold first line — **not** GitHub alert syntax (`> [!NOTE]`), because VS Code's built-in Markdown preview renders that syntax as literal text:
  ```markdown
  > **一句话结论**
  >
  > 核心结论及其成立条件。
  ```
  Use the labels `一句话结论`, `关键前提`, `读图要点`, `边界条件与未解问题`, `机制链条`, `检索局限`.
- Full rules: `rules/MARKDOWN_SPEC.md`.

---

## 5. Index maintenance

After the note passes QA:

```bash
python3 main.py --index papers/<slug>.md
```

This updates `papers/INDEX.md` with: date, title, journal, year, DOI/source, note link, status. Do not hand-edit rows unless `--index` cannot infer the metadata; if you do, keep the 7-column schema.

For a review covering multiple papers, use `templates/literature_review.md`; every cited paper must have a DOI and a reference entry.

---

## 6. Batch and subagent policy

- For 5+ papers, delegate one paper per subagent with an isolated context.
- Each subagent receives: the slug, `.raw/<slug>/`, `templates/paper_note.md`, and the QA commands.
- The parent agent receives only: note path, one-paragraph summary, figure origin, warnings.
- Never let a subagent write directly into `papers/INDEX.md` concurrently; the parent runs `--index` sequentially.

---

## 7. Completion checklist

- [ ] Profile exists (or onboarding completed in this conversation and saved).
- [ ] “找新文献”只打开了 `journals.json` / `.geo-reader/journals.json` 里的期刊页面，没有按对话主题自选文献。
- [ ] 候选清单以编号呈现（英文原题 + 中文机译标题），并在用户选择前停止；未创建证据包或笔记。
- [ ] `doctor.py` clean, or limitations stated.
- [ ] Evidence pack exists: `paper.json`, `fulltext.md`, `figures/manifest.json`.
- [ ] Figures preferred from browser; PDF fallback explicitly marked.
- [ ] Note written from `templates/paper_note.md`; no placeholder prose.
- [ ] Every key claim has an evidence anchor.
- [ ] `## 0. 文献坐标` has a ≥5-row citation table plus 竞争解释 and 后续检验; external works meet the `note_depth` target.
- [ ] Every external work has a verified DOI, or is marked “自动构造，需核对”.
- [ ] Every image uses `assets/<slug>/...` inside `papers/` and passes `--check-note`.
- [ ] No GitHub alert syntax (`> [!NOTE]`) remains in the note.
- [ ] `papers/INDEX.md` updated with `--index`.
- [ ] User received paths, figure origin and warnings.
- [ ] Update check run once (`--check-update`); result mentioned only if an update exists or the user asked.

---

## 8. Quick recovery

| Symptom | Action |
| :--- | :--- |
| “找新文献”没有先给清单 | 运行 `python3 main.py --new-literature`；不要改用主题搜索或从笔记推断 |
| 扫描结果为 0 | 检查 `.geo-reader/journals.json` 的 `url` / `enabled`；EPSL 先更新 `volumes`；页面改版后可能需要更新对应 `parser` |
| 期刊清单缺失 / JSON 错误 | `python3 main.py --journals-init`；确需覆盖个人副本时用 `--force`，或恢复 `journals.json` |
| 候选缺少中文标题 | 翻译服务限流或不可用；重跑 `python3 main.py --new-literature` 会补齐（缓存已译条目），不要自行编造；只要英文清单时用 `--no-translate` |
| 中文标题有术语错误 | 缓存保存原文机译，读取时应用 `scripts/translate.py` 的术语后编辑；补充规则即可，无需清缓存 |
| 个人清单是旧版 ISSN/Crossref 格式 | 备份 `.geo-reader/journals.json`，再运行 `python3 main.py --journals-init --force`；新清单按页面 URL 配置 |
| 扫描卡在 Cloudflare / 人机验证 | 在打开的 Chrome 窗口手动完成验证，然后重跑同一条命令；脚本不会自动刷新 |
| 某本期刊一直解析不到条目 | 把该页面的 HTML 存下来检查选择器；`parser` 与页面结构不匹配时条目会为 0，而不是编造 |
| No profile | Onboard in conversation, then write `.geo-reader/profile.json`; never ask for `--setup` |
| Chrome not running | `python3 main.py --doi ... --browser auto` (launches it) |
| Cloudflare challenge | Complete the check in the opened Chrome window; retry with `--wait 8` |
| 0 figures from browser | Check `manifest.json`; retry URL instead of DOI; then HTTP; PDF last |
| Images not visible in VS Code | Run `--check-note --fix`; confirm the note uses `assets/<slug>/...`, not `../assets/...` |
| Legacy root `assets/` | `python3 main.py --check-note --fix` copies files into `papers/assets/` and rewrites links |
| Note looks generic | Delete it and re-write from the evidence pack; never keep placeholder prose |
| `github_alert_syntax` | Run `--check-note --fix`, then reword the generated `> **要点**` label to the real one |
| `thin_reference_context` | Add the missing prehistory / rival / later-test papers, or lower `note_depth` if the user asked for a brief |
| `missing_reference_section` | Add `## 参考文献`; do not leave the anchor as the only entry |
| `--check-update` says offline | Not an error; retry later with `--refresh`, or set `GEO_READER_NO_UPDATE_CHECK=1` to silence the hint |
| `--update` refuses on a dirty tree | Commit or `git stash` the code changes; never `git reset --hard`. Notes and `.raw/` are unaffected |
| `--update` fails to fast-forward | Local history diverged from the release; report it and let the user decide (merge/rebase). Never force |
| Profile missing after an update | Restore `.geo-reader/backups/profile-<timestamp>.json`; `--update` also restores it automatically |
| Crossref 404 | Use `--url` or `--pdf`; the pipeline will still build an evidence pack |

Detailed recovery: `rules/TROUBLESHOOTING.md`.
