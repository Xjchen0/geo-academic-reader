#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Metadata, HTTP, PDF and open-access helpers.

This module never writes review prose. It only returns extracted evidence.
"""

import hashlib
import html as html_lib
import io
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

from .config import (
    CROSSREF_API_URL,
    DEFAULT_HEADERS,
    OPENALEX_API_URL,
    extract_doi,
)
from .figures import (
    dedupe_figures,
    download_image_http,
    guess_extension,
    image_dimensions,
    image_magic,
    is_probably_body_figure,
    normalize_caption,
    pick_srcset,
    upgrade_figure_url,
)


def _headers(extra: Optional[dict] = None) -> dict:
    headers = dict(DEFAULT_HEADERS)
    if extra:
        headers.update(extra)
    return headers


def clean_jats(text: str) -> str:
    """Remove JATS/HTML tags and collapse whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _first(value) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def _date_year(message: dict) -> str:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        parts = (message.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            return str(parts[0][0])
    return ""


def fetch_crossref_metadata(doi: str) -> Dict[str, object]:
    """Retrieve publication metadata from Crossref."""
    doi = (doi or "").strip()
    if not doi:
        return {"doi": "", "error": "empty DOI"}
    url = CROSSREF_API_URL + quote(doi, safe="")
    try:
        response = requests.get(
            url,
            headers=_headers({"Accept": "application/json"}),
            timeout=20,
        )
        if response.status_code == 404:
            return {"doi": doi, "error": "404 Not Found (Crossref)"}
        response.raise_for_status()
        message = response.json().get("message", {})
        authors = []
        for author in message.get("author", []) or []:
            name = " ".join(
                part for part in (author.get("given", ""), author.get("family", "")) if part
            ).strip()
            if not name:
                name = author.get("name", "") or ""
            if name:
                authors.append(name)
        container = message.get("container-title") or []
        short_container = message.get("short-container-title") or []
        journal = _first(container) or _first(short_container) or ""
        return {
            "title": clean_jats(_first(message.get("title"))),
            "authors": authors,
            "journal": clean_jats(journal),
            "year": _date_year(message),
            "abstract": clean_jats(message.get("abstract", "")),
            "doi": doi,
            "type": message.get("type", ""),
            "publisher": message.get("publisher", ""),
            "url": message.get("URL", ""),
            "license": _first((message.get("license") or [{}])[0].get("URL", ""))
            if message.get("license")
            else "",
            "source": "crossref",
        }
    except Exception as exc:
        return {"doi": doi, "error": str(exc)}


def fetch_apa_citation(doi: str) -> str:
    """Fetch a formal APA citation using DOI content negotiation."""
    doi = (doi or "").strip()
    if not doi:
        return ""
    try:
        response = requests.get(
            "https://doi.org/" + quote(doi, safe="/"),
            headers=_headers({"Accept": "text/x-bibliography; style=apa"}),
            timeout=20,
            allow_redirects=True,
        )
        if response.status_code >= 400:
            return ""
        text = response.text.strip()
        if not text or "<html" in text[:200].lower():
            return ""
        return re.sub(r"\s+", " ", text)
    except Exception:
        return ""


def resolve_doi_url(doi: str) -> str:
    """Resolve a DOI to the publisher landing page."""
    doi = (doi or "").strip()
    fallback = "https://doi.org/" + doi if doi else ""
    if not doi:
        return fallback
    try:
        response = requests.get(
            "https://doi.org/" + quote(doi, safe="/"),
            headers=_headers(),
            timeout=20,
            allow_redirects=True,
            stream=True,
        )
        final = response.url or fallback
        response.close()
        return final
    except Exception:
        return fallback


def resolve_open_access(doi: str) -> Dict[str, str]:
    """Use OpenAlex to locate an open-access PDF / landing page (no API key)."""
    doi = (doi or "").strip()
    if not doi:
        return {}
    try:
        response = requests.get(
            OPENALEX_API_URL + quote(doi, safe="/"),
            headers=_headers({"Accept": "application/json"}),
            timeout=20,
        )
        if response.status_code >= 400:
            return {}
        message = response.json()
        best = message.get("best_oa_location") or {}
        locations = message.get("locations") or []
        pdf_url = best.get("pdf_url") or ""
        landing = best.get("landing_page_url") or ""
        if not pdf_url:
            for location in locations:
                if location.get("pdf_url"):
                    pdf_url = location.get("pdf_url")
                    landing = landing or location.get("landing_page_url", "")
                    break
        return {
            "is_oa": str(bool(message.get("open_access", {}).get("is_oa"))).lower(),
            "pdf_url": pdf_url or "",
            "landing_page_url": landing or "",
            "oa_url": message.get("open_access", {}).get("oa_url", "") or "",
            "license": best.get("license", "") or "",
        }
    except Exception:
        return {}


def fetch_html(url: str) -> Tuple[str, str, int, str]:
    """Fetch HTML. Returns (html, final_url, status, error)."""
    try:
        response = requests.get(url, headers=_headers(), timeout=30, allow_redirects=True)
        if response.status_code >= 400:
            return "", response.url, response.status_code, "HTTP {}".format(response.status_code)
        if not response.encoding or response.encoding.lower() == "iso-8859-1":
            response.encoding = response.apparent_encoding or "utf-8"
        return response.text, response.url, response.status_code, ""
    except Exception as exc:
        return "", url, 0, str(exc)


def is_cloudflare_page(html: str) -> bool:
    sample = (html or "")[:200000].lower()
    markers = (
        "just a moment",
        "enable javascript and cookies to continue",
        "verify you are human",
        "cf-chl",
        "attention required",
    )
    return any(marker in sample for marker in markers)


def parse_html_page(html: str, base_url: str, download_images: bool = True) -> Dict[str, object]:
    """Parse an already-fetched HTML page into text, metadata and figures."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("beautifulsoup4 is required for HTML parsing. Run: pip install beautifulsoup4")

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    def meta(name: str) -> str:
        element = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        return (element.get("content", "") if element else "") or ""

    title = (
        meta("citation_title")
        or (soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "")
        or (soup.title.get_text(" ", strip=True) if soup.title else "")
    )
    article = (
        soup.find("article")
        or soup.find("main")
        or soup.find("div", class_=re.compile(r"article|content|body", re.I))
        or soup.body
        or soup
    )
    full_text = article.get_text("\n", strip=True) if article else soup.get_text("\n", strip=True)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()

    figures = []
    seen = set()

    def add_figure(img, figure_el=None):
        if img is None:
            return
        src = (
            img.get("data-src")
            or img.get("data-original")
            or img.get("data-lazy-src")
            or img.get("src")
            or ""
        )
        srcset_best = pick_srcset(img.get("srcset", ""))
        if srcset_best:
            src = srcset_best
        if not src:
            return
        src = upgrade_figure_url(requests.compat.urljoin(base_url, src))
        if src in seen:
            return
        seen.add(src)
        caption_el = (figure_el.find("figcaption") if figure_el else None) or img.find_parent("figcaption")
        caption = normalize_caption(
            caption_el.get_text(" ", strip=True) if caption_el else img.get("alt", "")
        )
        link_el = (figure_el.find("a", href=True) if figure_el else None) or img.find_parent("a", href=True)
        link = requests.compat.urljoin(base_url, link_el["href"]) if link_el else ""
        if link and re.search(r"\.(png|jpe?g|gif|webp)(\?|$)", link, re.I):
            src = upgrade_figure_url(link)
        figures.append(
            {
                "source_url": src,
                "caption": caption,
                "alt": img.get("alt", "") or "",
                "width": 0,
                "height": 0,
                "in_figure": bool(figure_el),
                "origin": "http",
            }
        )

    for figure_el in soup.find_all("figure"):
        for img in figure_el.find_all("img"):
            add_figure(img, figure_el)
    for img in article.find_all("img") if article else []:
        if not img.find_parent("figure"):
            add_figure(img, None)

    figures = [figure for figure in dedupe_figures(figures) if is_probably_body_figure(figure)]

    if download_images:
        for figure in figures:
            data, content_type, error = download_image_http(
                figure["source_url"], referer=base_url
            )
            if data:
                figure["data"] = data
                figure["mime"] = content_type
                width, height = image_dimensions(data)
                if width:
                    figure["width"] = width
                if height:
                    figure["height"] = height
            else:
                figure["fetch_error"] = error

    return {
        "title": clean_jats(title),
        "text": full_text,
        "figures": figures,
        "url": base_url,
        "doi": meta("citation_doi") or extract_doi(html) or "",
        "date": meta("citation_publication_date"),
        "journal": meta("citation_journal_title"),
        "authors": [
            element.get("content", "")
            for element in soup.find_all("meta", attrs={"name": "citation_author"})
            if element.get("content")
        ],
        "description": meta("description") or meta("og:description"),
        "method": "http",
    }


def fetch_web_paper_http(url: str) -> Dict[str, object]:
    html, final_url, status, error = fetch_html(url)
    if error:
        raise RuntimeError(error)
    if is_cloudflare_page(html):
        raise RuntimeError(
            "页面被 Cloudflare/反爬拦截，请使用 --browser auto 通过 Chrome 访问。"
        )
    page = parse_html_page(html, final_url)
    page["url"] = final_url
    return page


def download_pdf(url: str, dest: Path) -> Tuple[bool, str]:
    """Download a PDF and verify its magic bytes."""
    try:
        response = requests.get(
            url, headers=_headers({"Accept": "application/pdf,*/*"}), timeout=90, stream=True
        )
        if response.status_code >= 400:
            return False, "HTTP {}".format(response.status_code)
        content_type = response.headers.get("Content-Type", "").lower()
        first = b""
        chunks = []
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if not chunk:
                continue
            if not first:
                first = chunk[:8]
            chunks.append(chunk)
        data = b"".join(chunks)
        if not data.startswith(b"%PDF") and "pdf" not in content_type:
            return False, "响应不是 PDF（Content-Type: {}）".format(content_type or "unknown")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True, ""
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def _pdf_text_with_fitz(pdf_path: Path) -> Tuple[List[dict], dict, str]:
    import fitz  # PyMuPDF, optional

    document = fitz.open(str(pdf_path))
    pages = []
    for index, page in enumerate(document):
        pages.append({"page": index + 1, "text": page.get_text("text") or ""})
    metadata = dict(document.metadata or {})
    document.close()
    return pages, metadata, "fitz"


def _pdf_text_with_pypdf(pdf_path: Path) -> Tuple[List[dict], dict, str]:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages = []
    for index, page in enumerate(reader.pages):
        pages.append({"page": index + 1, "text": page.extract_text() or ""})
    metadata = {}
    try:
        if reader.metadata:
            metadata = {str(key).lstrip("/"): str(value) for key, value in reader.metadata.items()}
    except Exception:
        metadata = {}
    return pages, metadata, "pypdf"


CAPTION_RE = re.compile(r"^\s*(?:Fig(?:ure)?\.?\s*\d+[A-Za-z]?)\b", re.I)


def extract_pdf_figures_fitz(pdf_path: Path, dpi: int = 300) -> List[dict]:
    """Crop figure + caption regions at high resolution with PyMuPDF."""
    try:
        import fitz
    except ImportError:
        return []

    figures = []
    seen_hashes = set()
    try:
        document = fitz.open(str(pdf_path))
    except Exception:
        return []

    for page_index, page in enumerate(document):
        try:
            page_rect = page.rect
            page_area = max(page_rect.width * page_rect.height, 1.0)
            blocks = page.get_text("dict").get("blocks", [])
        except Exception:
            continue

        image_blocks = []
        caption_blocks = []
        for block in blocks:
            bbox = fitz.Rect(block.get("bbox", (0, 0, 0, 0)))
            if block.get("type") == 1:
                area = max(bbox.width * bbox.height, 0.0)
                if area < page_area * 0.015:
                    continue
                if bbox.width > page_rect.width * 0.95 and bbox.height > page_rect.height * 0.95:
                    continue
                image_blocks.append((bbox, area))
            elif block.get("type") == 0:
                text = " ".join(
                    span.get("text", "")
                    for line in block.get("lines", [])
                    for span in line.get("spans", [])
                ).strip()
                if text and CAPTION_RE.match(text):
                    caption_blocks.append((bbox, normalize_caption(text)))

        used_captions = set()
        for bbox, _area in image_blocks:
            best_index = None
            best_score = None
            for index, (cap_bbox, _cap_text) in enumerate(caption_blocks):
                if index in used_captions:
                    continue
                # Horizontal overlap is required.
                overlap = max(0.0, min(bbox.x1, cap_bbox.x1) - max(bbox.x0, cap_bbox.x0))
                if overlap < min(bbox.width, cap_bbox.width) * 0.15:
                    continue
                if cap_bbox.y0 >= bbox.y1 - 4:
                    gap = cap_bbox.y0 - bbox.y1
                elif cap_bbox.y1 <= bbox.y0 + 4:
                    gap = bbox.y0 - cap_bbox.y1
                else:
                    gap = 0.0
                if gap > 220:
                    continue
                score = gap + 0.2 * abs((bbox.x0 + bbox.x1) - (cap_bbox.x0 + cap_bbox.x1)) / 2
                if best_score is None or score < best_score:
                    best_score = score
                    best_index = index

            caption = ""
            crop = fitz.Rect(bbox)
            if best_index is not None:
                used_captions.add(best_index)
                cap_bbox, caption = caption_blocks[best_index]
                crop = crop | cap_bbox

            crop = fitz.Rect(
                max(crop.x0 - 6, page_rect.x0),
                max(crop.y0 - 6, page_rect.y0),
                min(crop.x1 + 6, page_rect.x1),
                min(crop.y1 + 6, page_rect.y1),
            )
            if crop.width < 80 or crop.height < 60:
                continue
            try:
                pixmap = page.get_pixmap(clip=crop, dpi=dpi, alpha=False)
                data = pixmap.tobytes("png")
            except Exception:
                continue
            digest = hashlib.sha1(data).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            width, height = image_dimensions(data)
            figures.append(
                {
                    "data": data,
                    "mime": "image/png",
                    "caption": caption,
                    "page": page_index + 1,
                    "width": width or pixmap.width,
                    "height": height or pixmap.height,
                    "origin": "pdf",
                    "is_body_figure": bool(caption),
                    "source_url": "",
                    "method": "pdf-crop",
                }
            )

    document.close()
    return figures


def extract_pdf_embedded_images(pdf_path: Path) -> List[dict]:
    """Fallback: extract embedded bitmap streams with pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return []

    figures = []
    seen_hashes = set()
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return []

    for page_index, page in enumerate(reader.pages):
        try:
            images = list(page.images)
        except Exception:
            continue
        for image in images:
            try:
                data = image.data
            except Exception:
                continue
            if not data:
                continue
            ext = image_magic(data)
            if not ext:
                continue
            width, height = image_dimensions(data)
            if width and height and (width < 250 or height < 150):
                continue
            digest = hashlib.sha1(data).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            figures.append(
                {
                    "data": data,
                    "mime": "image/{}".format("jpeg" if ext == ".jpg" else ext.lstrip(".")),
                    "caption": "",
                    "page": page_index + 1,
                    "width": width,
                    "height": height,
                    "origin": "pdf",
                    "is_body_figure": None,
                    "source_url": "",
                    "method": "pdf-embedded",
                }
            )
    return figures


def extract_pdf(pdf_path: Path, include_figures: bool = True) -> Dict[str, object]:
    """Extract PDF text, metadata, DOI and (optionally) figures."""
    if not pdf_path.exists():
        raise FileNotFoundError(str(pdf_path))

    try:
        pages, metadata, text_method = _pdf_text_with_fitz(pdf_path)
    except Exception:
        pages, metadata, text_method = _pdf_text_with_pypdf(pdf_path)

    full_text = "\n\n".join(
        "--- Page {} ---\n{}".format(page["page"], page["text"].strip())
        for page in pages
        if page["text"].strip()
    )
    first_pages = "\n".join(page["text"] for page in pages[:3])
    doi = (
        extract_doi(metadata.get("doi", ""))
        or extract_doi(metadata.get("DOI", ""))
        or extract_doi(metadata.get("subject", ""))
        or extract_doi(metadata.get("Subject", ""))
        or extract_doi(first_pages)
    )

    title = (metadata.get("title") or metadata.get("Title") or "").strip()
    if not title or title.lower() in ("untitled", "anonymous"):
        for line in first_pages.splitlines():
            line = line.strip()
            if len(line) > 15 and not CAPTION_RE.match(line) and not line.lower().startswith("doi"):
                title = line
                break
    if not title:
        title = pdf_path.stem.replace("_", " ")

    figures = []
    if include_figures:
        figures = extract_pdf_figures_fitz(pdf_path)
        if not figures:
            figures = extract_pdf_embedded_images(pdf_path)

    return {
        "title": title,
        "authors": [
            part.strip()
            for part in re.split(r"[;,]| and ", metadata.get("author", "") or "")
            if part.strip()
        ],
        "journal": (metadata.get("subject", "") or "").strip(),
        "year": _year_from_pdf_metadata(metadata),
        "doi": doi or "",
        "pages": pages,
        "full_text": full_text,
        "figures": figures,
        "metadata": metadata,
        "method": "pdf",
        "text_method": text_method,
    }


def _year_from_pdf_metadata(metadata: dict) -> str:
    for key in ("creationDate", "CreationDate", "modDate", "ModDate"):
        value = str(metadata.get(key, "") or "")
        match = re.search(r"(19|20)\d{2}", value)
        if match:
            return match.group(0)
    return ""
