#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Journal new-literature watch: list candidates, never extract them.

The workflow this module supports is deliberately two-stage:

1. ``scan`` reads the configured journal list (``journals.json`` or the user
   copy in ``.geo-reader/journals.json``), asks Crossref for each journal's
   recent records, and writes a numbered candidate list.
2. The agent presents that list and waits. Evidence extraction starts only
   after the user names the numbers they want.

There is no topic search and no inference from existing notes. The only
inputs are the journal list, the date window and the enable flags the user
configured.
"""

import datetime
import html
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

from .config import GUIDE_DIR, PROJECT_ROOT, load_profile
from .version import __version__

DEFAULT_JOURNALS_PATH = PROJECT_ROOT / "journals.json"
USER_JOURNALS_PATH = GUIDE_DIR / "journals.json"
SCAN_DIR = GUIDE_DIR / "journal-scan"
LATEST_MD = SCAN_DIR / "latest.md"
LATEST_JSON = SCAN_DIR / "latest.json"

CROSSREF_JOURNAL_URL = "https://api.crossref.org/journals/{issn}/works"
SELECT_FIELDS = (
    "DOI,title,container-title,published,published-online,published-print,"
    "issued,created,author,abstract,type,URL"
)
USER_AGENT = (
    "geo-academic-reader/{version} "
    "(+https://github.com/Xjchen0/geo-academic-reader)"
).format(version=__version__)

# Records that are not research articles. They are dropped rather than shown,
# because a correction or an editorial is never a reading candidate.
NOISE_TITLE_RE = re.compile(
    r"^\s*(?:(?:author|publisher)\s+)?"
    r"(?:correction|corrigendum|erratum|editorial|editor'?s note|"
    r"publisher'?s note|retraction|expression of concern|in this issue|"
    r"issue information|front matter|back matter|cover image|"
    r"table of contents|preface|foreword|obituary|book review|"
    r"daily briefing|briefing chat|podcast|research highlights?|"
    r"news & views|editorial board)\b",
    re.IGNORECASE,
)
# Nature Portfolio uses 10.1038/d... for news, comment and careers content;
# research and reviews use 10.1038/s.... Dropping the d-series keeps the list
# to primary literature without guessing from the title.
NOISE_DOI_RE = re.compile(r"^10\.1038/d\d", re.IGNORECASE)
COMMENTARY_RE = re.compile(
    r"\b(?:comment on|reply to|response to|matters arising|correspondence|"
    r"commentary)\b",
    re.IGNORECASE,
)
# Magazine front matter such as "Mineralogical Society of America" or
# "Sociedad Española de Mineralogía" is deposited as a journal-article by
# some publishers. A title counts as an organisation only when it contains an
# organisation word and every other word is capitalised or a connector, so
# "Association between mantle temperature and volcanism" stays a paper.
ORG_TOKEN_RE = re.compile(
    r"\b(?:Society|Association|Union|Academy|Institute|Sociedad|Société|"
    r"Società|Gesellschaft|Associazione|Sociedade|Mineralogía|Mineralogie)\b"
)
ORG_CONNECTORS = {
    "of", "the", "and", "for", "de", "la", "del", "et", "des", "du", "der",
    "di", "e", "y", "van", "von", "&",
}

# Crossref rate limits are shared per IP. Space requests globally so a small
# thread pool does not turn into a burst of 429s.
_RATE_LOCK = threading.Lock()
_LAST_REQUEST = [0.0]
MIN_REQUEST_INTERVAL = 0.35


class JournalConfigError(Exception):
    """The journal list is missing or malformed."""


class ScanError(Exception):
    """The scan could not run at all (configuration or argument problem)."""


def config_path() -> Path:
    """User copy wins; the shipped list is the fallback."""
    return USER_JOURNALS_PATH if USER_JOURNALS_PATH.is_file() else DEFAULT_JOURNALS_PATH


def load_config(path: Optional[Path] = None) -> dict:
    """Load and validate the journal list.

    Raises ``JournalConfigError`` with an actionable message instead of
    silently scanning nothing.
    """
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

    keyword_sets = payload.get("keyword_sets") or {}
    if not isinstance(keyword_sets, dict):
        raise JournalConfigError("keyword_sets 必须是对象：{}".format(target))

    seen_keys = set()
    seen_issns = set()
    normalised = []
    for raw in journals:
        if not isinstance(raw, dict):
            raise JournalConfigError("journals 中的每一项必须是对象：{!r}".format(raw))
        key = str(raw.get("key") or "").strip()
        issn = str(raw.get("issn") or "").strip().upper()
        name = str(raw.get("name") or "").strip()
        if not key or not issn or not name:
            raise JournalConfigError(
                "期刊条目必须同时有 key、name、issn：{!r}".format(raw)
            )
        if not re.match(r"^\d{4}-?\d{3}[\dX]$", issn):
            raise JournalConfigError("ISSN 格式不正确：{}（{}）".format(issn, key))
        if not re.match(r"^[a-z0-9][a-z0-9._-]*$", key):
            raise JournalConfigError(
                "key 只能使用小写字母、数字、点、下划线和连字符：{}".format(key)
            )
        if key in seen_keys:
            raise JournalConfigError("期刊 key 重复：{}".format(key))
        if issn in seen_issns:
            raise JournalConfigError("期刊 ISSN 重复：{}（{}）".format(issn, key))
        seen_keys.add(key)
        seen_issns.add(issn)

        set_name = raw.get("keyword_set")
        keywords = list(raw.get("keywords") or [])
        if set_name:
            if set_name not in keyword_sets:
                raise JournalConfigError(
                    "期刊 {} 引用了不存在的 keyword_set：{}".format(key, set_name)
                )
            keywords.extend(keyword_sets[set_name] or [])
        keywords = [str(word).strip() for word in keywords if str(word).strip()]

        normalised.append(
            {
                "key": key,
                "name": name,
                "issn": issn,
                "publisher": str(raw.get("publisher") or ""),
                "enabled": bool(raw.get("enabled", True)),
                "keywords": keywords,
            }
        )

    defaults = payload.get("defaults") or {}
    if not isinstance(defaults, dict):
        defaults = {}
    return {
        "version": payload.get("version", 1),
        "path": str(target),
        "defaults": {
            "days": int(defaults.get("days", 7)),
            "limit": int(defaults.get("limit", 80)),
            "sort": str(defaults.get("sort", "date")),
        },
        "journals": normalised,
    }


def init_user_config(force: bool = False) -> dict:
    """Copy the shipped list to ``.geo-reader/journals.json`` for editing."""
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
        "message": "已生成个人期刊清单；修改 enabled / keywords / defaults 后重新扫描即可。",
    }


def _clean(text) -> str:
    if isinstance(text, list):
        text = text[0] if text else ""
    text = str(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _date_parts(item: dict, key: str) -> Optional[List[int]]:
    block = item.get(key)
    if not isinstance(block, dict):
        return None
    parts = block.get("date-parts")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
        return None
    values = [int(part) for part in parts[0][:3] if isinstance(part, int)]
    return values or None


def _date_str(parts: Optional[List[int]]) -> Optional[str]:
    if not parts:
        return None
    if len(parts) == 1:
        return "{:04d}".format(parts[0])
    if len(parts) == 2:
        return "{:04d}-{:02d}".format(parts[0], parts[1])
    return "{:04d}-{:02d}-{:02d}".format(parts[0], parts[1], parts[2])


def _sort_date(parts: Optional[List[int]]) -> Optional[str]:
    """Pad month/year precision so string comparison stays chronological."""
    if not parts:
        return None
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return "{:04d}-{:02d}-{:02d}".format(year, month, day)


def _best_date(item: dict, today: datetime.date) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(display, sortable)`` for the most useful recent date.

    Crossref's ``published``/``issued`` is the issue date for many Elsevier
    journals, which can lie months in the future (e.g. a January issue
    deposited in October). When that happens we fall back to the record
    creation date so the list reflects when the paper actually appeared.
    """
    today_str = today.isoformat()
    candidates = [
        _date_parts(item, "published-online"),
        _date_parts(item, "published"),
        _date_parts(item, "issued"),
        _date_parts(item, "published-print"),
    ]
    for parts in candidates:
        sortable = _sort_date(parts)
        if sortable and sortable <= today_str:
            return _date_str(parts), sortable
    created = str((item.get("created") or {}).get("date-time") or "")[:10]
    if re.match(r"^\d{4}-\d{2}-\d{2}$", created):
        return created, created
    for parts in candidates:
        if _sort_date(parts):
            return _date_str(parts), _sort_date(parts)
    return None, None


