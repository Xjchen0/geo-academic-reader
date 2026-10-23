# Troubleshooting & Recovery

Start with the doctor:

```bash
python3 main.py --doctor
# or
python3 doctor.py --json
```

It reports Python, dependencies, Chrome, CDP 9222, the saved profile, VS Code settings, and workspace directories. If the profile is missing, that is normal on a fresh clone: say `开始使用` in the agent chat instead of looking for a setup command.

---

## First run and preferences

| Symptom | Likely cause | What to do |
|:---|:---|:---|
| No `.geo-reader/profile.json` | Fresh clone or cleared state | Say `开始使用`; the agent runs the onboarding conversation from `AGENTS.md` §0. |
| Agent starts extracting without asking | Onboarding section skipped | Tell it to follow `AGENTS.md` §0 first. Extraction without a profile is a contract violation. |
| Preferences changed unexpectedly | Profile edited or corrupted | Say `重新设置偏好`. The agent backs up a corrupted file before rewriting it. |
| Onboarding repeats every session | Agent cannot find the profile | Check `python3 main.py --profile`; confirm `.geo-reader/` is writable and not ignored by a tool that deletes it. |

---

## Browser and extraction

| Symptom | Likely cause | What to do |
|:---|:---|:---|
| `Chrome/Chromium/Edge not found` | No supported browser installed, or installed in a non-standard path | Install Chrome, or use `--browser off`. On macOS/Linux, make sure the app is in `/Applications` or on `PATH`. |
| `CDP 9222 not running` | No Chrome in debug mode | Use `--browser auto`, or `python3 doctor.py --launch-chrome`. The pipeline launches a dedicated profile at `.geo-reader/chrome-profile`. |
| Port 9222 is used by another program | Conflicting process | Close the other debug Chrome, or free the port. `--browser existing` will reuse whatever is there, which may be wrong. |
| Page opens but text is an abstract | Paywall or truncated page | Check `.raw/<slug>/fulltext.md`. Use an OA PDF, `--url`, or an institutional session. Do not write a full review from an abstract. |
| `browser challenge` warning | Cloudflare or similar check | Complete the check in the launched Chrome window, then retry with `--browser existing`. Increase `--wait` if the page is slow. |
| Browser text is fine but figures are 0 | JS figure viewer, lazy loading, or selector mismatch | Retry with `--wait 8`; inspect the manifest warnings; check the page manually. Some publishers do not expose a downloadable image. |
| Figure downloads fail with 403 | CDN blocks direct HTTP | The extractor already tries an in-page `fetch()`. If it still fails, the session lacks access or the URL requires additional headers. Record the missing figure; do not fabricate it. |
| Wrong or repeated figures | `srcset` candidates, responsive variants, or shared placeholders | Inspect `figures/manifest.json`; deduplication uses rewritten URLs and image bytes. Report persistent cases with the source URL. |
| Browser extraction works but text falls back to HTTP | Text was shorter than the threshold (300 chars for URL, 800 for DOI) | This is expected. Check `paper.json.method` (e.g. `text=http; figures=browser`). |

### Launching Chrome manually

```bash
python3 doctor.py --launch-chrome
```

Or copy the command printed by the doctor. It uses a separate profile so it does not disturb your everyday Chrome session.

---

## PDFs

| Symptom | Likely cause | What to do |
|:---|:---|:---|
| `Local PDF not found` | Wrong path or unexpanded `~` | Pass an absolute path or a path relative to the workspace root. Quote paths with spaces. |
| Empty or near-empty `fulltext.md` | Scanned PDF without a text layer | OCR is not included. Obtain a text-based PDF or extract from the publisher page. |
| PDF has no DOI | Preprint, internal report, or DOI not in the text layer | The extractor uses the filename as the slug and PDF images as the fallback. If you know the DOI, use `--doi` instead. |
| PDF figures are low quality | `pypdf` extracts embedded bitmaps as-is | Install `pymupdf` (`pip install -r requirements-optional.txt`) for caption-aware 300 dpi cropping. |
| PDF figures have no captions | Caption not adjacent or not detected | The manifest records empty captions. The note must say so; do not invent a caption. |
| PDF has a DOI but browser figures are missing | Paywall, challenge, or Chrome unavailable | The pipeline falls back to PDF figures. Check `paper.json.method` and `figures/manifest.json`. |

