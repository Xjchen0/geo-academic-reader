# Journal Extraction Rules & Strategies

This reference guide documents publisher-specific extraction patterns, high-resolution figure resolution rules, and anti-bot bypass strategies.

## Publisher & Journal Strategy Matrix

| Journal / Publisher | Access Mode | Figure High-Res Strategy | Fallback / Caveats |
|:---|:---|:---|:---|
| **Nature / Nature Comms** | HTTP / Chrome CDP | Replace `/w400/` or `/w450/` with `/w960/` in image URLs. If Springer CDN, append `_HTML.png`. | Public abstracts accessible via HTTP; full body & Supplementary requires Chrome CDP or proxy. |
| **Science / Science Advances** | Chrome CDP (9222) | Locate `figure` tags; extract `img` `src`. If 403 upon curl, use browser-context `fetch()` to base64. | Heavy Cloudflare challenge. Always wait 4–6s after navigation. Look for `h4.to-section`. |
| **Elsevier / ScienceDirect** (e.g. EPSL) | Chrome CDP (9222) | High-res images located under `/gr<N>.jpg` or `/fx<N>.jpg`. Extract via CDP page context. | Direct curl blocked by anti-bot headers. Must use browser context. |
| **AGU / Wiley** (GRL, JGR) | Chrome CDP (9222) | Inspect `div.article-section__content` -> `figure.figure-item`. | Wiley CDN requires session cookies. Use in-page evaluate to download. |
| **bioRxiv / medRxiv** | Direct HTTP / API | High-res images: append `.large.jpg` or extract from `.inline-figure`. | Completely Open Access. Direct `urllib` / `requests` works without browser. |
| **arXiv** | Direct HTTP / API | Use `https://arxiv.org/html/{id}` for HTML figures, or extract from source tarball. | Completely Open Access. Rate limit: 1 req/3s. |
| **PubMed Central (PMC)** | Direct HTTP / API | Extract high-res from `pmc/articles/PMC.../bin/` or BioC API. | Open Access subset provides direct `.tar.gz` and clean image assets. |

---

## High-Resolution Image Pattern Rewriting

```python
def get_high_res_figure_url(src_url: str) -> str:
    # Nature Portfolio
    if "springernature" in src_url or "nature.com" in src_url:
        src_url = src_url.replace("/w400/", "/w960/").replace("/w450/", "/w960/")
        src_url = src_url.replace("/w300/", "/w960/")
    
    # bioRxiv
    elif "biorxiv.org" in src_url and ".medium.gif" in src_url:
        src_url = src_url.replace(".medium.gif", ".large.jpg")
    
    # Science / AAAS
    elif "science.org" in src_url and "/w400/" in src_url:
        src_url = src_url.replace("/w400/", "/w1200/")

    return src_url
```

---

## Cloudflare & Anti-Bot Bypass Rules

1. **Never blast requests**: When navigating multiple papers on Science or Nature via Chrome CDP, maintain a minimum interval of 3–5 seconds between page loads.
2. **Context-Aware Figure Download**: If an image URL returns `403 Forbidden` when requested via python `requests` or `urllib`, download it inside the existing Chrome browser session using:
   ```javascript
   const resp = await fetch(imgUrl);
   const blob = await resp.blob();
   // convert to base64 and transfer to python/filesystem
   ```
3. **No-Browser Fallback**: If Chrome is not installed, prompt the user to use Open Access DOI / arXiv / bioRxiv or local PDF.
