# Journal Extraction Rules & Strategies

This reference describes what the extractor actually does (`scripts/browser.py`, `scripts/figures.py`, `scripts/fetch_paper.py`) and what to check when a publisher changes its markup.

The strategy is **browser-first, not selector-perfect**. The manifest is the source of truth: if a figure is missing or the origin says `pdf`, do not describe it as a browser-extracted high-resolution image.

---

## New-Article Watch: journal list, not topic search

`python3 main.py --new-literature` answers “find new papers” **only from the configured journal list** (`journals.json`, or `.geo-reader/journals.json` when present). It never reads `papers/`, `.raw/`, or the conversation to choose a topic.

The command is a listing step, not an extraction step:

1. It writes `.geo-reader/journal-scan/latest.md` and `latest.json` with numbered candidates.
2. The agent presents those candidates and stops.
3. Only after the user names numbers or DOIs does the agent run `--doi` and write notes.

### List schema

```json
{
  "version": 1,
  "defaults": { "days": 7, "limit": 80, "sort": "date" },
  "keyword_sets": {
    "earth_planetary": ["earth*", "mantle*", "mars", "volcan*"]
  },
  "journals": [
    {
      "key": "nature-geoscience",
      "name": "Nature Geoscience",
      "issn": "1752-0894",
      "publisher": "Springer Nature",
      "enabled": true,
      "keyword_set": "earth_planetary",
      "keywords": []
    }
  ]
}
```

- `key` is the CLI identifier (`--journal nature-geoscience`), unique and lowercase.
- `issn` is the Crossref journal ISSN; verify a new entry with `https://api.crossref.org/journals/<ISSN>`.
- `enabled: false` keeps an entry documented but out of the scan.
- `keyword_set` refers to a shared list; `keywords` appends inline terms. A trailing `*` marks a stem (`volcan*`); everything else is a whole word (`mars` does not match “marsh”).
- Keywords match the **title only** and are static configuration. They exist to keep broad journals (Nature, Science, PNAS, Nature Communications, Science Advances, Nature Astronomy) usable; specialist journals normally leave them empty.

### Crossref queries

Two queries per journal, merged by DOI:

| Query | Filter | Why |
| :--- | :--- | :--- |
| publication date | `from-pub-date` / `until-pub-date` | Catches Springer Nature and AGU records, whose `published` date tracks the online date |
| creation date | `from-created-date` / `until-created-date` | Catches Elsevier records, whose issue date can be months ahead (a January issue deposited in October) |

Both use `type:journal-article`. The scan paces requests globally (0.35 s), retries 429/5xx once, and runs at most three journals concurrently. A per-journal failure is reported in the output; it does not abort the rest.

The displayed date is the online date when it is not in the future, otherwise the record creation date. That is why an Elsevier paper can show today's date even though its issue is dated next year.

### What is filtered

- Corrections, corrigenda, errata, editorials, publisher's notes, retractions, expressions of concern, issue front/back matter, obituaries, book reviews, briefings, podcasts, and news & views.
- Nature Portfolio `10.1038/d...` DOIs (news, comment, careers); research and reviews use `10.1038/s...`.
- Magazine organisation names such as “Mineralogical Society of America” and “Société Française de Minéralogie et de Cristallographie”.
- Duplicate DOIs and duplicate normalised titles across journals.

Everything else is kept and shown. A broad journal can still contribute an opinion piece that Crossref types as `journal-article`; the list is for human selection, so do not silently narrow it further.

### Limits and blind spots

- Crossref lag: a paper visible on the publisher page today may appear in Crossref a day or more later. Rerun the scan; do not switch to scraping a single TOC to “fill the gap” without telling the user.
- `limit` is a global cap, but selection is round-robin across journals so a high-volume journal cannot hide the specialist ones. `total_found` reports the untruncated count.
- The list is a candidate list, not a completeness claim. Say so when presenting it.

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
