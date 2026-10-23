#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration and helper utilities for Academic Paper Reader.
"""

from pathlib import Path
import re

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}

CROSSREF_API_URL = "https://api.crossref.org/works/"
CHROME_CDP_HTTP = "http://127.0.0.1:9222"

def slugify(value: str) -> str:
    """Convert text/DOI to a clean, safe folder/file name."""
    value = re.sub(r"[^\w\s\.-]", "_", value)
    value = re.sub(r"[\s]+", "_", value)
    return value.strip("._")[:80]
