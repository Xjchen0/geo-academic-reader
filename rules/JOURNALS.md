# Journal Extraction Rules & Strategies

This reference describes what the extractor actually does (`scripts/browser.py`, `scripts/figures.py`, `scripts/fetch_paper.py`) and what to check when a publisher changes its markup.

The strategy is **browser-first, not selector-perfect**. The manifest is the source of truth: if a figure is missing or the origin says `pdf`, do not describe it as a browser-extracted high-resolution image.

---

## New-Article Watch: open the journal pages, not topic search

> **Two different routes.** “找新文献” = this page-scan route (`--new-literature`, journal pages, list only, then stop).
> “主题综述” = `--thematic-review` (Crossref topic search + per-item DOI/标题/作者/年份/摘要核验, then write).
> Never feed one route’s list into the other, and never use this route to satisfy a thematic review request.

`python3 main.py --new-literature` answers “find new papers” **only from the configured journal pages** (`journals.json`, or `.geo-reader/journals.json` when present). It never reads `papers/`, `.raw/`, or the conversation to choose a topic.

The command is a listing step, not an extraction step:

1. Chrome/CDP opens each configured page (research articles, current issue, early publication, or recent volumes).
2. A page-specific parser reads the entries the page itself lists.
3. Each title is translated to Chinese (cache first, then Bing) and stored as `title_zh`.
4. It writes `.geo-reader/journal-scan/latest.md` and `latest.json` with numbered candidates.
5. The agent presents those candidates and stops.
6. Only after the user names numbers or DOIs does the agent run `--doi` and write notes.

### Page list schema (v2)

```json
{
  "version": 2,
  "defaults": { "days": 0, "limit": 0, "sort": "journal" },
  "journals": [
    {
      "key": "ngeo",
      "name": "Nature Geoscience",
      "parser": "nature",
      "url": "https://www.nature.com/ngeo/research-articles",
      "enabled": true,
      "wait": 5,
      "scroll": false,
      "ready": "h3.c-card__title"
    },
    {
      "key": "epsl",
      "name": "EPSL",
      "parser": "epsl",
      "url_template": "https://www.sciencedirect.com/journal/earth-and-planetary-science-letters/vol/{volume}/suppl/C",
      "volumes": [699, 698, 697, 696],
      "enabled": true,
      "scroll": true,
      "ready": "a.article-content-title"
    }
  ]
}
```

- `key` is the CLI identifier (`--journal ngeo`), unique and lowercase.
- `parser` selects the page parser; it must be one of the supported names below.
- Supply either `url`, or `url_template` plus a non-empty `volumes` array containing `{volume}`.
- `enabled: false` keeps an entry documented but out of the scan.
- `wait` is the post-load settle time (seconds). `scroll` scrolls to the bottom to trigger lazy loading. `ready` is a CSS selector the scanner waits for before reading the HTML. `challenge_timeout` defaults to 60 seconds.
- `defaults.days: 0` means “take the page as it is”. A positive value filters only entries that have a date; undated items are kept. `limit: 0` means no cap.

### Parsers and pages

| parser | Page | Reads | Notes |
| :--- | :--- | :--- | :--- |
| `nature` | `nature.com/<journal>/research-articles` | `<article>` cards, `h3.c-card__title a`, `<time datetime>` | DOI is `10.1038/<article basename>` |
| `science_first` | `science.org/toc/science/0/0` | `h4/h5.to-section` date groups + `h3.article-title a[href="/doi/…"]` | First Release |
| `science_current` | `science.org/toc/science/current` | Same markup, only the “Research Articles” group | Skips news/comment |
| `science_advances` | `science.org/toc/sciadv/current` | `card` blocks inside the “Earth, Environmental, Ecological, and Space Sciences” group | Skips other sections |
| `epsl` | ScienceDirect volume page (`/vol/<n>/suppl/C`) | `a.anchor.article-content-title` + PII; DOI read from the surrounding block | Never invents a DOI from the PII |
| `agu` | AGU journal page | Only the first pane containing `div.issue-item` (Recently Published) | Ignores Most Cited / Most Read |
| `geology_current` | `pubs.geoscienceworld.org/geology/issue/current` | `h3.customLink.item-title a`; DOI from the PDF link code | `10.1130/<code>` |
| `geology_early` | `/geology/early-publication` | `h2.al-subgroup-outer-id` date groups + `h5.al-title a` | Date comes from the group heading |
| `gji` | `academic.oup.com/gji` | `div.widget-dynamic-entry.journalArticleItem`, `data-attribute` DOI, title div | Wait for the dynamic widget |
| `pnas` | `pnas.org/topic/earth-sci` | Card blocks between “Recent articles” and “Trending” | Stops at Trending |

