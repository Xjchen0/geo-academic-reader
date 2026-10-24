#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Journal new-literature watch: scrape the configured publisher pages.

The workflow is deliberately two-stage:

1. ``scan`` opens each configured journal page in Chrome, parses the article
   list that the publisher shows (research articles, current issue, early
   publication), and writes a numbered candidate list.
2. The agent presents that list and waits. Evidence extraction starts only
   after the user names the numbers they want.

The journal list and parsers follow the user's own workflow in
``/Users/xjchen/work/gongzhonghao2`` (``fetch_journals_*.js`` and
``gen_md_*.py``). There is no topic search, no OpenAlex query and no
inference from existing notes.
"""

import datetime
import html
import json
import re
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from .browser import BrowserChallenge, BrowserSession, ensure_chrome
from .config import GUIDE_DIR, PROJECT_ROOT

DEFAULT_JOURNALS_PATH = PROJECT_ROOT / "journals.json"
USER_JOURNALS_PATH = GUIDE_DIR / "journals.json"
SCAN_DIR = GUIDE_DIR / "journal-scan"
LATEST_MD = SCAN_DIR / "latest.md"
LATEST_JSON = SCAN_DIR / "latest.json"

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# Only unmistakable non-research records are dropped. Commentaries, brief
# reports and replies stay: the user may want to read or compare them.
NOISE_TITLE_RE = re.compile(
    r"^\s*(?:(?:author|publisher)\s+)?"
    r"(?:correction|corrigendum|erratum|retraction|expression of concern|"
    r"issue information|front matter|back matter|cover image|"
    r"table of contents)\b",
    re.IGNORECASE,
)


class JournalConfigError(Exception):
    """The journal list is missing or malformed."""


class ScanError(Exception):
    """The scan could not run at all (configuration or argument problem)."""


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _clean(fragment) -> str:
    """Strip tags, MathML wrappers and entities, then collapse whitespace.

    Unescape first: several publishers put escaped markup in title attributes
    (``&lt;i&gt;P&lt;/i&gt;-Wave``), which would otherwise survive the tag
    removal and reach the list as literal HTML.
    """
    if fragment is None:
        return ""
    text = html.unescape(str(fragment))
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<svg.*?</svg>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(
        r"<msub><mi>([A-Za-z]+)</mi><mn>(\d+)</mn></msub>", r"\1\2", text
    )
    text = re.sub(
        r"<msubsup><mi>([A-Za-z]+)</mi><mn>(\d+)</mn><mi>([A-Za-z]+)</mi></msubsup>",
        r"\1\2\3",
        text,
    )
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\u00a0", " ").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _absolute(base_url: str, href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(base_url, href)


def _valid_date(year, month, day) -> str:
    try:
        return datetime.date(int(year), int(month), int(day)).isoformat()
    except (TypeError, ValueError):
        return ""


def _parse_date(value) -> str:
    """Return ``YYYY-MM-DD`` for a publisher date string, else ``""``."""
    text = _clean(value)
    if not text:
        return ""

    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return _valid_date(match.group(1), match.group(2), match.group(3))

    month_names = (
        r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?"
    )
    match = re.search(
        r"\b(\d{1,2})\s+(" + month_names + r"),?\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if match:
        month = MONTHS.get(match.group(2).lower())
        if month:
            return _valid_date(match.group(3), month, match.group(1))

    match = re.search(
        r"\b(" + month_names + r")\s+(\d{1,2}),?\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if match:
        month = MONTHS.get(match.group(1).lower())
        if month:
            return _valid_date(match.group(3), month, match.group(2))
    return ""


def _normalise_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _is_noise(title: str) -> bool:
    return bool(NOISE_TITLE_RE.match(title or ""))


def _doi_from_path(path: str) -> str:
    """``/articles/s41586-026-11207-x`` -> ``10.1038/s41586-026-11207-x``."""
    match = re.search(r"/articles/([A-Za-z0-9._-]+)/?$", path or "")
    if not match:
        return ""
    name = match.group(1)
    if name.startswith("s") and re.search(r"\d", name):
        return "10.1038/" + name
    return ""


def _item(title, url, date="", doi="", kind="") -> Optional[dict]:
    title = _clean(title)
    if not title or _is_noise(title):
        return None
    iso = _parse_date(date)
    return {
        "title": title,
        "url": url,
        "doi": (doi or "").strip().lower(),
        "date": iso or _clean(date),
        "sort_date": iso,
        "kind": _clean(kind),
    }


# ---------------------------------------------------------------------------
# Page parsers (ported from gen_md_*.py in the reference workspace)
# ---------------------------------------------------------------------------

NATURE_TITLE_RE = re.compile(
    r'<h3[^>]*class="c-card__title"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.S,
)
NATURE_TIME_RE = re.compile(r'<time[^>]*datetime="([^"]+)"')

SCIENCE_SECTION_RE = re.compile(
    r'<h[45][^>]*class="[^"]*to-section[^"]*"[^>]*>(.*?)</h[45]>', re.S
)
SCIENCE_TITLE_RE = re.compile(
    r'<h3[^>]*class="[^"]*article-title[^"]*"[^>]*>.*?'
    r'<a[^>]*href="(/doi/([^"]+))"[^>]*>(.*?)</a>',
    re.S,
)


def parse_nature(page: str, base_url: str) -> List[dict]:
    items = []
    for block in re.findall(r"<article[^>]*>.*?</article>", page, re.S):
        match = NATURE_TITLE_RE.search(block)
        if not match:
            continue
        href = match.group(1)
        date_match = NATURE_TIME_RE.search(block)
        entry = _item(
            match.group(2),
            _absolute(base_url, href),
            date_match.group(1) if date_match else "",
            _doi_from_path(urlparse(href).path),
        )
        if entry:
            items.append(entry)
    return items


def _science_sections(page: str) -> List[Tuple[str, str]]:
    matches = list(SCIENCE_SECTION_RE.finditer(page))
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(page)
        sections.append((_clean(match.group(1)), page[match.end():end]))
    return sections


def _parse_science_segment(segment: str, base_url: str, date: str) -> List[dict]:
    items = []
    for match in SCIENCE_TITLE_RE.finditer(segment):
        entry = _item(
            match.group(3),
            _absolute(base_url, match.group(1)),
            date,
            match.group(2),
        )
        if entry:
            items.append(entry)
    return items


def parse_science_first(page: str, base_url: str) -> List[dict]:
    items = []
    for heading, segment in _science_sections(page):
        items.extend(_parse_science_segment(segment, base_url, heading))
    return items


def parse_science_current(page: str, base_url: str) -> List[dict]:
    for heading, segment in _science_sections(page):
        if "research article" in heading.lower():
            return _parse_science_segment(segment, base_url, "")
    return []


def parse_science_advances(page: str, base_url: str) -> List[dict]:
    selected = None
    for heading, segment in _science_sections(page):
        if "earth" in heading.lower():
            selected = segment
            break
    if selected is None:
        return []

    items = []
    cards = re.split(r'<div class="card(?=[" ])', selected)[1:]
    for card in cards:
        match = SCIENCE_TITLE_RE.search(card)
        if not match:
            continue
        time_match = re.search(r"<time[^>]*>(.*?)</time>", card, re.S)
        entry = _item(
            match.group(3),
            _absolute(base_url, match.group(1)),
            time_match.group(1) if time_match else "",
            match.group(2),
        )
        if entry:
            items.append(entry)
    return items


EPSL_TITLE_RE = re.compile(
    r'<a class="anchor article-content-title[^"]*"\s+'
    r'href="/science/article/pii/([A-Z0-9]+)"[^>]*>(.*?)</a>',
    re.S,
)
EPSL_DOI_RE = re.compile(r"https://doi\.org/(10\.1016/j\.epsl\.\d+\.\d+)")


def parse_epsl(page: str, base_url: str) -> List[dict]:
    items = []
    for match in EPSL_TITLE_RE.finditer(page):
        pii = match.group(1)
        # The DOI sits near the title link on ScienceDirect, but not always
        # inside the anchor. Read it from the surrounding block instead of
        # inventing one from the PII.
        chunk = page[max(0, match.start() - 400): match.end() + 400]
        doi_match = EPSL_DOI_RE.search(chunk)
        entry = _item(
            match.group(2),
            _absolute(base_url, "/science/article/pii/" + pii),
            "",
            doi_match.group(1) if doi_match else "",
        )
        if entry:
            items.append(entry)
    return items


def parse_agu(page: str, base_url: str) -> List[dict]:
    """AGU pages render Recently Published / Most Cited / Most Read panes."""
    panes = re.split(r'<div id="pane-[^"]+"', page)[1:]
    body = next((pane for pane in panes if '<div class="issue-item"' in pane), "")
    if not body:
        return []

    items = []
    for block in re.split(r'<div class="issue-item"', body)[1:]:
        doi_match = re.search(r"/doi/(10\.\d{4}/[A-Za-z0-9.]+)", block)
        title_match = re.search(
            r'<a href="/doi/[^"]+" title="([^"]+)" class="issue-item__title', block
        )
        if not (doi_match and title_match):
            continue
        date_match = re.search(
            r"First Published:</label><span[^>]*>\s*&nbsp;([^<]+)", block
        )
        entry = _item(
            title_match.group(1),
            "https://doi.org/" + doi_match.group(1),
            date_match.group(1) if date_match else "",
            doi_match.group(1),
        )
        if entry:
            items.append(entry)
    return items


def parse_geology_current(page: str, base_url: str) -> List[dict]:
    items = []
    for match in re.finditer(
        r'<h3 class="customLink item-title"[^>]*>\s*'
        r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        page,
        re.S,
    ):
        chunk = page[match.start(): match.start() + 8000]
        pdf_match = re.search(
            r'article-pdf/[^"]*?/([A-Za-z0-9]+\.\d+)\.pdf', chunk
        )
        doi = "10.1130/" + pdf_match.group(1) if pdf_match else ""
        entry = _item(
            match.group(2), _absolute(base_url, match.group(1)), "", doi
        )
        if entry:
            items.append(entry)
    return items


def parse_geology_early(page: str, base_url: str) -> List[dict]:
    groups = list(
        re.finditer(
            r'<h2[^>]*class="[^"]*al-subgroup-outer-id[^"]*"[^>]*>(.*?)</h2>',
            page,
            re.S,
        )
    )
    items = []
    for index, group in enumerate(groups):
        date = group.group(1)
        end = groups[index + 1].start() if index + 1 < len(groups) else len(page)
        segment = page[group.end():end]
        for match in re.finditer(
            r'<h5 class="al-title">\s*<a href="[^"]*/doi/'
            r'(10\.1130/[^"/]+)[^"]*"[^>]*>(.*?)</a>',
            segment,
            re.S,
        ):
            entry = _item(
                match.group(2),
                "https://doi.org/" + match.group(1),
                date,
                match.group(1),
            )
            if entry:
                items.append(entry)
    return items


def parse_gji(page: str, base_url: str) -> List[dict]:
    items = []
    for block in re.split(
        r'<div class="widget-dynamic-entry journalArticleItem', page
    )[1:]:
        doi_match = re.search(r'data-attribute="(10\.1093/gji/[A-Za-z0-9]+)"', block)
        title_match = re.search(
            r'<div class="widget-dynamic-journal-title"[^>]*>(.*?)</div>',
            block,
            re.S,
        )
        if not (doi_match and title_match):
            continue
        entry = _item(
            title_match.group(1),
            "https://doi.org/" + doi_match.group(1),
            "",
            doi_match.group(1),
        )
        if entry:
            items.append(entry)
    return items


def parse_pnas(page: str, base_url: str) -> List[dict]:
    recent = page.find("Recent articles")
    trending = page.find("Trending", recent) if recent >= 0 else -1
    segment = page[recent:trending] if recent >= 0 and trending > recent else page

    items = []
    for card in re.split(r'<div class="card(?=[" ])', segment)[1:]:
        match = re.search(
            r'<a href="(/doi/10\.1073/pnas\.[^"]+)" title="([^"]*)"', card
        )
        if not match:
            continue
        kind_match = re.search(r'card__meta__type">(.*?)</a>', card, re.S)
        date_match = re.search(r'card__meta__date">([^<]+)<', card)
        entry = _item(
            match.group(2),
            _absolute(base_url, match.group(1)),
            date_match.group(1) if date_match else "",
            match.group(1)[len("/doi/"):],
            kind_match.group(1) if kind_match else "",
        )
        if entry:
            items.append(entry)
    return items


PARSERS = {
    "nature": parse_nature,
    "science_first": parse_science_first,
    "science_current": parse_science_current,
    "science_advances": parse_science_advances,
    "epsl": parse_epsl,
    "agu": parse_agu,
    "geology_current": parse_geology_current,
    "geology_early": parse_geology_early,
    "gji": parse_gji,
    "pnas": parse_pnas,
}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def config_path() -> Path:
    """User copy wins; the shipped list is the fallback."""
    return USER_JOURNALS_PATH if USER_JOURNALS_PATH.is_file() else DEFAULT_JOURNALS_PATH


def load_config(path: Optional[Path] = None) -> dict:
    target = Path(path) if path else config_path()
    if not target.is_file():
        raise JournalConfigError(
            "找不到期刊清单：{}。请恢复 journals.json，或运行 "
            "python3 main.py --journals-init 生成个人副本。".format(target)
        )
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise JournalConfigError("期刊清单不是合法 JSON：{}（{}）".format(target, exc))
    if not isinstance(payload, dict):
        raise JournalConfigError("期刊清单顶层必须是对象：{}".format(target))

    journals = payload.get("journals")
    if not isinstance(journals, list) or not journals:
        raise JournalConfigError("期刊清单缺少非空的 journals 数组：{}".format(target))

    # 0.3.3 shipped an ISSN/Crossref list. The page scanner cannot use it, and
    # silently ignoring a user copy would be worse than stopping.
    if any(
        isinstance(raw, dict) and raw.get("issn") and not raw.get("parser")
        for raw in journals
    ):
        raise JournalConfigError(
            "期刊清单还是旧版 ISSN/Crossref 格式（v1），当前版本改为抓取期刊页面。"
            "请先备份 {}，再运行 python3 main.py --journals-init --force "
            "生成新的页面清单。".format(target)
        )

    seen_keys = set()
    normalised = []
    for raw in journals:
        if not isinstance(raw, dict):
            raise JournalConfigError("journals 中的每一项必须是对象：{!r}".format(raw))
        key = str(raw.get("key") or "").strip()
        name = str(raw.get("name") or "").strip()
        parser = str(raw.get("parser") or "").strip()
        if not key or not name or not parser:
            raise JournalConfigError(
                "期刊条目必须同时有 key、name、parser：{!r}".format(raw)
            )
        if not re.match(r"^[a-z0-9][a-z0-9._-]*$", key):
            raise JournalConfigError(
                "key 只能使用小写字母、数字、点、下划线和连字符：{}".format(key)
            )
        if key in seen_keys:
            raise JournalConfigError("期刊 key 重复：{}".format(key))
        if parser not in PARSERS:
            raise JournalConfigError(
                "期刊 {} 的 parser 不存在：{}（可用：{}）".format(
                    key, parser, ", ".join(sorted(PARSERS))
                )
            )

        url = str(raw.get("url") or "").strip()
        template = str(raw.get("url_template") or "").strip()
        volumes = raw.get("volumes") or []
        if url and template:
            raise JournalConfigError(
                "期刊 {} 只能配置 url 或 url_template 之一".format(key)
            )
        if not url and not template:
            raise JournalConfigError("期刊 {} 缺少 url 或 url_template".format(key))
        if url and not re.match(r"^https?://", url):
            raise JournalConfigError("期刊 {} 的 url 必须是 http(s) 地址".format(key))
        if template:
            if not isinstance(volumes, list) or not volumes:
                raise JournalConfigError(
                    "期刊 {} 使用 url_template 时必须给出 volumes 数组".format(key)
                )
            try:
                volumes = [int(volume) for volume in volumes]
            except (TypeError, ValueError):
                raise JournalConfigError(
                    "期刊 {} 的 volumes 必须是整数数组".format(key)
                )
            if "{volume}" not in template:
                raise JournalConfigError(
                    "期刊 {} 的 url_template 必须包含 {{volume}}".format(key)
                )

        seen_keys.add(key)
        normalised.append(
            {
                "key": key,
                "name": name,
                "parser": parser,
                "url": url,
                "url_template": template,
                "volumes": volumes,
                "enabled": bool(raw.get("enabled", True)),
                "wait": float(raw.get("wait", 5.0)),
                "challenge_timeout": int(raw.get("challenge_timeout", 60)),
                "scroll": bool(raw.get("scroll", False)),
                "ready": str(raw.get("ready") or ""),
            }
        )

    defaults = payload.get("defaults") or {}
    if not isinstance(defaults, dict):
        defaults = {}
    try:
        days = int(defaults.get("days", 0))
        limit = int(defaults.get("limit", 0))
    except (TypeError, ValueError):
        raise JournalConfigError("defaults 的 days / limit 必须是整数")
    sort = str(defaults.get("sort", "journal"))
    if days < 0 or limit < 0:
        raise JournalConfigError("defaults 的 days / limit 不能为负数")
    if sort not in ("journal", "date"):
        raise JournalConfigError("defaults 的 sort 只能是 journal 或 date")

    return {
        "version": payload.get("version", 2),
        "path": str(target),
        "defaults": {"days": days, "limit": limit, "sort": sort},
        "journals": normalised,
    }


def init_user_config(force: bool = False) -> dict:
    if USER_JOURNALS_PATH.exists() and not force:
        return {
            "path": str(USER_JOURNALS_PATH),
            "created": False,
            "message": "个人期刊清单已存在，未覆盖。直接编辑该文件即可。",
        }
    if not DEFAULT_JOURNALS_PATH.is_file():
        raise JournalConfigError("缺少默认期刊清单：{}".format(DEFAULT_JOURNALS_PATH))
    USER_JOURNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_JOURNALS_PATH.write_text(
        DEFAULT_JOURNALS_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return {
        "path": str(USER_JOURNALS_PATH),
        "created": True,
        "message": "已生成个人期刊清单；修改 journals 中的 url / enabled 后重新扫描。",
    }


def page_urls(entry: dict) -> List[str]:
    if entry.get("url"):
        return [entry["url"]]
    return [
        entry["url_template"].format(volume=volume)
        for volume in entry.get("volumes") or []
    ]


# ---------------------------------------------------------------------------
# Fetching and scanning
# ---------------------------------------------------------------------------


def _fetch_page(entry: dict, url: str) -> str:
    """Open one page in the user's Chrome and return rendered HTML.

    No retry loop: a Cloudflare challenge must be completed by the user in the
    visible window, and refreshing again can make the challenge worse.
    """
    ensure_chrome(launch=True)
    with BrowserSession(timeout=90) as session:
        return session.fetch_html(
            url,
            wait_seconds=entry.get("wait", 5.0),
            challenge_timeout=entry.get("challenge_timeout", 60),
            scroll=entry.get("scroll", False),
            ready_selector=entry.get("ready", ""),
        )


def scan(
    days: Optional[int] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    journal_keys: Optional[Iterable[str]] = None,
    config_file: Optional[Path] = None,
    today: Optional[datetime.date] = None,
    fetcher: Optional[Callable[[dict, str], str]] = None,
    logger: Optional[Callable[[str], None]] = None,
    translate: bool = False,
    translator: Optional[Callable[[str], str]] = None,
) -> dict:
    """Scrape the configured pages and return candidates plus page statuses.

    ``fetcher`` is injectable for tests; it takes ``(entry, url)`` and returns
    HTML. ``translate`` requests Chinese titles; ``translator`` is an optional
    ``english -> chinese`` callable used instead of the Bing client. This
    function never extracts evidence and never writes a note.
    """
    config = load_config(config_file)
    defaults = config["defaults"]
    days = int(defaults["days"] if days is None else days)
    limit = int(defaults["limit"] if limit is None else limit)
    sort = str(defaults["sort"] if sort is None else sort)
    if days < 0:
        raise ScanError("--days 不能为负数（0 表示按页面当前列表，不做日期过滤）")
    if limit < 0:
        raise ScanError("--limit 不能为负数")
    if sort not in ("journal", "date"):
        raise ScanError("--sort 只能是 journal 或 date")

    today = today or datetime.date.today()
    since = (today - datetime.timedelta(days=days)).isoformat() if days else ""
    wanted = {key.strip() for key in (journal_keys or []) if key and key.strip()}
    known = {entry["key"] for entry in config["journals"]}
    unknown = sorted(wanted - known)
    if unknown:
        raise ScanError(
            "期刊 key 不存在：{}。可用 key：{}".format(
                ", ".join(unknown), ", ".join(sorted(known))
            )
        )

    fetch = fetcher or _fetch_page
    entries = config["journals"]
    statuses = []
    candidates = []
    pages_total = 0
    filtered = 0

    for order, entry in enumerate(entries):
        if not entry["enabled"]:
            statuses.append(
                {
                    "key": entry["key"], "name": entry["name"],
                    "status": "disabled", "found": 0, "listed": 0,
                    "urls": page_urls(entry), "error": "",
                }
            )
            continue
        if wanted and entry["key"] not in wanted:
            statuses.append(
                {
                    "key": entry["key"], "name": entry["name"],
                    "status": "skipped", "found": 0, "listed": 0,
                    "urls": page_urls(entry), "error": "",
                }
            )
            continue

        urls = page_urls(entry)
        pages_total += len(urls)
        items = []
        errors = []
        challenge = False
        for page_index, url in enumerate(urls, 1):
            if logger:
                label = entry["name"]
                if len(urls) > 1:
                    label += " [{}/{}]".format(page_index, len(urls))
                logger("  → {} {}".format(label, url))
            try:
                page_html = fetch(entry, url)
            except BrowserChallenge as exc:
                challenge = True
                errors.append(str(exc))
                continue
            except Exception as exc:
                errors.append(str(exc))
                continue
            for item in PARSERS[entry["parser"]](page_html, url):
                item["journal_key"] = entry["key"]
                item["journal"] = entry["name"]
                item["journal_order"] = order
                item["source_page"] = url
                if since and item.get("sort_date") and item["sort_date"] < since:
                    filtered += 1
                    continue
                items.append(item)

        if not items and challenge:
            status = "challenge"
        elif not items and errors:
            status = "error"
        else:
            status = "ok"
        statuses.append(
            {
                "key": entry["key"],
                "name": entry["name"],
                "status": status,
                "found": len(items),
                "listed": 0,
                "urls": urls,
                "error": "; ".join(error for error in errors if error),
            }
        )
        candidates.extend(items)

    # Deduplicate globally: Science First Release and Current can overlap,
    # and co-published announcements share a DOI.
    unique: Dict[str, dict] = {}
    seen_titles = set()
    for candidate in candidates:
        doi = candidate.get("doi") or ""
        title_key = _normalise_title(candidate.get("title"))
        key = "doi:" + doi if doi else "title:" + title_key
        if key in unique:
            existing = unique[key]
            if doi and not existing.get("doi"):
                existing["doi"] = doi
                existing["url"] = candidate["url"]
            continue
        alt_key = "title:" + title_key if title_key else ""
        if alt_key and alt_key in unique:
            continue
        unique[key] = candidate
        if title_key:
            seen_titles.add(title_key)

    ordered = list(unique.values())
    total_found = len(ordered)

    if sort == "date":
        ordered.sort(
            key=lambda item: (
                item.get("sort_date") or "", -item.get("journal_order", 0)
            ),
            reverse=True,
        )
    else:
        ordered.sort(key=lambda item: item.get("journal_order", 0))

    # Round-robin keeps every selected journal visible when --limit is small.
    if limit and total_found > limit:
        queues: Dict[int, List[dict]] = {}
        for item in ordered:
            queues.setdefault(item["journal_order"], []).append(item)
        selected = []
        while len(selected) < limit:
            added = False
            for order in sorted(queues):
                queue = queues.get(order)
                if not queue:
                    continue
                selected.append(queue.pop(0))
                added = True
                if len(selected) >= limit:
                    break
            if not added:
                break
        ordered = selected
        if sort == "date":
            ordered.sort(
                key=lambda item: (
                    item.get("sort_date") or "", -item["journal_order"]
                ),
                reverse=True,
            )
        else:
            ordered.sort(key=lambda item: item["journal_order"])

    translation_meta = {
        "enabled": bool(translate),
        "provider": "",
        "cached": 0,
        "translated": 0,
        "missing": 0,
        "error": "",
    }
    for item in ordered:
        item.setdefault("title_zh", "")
    if translate and ordered:
        from .translate import translate_titles

        titles = [item["title"] for item in ordered]
        try:
            if translator is not None:
                mapping = {
                    _clean(title): _clean(translator(title)) for title in titles
                }
                mapping = {key: value for key, value in mapping.items() if value}
                translation_meta.update(
                    {
                        "provider": "custom",
                        "translated": len(mapping),
                        "missing": len(titles) - len(mapping),
                    }
                )
            else:
                mapping, meta = translate_titles(
                    titles,
                    SCAN_DIR / "translations.json",
                    logger=logger,
                )
                translation_meta.update(meta)
        except Exception as exc:
            mapping = {}
            translation_meta["error"] = str(exc)
            translation_meta["missing"] = len(titles)
        for item in ordered:
            item["title_zh"] = mapping.get(_clean(item["title"]), "")
        if not translation_meta.get("missing"):
            translation_meta["missing"] = sum(
                1 for item in ordered if not item.get("title_zh")
            )

    groups = []
    if sort == "journal":
        for entry in entries:
            items = [item for item in ordered if item["journal_key"] == entry["key"]]
            if not items:
                continue
            groups.append(
                {"key": entry["key"], "name": entry["name"], "items": items}
            )
    elif ordered:
        groups = [{"key": "all", "name": "按页面日期排序", "items": ordered}]

    index = 0
    for group in groups:
        for item in group["items"]:
            index += 1
            item["index"] = index
            for status in statuses:
                if status["key"] == item["journal_key"]:
                    status["listed"] += 1
                    break

    ordered = [item for group in groups for item in group["items"]]
    scanned = sum(
        1 for status in statuses if status["status"] in ("ok", "error", "challenge")
    )
    return {
        "generated_at": datetime.datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "source": "publisher-pages",
        "window": {
            "from": since,
            "to": today.isoformat(),
            "days": days,
            "filtered": filtered,
        },
        "config": config["path"],
        "sort": sort,
        "limit": limit,
        "scanned": scanned,
        "pages": pages_total,
        "total_found": total_found,
        "total": len(ordered),
        "truncated": bool(limit and total_found > len(ordered)),
        "translation": translation_meta,
        "journals": statuses,
        "groups": groups,
        "candidates": ordered,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _item_meta(item: dict) -> str:
    parts = [item["journal"]]
    if item.get("kind"):
        parts.append(item["kind"])
    if item.get("date"):
        parts.append(item["date"])
    if item.get("doi"):
        parts.append("[DOI](https://doi.org/{})".format(item["doi"]))
    if item.get("url"):
        parts.append("[原文]({})".format(item["url"]))
    return " · ".join(parts)


def render_markdown(payload: dict) -> str:
    window = payload["window"]
    translation = payload.get("translation") or {}
    lines = [
        "# 期刊新文献清单 · 抓取于 {}".format(
            payload["generated_at"][:16].replace("T", " ")
        ),
        "",
        "> **候选清单，尚未精读**",
        ">",
        "> 共 {} 篇，来自 {} 个期刊页面。在你明确回复编号或 DOI 之前，"
        "不得建立证据包、不得写笔记。".format(payload["total"], payload["pages"]),
        "",
    ]
    if translation.get("enabled"):
        lines.append(
            "> 中文标题为机器翻译，仅供检索；阅读与引用请以英文原题和原文为准。"
        )
        lines.append("")
        if translation.get("missing"):
            lines.append(
                "> 中文标题暂缺 {} 篇（翻译失败或限流）；重跑同一条命令会补齐。".format(
                    translation["missing"]
                )
            )
            lines.append("")
    if window["days"]:
        lines.append(
            "> 日期过滤：仅显示 {} 之后有明确日期的条目；无日期条目保留。".format(
                window["from"]
            )
        )
        lines.append("")
    if payload["truncated"]:
        lines.append(
            "> 说明：共 {} 篇，按 `--limit {}` 列出 {} 篇（各期刊轮转选取）。".format(
                payload["total_found"], payload["limit"], payload["total"]
            )
        )
        lines.append("")

    if not payload["groups"]:
        lines.extend([
            "没有解析到候选。请检查扫描告警；如果浏览器停在人机验证页，"
            "请在 Chrome 窗口中完成验证后重新运行同一条命令。",
            "",
        ])

    for group in payload["groups"]:
        lines.append("## {}（{} 篇）".format(group["name"], len(group["items"])))
        lines.append("")
        for item in group["items"]:
            lines.append("**[{}] {}**".format(item["index"], item["title"]))
            if translation.get("enabled"):
                lines.append("")
                lines.append(
                    "中文（机译）：{}".format(item.get("title_zh") or "暂缺")
                )
            lines.append("")
            lines.append(_item_meta(item))
            lines.append("")

    lines.extend([
        "---",
        "",
        "## 下一步",
        "",
        "回复要精读的编号（例如 `3, 7, 12`），或直接给出 DOI。"
        "**在你选择之前，这份清单不会触发任何抽取或写作。**",
        "",
        "这个脚本只负责抓页面和列清单；它不会运行 `--doi`，"
        "不会创建 `.raw/`，也不会写 `papers/*.md`。"
        "只有你回复编号或 DOI 之后，才会由 agent 逐篇建立证据包。",
        "",
        "列表来自各期刊官网的 research-articles / current issue / "
        "early publication 页面，不是主题检索，也不是按上下文推断。"
        "页面本身决定“最新”的范围；如需更早的文章，请直接给 DOI。",
        "",
    ])

    problems = [status for status in payload["journals"] if status.get("error")]
    if problems:
        lines.append("## 扫描告警")
        lines.append("")
        for status in problems:
            if status["status"] == "challenge":
                lines.append(
                    "- {}：遇到人机验证。请在打开的 Chrome 窗口完成验证，"
                    "然后重新运行同一条命令；脚本不会自动刷新。".format(
                        status["name"]
                    )
                )
            else:
                lines.append("- {}：{}".format(status["name"], status["error"]))
        lines.append("")
    return "\n".join(lines)


def render_console(payload: dict) -> str:
    window = payload["window"]
    translation = payload.get("translation") or {}
    lines = [
        "期刊新文献清单 · 抓取于 {}".format(
            payload["generated_at"][:16].replace("T", " ")
        ),
        "扫描 {} 个期刊页面，{} 篇候选（尚未建立证据包）".format(
            payload["pages"], payload["total"]
        ),
    ]
    if translation.get("enabled"):
        lines.append("中文标题为机器翻译，仅供检索；以英文原题为依据")
        if translation.get("missing"):
            lines.append(
                "中文标题暂缺 {} 篇（翻译失败或限流），重跑可补齐".format(
                    translation["missing"]
                )
            )
    if window["days"]:
        lines.append("日期过滤：{} 之后（无日期条目保留）".format(window["from"]))
    if payload["truncated"]:
        lines.append(
            "共 {} 篇，按 limit={} 列出 {} 篇（各期刊轮转选取）".format(
                payload["total_found"], payload["limit"], payload["total"]
            )
        )
    lines.append("")

    for group in payload["groups"]:
        lines.append("== {}（{} 篇）==".format(group["name"], len(group["items"])))
        for item in group["items"]:
            meta = [item["journal"]]
            if item.get("kind"):
                meta.append(item["kind"])
            if item.get("date"):
                meta.append(item["date"])
            if item.get("doi"):
                meta.append("DOI: " + item["doi"])
            lines.append("[{}] {}".format(item["index"], item["title"]))
            if translation.get("enabled"):
                lines.append(
                    "    中文：" + (item.get("title_zh") or "暂缺")
                )
            lines.append("    " + " · ".join(meta))
            if not item.get("doi") and item.get("url"):
                lines.append("    " + item["url"])
        lines.append("")

    if not payload["groups"]:
        lines.append("没有解析到候选。请检查扫描告警。")
        lines.append("")

    problems = [status for status in payload["journals"] if status.get("error")]
    if problems:
        lines.append("扫描告警：")
        for status in problems:
            if status["status"] == "challenge":
                lines.append(
                    "  - {}: 需要人工完成人机验证，完成后重跑同一条命令".format(
                        status["name"]
                    )
                )
            else:
                lines.append("  - {}: {}".format(status["name"], status["error"]))
        lines.append("")

    lines.append("下一步：回复编号选择要精读的条目；脚本不会自动抽取。")
    return "\n".join(lines)


def write_scan(payload: dict) -> dict:
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    day = payload["window"]["to"]
    markdown_path = SCAN_DIR / "scan-{}.md".format(day)
    json_path = SCAN_DIR / "scan-{}.json".format(day)
    markdown = render_markdown(payload)
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    LATEST_MD.write_text(markdown, encoding="utf-8")
    LATEST_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "markdown": str(markdown_path),
        "json": str(json_path),
        "latest_markdown": str(LATEST_MD),
        "latest_json": str(LATEST_JSON),
        "markdown_text": markdown,
    }