def _doi(item: dict) -> str:
    return str(item.get("DOI") or "").strip().lower()


def _title(item: dict) -> str:
    return _clean(item.get("title"))


def _abstract(item: dict) -> str:
    return _clean(item.get("abstract"))


def _first_author(item: dict) -> str:
    authors = item.get("author")
    if not isinstance(authors, list) or not authors:
        return ""
    first = authors[0] or {}
    family = _clean(first.get("family"))
    given = _clean(first.get("given"))
    if family and given:
        return "{} {}".format(given, family)
    return family or _clean(first.get("name"))


@lru_cache(maxsize=4096)
def _keyword_pattern(word: str) -> "re.Pattern":
    # A trailing ``*`` marks an explicit stem ("volcan*", "geochem*").
    # Everything else is a whole word, so "mars" no longer matches "marsh"
    # and "core" no longer matches "score".
    word = word.strip()
    if word.endswith("*"):
        return re.compile(r"\b" + re.escape(word[:-1]), re.IGNORECASE)
    return re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)


def _matches_keywords(item: dict, keywords: Sequence[str]) -> bool:
    """Match the configured keywords against the title only.

    Titles are the stable, comparable field. Matching abstracts pulled in
    unrelated biology and medicine papers from broad journals ("core" in
    "core genome", "score", and so on), which defeats the purpose of the
    journal list. Keywords are configured by the user, never derived from
    the conversation.
    """
    if not keywords:
        return True
    title = _title(item)
    return any(_keyword_pattern(word).search(title) for word in keywords)


