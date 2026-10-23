---
name: geo-academic-reader
version: "0.0.1-pre"
license: MIT
description: >-
  Extract, deeply interpret, and format scientific research papers (by DOI, web URL,
  or local PDF) into rich-media Markdown documents optimized for VS Code.
  Specialized for Earth Sciences, Geophysics, Geology, and general science (Nature, Science,
  AGU, Wiley, Elsevier, bioRxiv, arXiv). Use INSTEAD OF generic web reading or summary
  when you need: exact KaTeX mathematical formulas ($..$ and $$..$$), high-resolution figure
  extraction into local assets/, GFM callout alerts (> [!NOTE], > [!WARNING]), formal Crossref
  APA citations, or anti-bot bypass for academic publishers.
compatibility: >-
  Requires: Python >= 3.9 (requests, beautifulsoup4, pypdf, websockets).
  Optional: Google Chrome on port 9222 for paywalled/Cloudflare-protected journal pages.
---

# geo-academic-reader (v0.0.1-pre)

Transform raw scientific publications into high-fidelity, publication-grade Markdown documents designed specifically for modern **VS Code Markdown Preview**.

---

## ⚡ Quick Start & Invocation

```bash
# 1. First-time environment check & auto-setup:
python install.py
# Or:
python doctor.py --install

# 2. Extract and generate VS Code Markdown:
geo-reader --doi "10.1126/science.adz2675" --output ./output
geo-reader --url "https://www.nature.com/articles/s41586-026-10999-2" --output ./output
geo-reader --pdf "/path/to/paper.pdf" --output ./output

# (Direct python invocation if not installed to PATH):
python scripts/run_pipeline.py --doi "10.1126/science.adz2675" --output ./output
```

---

## 🎯 Input Matrix & Strategy Selection

| Input Source | Primary Strategy | Figure Resolution | Chrome 9222 Needed? |
|:---|:---|:---|:---|
| **DOI** (`10.xxxx/...`) | Crossref API + APA lookup + OA resolution | High-res publisher CDN rewrite | Only for paywalled journals |
| **Direct Paper URL** | HTML parser + figure extractor | DOM `<figure>` scan & rewrite | Required if Cloudflare-protected |
| **Local PDF** (`.pdf`) | Direct `pypdf` page & image stream parsing | Original embedded image stream | ❌ No Chrome required |
| **bioRxiv / arXiv / PMC** | Direct HTTP API / open access stream | Open access large assets | ❌ No Chrome required |

For publisher-specific scraping rules and figure rewrite patterns: see [rules/JOURNALS.md](rules/JOURNALS.md).

---

## 📐 VS Code Markdown Specifications (P0 Rules)

When writing or synthesizing the final paper interpretation, enforce the following standards:

1. **Native KaTeX Mathematics**:
   - Inline math: `$E = mc^2$` (never insert spaces directly after opening or before closing `$`).
   - Display math:
     ```markdown
     $$
     \mathcal{F}(x, t) = \sum_{k=1}^{N} \alpha_k \exp(-\lambda_k t) \cdot \Phi_k(x)
     $$
     ```
   - Zero Node.js / SVG conversion required.
2. **Local High-Resolution Assets**:
   - Always reference extracted figures via clean relative paths:
     `![Figure 1: Caption](./assets/<paper_slug>/fig1.png)`
   - Accompany each figure with an italicized, detailed explanatory caption.
3. **Structured GFM Alerts**:
   - `> [!NOTE]` for core research questions & hypotheses.
   - `> [!IMPORTANT]` for experimental parameters & methodological constraints.
   - `> [!WARNING]` for model boundaries, sample limitations, and uncertainties.
4. **Academic Neutrality (防夸大铁律)**:
   - Strictly ban sensational terms (`颠覆一切`, `彻底终结`, `空前突破`).
   - Maintain scholarly objectivity, emphasizing parameter sensitivity and model assumptions.

Full typography and KaTeX rules: [rules/MARKDOWN_SPEC.md](rules/MARKDOWN_SPEC.md).

---

## 🛑 Common Errors & Quick Recovery

| Error / Code | Meaning | Action / Recovery |
|:---|:---|:---|
| `404 Not Found` (Crossref) | Brand new paper or preprint not yet indexed | Switch to `--url` or download PDF and run `--pdf`. |
| `403 Forbidden` (Figures) | CDN blocks non-browser requests | Ensure Chrome 9222 is active (`python doctor.py`). Script will fetch via browser context. |
| Missing packages | Python environment uninitialized | Run `python doctor.py --install` or `python install.py`. |
| SSL / LibreSSL Warning | Legacy macOS Python 3.9 SSL engine | Switch to uv / conda environment: `uv pip install -r requirements.txt`. |

Comprehensive troubleshooting guide: [rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md).  
Agent context management & token optimization tips: [LESSONS.md](LESSONS.md).
