#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Figure URL upgrading, validation, download and manifest helpers."""

import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from .config import DEFAULT_HEADERS

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff")


def pick_srcset(srcset: str) -> Optional[str]:
    """Pick the largest candidate from an HTML srcset attribute."""
    if not srcset:
        return None
    best_url = None
    best_score = -1.0
    for part in re.split(r",\s*(?=\S)", srcset):
        part = part.strip()
        if not part:
            continue
        pieces = part.split()
        url = pieces[0]
        score = 1.0
        if len(pieces) > 1:
            descriptor = pieces[1].lower()
            try:
                if descriptor.endswith("w"):
                    score = float(descriptor[:-1])
                elif descriptor.endswith("x"):
                    score = float(descriptor[:-1]) * 1000.0
            except ValueError:
                score = 1.0
        if score > best_score:
            best_score = score
            best_url = url
    return best_url


def upgrade_figure_url(url: str) -> str:
    """Rewrite common publisher thumbnail URLs to their high-resolution form."""
    if not url:
        return url
    url = url.strip()
    if url.startswith("data:"):
        return url

    # Nature / Springer Nature: /lw685/, /w400/ ... -> /full/
    if "springernature.com" in url or "nature.com" in url:
        url = re.sub(r"/(?:lw|w)\d+/", "/full/", url)
        url = re.sub(r"[?&](?:as|width|w)=\w+", "", url)

    # Science / AAAS
    elif "science.org" in url:
        url = url.replace("/w400/", "/w1200/").replace("/w450/", "/w1200/")
        url = url.replace("/medium/", "/large/")

    # Elsevier / ScienceDirect: -gr1.jpg -> -gr1_lrg.jpg
    elif "els-cdn.com" in url or "sciencedirect.com" in url:
        url = re.sub(r"(-gr\d+)\.(jpg|jpeg|png)(\?.*)?$", r"\1_lrg.\2\3", url, flags=re.I)

    # bioRxiv / medRxiv
    elif "biorxiv.org" in url or "medrxiv.org" in url:
        url = url.replace(".medium.gif", ".large.jpg")
        url = url.replace(".full.gif", ".full.jpg")
        url = url.replace(".medium.jpg", ".full.jpg")

    return url


def guess_extension(url: str = "", content_type: str = "") -> str:
    content_type = (content_type or "").lower()
    if "png" in content_type:
        return ".png"
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    if "gif" in content_type:
        return ".gif"
    if "webp" in content_type:
        return ".webp"
    path = urlparse(url or "").path.lower()
    for ext in IMAGE_EXTS:
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".png"


def image_magic(data: bytes) -> Optional[str]:
    """Identify an image from its magic bytes; returns a file extension."""
    if not data:
        return None
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tif"
    return None


def image_dimensions(data: bytes) -> Tuple[Optional[int], Optional[int]]:
    """Read PNG/JPEG/GIF dimensions without Pillow."""
    if not data:
        return None, None

    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        try:
            width, height = struct.unpack(">II", data[16:24])
            return int(width), int(height)
        except Exception:
            return None, None

    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        try:
            width, height = struct.unpack("<HH", data[6:10])
            return int(width), int(height)
        except Exception:
            return None, None

    if data.startswith(b"\xff\xd8\xff"):
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                index += 2
                continue
            if index + 4 > len(data):
                break
            length = struct.unpack(">H", data[index + 2:index + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                if index + 9 <= len(data):
                    height, width = struct.unpack(">HH", data[index + 5:index + 9])
                    return int(width), int(height)
                break
            index += 2 + length

    return None, None


def is_probably_body_figure(figure: dict) -> bool:
    """Filter publisher chrome (logos, icons, tracking pixels, avatars)."""
    url = (figure.get("src") or figure.get("source_url") or "").lower()
    caption = (figure.get("caption") or "").lower()
    if not url or url.startswith("data:"):
        return False
    bad_tokens = (
        "logo", "icon", "avatar", "sprite", "badge", "spinner", "loading",
        "tracking", "pixel", "advert", "banner", "social", "favicon",
    )
    if any(token in url for token in bad_tokens):
        return False
    width = figure.get("width") or 0
    height = figure.get("height") or 0
    rect_width = (figure.get("rect") or {}).get("width") or 0
    if width and width < 250 and rect_width < 220:
        return False
    if height and height < 120 and rect_width < 220:
        return False
    if not caption and not figure.get("in_figure") and rect_width and rect_width < 300:
        return False
    return True


def dedupe_figures(figures: Iterable[dict]) -> List[dict]:
    seen = set()
    result = []
    for figure in figures:
        key = (figure.get("source_url") or figure.get("src") or "").strip()
        if not key:
            continue
        key = upgrade_figure_url(key)
        if key in seen:
            continue
        seen.add(key)
        figure = dict(figure)
        figure["source_url"] = key
        result.append(figure)
    return result


def normalize_caption(caption: str) -> str:
    caption = re.sub(r"\s+", " ", (caption or "")).strip()
    return caption


def figure_label(caption: str) -> Optional[str]:
    match = re.match(
        r"^\s*((?:Fig(?:ure)?\.?)\s*\d+[A-Za-z]?(?:\s*[\(（].*?[\)）])?)",
        caption or "",
        flags=re.I,
    )
    return match.group(1).strip() if match else None


def figure_filename(index: int, ext: str) -> str:
    return "fig_{:02d}{}".format(index, ext)


def write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cleanup_old_figures(assets_dir: Path, keep_names: Iterable[str]) -> List[str]:
    """Remove only generated fig_*.ext files that are not part of the new manifest."""
    keep = {str(name) for name in keep_names}
    removed = []
    if not assets_dir.exists():
        return removed
    for path in assets_dir.iterdir():
        if path.is_file() and re.match(r"^fig_\d+\.(png|jpe?g|gif|webp|tiff?)$", path.name, re.I):
            if path.name not in keep:
                try:
                    path.unlink()
                    removed.append(path.name)
                except OSError:
                    pass
    return removed


def download_image_http(url: str, referer: str = "", timeout: int = 60) -> Tuple[Optional[bytes], str, str]:
    """Download an image with a Referer header. Returns (bytes, content_type, error)."""
    if not url:
        return None, "", "empty url"
    import requests  # imported lazily so offline helpers work without the package

    headers = dict(DEFAULT_HEADERS)
    headers["Accept"] = "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    if referer:
        headers["Referer"] = referer
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code >= 400:
            return None, "", "HTTP {}".format(response.status_code)
        if not response.content:
            return None, "", "empty response"
        return response.content, response.headers.get("Content-Type", ""), ""
    except Exception as exc:
        return None, "", str(exc)


def file_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
