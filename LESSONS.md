# LESSONS — Operational Notes

Observations from running this workspace on real papers. The theme is the same throughout: keep extraction and interpretation separate, and keep the parent context small.

---

## [tags: architecture, evidence, separation] Scripts Extract, Agents Interpret

- The most damaging failure was a generator that produced plausible paragraphs and sample equations for every paper. It made notes look complete while destroying trust in them.
- The current contract is narrow on purpose: `.raw/<slug>/paper.json`, `fulltext.md`, `figures/manifest.json`, and `papers/assets/<slug>/` only. No review text is generated.
- When a note looks thin, the fix is better evidence or an honest `原文未提供`, not a more fluent template.
- If the evidence pack and the note disagree about figure origin, the manifest wins.

## [tags: figures, browser-first, resolution] Browser First, PDF Second

- Publisher thumbnails (`/w400/`, `/lw685/`, `.medium.gif`) are often what appears in the initial DOM. Rewrite to `/full/`, `/w1200/`, or `.large.jpg` before downloading.
- A rendered page is the best source for figure order, captions, and panel structure. PDF embedded images often split a multi-panel figure or lose the caption entirely.
- For a PDF with a DOI, the pipeline still opens the publisher page. PDF figures are only a fallback, and `paper.json.method` must reflect that.
- Direct image URLs may return 403 even when the page is accessible. Fetching in the page context works because the browser supplies the session and referer.
- Never describe a PDF bitmap as a "high-resolution publisher figure".

## [tags: access, cloudflare, ethics] Access Is Not Bypass

- Reusing the user's Chrome session is about rendering and figure access, not circumventing paywalls.
- Cloudflare and similar checks are interactive. Wait, complete them manually if needed, then retry with `--browser existing`.
- Batch jobs run sequentially. Parallel crawls against one publisher are both fragile and impolite.
- Open-access PDFs (OpenAlex, arXiv, bioRxiv, PMC) are preferable for text. Use the paywalled page only for what the session can already see.

## [tags: captions, manifest, honesty] Captions Are Evidence

- Caption extraction is the weakest link. A figure may have no `figcaption`, a caption shared across panels, or a caption far from the image.
- The manifest records what was found. The note must not upgrade an empty caption into a confident title.
- When `is_body_figure` is false or uncertain, check the image manually before using it. Page chrome and inline icons sometimes survive filtering.
- If a figure is missing, say which figure and why (paywall, 403, viewer), instead of silently dropping it.

## [tags: context, token-budget, agent-loop] Context Pressure

- A full paper can be 15k–30k words. Dumping it into the parent conversation invites compaction and loses the thread.
- Read `fulltext.md` in sections, or delegate one paper per subagent. Keep only the structured conclusions in the parent.
- Persist intermediate findings to the note or a scratch file instead of repeating them in chat.
- For a batch, process one paper at a time: extract → write → QA → index. Do not extract all papers first and then try to hold them all in context.

## [tags: qa, vscode, images] Preview Failures Are Usually Workspace Roots

- Notes live in `papers/`; images live in `papers/assets/<slug>/`. The only correct link is `assets/<slug>/fig_XX.png`.
- VS Code's Markdown preview restricts local images to the workspace folder. A project-root `assets/` breaks whenever the user opens `papers/` or a single file, while editor hover still works because it resolves the file differently. That mismatch produced a long false trail before the root cause was clear.
- Keep the figure library inside `papers/` so every plausible workspace root contains it.
- `--check-note --fix` catches missing files, zero-byte files, invalid magic bytes, legacy root assets, and non-standard relative paths, and migrates legacy figures.
- A zero-byte or HTML file with a `.png` extension is worse than a missing figure because it looks present. Validate magic bytes.
- Do not "fix" a report by deleting figures. Fix the path or report the missing evidence.

## [tags: katex, math, vscode] Formulas

- VS Code renders KaTeX natively; no Node.js or SVG conversion.
- Only reproduce equations present in the source. Sample equations are a tell that the note was templated.
- Keep display math balanced; an odd number of `$$` breaks the rest of the preview.
- Use `\$` for literal currency.

## [tags: markdown, vscode, callouts] Callouts

- VS Code's built-in Markdown preview does not render GitHub alert syntax (`> [!NOTE]`, `> [!WARNING]`); it prints the marker as plain text. Use a blockquote with a bold label instead:
  ```markdown
  > **一句话结论**
  >
  > The claim and its boundary conditions.
  ```
- Keep the label on its own quoted line and leave a quoted blank line before the body, otherwise the bold label and the paragraph collapse into one line.
- `--check-note` now treats the marker as an error and `--fix` rewrites it to `> **要点**`. The label is a guess; reword it to the real function rather than shipping "要点" everywhere.

## [tags: references, citation-network, classic-papers] A Classic Paper Is a Position, Not a PDF

- The first version of the note template only asked for "文献定位" in three bullets. The result was a competent summary that never said who the paper was arguing with. That is a book report, not a classic-paper read.
- What changed the quality was forcing three things: a citation table with 年份 / 工作 / 核心贡献 / 与本文的关系; an explicit **竞争解释** paragraph; and an explicit **后续检验** paragraph.
- Counts are a floor, not a goal. 10 external works for a deep read, 6 for standard, 3 for brief, 15 for a review. Only entries under `## 参考文献` count; the anchor is excluded.
- The failure mode the count creates is padding: adding plausible titles that were never read. The check cannot detect that, so the template says it out loud — if the literature is missing, say which part, do not fill the gap.
- Give every external work a DOI. A citation you cannot resolve is a liability in a note that is supposed to be reusable years later.

## [tags: tone, objectivity] Academic Neutrality

- Ban `颠覆一切`, `彻底终结`, `完美解决`, `前所未有`, and similar phrasing.
- Distinguish the authors' claims, the data, and your inference. A note that merges all three is not useful for later citation.
- Put boundary conditions and sample limitations in a `> **边界条件与未解问题**` blockquote, not in a closing flourish.

## [tags: subagent, delegation, batch] Subagent Delegation

- Delegate one paper per subagent when the batch is larger than two or three papers.
- Give each subagent: the slug, the evidence-pack paths, the note template, the QA commands, and the instruction not to invent content.
- The parent should receive the note path, a 3–5 sentence summary, figure count and origin, QA status, and any unresolved warnings.
- Review at least one subagent-produced note yourself before trusting the batch; template drift is contagious.

## [tags: updates, data-safety, versioning] Updates Replace Code, Never Evidence

- A paper workspace holds two kinds of files with opposite lifecycles: code (replaceable) and notes/packs/preferences (not replaceable). Mixing them in one updater is how people lose months of work.
- The updater's allowlist is the safety boundary. `papers/`, `.raw/`, `.geo-reader/` and `input_pdfs/` are never in it; a git checkout is fast-forwarded only when the tracked tree is clean.
- Refusing to update a dirty tree is the correct behaviour, not a bug. A silent `reset --hard` would "fix" the error by deleting the user's work.
- Version checks must be cheap and offline-safe: a six-hour cache, a short timeout, exit code 0 on failure. An update check that fails a reading task trains users to disable it.
- Patch-first versioning (`0.3.0 → 0.3.1`) keeps release numbering legible for a user who only wants to know whether their copy is current.