The shipped list covers 17 sections: Nature, Nature Geoscience, Nature Communications (two pages), Science First Release and Current, Science Advances, EPSL volumes 696–699, GRL, JGR-Solid Earth, JGR-Planets, Tectonics, G-Cubed, Geology current and early publication, GJI, and PNAS Earth.

### Filtering and deduplication

- Corrections, corrigenda, errata, retractions, expressions of concern, issue front/back matter and cover images are dropped before numbering.
- Duplicate DOIs are collapsed globally; entries without a DOI are matched by normalised title.
- There is **no keyword filter**. A broad journal (Nature, Science, PNAS) will list non-geoscience papers too; that is the definition of the user's list, so do not narrow it from the conversation.
- `total_found` is the count after dedupe; `total` is the count after `--limit`.

### Chinese titles

- `scripts/translate.py` translates each English title with Bing's public translator (`cn.bing.com`, `ttranslatev3` + abuse-prevention token). Google is unreachable from mainland networks; MyMemory's free quota is too small for a 300-item scan.
- Results live in `.geo-reader/journal-scan/translations.json` (`{version, provider, updated_at, titles: {english: chinese}}`). A rerun reuses the cache and only translates new titles.
- The cache stores the **raw** machine output; `TERM_FIXES` applies a geoscience glossary on read, so correcting a term does not require clearing the cache. Current rules include fugacity→逸度, sub-arc→弧下, back-arc→弧后, magma ocean→岩浆洋, stagnant slab→停滞板片, delamination→拆沉, large igneous province→大火成岩省, flood basalt→溢流玄武岩, mid-ocean ridge→洋中脊, conductance→电导.
- `latest.md` labels the block “中文（机译），仅供检索” and the English title stays authoritative. A title that could not be translated is printed as “暂缺” with a count in the header; the scan never invents one. `--no-translate` skips the step entirely.
- Titles containing escaped inline markup (`NH&lt;sub&gt;4&lt;/sub&gt;`) are unescaped **before** tags are stripped, so the cache key and the displayed title are the clean text.
- Translation failures are non-fatal: the scan still writes the list and records `translation` (`provider`, `cached`, `translated`, `missing`, `error`) in `latest.json`.

### Limits and blind spots

- The page decides what “latest” means. A research-articles page may contain papers from the past several weeks; a volume page contains the whole issue. This is intentional.
- EPSL is configured by volume. When a new volume opens, update `volumes`; otherwise the scan silently keeps showing old issues.
- Cloudflare or a human check: the scanner waits politely, reports `challenge`, and stops. It does not refresh or retry in a loop. Ask the user to finish the check in the opened Chrome window, then rerun the same command.
- If a publisher changes markup, the parser returns 0 for that page. Report it; never fabricate entries.
- Pages are fetched sequentially to stay polite. A full scan of 20 pages typically takes a few minutes.

Detailed extractor behaviour follows.

---

## Publisher Strategy Matrix

| Publisher / source | Text route | Figure route | Known caveats |
|:---|:---|:---|:---|
| **Nature Portfolio / Springer Nature** | Rendered page via Chrome; HTTP fallback | `<figure>` scan, `src`/`srcset`, URL rewrite to `/full/` | Paywalled body text may be absent; abstract may still be extractable |
| **Science / AAAS** | Rendered page via Chrome | Figure scan; `/w400/` or `/w450/` → `/w1200/`, `/medium/` → `/large/` | Bot challenge is common; wait or complete it manually |
| **Elsevier / ScienceDirect** | Rendered page via Chrome | Figure scan; `-grN.jpg` → `-grN_lrg.jpg` | Direct HTTP often blocked; page-context fetch is more reliable |
| **AGU / Wiley** | Rendered page via Chrome | Figure scan, then page-context fetch | Session cookies matter; figure markup varies by journal |
| **bioRxiv / medRxiv** | HTTP / rendered page | `.medium.gif` → `.large.jpg`, `.medium.jpg` → `.full.jpg` | Usually open access; prefer direct HTTP to save resources |
| **arXiv** | HTTP / HTML version | HTML figure scan where available; otherwise PDF | HTML may not exist for older papers; rate-limit requests |
| **PubMed Central** | HTTP | Figure scan or PDF fallback | Only the OA subset provides clean assets |
| **Generic publisher page** | Rendered page → HTTP | Any `<figure>` with a caption and a reasonably large image | Custom viewers and canvases may not expose a downloadable image |