---

## Images not showing in VS Code

This is almost always a path or workspace-root problem. A useful symptom to recognize: hovering the image link in the editor shows a thumbnail, but the preview shows a broken image. Hover resolves the file on disk; the preview is a webview restricted to the workspace folder.

1. Run:

   ```bash
   python3 main.py --check-note "papers/<slug>.md" --fix
   ```

2. Confirm the note uses `assets/<slug>/fig_01.png` and the file lives under `papers/assets/<slug>/`. Older notes may use `../assets/...` with the file in a project-root `assets/`; `--fix` migrates the file and rewrites the link.

3. Confirm the file is a real image:

   ```bash
   file "papers/assets/<slug>/fig_01.png"
   ```

   If it reports HTML or text, the download saved an error page. Delete that figure, re-extract, and inspect the manifest warnings.

4. In VS Code, run **Markdown: Refresh Preview** from the Command Palette.

5. The figure library intentionally sits inside `papers/` so the preview works whether the workspace root is the project root, `papers/`, or a single note file.

`--fix` only rewrites unambiguous targets. If several files share a basename under `papers/assets/`, it leaves the link alone and reports an error.

---

## Metadata and citations

| Symptom | Likely cause | What to do |
|:---|:---|:---|
| Crossref 404 | Brand-new DOI, preprint, or registration delay | Use `--url` or `--pdf`. |
| Missing journal/year | Page metadata incomplete; Crossref record sparse | Check `paper.json`; fill the front matter manually from the PDF or publisher page, and mark the source. |
| APA citation looks generic | `apa_source` is `constructed` | Verify authors, year, title, and journal manually before citing. |
| Wrong DOI in a note | DOI detected from a reference list or page boilerplate | Use the DOI from `paper.json`; if it is wrong, re-extract with the explicit DOI. |

---

## Python environment

| Symptom | Likely cause | What to do |
|:---|:---|:---|
| `ModuleNotFoundError` | Dependencies not installed for the active interpreter | `python3 doctor.py --install`, or `pip install -r requirements.txt`. Check `sys.executable` in the doctor output. |
| `NotOpenSSLWarning` on macOS | Legacy system Python linked against LibreSSL | Use a modern Python via `uv`, conda, or python.org. The package filters this warning where possible. |
| `UnicodeDecodeError` on Windows | Console code page is not UTF-8 | Set `PYTHONUTF8=1` before running, or use Windows Terminal. All file I/O in the project is UTF-8. |
| `pip install -e .` fails | `scripts/` package or build backend mismatch | Use the current tree; `pyproject.toml` expects `scripts/__init__.py`. Then retry. |
| `geo-reader: command not found` | Editable install did not complete or scripts directory is not on `PATH` | Use `python3 main.py ...` directly, or reinstall with `python3 -m pip install -e .`. |

---

## Index and notes

| Symptom | Likely cause | What to do |
|:---|:---|:---|
| Duplicate rows in `papers/INDEX.md` | Note renamed, or rows added manually | `--index` updates the row matching the note link. Remove stale duplicates manually, then re-run. |
| Row has `—` for journal/year | Front matter missing fields | Add `journal` and `year` to the YAML front matter, then re-run `--index`. |
| `--index` cannot find the note | Path typo | Pass the path relative to the workspace root: `papers/<slug>.md`. |
| QA reports `placeholder_content` | The old generator's template text is still present | Delete the generic paragraphs and write from the evidence pack. Do not merely reword them. |
| QA reports `unbalanced_display_math` | An odd number of `$$` delimiters | Close the block or remove the stray delimiter. |

---

## Re-extracting safely

To refresh a paper:

```bash
python3 main.py --doi "10.xxxx/..." --max-figures 30
```

This overwrites the evidence pack and generated `fig_*.ext` files for that slug, but leaves `papers/<slug>.md` untouched. If figure numbering changes, re-check the note's figure sections against the new manifest.

Do not delete `.raw/` casually: it is the audit trail for every claim in the note.

---

## Reporting a reproducible problem

Include:

- the command you ran;
- `python3 doctor.py --json` output;
- `.raw/<slug>/paper.json` and `figures/manifest.json` (warnings especially);
- whether the page is accessible in your normal Chrome session;
- platform and Python version.

Do not include paywalled full text or copyrighted figures in a public issue.
