#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thematic literature review: topic search, Crossref verification, fact-check sheet.

Scope
-----
This module serves the *thematic review* route only. It is a different
contract from ``--new-literature``:

* ``--new-literature`` opens the user's configured journal pages and lists what
  those pages list. It never guesses a topic.
* ``--thematic-review`` starts from a topic (or from a list of DOIs the user
  already has) and verifies every entry against Crossref.

The module never writes review prose. It produces a verified working set and a
human fact-check sheet under ``.raw/reviews/<slug>/``; the agent writes the
note from those files.
"""

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, urlencode

import requests

from .config import (
    CROSSREF_API_URL,
    DEFAULT_HEADERS,
    OPENALEX_API_URL,
    RAW_DIR,
    now_iso,
    slugify,
)
from .fetch_paper import clean_jats, fetch_crossref_metadata

REVIEW_ROOT = RAW_DIR / "reviews"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"

# Evidence tiers. They map onto AGENTS.md 1.4: direct evidence, author
# inference, and the reader's own assessment. Every claim in a thematic note
# carries one of them, so the note never mixes levels of certainty silently.
EVIDENCE_TIERS = ("direct", "reported", "inferred", "assessment", "unverified")
EVIDENCE_TIER_LABELS = {
    "direct": "【直证】",
    "reported": "【转述】",
    "inferred": "【推断】",
    "assessment": "【评估】",
    "unverified": "【未核实】",
}
EVIDENCE_TIER_HELP = {
    "direct": "原文或证据包中可直接查证的陈述，附页码 / 图号 / 原文段落锚点。",
    "reported": "来自二手来源（他人综述、数据库摘要）的转述，尚未回到原文核对。",
    "inferred": "作者在文中提出的推断，或由证据包数据推出、但作者未直接写出的结论。",
    "assessment": "笔记者（Agent 或人）的综合判断，不是原文结论。",
    "unverified": "尚未核验的信息；写作时必须显式标注为待核，不得当作事实陈述。",
}

# Roles inside the citation network.
ROLES = ("anchor", "predecessor", "later_test", "topic_candidate", "user_supplied")
ROLE_LABELS = {
    "anchor": "锚定论文",
    "predecessor": "前史文献",
    "later_test": "后续检验",
    "topic_candidate": "主题候选",
    "user_supplied": "用户指定",
}
ROLE_PRIORITY = {role: index for index, role in enumerate(ROLES)}

DEFAULT_WORK_TYPES = ("journal-article",)
DEFAULT_MAX_REFS = 25
# A predecessor list can be hundreds of entries; verifying all of them would
# hammer Crossref and still not answer "which of these matter".
MAX_PREDECESSOR_CANDIDATES = 60
MAX_FORWARD_CANDIDATES = 40


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _headers(mailto: str = "") -> Dict[str, str]:
    headers = dict(DEFAULT_HEADERS)
    headers["Accept"] = "application/json"
    if mailto:
        headers["From"] = mailto
    return headers


def _request_json(url: str, params: Optional[dict] = None, mailto: str = "") -> dict:
    """GET a JSON endpoint. Returns {"error": ...} instead of raising."""
    query = dict(params or {})
    if mailto and "mailto" not in query:
        query["mailto"] = mailto
    try:
        response = requests.get(
            url, params=query, headers=_headers(mailto), timeout=25
        )
        if response.status_code >= 400:
            return {"error": "HTTP {}".format(response.status_code)}
        return response.json()
    except Exception as exc:
        return {"error": str(exc)}


def normalise_doi(value: str) -> str:
    doi = str(value or "").strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.rstrip(".,;:)]>\"'").strip()


def _entry_year(issued) -> str:
    parts = (issued or {}).get("date-parts") or []
    if parts and parts[0] and parts[0][0]:
        return str(parts[0][0])
    return ""


def _entry_authors(authors) -> List[str]:
    names = []
    for author in authors or []:
        name = " ".join(
            part for part in (author.get("given", ""), author.get("family", "")) if part
        ).strip()
        if not name:
            name = (author.get("name") or "").strip()
        if name:
            names.append(name)
    return names


# ---------------------------------------------------------------------------
# Stage 1 - topic candidates (Crossref relevance search)
# ---------------------------------------------------------------------------

def search_crossref_topic(
    topic: str,
    rows: int = 20,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    mailto: str = "",
    types: Iterable[str] = DEFAULT_WORK_TYPES,
) -> dict:
    """Search Crossref by topic. This is a *topic* search, not a journal scan.

    The page-driven ``--new-literature`` route lists what a journal currently
    publishes. This function ranks works by how well they match the query
    text; the two must never be mixed in one list.
    """
    topic = (topic or "").strip()
    if not topic:
        return {"topic": topic, "error": "主题为空", "items": [], "total": 0}

    params = {
        "query.bibliographic": topic,
        "rows": max(1, min(int(rows), 100)),
        "sort": "relevance",
        "select": (
            "DOI,title,author,issued,container-title,type,"
            "is-referenced-by-count,abstract,URL"
        ),
    }
    filters = []
    work_types = [value for value in (types or []) if value]
    if work_types:
        filters.append("type:{}".format(",".join(work_types)))
    if from_year:
        filters.append("from-pub-date:{}-01-01".format(int(from_year)))
    if to_year:
        filters.append("until-pub-date:{}-12-31".format(int(to_year)))
    if filters:
        params["filter"] = ",".join(filters)

    payload = _request_json(CROSSREF_API_URL, params=params, mailto=mailto)
    if payload.get("error"):
        return {"topic": topic, "error": payload["error"], "items": [], "total": 0}

    message = payload.get("message") or {}
    items = []
    for entry in message.get("items") or []:
        doi = normalise_doi(entry.get("DOI", ""))
        if not doi:
            continue
        items.append(
            {
                "doi": doi,
                "title": clean_jats((entry.get("title") or [""])[0]),
                "authors": _entry_authors(entry.get("author")),
                "journal": clean_jats((entry.get("container-title") or [""])[0]),
                "year": _entry_year(entry.get("issued")),
                "type": entry.get("type", ""),
                "cited_by": entry.get("is-referenced-by-count", 0),
                "abstract": clean_jats(entry.get("abstract", "")),
                "url": entry.get("URL", ""),
                "relevance_rank": len(items) + 1,
            }
        )
    return {
        "topic": topic,
        "total": message.get("total-results", 0),
        "items": items,
        "query": urlunparse_query(params),
    }


def urlunparse_query(params: dict) -> str:
    """Render a query dict for the report (without leaking a mailto address)."""
    safe = {key: value for key, value in (params or {}).items() if key != "mailto"}
    return urlencode(safe)


# ---------------------------------------------------------------------------
# Stage 2 - the citation network around an anchor paper
# ---------------------------------------------------------------------------

def fetch_reference_dois(doi: str, mailto: str = "") -> List[dict]:
    """DOIs the anchor paper cites, taken from the Crossref reference list.

    Crossref only exposes reference lists for works whose publisher deposits
    them, so an empty list means "not deposited", not "no predecessors".
    """
    doi = normalise_doi(doi)
    if not doi:
        return []
    payload = _request_json(
        CROSSREF_API_URL + quote(doi, safe=""), mailto=mailto
    )
    if payload.get("error"):
        return []
    message = payload.get("message") or {}
    entries: List[dict] = []
    seen = set()
    for reference in message.get("reference") or []:
        ref_doi = normalise_doi(reference.get("DOI", ""))
        if not ref_doi or ref_doi in seen:
            continue
        seen.add(ref_doi)
        entries.append(
            {
                "doi": ref_doi,
                "year": str(reference.get("year", "") or ""),
                "unstructured": (reference.get("unstructured") or "").strip(),
                "author": (reference.get("author") or "").strip(),
                "journal": (reference.get("journal-title") or "").strip(),
            }
        )
    return entries[:MAX_PREDECESSOR_CANDIDATES]


def fetch_forward_citations(doi: str, limit: int = 20, mailto: str = "") -> List[dict]:
    """DOIs of works that cite the anchor paper (OpenAlex), for later tests.

    OpenAlex is used only to *find* forward citations; every candidate is
    still verified against Crossref before it enters the working set.
    """
    doi = normalise_doi(doi)
    if not doi:
        return []
    work = _request_json(OPENALEX_API_URL + quote(doi, safe="/"), mailto=mailto)
    if work.get("error"):
        return []
    work_id = work.get("id") or ""
    if not work_id:
        return []
    wid = work_id.rsplit("/", 1)[-1]
    payload = _request_json(
        OPENALEX_WORKS_URL,
        params={
            "filter": "cites:{}".format(wid),
            "per-page": max(1, min(int(limit), MAX_FORWARD_CANDIDATES)),
        },
        mailto=mailto,
    )
    if payload.get("error"):
        return []
    entries: List[dict] = []
    for item in payload.get("results") or []:
        candidate = normalise_doi(item.get("doi", ""))
        if not candidate:
            continue
        source = ((item.get("primary_location") or {}).get("source") or {}) or {}
        entries.append(
            {
                "doi": candidate,
                "title": (item.get("title") or "").strip(),
                "year": str(item.get("publication_year") or ""),
                "journal": (source.get("display_name") or "").strip(),
                "cited_by": item.get("cited_by_count", 0),
            }
        )
    return entries


# ---------------------------------------------------------------------------
# Stage 2b - per-item verification against Crossref
# ---------------------------------------------------------------------------

def verify_doi(doi: str, mailto: str = "") -> dict:
    """Verify one DOI against Crossref: title, authors, year, journal, abstract."""
    doi = normalise_doi(doi)
    if not doi:
        return {"doi": "", "verified": False, "error": "DOI 为空"}
    metadata = fetch_crossref_metadata(doi)
    error = metadata.get("error", "")
    abstract = metadata.get("abstract", "") or ""
    verified = not error
    return {
        "doi": doi,
        "verified": verified,
        "error": error,
        "title": metadata.get("title", "") or "",
        "authors": list(metadata.get("authors") or []),
        "journal": metadata.get("journal", "") or "",
        "year": metadata.get("year", "") or "",
        "abstract": abstract,
        "abstract_available": bool(abstract),
        "type": metadata.get("type", "") or "",
        "publisher": metadata.get("publisher", "") or "",
        "url": metadata.get("url", "") or "",
        "license": metadata.get("license", "") or "",
        "source": "crossref",
        "roles": [],
        "default_tier": (
            "unverified" if not verified else ("direct" if abstract else "reported")
        ),
    }


# ---------------------------------------------------------------------------
# Stage 3 - the working set
# ---------------------------------------------------------------------------

def parse_doi_list(value: str) -> List[str]:
    """Accept a comma/space separated list, or the path of a text file."""
    text = str(value or "").strip()
    if not text:
        return []
    candidate = Path(text)
    if candidate.is_file():
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = value
    found = []
    for token in re.split(r"[\s,;]+", text):
        doi = normalise_doi(token)
        if doi.startswith("10.") and doi not in found:
            found.append(doi)
    return found


def _sort_key(entry: dict) -> Tuple:
    roles = entry.get("roles") or []
    role = min((ROLE_PRIORITY.get(item, 99) for item in roles), default=99)
    try:
        year = int(entry.get("year") or 0)
    except (TypeError, ValueError):
        year = 0
    return (role, -year, entry.get("doi", ""))


def build_working_set(
    topic: str = "",
    refs: Optional[Iterable[str]] = None,
    anchor: str = "",
    max_refs: int = DEFAULT_MAX_REFS,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    mailto: str = "",
    include_forward: bool = True,
    logger=None,
) -> dict:
    """Build a verified working set for one thematic review.

    Returns a payload with:
      * ``references`` - verified entries (Crossref metadata + abstract)
      * ``candidates`` - discovered but not yet verified entries
      * ``query`` - how the candidates were found, for the report
    """
    emit = logger or (lambda *_a, **_k: None)

    entries: Dict[str, dict] = {}
    order: List[str] = []

    def _register(doi: str, role: str, seed: dict = None) -> str:
        doi = normalise_doi(doi)
        if not doi:
            return ""
        if doi not in entries:
            entries[doi] = {
                "doi": doi,
                "verified": False,
                "error": "",
                "title": "",
                "authors": [],
                "journal": "",
                "year": "",
                "abstract": "",
                "abstract_available": False,
                "type": "",
                "publisher": "",
                "url": "",
                "license": "",
                "source": "",
                "roles": [],
                "default_tier": "unverified",
            }
            order.append(doi)
        entry = entries[doi]
        if role and role not in entry["roles"]:
            entry["roles"].append(role)
        if seed:
            for key in ("year", "journal", "title"):
                if not entry.get(key) and seed.get(key):
                    entry[key] = seed[key]
        return doi

    anchor_doi = normalise_doi(anchor)
    for doi in parse_doi_list(",".join(refs or [])):
        _register(doi, "user_supplied")

    topic_result = {"topic": topic, "items": [], "total": 0, "error": ""}
    if topic:
        emit("  主题检索（Crossref relevance）: {}".format(topic))
        topic_result = search_crossref_topic(
            topic,
            rows=max(1, min(int(max_refs), 50)),
            from_year=from_year,
            to_year=to_year,
            mailto=mailto,
        )
        if topic_result.get("error"):
            emit("  [WARN] 主题检索失败: {}".format(topic_result["error"]))
        for item in topic_result.get("items", []):
            _register(item["doi"], "topic_candidate", item)

    if anchor_doi:
        _register(anchor_doi, "anchor")

    predecessors: List[dict] = []
    forward: List[dict] = []
    if anchor_doi:
        emit("  读取锚定论文的引用列表（Crossref reference）...")
        predecessors = fetch_reference_dois(anchor_doi, mailto=mailto)
        emit("  读取引用锚定论文的后续文献（OpenAlex forward citations）...")
        if include_forward:
            forward = fetch_forward_citations(anchor_doi, mailto=mailto)
        for item in predecessors:
            _register(item["doi"], "predecessor", item)
        for item in forward:
            _register(item["doi"], "later_test", item)

    # Verify in priority order: anchor, user-supplied, topic candidates,
    # predecessors, later tests. Everything past the budget stays unverified.
    priority = {"anchor": 0, "user_supplied": 1, "topic_candidate": 2,
                "predecessor": 3, "later_test": 4}

    def _rank(doi: str) -> int:
        roles = entries[doi].get("roles") or []
        return min((priority.get(role, 9) for role in roles), default=9)

    ordered = sorted(order, key=lambda doi: (_rank(doi), order.index(doi)))
    budget = max(1, int(max_refs))
    verified_count = 0
    for index, doi in enumerate(ordered, 1):
        if verified_count >= budget:
            break
        emit("  核验 {}/{}: {}".format(index, min(len(ordered), budget), doi))
        verified = verify_doi(doi, mailto=mailto)
        entry = entries[doi]
        for key, value in verified.items():
            if key == "roles":
                continue
            entry[key] = value
        entry["roles"] = sorted(
            entry.get("roles") or [], key=lambda role: ROLE_PRIORITY.get(role, 99)
        )
        verified_count += 1

    references = [
        entry for entry in sorted(entries.values(), key=_sort_key)
        if entry.get("verified")
    ]
    candidates = [
        entry for entry in sorted(entries.values(), key=_sort_key)
        if not entry.get("verified")
    ]

    return {
        "generated_at": now_iso(),
        "topic": topic,
        "anchor_doi": anchor_doi,
        "max_refs": budget,
        "from_year": from_year,
        "to_year": to_year,
        "query": {
            "route": "thematic-review",
            "topic_query": topic_result.get("query", ""),
            "topic_total": topic_result.get("total", 0),
            "topic_error": topic_result.get("error", ""),
            "predecessors_found": len(predecessors),
            "forward_citations_found": len(forward),
            "include_forward": bool(include_forward),
        },
        "evidence_tiers": {
            tier: {"label": EVIDENCE_TIER_LABELS[tier], "help": EVIDENCE_TIER_HELP[tier]}
            for tier in EVIDENCE_TIERS
        },
        "references": references,
        "candidates": candidates,
    }


# ---------------------------------------------------------------------------
# Stage 4 - reports the human still has to work through
# ---------------------------------------------------------------------------

def _short(text: str, limit: int = 480) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _authors_line(authors: List[str]) -> str:
    if not authors:
        return "（Crossref 未提供作者）"
    if len(authors) <= 3:
        return "; ".join(authors)
    return "{} 等 {} 人".format("; ".join(authors[:3]), len(authors))


def render_candidates_md(payload: dict) -> str:
    topic = payload.get("topic") or "（未命名主题）"
    anchor = payload.get("anchor_doi") or ""
    references = payload.get("references") or []
    candidates = payload.get("candidates") or []
    query = payload.get("query") or {}

    lines = [
        "# 主题综述候选清单：{}".format(topic),
        "",
        "> 口径说明：本清单来自**主题检索**（Crossref relevance）与用户指定的 DOI，",
        "> 与 `--new-literature` 的**期刊页面扫描**不是同一件事，不可混用同一份清单。",
        "> 元数据由 Crossref 逐条核验；`核验=否` 的条目不得直接写进笔记。",
        "",
        "- 生成时间：{}".format(payload.get("generated_at", "")),
        "- 主题检索式：`{}`".format(query.get("topic_query", "") or "（未使用）"),
        "- 主题检索命中：{} 条（Crossref total-results）".format(query.get("topic_total", 0)),
        "- 锚定论文：{}".format(anchor or "（未指定）"),
        "- 已核验条目：{} | 待核验候选：{}".format(len(references), len(candidates)),
        "",
        "## 1. 已核验条目（Crossref）",
        "",
        "| # | 角色 | 年份 | 标题 | 期刊 | DOI | 摘要 | 默认层级 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    index = 0
    for entry in references:
        index += 1
        roles = "/".join(
            ROLE_LABELS.get(role, role) for role in entry.get("roles") or []
        )
        lines.append(
            "| {} | {} | {} | {} | {} | [{}](https://doi.org/{}) | {} | {} |".format(
                index,
                roles,
                entry.get("year") or "—",
                _short(entry.get("title", ""), 90) or "（Crossref 未提供标题）",
                _short(entry.get("journal", ""), 40) or "—",
                entry.get("doi", ""),
                entry.get("doi", ""),
                "有" if entry.get("abstract_available") else "无",
                EVIDENCE_TIER_LABELS.get(entry.get("default_tier", ""), ""),
            )
        )
    if not references:
        lines.append("| — | — | — | 无已核验条目 | — | — | — | — |")

    lines += [
        "",
        "## 2. 待核验候选（仅作线索）",
        "",
        "| # | 角色 | 年份 | 线索标题 | 期刊 | DOI |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    offset = index
    for entry in candidates:
        offset += 1
        roles = "/".join(
            ROLE_LABELS.get(role, role) for role in entry.get("roles") or []
        )
        lines.append(
            "| {} | {} | {} | {} | {} | [{}](https://doi.org/{}) |".format(
                offset,
                roles,
                entry.get("year") or "—",
                _short(entry.get("title", ""), 80) or "（引用列表未给标题）",
                _short(entry.get("journal", ""), 40) or "—",
                entry.get("doi", ""),
                entry.get("doi", ""),
            )
        )
    if not candidates:
        lines.append("| — | — | — | 无待核验候选 | — | — |")

    lines += ["", "## 3. 已核验条目摘要（写作用原文依据）", ""]
    for number, entry in enumerate(references, 1):
        lines.append("### {}. {}".format(number, entry.get("title") or entry.get("doi")))
        lines.append("")
        lines.append("- DOI：{}".format(entry.get("doi", "")))
        lines.append("- 作者：{}".format(_authors_line(entry.get("authors") or [])))
        lines.append("- 期刊：{} | 年份：{} | 类型：{}".format(
            entry.get("journal") or "—",
            entry.get("year") or "—",
            entry.get("type") or "—",
        ))
        abstract = entry.get("abstract") or ""
        if abstract:
            lines.append("- 摘要（Crossref 原文）：{}".format(_short(abstract, 900)))
        else:
            lines.append("- 摘要：Crossref 未提供摘要；需要回到出版商页面或 PDF 取。")
        lines.append("")

    lines += [
        "---",
        "",
        "*本清单由 `python3 main.py --thematic-review` 生成；脚本不写综述正文。*",
        "*人工复核清单见同目录 `factcheck.md`。*",
        "",
    ]
    return "\n".join(lines)


def render_factcheck_md(payload: dict) -> str:
    topic = payload.get("topic") or "（未命名主题）"
    references = payload.get("references") or []
    candidates = payload.get("candidates") or []

    lines = [
        "# 人工事实复核清单：{}".format(topic),
        "",
        "> 自动核验只覆盖 Crossref 元数据（标题 / 作者 / 年份 / 期刊 / 摘要）。",
        "> 本清单里的每一条都需要人回到原文或出版商页面确认；未复核的论断在笔记中必须标注【未核实】。",
        "",
        "- 生成时间：{}".format(payload.get("generated_at", "")),
        "- 待复核条目：{} | 待核验候选：{}".format(len(references), len(candidates)),
        "",
        "## 1. 逐条元数据复核（Crossref → 出版商页面）",
        "",
        "| # | DOI | 需核对 | 复核人 | 结论 | 备注 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for number, entry in enumerate(references, 1):
        checks = "标题、作者、年份、期刊"
        if not entry.get("abstract_available"):
            checks += "、摘要（Crossref 缺）"
        lines.append(
            "| {} | {} | {} |  |  |  |".format(
                number, entry.get("doi", ""), checks
            )
        )
    if not references:
        lines.append("| — | — | — |  |  |  |")

    lines += [
        "",
        "## 2. 论断级复核（笔记每条关键论断一行）",
        "",
        "| # | 论断（原文摘录） | 证据锚点 | 来源类型 | 层级 | 已复核 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
        "| 1 |  |  |  |  |  |",
        "",
        "> 来源类型：原文正文 / 原文图件 / 摘要 / 二手综述 / 作者推断 / 笔者判断。",
        "> 层级：" + " / ".join(
            "{} {}".format(EVIDENCE_TIER_LABELS[tier], tier) for tier in EVIDENCE_TIERS
        ),
        "",
        "## 3. 机器无法覆盖的检查项",
        "",
        "- [ ] 图表数值与原文逐一比对（坐标轴、单位、误差棒、对照组）",
        "- [ ] 样本量、地点、时间窗、关键参数与原文一致",
        "- [ ] 竞争解释确实被原文正面讨论，而不是本文替它编的",
        "- [ ] 后续检验确实检验了锚定论文的结论，而不是无关的引用",
        "- [ ] 每张嵌入的图件来自 `manifest.json` 的原文图注，未自行改写",
        "",
        "## 4. 复核结论",
        "",
        "- 复核人：",
        "- 完成日期：",
        "- 未解决项：",
        "",
    ]
    return "\n".join(lines)


def review_slug(payload: dict) -> str:
    topic = payload.get("topic") or ""
    anchor = payload.get("anchor_doi") or ""
    if topic:
        return slugify(topic)[:60] or "thematic-review"
    if anchor:
        return slugify(anchor.replace("/", "_"))[:60]
    return "thematic-review"


def write_working_set(payload: dict, out_dir: Optional[Path] = None) -> Dict[str, str]:
    """Write candidates.md, references.json and factcheck.md."""
    directory = Path(out_dir) if out_dir else (REVIEW_ROOT / review_slug(payload))
    directory.mkdir(parents=True, exist_ok=True)

    candidates_path = directory / "candidates.md"
    references_path = directory / "references.json"
    factcheck_path = directory / "factcheck.md"

    candidates_path.write_text(render_candidates_md(payload), encoding="utf-8")
    factcheck_path.write_text(render_factcheck_md(payload), encoding="utf-8")
    references_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "directory": str(directory),
        "candidates": str(candidates_path),
        "references": str(references_path),
        "factcheck": str(factcheck_path),
    }


def render_console(payload: dict) -> str:
    references = payload.get("references") or []
    candidates = payload.get("candidates") or []
    query = payload.get("query") or {}
    lines = [
        "",
        "=" * 64,
        "主题综述工作集已生成：{}".format(payload.get("topic") or "（未命名主题）"),
        "=" * 64,
        "  路由      : 主题综述（Crossref 核验），不是期刊页面扫描",
        "  主题检索式: {}".format(query.get("topic_query", "") or "（未使用）"),
        "  锚定论文  : {}".format(payload.get("anchor_doi") or "（未指定）"),
        "  已核验    : {} 条".format(len(references)),
        "  待核验    : {} 条".format(len(candidates)),
        "",
    ]
    for number, entry in enumerate(references, 1):
        roles = "/".join(
            ROLE_LABELS.get(role, role) for role in entry.get("roles") or []
        )
        lines.append("  [{}] {} ({})".format(number, entry.get("doi", ""), roles))
        lines.append("      {}".format(_short(entry.get("title", ""), 90)))
        lines.append(
            "      {} | {} | 摘要 {}".format(
                entry.get("journal") or "—",
                entry.get("year") or "—",
                "有" if entry.get("abstract_available") else "无",
            )
        )
    if candidates:
        lines.append("")
        lines.append("  待核验候选（仅线索）：")
        for entry in candidates[:15]:
            lines.append(
                "    - {} {} {}".format(
                    entry.get("doi", ""),
                    entry.get("year") or "—",
                    _short(entry.get("title", ""), 70),
                )
            )
    lines.append("")
    lines.append("下一步（由 Agent 完成，脚本不写综述正文）：")
    lines.append("  1. 读候选清单与摘要，选出锚定论文与引用网络")
    lines.append("  2. 读 factcheck.md，逐条人工复核后再落笔")
    lines.append("  3. 按 templates/thematic_review.md 写 papers/<slug>.md")
    lines.append("     关键论断标 【直证】/【转述】/【推断】/【评估】/【未核实】")
    lines.append("  4. python3 main.py --check-note papers/<slug>.md --fix")
    lines.append("  5. python3 main.py --index papers/<slug>.md")
    lines.append("=" * 64)
    lines.append("")
    return "\n".join(lines)