Rules of thumb:

- If the page is JavaScript-rendered and HTTP returns little text, use `--browser auto`.
- If the browser returns a challenge page, the run records a warning and falls back. Do not pretend the extraction succeeded.
- If browser figures are empty but the page clearly has figures, inspect the text of `figures/manifest.json` warnings and retry after the page finishes loading (`--wait 8`).

---

## High-Resolution URL Rewriting

Implemented in `upgrade_figure_url()`:

```python
# Nature / Springer Nature: /lw685/, /w400/, ... -> /full/
if "springernature.com" in url or "nature.com" in url:
    url = re.sub(r"/(?:lw|w)\d+/", "/full/", url)
    url = re.sub(r"[?&](?:as|width|w)=\w+", "", url)

# Science / AAAS
elif "science.org" in url:
    url = url.replace("/w400/", "/w1200/").replace("/w450/", "/w1200/")
    url = url.replace("/medium/", "/large/")

# Elsevier / ScienceDirect
elif "els-cdn.com" in url or "sciencedirect.com" in url:
    url = re.sub(r"(-gr\d+)\.(jpg|jpeg|png)(\?.*)?$", r"\1_lrg.\2\3", url, flags=re.I)

# bioRxiv / medRxiv
elif "biorxiv.org" in url or "medrxiv.org" in url:
    url = url.replace(".medium.gif", ".large.jpg")
    url = url.replace(".full.gif", ".full.jpg")
    url = url.replace(".medium.jpg", ".full.jpg")
```

Additional behavior:

- `srcset` candidates are parsed and the largest descriptor is chosen before rewriting.
- If a rewritten URL fails, the extractor records the failure and may still keep a working lower-resolution candidate from the page.
- Repeated URLs after rewriting are de-duplicated.
- Icons, logos, sprites, tracking pixels, and very small images are filtered by URL token, dimensions, and layout width.

### Adding a new publisher

1. Open the article in Chrome and inspect a figure's `src` and `srcset`.
2. Add a narrow rewrite rule to `upgrade_figure_url()`; do not broadly rewrite every URL on a domain.
3. Verify that the rewritten URL returns image bytes, not an HTML error page.
4. Run a single extraction and inspect `figures/manifest.json` for `origin`, `width`, `height`, and warnings.

---

## Access and Anti-Bot Behavior

The pipeline uses the user's local Chrome session to render pages and, when direct HTTP is blocked, downloads image bytes with an in-page `fetch()`. This is intended for content the user can already access. It is **not** a paywall bypass.

Practical rules:

1. **Keep navigation human-paced.** Do not run large parallel crawls against one publisher. Batch jobs are sequential for this reason.
2. **Prefer open access.** If OpenAlex exposes an OA PDF, use it for text. Do not hammer a paywalled page for figures that are not visible.
3. **Complete challenges manually.** If Cloudflare or a similar check appears, finish it in the launched Chrome window, then retry with `--browser existing`.
4. **Respect terms and licences.** Figure reuse may require permission even when the image is technically downloadable.
5. **Do not retry indefinitely.** A failed figure is recorded; report it in the note instead of fabricating a description.

---

## What the Extractor Reads

From each `<figure>`-like element it collects:

- image URL from `src`, `data-src`, or the largest `srcset` candidate;
- caption text from `figcaption` or nearby caption elements;
- whether the element is inside a `<figure>`;
- rendered width/height and natural dimensions;
- page URL and, for PDFs, page number.

It then filters, de-duplicates, downloads, validates magic bytes, and writes the manifest. Captions can still be incomplete or merge multiple panels; the agent must not invent missing text.
