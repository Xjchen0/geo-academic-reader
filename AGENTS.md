# AGENTS.md — geo-academic-reader v0.2.1

> **Read this file before doing any literature task in this workspace.**
> The workspace turns papers (DOI / URL / PDF) into a **raw evidence pack**, then the agent writes a **VS Code-ready literature note** from that evidence. The Python pipeline never writes review prose.

---

## 0. First run: load the user profile

At the start of every session:

1. Read `.geo-reader/profile.json` if it exists.
2. If it does not exist, ask the user to run:
   ```bash
   python3 main.py --setup
   ```
   or run the wizard yourself when the user wants guidance. Do not silently assume preferences.
3. Adapt your behaviour to the profile:

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

The onboarding choices are also printed by:
```bash
python3 main.py --guide
```

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

- Notes live in `papers/`; figures live in `assets/<slug>/`.
- The only valid relative form is:
  ```markdown
  ![图 1：图注](../assets/<slug>/fig_01.png)
  ```
- **Never** use `./assets/...` or `assets/...` from a note in `papers/`; those resolve to `papers/assets/...` and show a broken image.
- Do not use HTML `<img>` tags or absolute `file://` paths.
- Before claiming completion, run:
  ```bash
  python3 main.py --check-note papers/<slug>.md --fix
  ```
  This verifies file existence, non-zero size, image magic bytes, relative path correctness, placeholder content and unbalanced `$$`.

### 1.4 Academic neutrality

- Forbidden: “颠覆一切”, “彻底终结”, “空前重大突破”, “完美解决”, “前所未有”.
- Required: state boundary conditions, sample limits, parameter sensitivity and model assumptions.
- Distinguish **direct evidence**, **author inference**, and **your own assessment**.

---

## 2. Directory contract

| Path | Role |
| :--- | :--- |
| `input_pdfs/` | Drop-zone for raw PDFs. |
| `.raw/<slug>/paper.json` | Metadata + extraction provenance (no full text). |
| `.raw/<slug>/fulltext.md` | Extracted text with page / section markers. |
| `.raw/<slug>/figures/manifest.json` | Figure captions, origin, dimensions, local paths. |
| `.raw/<slug>/README.md` | Human-readable evidence summary + next steps. |
| `assets/<slug>/fig_01.png` | Final figure files referenced by notes. |
| `papers/<slug>.md` | Agent-written literature note (the only review artifact). |
| `papers/INDEX.md` | Note catalog, maintained by `--index`. |
| `templates/paper_note.md` | Mandatory single-paper note template. |
| `templates/literature_review.md` | Multi-paper review template. |
| `PROMPTS.md` | Copy-paste prompts for users. |
| `rules/` | Scraping, KaTeX, troubleshooting details. |

`.raw/` and `.geo-reader/` are local and git-ignored. `papers/` and `assets/` are the durable knowledge base.

---

## 3. Standard operating procedure

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
- Front matter: `title`, `journal`, `year`, `doi`, `source`, `raw`, `status`, `reviewed_at`, `tags`.
- One-sentence conclusion under `> [!NOTE]`.
- Research question and explicit hypotheses (or “作者未显式提出假说”).
- Data, methods, boundary conditions, reproducibility.
- Per-figure reading: axes, variables, controls, inflection points, what the figure supports/does not support.
- Mechanism/discussion, separating evidence from inference.
- Limitations under `> [!WARNING]`, including author-stated and reader-identified limits.
- References; mark constructed citations as “自动构造，需核对”.

**Evidence anchors** are mandatory for key claims:
- PDF: `（第 3 页）`
- Web: `（原文 §Results 第 2 段）`
- Figure: `（图 2）`

### Step 5 — QA before delivery

```bash
python3 main.py --check-note papers/<slug>.md --fix
python3 main.py --index papers/<slug>.md
```

If `--check-note` reports errors that cannot be fixed automatically (missing figures, placeholder prose), fix them manually or re-run extraction with browser enabled.

### Step 6 — Report to the user

Report:
- Note path and evidence-pack path.
- Figure count and origin (`browser` / `http` / `pdf`).
- Any warnings or unverified claims.
- The exact next command the user may want.

Do not claim completion if images are missing or the note still contains placeholders.

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
- GFM alerts:
  - `> [!NOTE]` — core question / one-sentence conclusion.
  - `> [!IMPORTANT]` — parameters and constraints.
  - `> [!TIP]` — how to read a figure.
  - `> [!WARNING]` — limitations and uncertainty.
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

- [ ] Profile read (or user asked to run `--setup`).
- [ ] `doctor.py` clean, or limitations stated.
- [ ] Evidence pack exists: `paper.json`, `fulltext.md`, `figures/manifest.json`.
- [ ] Figures preferred from browser; PDF fallback explicitly marked.
- [ ] Note written from `templates/paper_note.md`; no placeholder prose.
- [ ] Every key claim has an evidence anchor.
- [ ] Every image uses `../assets/<slug>/...` and passes `--check-note`.
- [ ] `papers/INDEX.md` updated with `--index`.
- [ ] User received paths, figure origin and warnings.

---

## 8. Quick recovery

| Symptom | Action |
| :--- | :--- |
| Chrome not running | `python3 main.py --doi ... --browser auto` (launches it) |
| Cloudflare challenge | Complete the check in the opened Chrome window; retry with `--wait 8` |
| 0 figures from browser | Check `manifest.json`; retry URL instead of DOI; then HTTP; PDF last |
| Images not visible in VS Code | `python3 main.py --check-note papers/<slug>.md --fix` |
| Note looks generic | Delete it and re-write from the evidence pack; never keep placeholder prose |
| Crossref 404 | Use `--url` or `--pdf`; the pipeline will still build an evidence pack |

Detailed recovery: `rules/TROUBLESHOOTING.md`.
