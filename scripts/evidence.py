#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-pack builder.

The pipeline's contract is deliberately narrow:

    .raw/<slug>/paper.json
    .raw/<slug>/fulltext.md
    .raw/<slug>/figures/manifest.json
    papers/assets/<slug>/fig_01.png ...

It does not write a review, a summary, or a literature note. Those are written
by the agent from the evidence pack using templates/paper_note.md.
"""

import datetime
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .browser import BrowserChallenge, BrowserError, BrowserSession, ensure_chrome
from .config import (
    ASSETS_DIR,
    PAPERS_DIR,
    PROJECT_ROOT,
    RAW_DIR,
    RAW_INDEX_FILE,
    doi_to_slug,
    ensure_workspace_dirs,
    extract_doi,
    now_iso,
    relative_posix,
    slugify,
    today_iso,
    url_to_slug,
)
from .fetch_paper import (
    download_pdf,
    extract_pdf,
    fetch_apa_citation,
    fetch_crossref_metadata,
    fetch_web_paper_http,
    resolve_doi_url,
    resolve_open_access,
)
from .figures import (
    cleanup_old_figures,
    download_image_http,
    figure_filename,
    figure_label,
    guess_extension,
    image_dimensions,
    image_magic,
    is_probably_body_figure,
    normalize_caption,
    write_manifest,
)


def _log(quiet: bool, message: str) -> None:
    if not quiet:
        print(message)


def _browser_extract(
    url: str,
    browser_mode: str,
    wait_seconds: float,
    max_figures: int,
    warnings: List[str],
    quiet: bool,
) -> Optional[dict]:
    if browser_mode == "off":
        _log(quiet, "    [browser] 已禁用，跳过浏览器抽取。")
        return None
    try:
        _log(quiet, "    [browser] 检查 Chrome CDP ...")
        ensure_chrome(launch=(browser_mode == "auto"))
        _log(quiet, "    [browser] 打开页面并抽取高清图 ...")
        with BrowserSession() as session:
            page = session.extract(
                url,
                wait_seconds=wait_seconds,
                max_figures=max_figures,
            )
        _log(quiet, "    [browser] 完成：{} 字符，{} 张候选图。".format(
            len(page.get("text", "")), len(page.get("figures", []))
        ))
        return page
    except BrowserChallenge as exc:
        warnings.append("browser challenge: {}".format(exc))
        _log(quiet, "    [browser] 人机验证未通过，转 HTTP/PDF 回退。")
    except BrowserError as exc:
        warnings.append("browser unavailable: {}".format(exc))
        _log(quiet, "    [browser] 不可用：{}".format(exc))
    except Exception as exc:
        warnings.append("browser error: {}".format(exc))
        _log(quiet, "    [browser] 异常：{}".format(exc))
    return None


def _merge_metadata(base: dict, fallback: dict) -> dict:
    merged = dict(base or {})
    for key in ("title", "journal", "year", "doi", "abstract", "url"):
        if not merged.get(key) and (fallback or {}).get(key):
            merged[key] = fallback[key]
    if not merged.get("authors") and (fallback or {}).get("authors"):
        merged["authors"] = fallback["authors"]
    return merged


def _page_metadata(page: dict) -> dict:
    year = ""
    date = str(page.get("date") or "")
    if len(date) >= 4 and date[:4].isdigit():
        year = date[:4]
    return {
        "title": page.get("title", ""),
        "journal": page.get("site", ""),
        "year": year,
        "doi": page.get("doi", ""),
        "authors": page.get("authors", []),
        "abstract": page.get("description", ""),
        "url": page.get("url", ""),
    }


def _pdf_metadata(pdf_data: dict) -> dict:
    return {
        "title": pdf_data.get("title", ""),
        "journal": pdf_data.get("journal", ""),
        "year": pdf_data.get("year", ""),
        "doi": pdf_data.get("doi", ""),
        "authors": pdf_data.get("authors", []),
        "abstract": "",
    }


def _construct_apa(metadata: dict) -> Tuple[str, str]:
    authors = metadata.get("authors") or []
    if len(authors) > 6:
        author_str = ", ".join(authors[:6]) + ", et al."
    elif authors:
        author_str = ", ".join(authors)
    else:
        author_str = "Unknown author"
    year = metadata.get("year") or "n.d."
    title = metadata.get("title") or "Untitled"
    journal = metadata.get("journal") or ""
    citation = "{} ({}). {}. {}".format(author_str, year, title, journal).strip()
    return citation, "constructed"


def _page_figures(
    page: dict,
    referer: str,
    warnings: List[str],
) -> List[dict]:
    figures = []
    for raw in page.get("figures", []) or []:
        figure = dict(raw)
        figure["caption"] = normalize_caption(figure.get("caption", ""))
        figure["origin"] = "browser"
        figure["download"] = "browser"
        figure["method"] = figure.get("method") or "browser"
        if not figure.get("data"):
            data, content_type, error = download_image_http(
                figure.get("source_url", ""), referer=referer
            )
            if data:
                figure["data"] = data
                figure["mime"] = content_type
                figure["download"] = "http"
            else:
                warnings.append(
                    "figure download failed: {} ({})".format(
                        figure.get("source_url", ""), error or figure.get("fetch_error", "")
                    )
                )
                continue
        width, height = image_dimensions(figure["data"])
        if width:
            figure["width"] = width
        if height:
            figure["height"] = height
        if not is_probably_body_figure(figure):
            continue
        figure["is_body_figure"] = bool(figure.get("in_figure")) or bool(figure.get("caption"))
        figures.append(figure)

    # Deduplicate identical bytes.
    unique = []
    seen = set()
    for figure in figures:
        digest = hashlib.sha1(figure.get("data", b"")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        unique.append(figure)
    return unique


def _save_figures(
    figures: List[dict],
    slug: str,
    warnings: List[str],
) -> List[dict]:
    assets_dir = ASSETS_DIR / slug
    assets_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    kept_names = []
    seen_hashes = set()
    index = 0
    for figure in figures:
        data = figure.get("data")
        if not data:
            continue
        digest = hashlib.sha1(data).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)

        index += 1
        ext = image_magic(data) or guess_extension(
            figure.get("source_url", ""), figure.get("mime", "")
        )
        filename = figure_filename(index, ext)
        destination = assets_dir / filename
        destination.write_bytes(data)
        kept_names.append(filename)

        width, height = image_dimensions(data)
        caption = normalize_caption(figure.get("caption", ""))
        entries.append(
            {
                "id": "fig_{:02d}".format(index),
                "label": figure_label(caption),
                "caption": caption,
                "file": filename,
                "local_path": relative_posix(destination, PROJECT_ROOT),

                "markdown_path": "assets/{}/{}".format(slug, filename),
                "origin": figure.get("origin", "unknown"),
                "download": figure.get("download", figure.get("origin", "unknown")),
                "method": figure.get("method", ""),
                "source_url": figure.get("source_url", ""),
                "page": figure.get("page"),
                "width": width or figure.get("width"),
                "height": height or figure.get("height"),
                "bytes": len(data),
                "is_body_figure": figure.get("is_body_figure"),
            }
        )

    removed = cleanup_old_figures(assets_dir, kept_names)
    if removed:
        warnings.append("removed stale figures: {}".format(", ".join(removed)))
    return entries


def _manifest_payload(slug: str, source: str, figures: List[dict], warnings: List[str]) -> dict:
    return {
        "schema_version": 1,
        "slug": slug,
        "source": source,
        "extracted_at": now_iso(),
        "figure_count": len(figures),
        "figures": figures,
        "warnings": warnings,
    }


def _write_fulltext(
    path: Path,
    metadata: dict,
    pages: List[dict],
    text: str,
    source_url: str,
    method: str,
    warnings: List[str],
) -> None:
    lines = [
        "# {}".format(metadata.get("title") or "Extracted Paper"),
        "",
        "<!-- Evidence pack. This is raw extracted text, not a literature review. -->",
        "",
        "- **DOI**: {}".format(metadata.get("doi") or "N/A"),
        "- **Source**: {}".format(source_url or "N/A"),
        "- **Extraction method**: {}".format(method or "unknown"),
        "- **Extracted at**: {}".format(now_iso()),
    ]
    if warnings:
        lines.append("- **Warnings**: {}".format("; ".join(warnings)))
    lines.extend(["", "---", ""])

    if pages and any((page.get("text") or "").strip() for page in pages):
        for page in pages:
            page_text = (page.get("text") or "").strip()
            if not page_text:
                continue
            lines.extend(["## Page {}".format(page.get("page")), "", page_text, ""])
    else:
        lines.extend(["## Extracted Text", "", (text or "").strip(), ""])

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_raw_readme(path: Path, slug: str, metadata: dict, figures: List[dict], warnings: List[str]) -> None:
    lines = [
        "# Evidence pack: {}".format(metadata.get("title") or slug),
        "",
        "This folder contains **raw evidence**, not a literature review. The agent must write",
        "`papers/{}.md` from these files using `templates/paper_note.md`.".format(slug),
        "",
        "## Files",
        "",
        "- `paper.json` — metadata and extraction provenance",
        "- `fulltext.md` — extracted text with page markers",
        "- `figures/manifest.json` — captions, provenance, dimensions and local paths",
        "- `../../papers/assets/{}/` — downloaded figure files (next to the notes)".format(slug),
        "",
        "## Figures",
        "",
    ]
    if figures:
        lines.append("| ID | Caption | Origin | Local path |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for figure in figures:
            caption = (figure.get("caption") or "").replace("|", "-")[:120]
            lines.append(
                "| {} | {} | {} | `{}` |".format(
                    figure.get("id"), caption or "—", figure.get("origin"), figure.get("markdown_path")
                )
            )
    else:
        lines.append("_No figures were extracted._")
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append("- {}".format(warning))
    lines.extend(
        [
            "",
            "## Next steps",
            "",
            "```bash",
            "python3 main.py --check-note papers/{}.md --fix".format(slug),
            "python3 main.py --index papers/{}.md".format(slug),
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _update_raw_index(slug: str, metadata: dict, method: str, figure_count: int) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_INDEX_FILE.exists():
        RAW_INDEX_FILE.write_text(
            "# Evidence Packs (原始证据包)\n\n"
            "> Generated by the extraction pipeline. These are raw sources, not literature notes.\n\n"
            "| Date | Slug | Title | Source | Text | Figures | Pack |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n",
            encoding="utf-8",
        )
    content = RAW_INDEX_FILE.read_text(encoding="utf-8")
    title = (metadata.get("title") or slug).replace("|", "-").replace("\n", " ").strip()
    doi = metadata.get("doi") or ""
    source = "[{}](https://doi.org/{})".format(doi, doi) if doi else (metadata.get("source") or "—")
    row = "| {} | `{}` | {} | {} | {} | {} | [paper.json]({}/paper.json) |\n".format(
        today_iso(), slug, title, source, method, figure_count, slug
    )
    lines = [line for line in content.splitlines() if not line.startswith("| {} | `{}` |".format(today_iso(), slug))]
    # Remove any previous row for this slug regardless of date.
    lines = [line for line in lines if "`{}`".format(slug) not in line or not line.startswith("| ")]
    RAW_INDEX_FILE.write_text("\n".join(lines).rstrip() + "\n" + row, encoding="utf-8")


def extract_evidence(
    source_type: str,
    source_value: str,
    browser_mode: str = "auto",
    wait_seconds: float = 4.0,
    max_figures: int = 30,
    quiet: bool = False,
) -> dict:
    """Extract one paper into an evidence pack and return a summary dict."""
    ensure_workspace_dirs()
    warnings: List[str] = []
    metadata: dict = {}
    page = None
    pdf_data = None
    pages: List[dict] = []
    text = ""
    figures: List[dict] = []
    method_text = ""
    method_figures = ""
    source_url = ""
    final_url = ""
    doi = ""
    slug = ""
    open_access: Dict[str, str] = {}
    apa = ""

    if source_type == "doi":
        doi = extract_doi(source_value) or source_value.strip()
        slug = doi_to_slug(doi)
        _log(quiet, "  [1/5] Crossref 元数据 ...")
        metadata = fetch_crossref_metadata(doi)
        if metadata.get("error"):
            warnings.append("crossref: {}".format(metadata["error"]))
        apa = fetch_apa_citation(doi)
        open_access = resolve_open_access(doi)
        source_url = resolve_doi_url(doi) or open_access.get("landing_page_url") or "https://doi.org/{}".format(doi)
        _log(quiet, "  [2/5] 浏览器优先抽取：{}".format(source_url))
        page = _browser_extract(source_url, browser_mode, wait_seconds, max_figures, warnings, quiet)
        if page:
            text = page.get("text", "")
            final_url = page.get("url", source_url)
            method_text = "browser"
            figures = _page_figures(page, final_url or source_url, warnings)
            metadata = _merge_metadata(metadata, _page_metadata(page))
        if len(text) < 800:
            _log(quiet, "  [3/5] 浏览器正文不足，尝试直接 HTTP ...")
            try:
                http_page = fetch_web_paper_http(source_url)
                if len(http_page.get("text", "")) > len(text):
                    text = http_page.get("text", "")
                    final_url = http_page.get("url", source_url)
                    method_text = "http"
                    if not figures:
                        figures = _page_figures(http_page, final_url, warnings)
                    metadata = _merge_metadata(metadata, _page_metadata(http_page))
            except Exception as exc:
                warnings.append("http: {}".format(exc))
        if len(text) < 800 and open_access.get("pdf_url"):
            _log(quiet, "  [4/5] 正文仍不足，下载开放获取 PDF ...")
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_path = Path(temp_dir) / "{}.pdf".format(slug)
                ok, error = download_pdf(open_access["pdf_url"], pdf_path)
                if ok:
                    pdf_data = extract_pdf(pdf_path, include_figures=(not figures))
                    pages = pdf_data["pages"]
                    text = pdf_data["full_text"]
                    method_text = "pdf"
                    metadata = _merge_metadata(metadata, _pdf_metadata(pdf_data))
                    if not figures:
                        figures = [dict(figure, origin="pdf") for figure in pdf_data["figures"]]
                        method_figures = "pdf"
                else:
                    warnings.append("open access PDF: {}".format(error))

    elif source_type == "url":
        source_url = source_value.strip()
        _log(quiet, "  [1/5] 浏览器优先抽取：{}".format(source_url))
        page = _browser_extract(source_url, browser_mode, wait_seconds, max_figures, warnings, quiet)
        if page:
            text = page.get("text", "")
            final_url = page.get("url", source_url)
            method_text = "browser"
            figures = _page_figures(page, final_url or source_url, warnings)
            metadata = _merge_metadata(metadata, _page_metadata(page))
        if len(text) < 300:
            _log(quiet, "  [2/5] 浏览器正文不足，尝试直接 HTTP ...")
            try:
                http_page = fetch_web_paper_http(source_url)
                text = http_page.get("text", "")
                final_url = http_page.get("url", source_url)
                method_text = "http"
                if not figures:
                    figures = _page_figures(http_page, final_url, warnings)
                metadata = _merge_metadata(metadata, _page_metadata(http_page))
            except Exception as exc:
                warnings.append("http: {}".format(exc))
        doi = extract_doi(metadata.get("doi", "")) or extract_doi(final_url) or extract_doi(source_url)
        if doi:
            slug = doi_to_slug(doi)
            _log(quiet, "  [3/5] 页面含 DOI，补充 Crossref 元数据 ...")
            crossref = fetch_crossref_metadata(doi)
            if crossref.get("error"):
                warnings.append("crossref: {}".format(crossref["error"]))
            metadata = _merge_metadata(metadata, crossref)
            metadata["doi"] = doi
            apa = fetch_apa_citation(doi)
            open_access = resolve_open_access(doi)
            if len(text) < 800 and open_access.get("pdf_url"):
                _log(quiet, "  [4/5] 正文不足，下载开放获取 PDF ...")
                with tempfile.TemporaryDirectory() as temp_dir:
                    pdf_path = Path(temp_dir) / "{}.pdf".format(slug)
                    ok, error = download_pdf(open_access["pdf_url"], pdf_path)
                    if ok:
                        pdf_data = extract_pdf(pdf_path, include_figures=(not figures))
                        pages = pdf_data["pages"]
                        text = pdf_data["full_text"]
                        method_text = "pdf"
                        metadata = _merge_metadata(metadata, _pdf_metadata(pdf_data))
                        if not figures:
                            figures = [dict(figure, origin="pdf") for figure in pdf_data["figures"]]
                            method_figures = "pdf"
                    else:
                        warnings.append("open access PDF: {}".format(error))
        else:
            slug = url_to_slug(source_url, metadata.get("title", ""))

    elif source_type == "pdf":
        pdf_path = Path(source_value).expanduser().resolve()
        if not pdf_path.exists():
            raise FileNotFoundError("Local PDF not found: {}".format(pdf_path))
        _log(quiet, "  [1/5] 解析本地 PDF 文本与 DOI ...")
        pdf_data = extract_pdf(pdf_path, include_figures=True)
        pages = pdf_data["pages"]
        text = pdf_data["full_text"]
        method_text = "pdf"
        metadata = _merge_metadata(metadata, _pdf_metadata(pdf_data))
        doi = pdf_data.get("doi", "")
        slug = doi_to_slug(doi) if doi else slugify(pdf_path.stem)
        if doi:
            _log(quiet, "  [2/5] PDF 含 DOI，补充 Crossref 与浏览器高清图 ...")
            crossref = fetch_crossref_metadata(doi)
            if crossref.get("error"):
                warnings.append("crossref: {}".format(crossref["error"]))
            metadata = _merge_metadata(metadata, crossref)
            metadata["doi"] = doi
            open_access = resolve_open_access(doi)
            source_url = resolve_doi_url(doi) or open_access.get("landing_page_url") or "https://doi.org/{}".format(doi)
            page = _browser_extract(source_url, browser_mode, wait_seconds, max_figures, warnings, quiet)
            if page:
                final_url = page.get("url", source_url)
                browser_figures = _page_figures(page, final_url, warnings)
                if browser_figures:
                    figures = browser_figures
                    method_figures = "browser"
                else:
                    figures = [dict(figure, origin="pdf") for figure in pdf_data["figures"]]
                    method_figures = "pdf"
                if len(text) < 800:
                    text = page.get("text", text)
                    method_text = "browser+pdf"
            else:
                figures = [dict(figure, origin="pdf") for figure in pdf_data["figures"]]
                method_figures = "pdf"
        else:
            _log(quiet, "  [2/5] 未在 PDF 中找到 DOI，使用 PDF 内嵌图作为回退 ...")
            warnings.append("PDF 中未找到 DOI；图片来自 PDF 内嵌位图，可能缺少图注。")
            source_url = str(pdf_path)
            figures = [dict(figure, origin="pdf") for figure in pdf_data["figures"]]
            method_figures = "pdf"
    else:
        raise ValueError("Unknown source_type: {}".format(source_type))

    if not metadata.get("title"):
        metadata["title"] = slug.replace("_", " ")
    if not metadata.get("doi") and doi:
        metadata["doi"] = doi

    apa = apa or ""
    if not apa and doi:
        apa = fetch_apa_citation(doi)
    if not apa:
        apa, apa_source = _construct_apa(metadata)
    else:
        apa_source = "doi-content-negotiation"

    _log(quiet, "  [5/5] 写入证据包与图片 ...")
    figure_entries = _save_figures(figures, slug, warnings)
    origins = sorted({entry.get("origin", "unknown") for entry in figure_entries})
    figure_method = ",".join(origins) if origins else (method_figures or "none")
    method = "text={}; figures={}".format(method_text or "unknown", figure_method)
    if not text or len(text) < 800:
        warnings.append(
            "正文少于 800 字符；可能是摘要页、付费墙或抽取失败。请检查 fulltext.md 后再写笔记。"
        )
    if not figure_entries:
        warnings.append("未提取到图片。若论文有图，请检查浏览器访问权限或使用 --browser auto。")

    raw_dir = RAW_DIR / slug
    raw_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = raw_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    manifest = _manifest_payload(slug, source_url, figure_entries, warnings)
    manifest_path = figures_dir / "manifest.json"
    write_manifest(manifest_path, manifest)

    fulltext_path = raw_dir / "fulltext.md"
    _write_fulltext(
        fulltext_path,
        metadata,
        pages,
        text,
        final_url or source_url,
        method_text or "unknown",
        warnings,
    )

    paper = {
        "schema_version": 1,
        "slug": slug,
        "title": metadata.get("title", ""),
        "authors": metadata.get("authors", []),
        "journal": metadata.get("journal", ""),
        "year": metadata.get("year", ""),
        "doi": metadata.get("doi") or doi or "",
        "doi_url": "https://doi.org/{}".format(metadata.get("doi") or doi) if (metadata.get("doi") or doi) else "",
        "source_type": source_type,
        "source": source_value,
        "final_url": final_url or source_url,
        "apa_citation": apa,
        "apa_source": apa_source,
        "abstract": metadata.get("abstract", ""),
        "description": metadata.get("description", ""),
        "extracted_at": now_iso(),
        "method": method,
        "open_access": open_access,
        "warnings": warnings,
        "stats": {
            "text_chars": len(text or ""),
            "pages": len(pages) if pages else None,
            "figures": len(figure_entries),
            "text_method": method_text or "unknown",
            "figure_method": figure_method,
        },
        "files": {
            "fulltext": "fulltext.md",
            "figures_manifest": "figures/manifest.json",
            "readme": "README.md",
            "assets_dir": relative_posix(ASSETS_DIR / slug, PROJECT_ROOT),
        },
    }
    paper_path = raw_dir / "paper.json"
    paper_path.write_text(json.dumps(paper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _write_raw_readme(raw_dir / "README.md", slug, metadata, figure_entries, warnings)
    _update_raw_index(slug, metadata, method, len(figure_entries))

    return {
        "slug": slug,
        "title": paper["title"],
        "doi": paper["doi"],
        "raw_dir": str(raw_dir),
        "paper_json": str(paper_path),
        "fulltext": str(fulltext_path),
        "manifest": str(manifest_path),
        "assets_dir": str(ASSETS_DIR / slug),
        "figures": len(figure_entries),
        "method": method,
        "warnings": warnings,
        "note_template": str(Path("templates") / "paper_note.md"),
        "next_note": str(PAPERS_DIR / "{}.md".format(slug)),
    }
