# Lessons — academic-paper-reader

This file records operational wisdom and agent runtime optimization techniques discovered across iterations.

---

## [tags: context, token-budget, agent-loop] Context Pressure & Long Papers
- Full scientific papers easily exceed 15,000–30,000 words (40k+ tokens), risking context window overflow or early agent context compaction.
- **Rule**: Never dump raw 100-page full-text into conversation history. Extract structured subsections (Abstract, Introduction hypotheses, Key Results per figure, Limitations) before generating the final synthesis.
- After extracting figure URLs and captions, immediately persist them to `./assets/` and generate the working notes.

## [tags: figures, resolution, cdn, assets] High-Resolution Figure Extraction
- Publishers frequently serve low-res thumbnails (`/w400/`, `.medium.gif`) inside initial DOM `<figure>` tags.
- Always apply pattern rewrites (e.g. `/w400/` $\to$ `/w960/` for Nature, `.medium.gif` $\to$ `.large.jpg` for bioRxiv) before downloading.
- If a CDN URL returns 403 on direct curl, download it directly from the Chrome CDP context via JavaScript `fetch()`.

## [tags: paywalls, cloudflare, anti-bot, cdp] Chrome CDP vs. Open Access Strategy
- Open Access repositories (bioRxiv, medRxiv, arXiv, Europe PMC) do NOT require browser automation. Use direct HTTP APIs to save CPU and RAM.
- Nature, Science, Elsevier, and Wiley pages often activate Cloudflare challenge or dynamic JS rendering. Route these through the active Chrome 9222 instance.
- Always run `doctor.py` to confirm whether Chrome 9222 is alive before initiating complex journal crawls.

## [tags: katex, math, vscode, rendering] KaTeX Mathematics in VS Code
- Modern VS Code (v1.58+) natively renders KaTeX in its Markdown Preview.
- Do NOT convert LaTeX formulas into inline SVG tags or base64 images unless publishing to WeChat or restrictive platforms. Native KaTeX preserves readability and allows users to copy equations directly.
- Ensure math is delimited with `$..$` (inline) and `$$..$$` (display block) with no space immediately after opening or before closing `$`.

## [tags: tone, objectivity, academic-neutrality] Academic Tone & Anti-Hyperbole
- Academic interpretations must remain strictly objective and scholarly.
- Flag and eliminate any sensationalist jargon (e.g., "颠覆一切", "终结争议", "前所未有").
- Emphasize boundary conditions, model assumptions, and limitations under a dedicated `> [!WARNING]` callout.

## [tags: subagent, delegation, isolation] Subagent Delegation
- When analyzing a batch of papers (e.g., 5–10 papers from a journal TOC), delegate each paper extraction to a distinct subagent with isolated context.
- The parent agent should only receive the resulting Markdown path and a concise executive summary, keeping the parent context clean.