def _looks_like_org(title: str) -> bool:
    if not ORG_TOKEN_RE.search(title):
        return False
    words = re.findall(r"[^\s]+", title)
    for word in words:
        clean = word.strip(".,;:()")
        if not clean:
            continue
        if clean.lower() in ORG_CONNECTORS:
            continue
        if clean[0].isupper():
            continue
        return False
    return True


def _is_noise(title: str) -> bool:
    return bool(NOISE_TITLE_RE.match(title) or _looks_like_org(title))


def _pace() -> None:
    with _RATE_LOCK:
        wait = MIN_REQUEST_INTERVAL - (time.monotonic() - _LAST_REQUEST[0])
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST[0] = time.monotonic()


def _kind(title: str) -> str:
    return "commentary" if COMMENTARY_RE.search(title) else "article"


def _normalise_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _headers() -> Dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "application/json"}


def _request(url: str, params: dict, timeout: float = 25.0) -> dict:
    last_error = None
    for attempt in range(2):
        _pace()
        try:
            response = requests.get(url, params=params, headers=_headers(), timeout=timeout)
            if response.status_code == 429 and attempt == 0:
                try:
                    delay = float(response.headers.get("Retry-After", "5"))
                except (TypeError, ValueError):
                    delay = 5.0
                last_error = "HTTP 429"
                time.sleep(max(3.0, min(delay, 15.0)))
                continue
            if response.status_code in (500, 502, 503, 504) and attempt == 0:
                last_error = "HTTP {}".format(response.status_code)
                time.sleep(2.0)
                continue
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # network/JSON errors are reported, not raised
            last_error = str(exc)
            if attempt == 0:
                time.sleep(1.0)
    raise ScanError(str(last_error or "unknown error"))


_SORT_FIELDS = {"from-pub-date": "published", "from-created-date": "created"}


