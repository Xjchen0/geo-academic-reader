# VS Code Markdown & KaTeX Specification

This document defines the writing and layout rules for notes in `papers/`. The built-in QA (`python3 main.py --check-note`) enforces part of it; the rest is the agent's responsibility.

---

## 1. Front Matter

Every note starts with YAML front matter so that `--index` can build the catalog without guessing:

```yaml
---
title: "Paper title"
journal: "Nature Communications"
year: 2026
doi: "10.1038/s41467-026-69772-8"
source: "https://www.nature.com/articles/s41467-026-69772-8"
raw: "../.raw/10.1038_s41467-026-69772-8/paper.json"
status: 已精读
reviewed_at: "2026-10-24"
tags: []
---
```

- `title`, `journal`, `year`, `doi`, `source` are used by `--index`.
- Keep `raw` pointing at the evidence pack so a future reader can audit the note.
- Use `status: 已精读` only after `--check-note` passes.
- Paths are relative to `papers/`: `../.raw/...` for the evidence pack and `assets/...` for figures.

---

## 2. Figures

Figures live in `papers/assets/<slug>/`, in the same directory tree as the note, so there is exactly one correct link form:

```markdown
![图 1：图注](assets/<slug>/fig_01.png)
*图 1：图注（来源：browser；原始链接：https://...）*
```

Why the extra `papers/` level matters: VS Code's Markdown preview restricts local images to the workspace folder. If the user opens only `papers/` — a common habit — a project-root `assets/` folder is outside that root and every image silently fails, even though hovering the link in the editor shows a thumbnail. Keeping the library under `papers/` makes the note render when the user opens the project root, `papers/`, or the single `.md` file.

Rules:

- **Do not** use `../assets/...`, `./assets/...`, absolute paths, `file://`, or a remote URL as the primary image.
- Use the `markdown_path` value from `figures/manifest.json`.
- Use the manifest caption. If it is empty, write `*图 1：原文未提供图注*`.
- Do not rename files or invent `fig_01.jpg` when the manifest says `fig_01.png`.
- If a note has no figures, remove the figure section rather than adding placeholder images.

### Diagnosing a missing image

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
```

The checker:

1. resolves each local image against the note's directory;
2. verifies the file exists, is non-empty, and has valid PNG/JPEG/GIF/WebP/TIFF magic bytes;
3. errors if the file sits in a legacy root-level `assets/`;
4. requires the normalized relative path to equal `assets/<slug>/...` under `papers/`;
5. can rewrite a broken link and migrate legacy figures when the target is unambiguous.

If the file itself is missing, do not hide the problem. Record it in the note and in the delivery summary.

---

## 3. Mathematics (KaTeX)

VS Code renders KaTeX natively. No extension is needed.

- Inline: `$E = mc^2$`, `$\sigma_{ij}$`.
- Display:

  ```markdown
  $$
  \frac{\partial \mathbf{u}}{\partial t} + (\mathbf{u} \cdot \nabla)\mathbf{u} = -\frac{1}{\rho}\nabla p + \nu \nabla^2 \mathbf{u}
  $$
  ```

- No space immediately after the opening `$` or before the closing `$`.
- Escape literal currency: `\$100`.
- Do not use SVG, base64 images, or screenshots for equations.
- **Only reproduce equations that appear in the source.** If a derivation is reconstructed, label it as your own and explain the assumptions; prefer omitting it.
- Check that each `$$` block is closed. The QA reports an odd count.

---

## 4. GFM Alerts

```markdown
> [!NOTE] 一句话结论
> 核心结论及其成立条件。

> [!IMPORTANT] 关键前提
> 样品代表性、平衡态假设、边界条件、模型分辨率。

> [!TIP] 读图要点
> 坐标轴、色标、对照组、拐点、置信区间。

> [!WARNING] 边界与不确定性
> 样品边界、方法边界、参数敏感性、外推风险。
```

Use them sparingly. A note where every paragraph is an alert is harder to read than plain prose.

---

## 5. Evidence Anchors

Every important claim should be traceable:

- PDF source: `（第 7 页）`.
- Web source: `（Results，第 3 段）` or `（Methods, "Sample preparation"）`.
- Figure claim: reference the figure number and the manifest caption.
- Missing evidence: `原文未提供` or `证据包中未包含该信息`.

Do not cite a page number that is not present in `fulltext.md`. Browser-extracted text has no page numbers; use section/paragraph anchors instead.

---

## 6. Academic Tone

Avoid:

- `颠覆一切`
- `彻底终结`
- `空前重大突破`
- `完美解决`
- `前所未有`

Prefer:

- “该结果在作者设定的温压区间内支持 X，但向 Y 条件外推仍需验证。”
- “作者认为 A 导致 B；现有证据是相关性与数值拟合，缺少独立实验对照。”
- “样本量较小，区域代表性有限。”

Separate three things explicitly:

1. what the authors claim;
2. what the data show;
3. what you infer.

---

## 7. Note Structure

Use `templates/paper_note.md`:

1. one-sentence conclusion;
2. literature positioning;
3. scientific question and hypotheses;
4. data and methods;
5. figure-by-figure interpretation;
6. mechanism and discussion;
7. limitations and uncertainty;
8. reusable takeaways;
9. references.

For multi-paper synthesis, use `templates/literature_review.md` instead.

---

## 8. Pre-Delivery Checklist

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"
python3 main.py --list
```

- [ ] Front matter complete.
- [ ] Every image resolves to `assets/<slug>/...` and the file lives under `papers/assets/`.
- [ ] Figure captions match the manifest.
- [ ] No template placeholders or sample equations.
- [ ] Evidence anchors are present for key claims.
- [ ] Limitations distinguish author-stated from reviewer-inferred.
- [ ] `papers/INDEX.md` has exactly one row for the note.
