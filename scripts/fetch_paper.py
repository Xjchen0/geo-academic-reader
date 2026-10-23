#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paper Fetcher & Asset Extractor
Supports:
1. Crossref metadata & APA citation lookup.
2. Local PDF extraction (text + embedded images via pypdf).
3. Web extraction (Direct HTTP for Open Access / bioRxiv / PMC / Nature).
4. Chrome CDP 9222 connection for paywalled & Cloudflare-protected pages.
"""

import os
import sys
import re
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional

from .config import DEFAULT_HEADERS, CROSSREF_API_URL, CHROME_CDP_HTTP, slugify

def extract_doi(input_str: str) -> Optional[str]:
    """Extract DOI from raw string or URL."""
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", input_str)
    if match:
        doi = match.group(0).rstrip(".,;")
        return doi
    return None

def fetch_crossref_metadata(doi: str) -> Dict[str, Any]:
    """Retrieve publication metadata from Crossref."""
    url = f"{CROSSREF_API_URL}{doi}"
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            message = data.get("message", {})
            title = message.get("title", [""])[0] if message.get("title") else "Untitled Publication"
            authors = []
            for a in message.get("author", []):
                given = a.get("given", "")
                family = a.get("family", "")
                authors.append(f"{given} {family}".strip())
            container = message.get("container-title", [""])
            journal = container[0] if container else "Unknown Journal"
            published = message.get("published", {}).get("date-parts", [[None]])[0]
            year = str(published[0]) if published and published[0] else ""
            return {
                "title": title,
                "authors": authors,
                "journal": journal,
                "year": year,
                "abstract": message.get("abstract", ""),
                "doi": doi
            }
    except Exception as e:
        return {
            "title": f"Paper ({doi})",
            "authors": [],
            "journal": "Academic Publication",
            "year": "",
            "abstract": "",
            "doi": doi,
            "error": str(e)
        }

def fetch_apa_citation(doi: str) -> str:
    """Fetch formal APA citation using DOI Content Negotiation."""
    url = f"https://doi.org/{doi}"
    headers = dict(DEFAULT_HEADERS)
    headers["Accept"] = "text/x-bibliography; style=apa"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            citation = resp.read().decode("utf-8").strip()
            return citation
    except Exception:
        return f"DOI: {doi}"

def extract_from_local_pdf(pdf_path: Path, output_assets_dir: Path) -> Dict[str, Any]:
    """Extract text and embedded images from a local PDF using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required for local PDF extraction. Run: pip install pypdf")

    output_assets_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(pdf_path))
    extracted_text = []
    figures = []
    
    img_count = 0
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            extracted_text.append(f"--- Page {page_num + 1} ---\n{text}")
        
        # Extract images
        for img_obj in page.images:
            img_count += 1
            filename = f"fig_page{page_num + 1}_{img_count}_{img_obj.name}"
            # Clean filename
            filename = re.sub(r"[^\w\.-]", "_", filename)
            if not filename.endswith((".png", ".jpg", ".jpeg")):
                filename += ".png"
            dest_file = output_assets_dir / filename
            try:
                with open(dest_file, "wb") as f:
                    f.write(img_obj.data)
                figures.append({
                    "filename": filename,
                    "rel_path": f"./assets/{output_assets_dir.name}/{filename}",
                    "caption": f"Extracted figure from Page {page_num + 1}"
                })
            except Exception:
                pass

    return {
        "title": pdf_path.stem.replace("_", " "),
        "full_text": "\n\n".join(extracted_text),
        "figures": figures
    }

def fetch_web_paper(url: str, output_assets_dir: Path) -> Dict[str, Any]:
    """Direct HTTP fetch for Open Access web pages."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("beautifulsoup4 is required for HTML parsing. Run: pip install beautifulsoup4")

    output_assets_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled Article"

    # Extract article content
    article_tag = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile("article|content|body"))
    full_text = article_tag.get_text("\n", strip=True) if article_tag else soup.get_text("\n", strip=True)

    # Extract figures
    figures = []
    fig_tags = soup.find_all(["figure", "div"], class_=re.compile("figure|fig"))
    for i, ft in enumerate(fig_tags):
        img = ft.find("img")
        caption_tag = ft.find(["figcaption", "p"])
        caption = caption_tag.get_text(strip=True) if caption_tag else f"Figure {i+1}"
        if img and img.get("src"):
            img_url = img["src"]
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            elif img_url.startswith("/"):
                # Relative URL, construct with domain
                from urllib.parse import urlparse
                parsed = urlparse(url)
                img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
            
            # Download figure
            ext = ".png" if ".png" in img_url.lower() else ".jpg"
            fn = f"fig_{i+1}{ext}"
            dest = output_assets_dir / fn
            try:
                img_req = urllib.request.Request(img_url, headers=DEFAULT_HEADERS)
                with urllib.request.urlopen(img_req, timeout=15) as img_resp:
                    dest.write_bytes(img_resp.read())
                figures.append({
                    "filename": fn,
                    "rel_path": f"./assets/{output_assets_dir.name}/{fn}",
                    "caption": caption
                })
            except Exception:
                pass

    return {
        "title": title,
        "full_text": full_text,
        "figures": figures
    }