def _fetch_query(
    entry: dict, since: str, until: str, date_filter: str, rows: int, mailto: str
) -> List[dict]:
    params = {
        "filter": "{0}:{1},{2}:{3},type:journal-article".format(
            date_filter, since, date_filter.replace("from-", "until-"), until
        ),
        "sort": _SORT_FIELDS[date_filter],
        "order": "desc",
        "rows": rows,
        "select": SELECT_FIELDS,
    }
    if mailto:
        params["mailto"] = mailto
    payload = _request(CROSSREF_JOURNAL_URL.format(issn=entry["issn"]), params)
    items = (payload.get("message") or {}).get("items") or []
    return [item for item in items if isinstance(item, dict)]


def fetch_journal(
    entry: dict,
    since: datetime.date,
    until: datetime.date,
    rows: int = 200,
    mailto: str = "",
) -> Tuple[List[dict], Optional[str]]:
    """Fetch one journal, unioning publication-date and creation-date queries.

    The union matters: Springer Nature deposits metadata before the online
    date, while Elsevier's issue dates can be months ahead. Either query alone
    silently misses a class of new papers.
    """
    since_str = since.isoformat()
    until_str = until.isoformat()
    collected: Dict[str, dict] = {}
    errors = []
    for date_filter in ("from-pub-date", "from-created-date"):
        try:
            items = _fetch_query(entry, since_str, until_str, date_filter, rows, mailto)
        except Exception as exc:
            errors.append("{}: {}".format(date_filter, exc))
            continue
        for item in items:
            doi = _doi(item)
            if doi and doi not in collected:
                collected[doi] = item
    if errors and not collected:
        return [], "; ".join(errors)
    return list(collected.values()), ("; ".join(errors) if errors else None)


def _build_candidate(item: dict, entry: dict, today: datetime.date) -> Optional[dict]:
    title = _title(item)
    doi = _doi(item)
    if not title or not doi or _is_noise(title) or NOISE_DOI_RE.match(doi):
        return None
    display, sortable = _best_date(item, today)
    abstract = _abstract(item)
    return {
        "journal_key": entry["key"],
        "journal": entry["name"],
        "publisher": entry["publisher"],
        "issn": entry["issn"],
        "title": title,
        "doi": doi,
        "url": "https://doi.org/{}".format(doi),
        "date": display,
        "sort_date": sortable,
        "first_author": _first_author(item),
        "abstract_snippet": (abstract[:400] + "…") if len(abstract) > 400 else abstract,
        "kind": _kind(title),
    }


def scan(
    days: Optional[int] = None,
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    journal_keys: Optional[Iterable[str]] = None,
    config_file: Optional[Path] = None,
    today: Optional[datetime.date] = None,
    fetcher: Optional[Callable] = None,
) -> dict:
    """Scan the configured journals and return candidates plus journal status.

    ``fetcher`` is injectable for tests; it has the same signature as
    ``fetch_journal``. This function never extracts evidence.
    """
    config = load_config(config_file)
    defaults = config["defaults"]
    days = int(defaults["days"] if days is None else days)
    limit = int(defaults["limit"] if limit is None else limit)
    sort = str(defaults["sort"] if sort is None else sort)
    if days < 1:
        raise ScanError("--days 必须大于 0")
    if limit < 0:
        raise ScanError("--limit 不能为负数")
    if sort not in ("journal", "date"):
        raise ScanError("--sort 只能是 journal 或 date")

    today = today or datetime.date.today()
    since = today - datetime.timedelta(days=days)
    wanted = {key.strip() for key in (journal_keys or []) if key and key.strip()}
    known = {entry["key"] for entry in config["journals"]}
    unknown = sorted(wanted - known)
    if unknown:
        raise ScanError(
            "期刊 key 不存在：{}。可用 key：{}".format(
                ", ".join(unknown), ", ".join(sorted(known))
            )
        )

    profile = load_profile()
    mailto = str(profile.get("citation_contact") or "").strip()
    fetch = fetcher or fetch_journal
    entries = config["journals"]

    statuses_by_order: Dict[int, dict] = {}
    active = []
    for order, entry in enumerate(entries):
        if not entry["enabled"]:
            statuses_by_order[order] = {
                "key": entry["key"], "name": entry["name"],
                "status": "disabled", "found": 0, "listed": 0,
            }
        elif wanted and entry["key"] not in wanted:
            statuses_by_order[order] = {
                "key": entry["key"], "name": entry["name"],
                "status": "skipped", "found": 0, "listed": 0,
            }
        else:
            active.append((order, entry))

    def work(pair):
        order, entry = pair
        try:
            items, error = fetch(entry, since, today, 200, mailto)
        except Exception as exc:
            items, error = [], str(exc)
        return order, entry, items, error

    # Crossref is an API, not a publisher page; a small pool is both polite
    # and much faster than 60 sequential requests. A custom fetcher (tests)
    # runs sequentially so its behaviour is deterministic.
    if fetcher or len(active) < 2:
        results = [work(pair) for pair in active]
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(work, active))

    candidates = []
    for order, entry, items, error in results:
        kept = []
        for item in items:
            if not _matches_keywords(item, entry["keywords"]):
                continue
            candidate = _build_candidate(item, entry, today)
            if candidate:
                candidate["journal_order"] = order
                kept.append(candidate)
        candidates.extend(kept)
        statuses_by_order[order] = {
            "key": entry["key"],
            "name": entry["name"],
            "status": "error" if error and not kept else "ok",
            "found": len(items),
            "listed": 0,
            "error": error,
        }

    statuses = [statuses_by_order[index] for index in range(len(entries))]

    # Dedupe across journals (shared DOIs/titles happen with co-published
    # announcements) before applying the global limit.
    unique: Dict[str, dict] = {}
    seen_titles = set()
    for candidate in candidates:
        doi = candidate["doi"]
        title_key = _normalise_title(candidate["title"])
        if doi in unique or (title_key and title_key in seen_titles):
            continue
        unique[doi] = candidate
        seen_titles.add(title_key)

    ordered = sorted(
        unique.values(),
        key=lambda item: (item["sort_date"] or "", -item["journal_order"]),
        reverse=True,
    )
    total_found = len(ordered)

    # A plain top-N cut would let Nature and Nature Communications consume the
    # whole budget and hide every specialist journal. Round-robin keeps the
    # list representative, then the cut items are shown in date order.
    if limit and total_found > limit:
        queues: Dict[str, List[dict]] = {}
        for item in ordered:
            queues.setdefault(item["journal_key"], []).append(item)
        config_order = [entry["key"] for entry in entries]
        selected = []
        while len(selected) < limit:
            added = False
            for key in config_order:
                queue = queues.get(key)
                if not queue:
                    continue
                selected.append(queue.pop(0))
                added = True
                if len(selected) >= limit:
                    break
            if not added:
                break
        ordered = selected
        ordered.sort(
            key=lambda item: (item["sort_date"] or "", -item["journal_order"]),
            reverse=True,
        )

    groups = []
    if sort == "journal":
        for entry in config["journals"]:
            items = [item for item in ordered if item["journal_key"] == entry["key"]]
            if not items:
                continue
            items.sort(key=lambda item: (item["sort_date"] or ""), reverse=True)
            groups.append({"key": entry["key"], "name": entry["name"], "items": items})
    elif ordered:
        groups = [{"key": "all", "name": "按上线日期排序", "items": ordered}]

    index = 0
    for group in groups:
        for item in group["items"]:
            index += 1
            item["index"] = index
            for status in statuses:
                if status["key"] == item["journal_key"]:
                    status["listed"] += 1
                    break

    # Keep the JSON candidate order identical to the rendered order.
    ordered = [item for group in groups for item in group["items"]]

    scanned = sum(1 for status in statuses if status["status"] in ("ok", "error"))
    return {
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "window": {"from": since.isoformat(), "to": today.isoformat(), "days": days},
        "config": config["path"],
        "sort": sort,
        "limit": limit,
        "scanned": scanned,
        "total_found": total_found,
        "total": len(ordered),
        "truncated": bool(limit and total_found > len(ordered)),
        "journals": statuses,
        "groups": groups,
        "candidates": ordered,
    }


def _item_line(item: dict) -> str:
    meta = [item["journal"]]
    if item.get("date"):
        meta.append(item["date"])
    if item.get("first_author"):
        meta.append(item["first_author"])
    if item.get("kind") == "commentary":
        meta.append("评论/回复")
    return " · ".join(meta)


def render_markdown(payload: dict) -> str:
    window = payload["window"]
    lines = [
        "# 期刊新文献清单 · {} → {}".format(window["from"], window["to"]),
        "",
        "> **候选清单，尚未精读**",
        ">",
        "> 共 {} 篇候选（扫描 {} 本期刊）。在用户明确选择编号之前，"
        "不得建立证据包、不得写笔记。".format(payload["total"], payload["scanned"]),
        "",
    ]
    if payload["truncated"]:
        lines.append(
            "> 说明：窗口内共 {} 篇，按 `--limit {}` 只列出 {} 篇。"
            "各期刊按清单顺序轮转选取，避免高产期刊挤掉专业期刊；"
            "需要更多请加大 `--limit`，或先用 `--journal` 只看某几本。".format(
                payload["total_found"], payload["limit"], payload["total"]
            )
        )
        lines.append("")

    if not payload["groups"]:
        lines.extend([
            "窗口内没有检索到条目。可以加大 `--days`，或检查 "
            "`.geo-reader/journals.json` 中的 `enabled` 与 ISSN。",
            "",
        ])

    for group in payload["groups"]:
        lines.append("## {}".format(group["name"]))
        lines.append("")
        for item in group["items"]:
            lines.append("**[{}] {}**".format(item["index"], item["title"]))
            lines.append("")
            lines.append(
                "{} · [{}]({})".format(_item_line(item), item["doi"], item["url"])
            )
            if item.get("abstract_snippet"):
                lines.append("")
                lines.append("> 摘要开头：{}".format(item["abstract_snippet"]))
            lines.append("")

    lines.extend([
        "---",
        "",
        "## 下一步",
        "",
        "回复要精读的编号（例如 `3, 7, 12`），或直接给出 DOI。"
        "**在你选择之前，这份清单不会触发任何抽取或写作。**",
        "",
        "选定后才会逐篇执行：",
        "",
        "```bash",
        'python3 main.py --doi "<选中的 DOI>"',
        "```",
        "",
        "扫描口径：Crossref 按 ISSN 拉取每本期刊在该窗口内“新上线”或“新登记”的 "
        "`journal-article`，合并去重，并去掉更正、勘误、社论、撤稿等非研究条目。"
        "Crossref 的收录时间可能晚于出版社页面，因此清单是候选而非完备列表。",
        "",
    ])

    problems = [status for status in payload["journals"] if status.get("error")]
    if problems:
        lines.append("## 扫描告警")
        lines.append("")
        for status in problems:
            lines.append("- {}：{}".format(status["name"], status["error"]))
        lines.append("")
    return "\n".join(lines)


def render_console(payload: dict) -> str:
    window = payload["window"]
    lines = [
        "期刊新文献清单 · {} → {}".format(window["from"], window["to"]),
        "扫描 {} 本期刊，{} 篇候选（尚未建立证据包）".format(
            payload["scanned"], payload["total"]
        ),
    ]
    if payload["truncated"]:
        lines.append(
            "窗口内共 {} 篇，按 limit={} 只列出 {} 篇（各期刊轮转选取）".format(
                payload["total_found"], payload["limit"], payload["total"]
            )
        )
    lines.append("")
    for group in payload["groups"]:
        lines.append("== {} ==".format(group["name"]))
        for item in group["items"]:
            lines.append("[{}] {}".format(item["index"], item["title"]))
            lines.append("    {}".format(_item_line(item)))
            lines.append("    DOI: {}".format(item["doi"]))
        lines.append("")
    if not payload["groups"]:
        lines.append("窗口内没有检索到条目。可加大 --days 或检查期刊清单。")
        lines.append("")
    problems = [status for status in payload["journals"] if status.get("error")]
    if problems:
        lines.append("扫描告警：")
        for status in problems:
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
