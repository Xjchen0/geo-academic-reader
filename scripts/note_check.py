#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Literature-note QA: image paths, placeholders, index maintenance."""

import json
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote

from .config import (
    ASSETS_DIR,
    INDEX_FILE,
    LEGACY_ASSETS_DIR,
    PAPERS_DIR,
    PROJECT_ROOT,
    RAW_DIR,
    extract_doi,
    relative_posix,
    today_iso,
)
from .console import ARROW, NOTE, OK
from .figures import image_magic

MD_IMAGE_RE = re.compile(
    r"!\[[^\]]*\]\(\s*(?:<([^>]+)>|([^)\s]+))(?:\s+[\"'][^\"']*[\"'])?\s*\)"
)
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)

PLACEHOLDER_MARKERS = (
    r"\mathcal{F}(x, t) = \sum_{k=1}^{N}",
    "本研究所关注的科学核心问题在于解析关键动力学机制",
    "作者团队综合运用了多源数据采集与高精度数值模拟",
    "上图清晰展示了关键变量随控制参数变化的响应特征",
    "研究中建立的本构关系可表述为如下参数方程",
    "（注：未检测到独立图件或当前文献为纯文本分析）",
)

FORBIDDEN_WORDS = ("颠覆一切", "彻底终结", "空前重大突破", "完美解决", "前所未有")

# The note is read by a colleague and by someone who just entered the
# subfield. Both need the takeaway in plain words, up front, as a labelled
# blockquote. This is the one mechanical part of the writing-style contract
# (rules/WRITING_STYLE.md) that a script can actually check.
LEAD_SUMMARY_LABELS = ("一句话结论", "综述范围与核心判断", "核心结论", "核心问题")
LEAD_SUMMARY_RE = re.compile(
    r"^[ \t]*>[ \t]*\*\*(?P<label>[^*]+)\*\*[ \t]*$",
    re.M,
)

# VS Code's built-in Markdown preview does not understand GitHub alert
# syntax; it prints "> [!NOTE]" as literal text. Catch it before delivery.
ALERT_RE = re.compile(
    r"^(?P<indent>[ \t]*)>[ \t]*\[!(?P<kind>NOTE|TIP|IMPORTANT|WARNING|CAUTION)\][ \t]*(?P<rest>.*)$",
    re.I | re.M,
)
ALERT_LABELS = {
    "note": "要点",
    "tip": "读图要点",
    "important": "关键前提",
    "warning": "注意事项",
    "caution": "注意事项",
}

# A classic-paper note must talk to a network of papers, not just summarise
# one PDF. Targets scale with the note depth declared in the front matter.
REFERENCE_TARGETS = {"brief": 3, "standard": 6, "deep": 10}
REVIEW_TARGET = 15
# A review that cites 15+ works must also show them. Without original figures a
# review degenerates into a text-only digest, so the review branch carries its
# own minimum number of embedded publisher figures.
REVIEW_FIGURE_TARGET = 3
# Non-review notes: a deep read is expected to walk its figures; a brief note
# may legitimately carry none.
NOTE_FIGURE_TARGETS = {"brief": 0, "standard": 1, "deep": 3}
REFERENCE_HEADING_RE = re.compile(r"^(#{1,3})[ \t]*.*?(?:参考文献|references?)[ \t]*$", re.I | re.M)
RELATED_HEADING_RE = re.compile(
    r"^(#{1,4})[ \t]*.*?(?:文献坐标|文献定位|文献脉络|研究脉络|引用脉络|学术史|时间线|timeline|related\s+works?|literature\s+context).*$",
    re.I | re.M,
)
BIB_ENTRY_RE = re.compile(r"^[ \t]*(?:\d+[.)]|[-*+])[ \t]+(?P<body>\S.*)$", re.M)
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\]\)<>\"',;]+", re.I)
AUTO_CITATION_MARKER = "自动构造"
TABLE_ROW_RE = re.compile(r"^[ \t]*\|.*\|[ \t]*$", re.M)
TABLE_SEPARATOR_RE = re.compile(r"^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$")

# A thematic review (note_type contains 主题) is a different artefact from a
# classic-paper note: it stands on one anchor paper, maps a citation network
# around it, weighs competing explanations, records later tests, marks the
# evidence level of every claim, and carries a human fact-check.
THEMATIC_TYPE_MARKERS = ("主题", "thematic")
EVIDENCE_TIER_RE = re.compile(r"[【\[]\s*(直证|转述|推断|评估|未核实)\s*[】\]]")
THEMATIC_ANCHOR_HEADING_RE = re.compile(
    r"^(#{1,4})[ \t]*.*?(?:锚定论文|锚点论文|anchor\s+paper|anchor\s+work).*$",
    re.I | re.M,
)
THEMATIC_RIVAL_RE = re.compile(
    r"(?:竞争解释|竞争假说|竞争性解释|competing\s+explanations?|rival\s+hypothes?)",
    re.I,
)
THEMATIC_LATER_RE = re.compile(
    r"(?:后续检验|后续检验与再评估|later\s+tests?|subsequent\s+tests?|follow[\s-]?up\s+tests?)",
    re.I,
)
THEMATIC_FACTCHECK_RE = re.compile(
    r"(?:人工事实复核|事实复核|人工核验|fact[\s-]?check)", re.I
)
THEMATIC_MIN_TIERS = 3


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _canonical_counterpart(resolved: Path) -> Optional[Path]:
    """Map a legacy <root>/assets/<slug>/<file> path into papers/assets/."""
    if not _is_within(resolved, LEGACY_ASSETS_DIR):
        return None
    try:
        relative = resolved.resolve().relative_to(LEGACY_ASSETS_DIR.resolve())
    except ValueError:
        return None
    return (ASSETS_DIR / relative).resolve()


def _legacy_counterpart(resolved: Path) -> Optional[Path]:
    if not _is_within(resolved, ASSETS_DIR):
        return None
    try:
        relative = resolved.resolve().relative_to(ASSETS_DIR.resolve())
    except ValueError:
        return None
    return (LEGACY_ASSETS_DIR / relative).resolve()


def _iter_image_refs(text: str):
    for match in MD_IMAGE_RE.finditer(text):
        ref = match.group(1) or match.group(2) or ""
        yield ref, match.start(), match.end(), "markdown"
    for match in HTML_IMAGE_RE.finditer(text):
        yield match.group(1), match.start(), match.end(), "html"


def parse_front_matter(text: str) -> Dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data = {}
    for line in text[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _section_body(text: str, heading: "re.Match") -> str:
    """Return the body of a heading, stopping at the next heading of the same or higher level."""
    level = len(heading.group(1))
    rest = text[heading.end():]
    stop = re.search(r"^#{1,%d}[ \t]" % level, rest, re.M)
    return rest[: stop.start()] if stop else rest


def _max_table_rows(text: str) -> int:
    """Largest number of data rows in any Markdown table in ``text``."""
    best = 0
    block: List[str] = []

    def flush() -> None:
        nonlocal best
        rows = [
            line
            for line in block
            if line.strip()
            and not TABLE_SEPARATOR_RE.match(line)
            and not re.match(r"^[ \t]*\|[ \t]*:?-{1,}:?", line)
        ]
        # The first row of a Markdown table is the header.
        best = max(best, max(0, len(rows) - 1))
        block.clear()

    for line in text.splitlines():
        if TABLE_ROW_RE.match(line):
            block.append(line)
        else:
            if block:
                flush()
    if block:
        flush()
    return best


def _normalise_doi(value: str) -> str:
    doi = value.strip().lower()
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", "", doi)
    return doi.rstrip(".,;:)]>").strip()


def analyse_citations(text: str, front: Dict[str, str]) -> Dict[str, object]:
    """Count external works cited by a note and check its citation network."""
    depth = (front.get("note_depth") or front.get("depth") or "standard").lower()
    if depth not in REFERENCE_TARGETS:
        depth = "standard"
    note_type = "{} {}".format(front.get("note_type", ""), front.get("type", "")).lower()
    target = REFERENCE_TARGETS[depth]
    is_review = "综述" in note_type or "review" in note_type
    if is_review:
        target = max(target, REVIEW_TARGET)
    is_thematic = any(marker in note_type for marker in THEMATIC_TYPE_MARKERS)

    reference_heading = REFERENCE_HEADING_RE.search(text)
    related_heading = RELATED_HEADING_RE.search(text)

    entries = 0
    dois = set()
    doi_list: List[str] = []
    without_doi = 0
    if reference_heading:
        body = _section_body(text, reference_heading)
        for match in BIB_ENTRY_RE.finditer(body):
            entry = match.group("body").strip()
            if not entry or entry.startswith("|"):
                continue
            entries += 1
            found = {_normalise_doi(value) for value in DOI_RE.findall(entry)}
            dois |= found
            doi_list.extend(sorted(found))
            if not found and AUTO_CITATION_MARKER not in entry:
                without_doi += 1

    anchor = _normalise_doi(front.get("doi", "")) if front.get("doi") else ""
    anchor_listed = bool(anchor and anchor in dois)
    external = max(0, entries - (1 if anchor_listed else 0))
    external_dois = len(dois - ({anchor} if anchor else set()))

    return {
        "depth": depth,
        "target": target,
        "is_review": is_review,
        "is_thematic": is_thematic,
        "figure_target": REVIEW_FIGURE_TARGET if is_review else NOTE_FIGURE_TARGETS.get(depth, 1),
        "entries": entries,
        "external": external,
        "external_dois": external_dois,
        "dois": sorted(dois),
        "without_doi": without_doi,
        "duplicate_dois": len({value for value in doi_list if doi_list.count(value) > 1}),
        "has_reference_section": reference_heading is not None,
        "has_related_section": related_heading is not None,
        "max_table_rows": _max_table_rows(text),
    }


def infer_note_metadata(note_path: Path) -> Dict[str, str]:
    text = note_path.read_text(encoding="utf-8", errors="replace")
    front = parse_front_matter(text)
    title = front.get("title") or ""
    if not title:
        match = re.search(r"^#\s+(.+)$", text, re.M)
        title = match.group(1).strip() if match else note_path.stem
    doi = front.get("doi") or extract_doi(text) or ""
    return {
        "title": title,
        "journal": front.get("journal", ""),
        "year": front.get("year", ""),
        "doi": doi,
        "source": front.get("source", ""),
        "status": front.get("status", "已精读"),
    }


def validate_note(note_path: Path, strict: bool = False) -> Dict[str, object]:
    note_path = Path(note_path).resolve()
    if not note_path.exists():
        return {
            "note": str(note_path),
            "issues": [{"severity": "error", "code": "missing_note", "line": 0, "message": "笔记文件不存在"}],
            "images": 0,
        }

    text = note_path.read_text(encoding="utf-8", errors="replace")
    issues: List[dict] = []
    images = 0
    # Figures that resolve to a real, readable file. A broken image link is
    # already an error; it must not count towards the "illustrated" quota.
    embedded_images = 0

    if not text.startswith("---"):
        issues.append(
            {
                "severity": "warning",
                "code": "missing_front_matter",
                "line": 1,
                "message": "缺少 YAML front matter（建议包含 title/doi/journal/year/source）。",
            }
        )

    for ref, start, _end, kind in _iter_image_refs(text):
        line = _line_of(text, start)
        if not ref or ref.startswith(("http://", "https://", "data:", "#", "mailto:")):
            continue
        images += 1
        clean_ref = unquote(ref.split("#", 1)[0])
        resolved = (note_path.parent / clean_ref).resolve()

        if not resolved.exists():
            # A legacy root-level assets/ file may still satisfy a note that
            # already uses the new "assets/<slug>/..." form.
            legacy = _legacy_counterpart(resolved)
            if legacy is not None and legacy.exists():
                target = _canonical_counterpart(legacy)
                issues.append(
                    {
                        "severity": "error",
                        "code": "legacy_assets_layout",
                        "line": line,
                        "message": (
                            "图片仍在旧版根目录 assets/，VS Code 只打开 papers/ 或单个笔记时"
                            "预览会裂图；运行 --check-note --fix 迁移到 papers/assets/: {}"
                        ).format(ref),
                        "ref": ref,
                        "migration_target": relative_posix(target, note_path.parent) if target else "",
                    }
                )
                continue
            issues.append(
                {
                    "severity": "error",
                    "code": "missing_image",
                    "line": line,
                    "message": "图片不存在: {}".format(ref),
                    "ref": ref,
                    "expected": relative_posix(resolved, note_path.parent),
                }
            )
            continue
        if not resolved.is_file():
            issues.append(
                {
                    "severity": "error",
                    "code": "not_a_file",
                    "line": line,
                    "message": "图片路径不是文件: {}".format(ref),
                    "ref": ref,
                }
            )
            continue
        if resolved.stat().st_size == 0:
            issues.append(
                {
                    "severity": "error",
                    "code": "empty_image",
                    "line": line,
                    "message": "图片文件为 0 字节: {}".format(ref),
                    "ref": ref,
                }
            )
            continue
        data = resolved.read_bytes()[:64]
        if not image_magic(data):
            issues.append(
                {
                    "severity": "warning",
                    "code": "invalid_image_magic",
                    "line": line,
                    "message": "无法识别图片格式（可能已损坏）: {}".format(ref),
                    "ref": ref,
                }
            )
        else:
            embedded_images += 1

        if _is_within(resolved, LEGACY_ASSETS_DIR):
            target = _canonical_counterpart(resolved)
            issues.append(
                {
                    "severity": "error",
                    "code": "legacy_assets_layout",
                    "line": line,
                    "message": (
                        "图片位于旧版根目录 assets/，在只打开 papers/ 或单个笔记时无法预览；"
                        "运行 --check-note --fix 迁移: {}"
                    ).format(ref),
                    "ref": ref,
                    "migration_target": relative_posix(target, note_path.parent) if target else "",
                }
            )
            continue

        if not _is_within(resolved, ASSETS_DIR):
            issues.append(
                {
                    "severity": "warning",
                    "code": "outside_assets",
                    "line": line,
                    "message": "图片不在 papers/assets/ 下，换机器或移动工作区后容易失效: {}".format(ref),
                    "ref": ref,
                }
            )

        expected = relative_posix(resolved, note_path.parent)
        if os.path.normpath(clean_ref) != os.path.normpath(expected):
            issues.append(
                {
                    "severity": "error",
                    "code": "wrong_relative_path",
                    "line": line,
                    "message": "相对路径不规范：{}（建议 {}）".format(ref, expected),
                    "ref": ref,
                    "expected": expected,
                }
            )

    lowered = text.lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker.lower() in lowered:
            issues.append(
                {
                    "severity": "error",
                    "code": "placeholder_content",
                    "line": _line_of(text, lowered.index(marker.lower())),
                    "message": "检测到管线模板占位内容，必须删除或改写: {}".format(marker[:40]),
                }
            )

    for word in FORBIDDEN_WORDS:
        if word in text:
            issues.append(
                {
                    "severity": "warning",
                    "code": "hyperbole",
                    "line": _line_of(text, text.index(word)),
                    "message": "检测到夸大措辞：{}".format(word),
                }
            )

    for match in ALERT_RE.finditer(text):
        kind = match.group("kind").upper()
        issues.append(
            {
                "severity": "error",
                "code": "github_alert_syntax",
                "line": _line_of(text, match.start()),
                "message": (
                    "GitHub alert 语法 > [!{}] 在 VS Code 内置预览中会原样显示为文字；"
                    "改用 > **{}** 加引用块的写法（--fix 可自动改写，标签措辞需人工核对）"
                ).format(kind, ALERT_LABELS.get(kind.lower(), "要点")),
            }
        )

    # Opening takeaway: a labelled blockquote the reader can quote on its own.
    lead_labels = [
        match.group("label").strip()
        for match in LEAD_SUMMARY_RE.finditer(text)
        if match.group("label").strip() in LEAD_SUMMARY_LABELS
    ]
    if not lead_labels:
        issues.append(
            {
                "severity": "warning",
                "code": "missing_lead_summary",
                "line": 0,
                "message": (
                    "缺少带标签的开篇结论块（{}）：读者应当能在第一屏读到一句话结论，"
                    "而不是自己从正文里概括。"
                ).format("、".join(LEAD_SUMMARY_LABELS[:2])),
            }
        )

    citations = analyse_citations(text, parse_front_matter(text))
    front = parse_front_matter(text)
    if not citations["has_related_section"]:
        issues.append(
            {
                "severity": "error",
                "code": "missing_related_context",
                "line": 0,
                "message": (
                    "缺少“文献坐标/文献脉络”章节：经典文献精读必须交代本文与哪些工作对话，"
                    "不能只总结单篇论文。"
                ),
            }
        )
    if not citations["has_reference_section"]:
        issues.append(
            {
                "severity": "error",
                "code": "missing_reference_section",
                "line": 0,
                "message": "缺少“参考文献 / References”章节；每条外部文献应给出可核验 DOI。",
            }
        )
    elif citations["external"] == 0:
        issues.append(
            {
                "severity": "error",
                "code": "no_external_references",
                "line": 0,
                "message": (
                    "参考文献只有本文自身或为空：经典文献精读至少应引用 {} 篇外部文献。"
                ).format(citations["target"]),
            }
        )
    elif citations["external"] < citations["target"]:
        issues.append(
            {
                "severity": "warning",
                "code": "thin_reference_context",
                "line": 0,
                "message": (
                    "外部文献 {} 篇，低于 {} 深度建议的 {} 篇；补充前史、竞争假说与后续检验。"
                ).format(citations["external"], citations["depth"], citations["target"]),
            }
        )
    if citations["max_table_rows"] < 5:
        issues.append(
            {
                "severity": "error" if citations["is_thematic"] else "warning",
                "code": "missing_citation_table",
                "line": 0,
                "message": (
                    "未找到至少 5 行的引用脉络表；用“年份 | 工作 | 核心贡献 | 与本文关系”表格"
                    "把前史、竞争解释与后续检验排开。"
                ),
            }
        )
    if citations["without_doi"]:
        issues.append(
            {
                "severity": "warning",
                "code": "references_without_doi",
                "line": 0,
                "message": (
                    "{} 条参考文献没有 DOI；请补 DOI，无法核验的条目标注“自动构造，需核对”。"
                ).format(citations["without_doi"]),
            }
        )
    if citations["duplicate_dois"]:
        issues.append(
            {
                "severity": "warning",
                "code": "duplicate_reference_doi",
                "line": 0,
                "message": "参考文献中有 {} 个重复 DOI，请合并同一条目。".format(
                    citations["duplicate_dois"]
                ),
            }
        )

    # 图文并茂: a review that cites 15+ works but shows no figure is a digest,
    # not a review. Reviews must embed original publisher figures.
    figure_target = citations["figure_target"]
    if figure_target and embedded_images < figure_target:
        if citations["is_review"]:
            issues.append(
                {
                    "severity": "error",
                    "code": "review_without_figures",
                    "line": 0,
                    "message": (
                        "综述只嵌入了 {} 张图，少于要求的 {} 张：综述必须图文并茂。"
                        "先用 --doi 为关键文献建立证据包，再从 papers/assets/<slug>/ "
                        "嵌入原文图件并配“读图要点”。"
                    ).format(embedded_images, figure_target),
                }
            )
        else:
            issues.append(
                {
                    "severity": "warning",
                    "code": "note_without_figures",
                    "line": 0,
                    "message": (
                        "正文没有可用的原文图件（{} / {} 张）：{} 深度的笔记应当逐图阅读。"
                    ).format(embedded_images, figure_target, citations["depth"]),
                }
            )

    # 主题综述: an anchor paper, a citation network, competing explanations,
    # later tests, marked evidence levels and a human fact-check. These rules
    # only fire for note_type containing 主题, so classic-paper notes and the
    # existing library keep their current behaviour.
    if citations["is_thematic"]:
        anchor_front = _normalise_doi(front.get("anchor_doi", ""))
        anchor_heading = THEMATIC_ANCHOR_HEADING_RE.search(text)
        if not anchor_front and not anchor_heading:
            issues.append(
                {
                    "severity": "error",
                    "code": "missing_anchor_paper",
                    "line": 0,
                    "message": (
                        "主题综述必须指明锚定论文：front matter 写 anchor_doi，"
                        "并设置“## 锚定论文”章节。"
                    ),
                }
            )
        if anchor_front and anchor_front not in citations["dois"]:
            issues.append(
                {
                    "severity": "error",
                    "code": "anchor_not_in_references",
                    "line": 0,
                    "message": (
                        "锚定论文 {} 没有出现在参考文献表中；锚定论文也必须是一条可核验的引用。"
                    ).format(anchor_front),
                }
            )
        if not THEMATIC_RIVAL_RE.search(text):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing_competing_explanations",
                    "line": 0,
                    "message": (
                        "缺少“竞争解释”段落：至少写出两个竞争假说，"
                        "并说明每个假说依赖的判据，以及锚定论文能否排除它。"
                    ),
                }
            )
        if not THEMATIC_LATER_RE.search(text):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing_later_tests",
                    "line": 0,
                    "message": (
                        "缺少“后续检验”段落：说明锚定论文的结论后来被哪些工作检验过。"
                        "如果确实没有检索，请写“检索未覆盖”，不要暗示不存在。"
                    ),
                }
            )
        if not THEMATIC_FACTCHECK_RE.search(text):
            issues.append(
                {
                    "severity": "error",
                    "code": "missing_factcheck_section",
                    "line": 0,
                    "message": (
                        "缺少“人工事实复核”章节：记录哪些条目已回到原文核对、"
                        "哪些仍未核验（.raw/reviews/<slug>/factcheck.md 是工作底稿）。"
                    ),
                }
            )
        tiers = sorted(set(EVIDENCE_TIER_RE.findall(text)))
        if not tiers:
            issues.append(
                {
                    "severity": "error",
                    "code": "missing_evidence_tiers",
                    "line": 0,
                    "message": (
                        "没有标注证据层级：关键论断后必须标 【直证】/【转述】/【推断】/"
                        "【评估】/【未核实】 之一。"
                    ),
                }
            )
        elif len(tiers) < THEMATIC_MIN_TIERS:
            issues.append(
                {
                    "severity": "warning",
                    "code": "thin_evidence_tiers",
                    "line": 0,
                    "message": (
                        "只用到 {} 种证据层级（{}）；主题综述通常需要直证、转述、"
                        "推断/评估至少三层，才能显示结论的支撑结构。"
                    ).format(len(tiers), "、".join(tiers)),
                }
            )

    # Display math should be balanced.
    if text.count("$$") % 2 != 0:
        issues.append(
            {
                "severity": "warning",
                "code": "unbalanced_display_math",
                "line": 0,
                "message": "检测到奇数个 $$，块级公式可能未闭合。",
            }
        )

    if strict:
        for issue in issues:
            if issue["severity"] == "warning":
                issue["severity"] = "error"

    return {
        "note": str(note_path),
        "title": infer_note_metadata(note_path).get("title", ""),
        "images": images,
        "embedded_images": embedded_images,
        "issues": issues,
        "errors": sum(1 for issue in issues if issue["severity"] == "error"),
        "warnings": sum(1 for issue in issues if issue["severity"] == "warning"),
        "citations": citations,
    }


def _replace_image_ref(text: str, old: str, new: str) -> str:
    """Replace only the link destination, never a substring of another path."""
    if not old or old == new:
        return text
    count = 0
    for pattern in ("]({})".format(old), "](<{}>)".format(old)):
        if pattern in text:
            count += text.count(pattern)
            text = text.replace(pattern, "]({})".format(new) if not pattern.startswith("](<") else "](<{}>)".format(new))
    for quote in ('"', "'"):
        pattern = "src={q}{old}{q}".format(q=quote, old=old)
        if pattern in text:
            count += text.count(pattern)
            text = text.replace(pattern, "src={q}{new}{q}".format(q=quote, new=new))
    return text


def _fix_alerts(text: str) -> Tuple[str, int]:
    """Rewrite GitHub alert markers as labelled blockquotes VS Code can render."""

    def replace(match: "re.Match") -> str:
        label = ALERT_LABELS.get(match.group("kind").lower(), "要点")
        rest = match.group("rest").strip()
        # Keep a quoted blank line after the label, otherwise the bold label
        # and the following paragraph collapse onto one rendered line.
        lines = ["> **{}**".format(label), ">"]
        if rest:
            lines.append("> " + rest)
        return "\n".join(lines)

    return ALERT_RE.subn(replace, text)


def _copy_asset(source: Path, target: Path) -> bool:
    """Copy an image without overwriting a different, already-migrated file."""
    if not source.is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return True
    try:
        import shutil

        shutil.copy2(str(source), str(target))
        return True
    except OSError:
        return False


def _sync_evidence_paths(slug: str) -> None:
    """Keep .raw/<slug>/ figures/manifest.json in sync after a migration."""
    if not slug:
        return
    manifest_path = RAW_DIR / slug / "figures" / "manifest.json"
    assets_dir = ASSETS_DIR / slug
    if not manifest_path.exists() or not assets_dir.exists():
        return
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return
    changed = False
    for figure in payload.get("figures") or []:
        name = figure.get("file") or Path(
            figure.get("markdown_path") or figure.get("local_path") or ""
        ).name
        target = assets_dir / name if name else None
        if not name or not target or not target.is_file():
            continue
        updates = {
            "file": name,
            "markdown_path": "assets/{}/{}".format(slug, name),
            "local_path": relative_posix(target, PROJECT_ROOT),
        }
        for key, value in updates.items():
            if figure.get(key) != value:
                figure[key] = value
                changed = True
        if "source_url" not in figure and figure.get("url"):
            figure["source_url"] = figure["url"]
            changed = True
        if "is_body_figure" not in figure:
            figure["is_body_figure"] = figure.get("body_figure", figure.get("in_figure"))
            changed = True
    payload["assets_dir"] = relative_posix(assets_dir, PROJECT_ROOT)
    if changed:
        manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    paper_path = RAW_DIR / slug / "paper.json"
    if paper_path.exists():
        try:
            paper = json.loads(paper_path.read_text(encoding="utf-8"))
        except Exception:
            return
        files = paper.setdefault("files", {})
        value = relative_posix(assets_dir, PROJECT_ROOT)
        if files.get("assets_dir") != value:
            files["assets_dir"] = value
            paper_path.write_text(
                json.dumps(paper, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )


def fix_note(note_path: Path, dry_run: bool = False) -> Dict[str, object]:
    note_path = Path(note_path).resolve()
    report = validate_note(note_path)
    text = note_path.read_text(encoding="utf-8", errors="replace")
    changed = False
    fixed = []
    migrated = []
    touched_slugs = set()
    referenced_slugs = set()

    for ref, _start, _end, _kind in _iter_image_refs(text):
        clean = os.path.normpath(unquote(ref.split("#", 1)[0]))
        parts = Path(clean).parts
        if len(parts) >= 2 and parts[0] == "assets":
            referenced_slugs.add(parts[1])

    for issue in report["issues"]:
        code = issue["code"]
        if code not in ("missing_image", "wrong_relative_path", "legacy_assets_layout"):
            continue
        ref = issue.get("ref", "")
        expected = issue.get("expected", "")
        replacement = None

        if code == "legacy_assets_layout":
            source = (note_path.parent / ref).resolve()
            if not source.exists():
                # The note already uses "assets/<slug>/..." but the file is
                # still in the legacy root-level assets/ directory.
                source = _legacy_counterpart(source) or source
            relative = None
            if _is_within(source, LEGACY_ASSETS_DIR) and source.exists():
                relative = source.relative_to(LEGACY_ASSETS_DIR.resolve())
            if relative is not None:
                target = ASSETS_DIR / relative
                if _copy_asset(source, target):
                    touched_slugs.add(relative.parts[0] if relative.parts else "")
                    replacement = relative_posix(target, note_path.parent)
                    migrated.append({"from": ref, "to": replacement, "file": str(target)})

        elif code == "wrong_relative_path" and expected:
            candidate = (note_path.parent / expected).resolve()
            if candidate.exists():
                replacement = expected

        elif code == "missing_image":
            basename = Path(ref).name
            matches = [path for path in ASSETS_DIR.rglob(basename) if path.is_file()]
            if len(matches) == 1:
                replacement = relative_posix(matches[0], note_path.parent)
            else:
                legacy_matches = [
                    path for path in LEGACY_ASSETS_DIR.rglob(basename) if path.is_file()
                ] if LEGACY_ASSETS_DIR.exists() else []
                if len(legacy_matches) == 1:
                    source = legacy_matches[0]
                    relative = source.relative_to(LEGACY_ASSETS_DIR.resolve())
                    target = ASSETS_DIR / relative
                    if _copy_asset(source, target):
                        touched_slugs.add(relative.parts[0] if relative.parts else "")
                        replacement = relative_posix(target, note_path.parent)
                        migrated.append({"from": ref, "to": replacement, "file": str(target)})

        if replacement and replacement != ref:
            text = _replace_image_ref(text, ref, replacement)
            changed = True
            fixed.append({"from": ref, "to": replacement, "line": issue["line"]})

    text, fixed_alerts = _fix_alerts(text)
    if fixed_alerts:
        changed = True

    if changed and not dry_run:
        note_path.write_text(text, encoding="utf-8")

    if not dry_run:
        # Keep the canonical folder complete for every slug touched by this
        # note, including figures the note did not reference yet.
        for slug in sorted(filter(None, touched_slugs | referenced_slugs)):
            legacy_dir = LEGACY_ASSETS_DIR / slug
            if legacy_dir.is_dir():
                for source in legacy_dir.rglob("*"):
                    if not source.is_file():
                        continue
                    relative = source.relative_to(legacy_dir)
                    _copy_asset(source, ASSETS_DIR / slug / relative)
            _sync_evidence_paths(slug)

    return {
        "note": str(note_path),
        "changed": changed,
        "fixed": fixed,
        "fixed_alerts": fixed_alerts,
        "migrated": migrated,
        "dry_run": dry_run,
        "report": validate_note(note_path) if (changed or migrated) and not dry_run else report,
    }


def print_report(report: dict) -> None:
    note = report.get("note", "")
    print("\n{} {}".format(NOTE, note))
    print("   图片: {} | 错误: {} | 警告: {}".format(
        report.get("images", 0), report.get("errors", 0), report.get("warnings", 0)
    ))
    citations = report.get("citations") or {}
    if citations:
        print("   文献: {} 篇外部文献（目标 ≥{}，深度 {}）| 引用表 {} 行 | DOI {} 个".format(
            citations.get("external", 0),
            citations.get("target", 0),
            citations.get("depth", "standard"),
            citations.get("max_table_rows", 0),
            citations.get("external_dois", 0),
        ))
    if citations.get("is_thematic"):
        print("   路线: 主题综述（锚定论文 + 引用网络 + 竞争解释 + 后续检验 + 证据层级）")
    issues = report.get("issues", [])
    if not issues:
        print("   {} 未发现问题".format(OK))
        return
    for issue in issues:
        location = "L{}".format(issue["line"]) if issue.get("line") else "—"
        print("   [{}] {} {}: {}".format(
            issue["severity"].upper(), location, issue["code"], issue["message"]
        ))


def scan_notes() -> List[Path]:
    if not PAPERS_DIR.exists():
        return []
    return sorted(
        path for path in PAPERS_DIR.glob("*.md") if path.name.lower() != "index.md"
    )


def check_notes(paths: Optional[Iterable[Path]] = None, fix: bool = False, strict: bool = False) -> List[dict]:
    targets = [Path(path) for path in paths] if paths else scan_notes()
    reports = []
    for target in targets:
        if fix:
            result = fix_note(target)
            report = result["report"]
            print_report(report)
            if result["fixed"]:
                print("   {} 已修复 {} 处路径".format(ARROW, len(result["fixed"])))
            if result.get("fixed_alerts"):
                print("   {} 已改写 {} 处 GitHub alert 标记，请核对标签措辞".format(
                    ARROW, result["fixed_alerts"]
                ))
            if result.get("migrated"):
                print("   {} 已迁移 {} 张图片到 papers/assets/".format(ARROW, len(result["migrated"])))
        else:
            report = validate_note(target, strict=strict)
            print_report(report)
        reports.append(report)
    if not targets:
        print("未找到需要检查的笔记（papers/*.md）。")
    return reports


def ensure_index_header() -> str:
    header = (
        "# 📚 Academic Literature Library Index (学术文献精读知识库索引)\n\n"
        "> Maintained by `python3 main.py --index papers/<note>.md`.\n\n"
        "| 归档日期 | 论文标题 | 期刊 | 年份 | DOI / 来源 | 精读笔记 | 状态 |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    )
    if not INDEX_FILE.exists():
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text(header, encoding="utf-8")
        return header

    content = INDEX_FILE.read_text(encoding="utf-8")
    if "| 状态 |" in content:
        return content

    lines = content.splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.startswith("| 归档日期") or line.startswith("| Date"):
            lines[index] = "| 归档日期 | 论文标题 | 期刊 | 年份 | DOI / 来源 | 精读笔记 | 状态 |"
            if index + 1 < len(lines) and lines[index + 1].startswith("| :"):
                lines[index + 1] = "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
            replaced = True
            break
    if not replaced:
        lines.extend(header.splitlines())
    new_content = "\n".join(lines).rstrip() + "\n"
    INDEX_FILE.write_text(new_content, encoding="utf-8")
    return new_content


def _escape_cell(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).replace("|", "-").strip()


def index_note(note_path: Path) -> dict:
    note_path = Path(note_path).resolve()
    if not note_path.exists():
        raise FileNotFoundError(str(note_path))
    ensure_index_header()
    metadata = infer_note_metadata(note_path)
    title = _escape_cell(metadata["title"])
    journal = _escape_cell(metadata["journal"]) or "—"
    year = _escape_cell(metadata["year"]) or "—"
    status = _escape_cell(metadata["status"]) or "已精读"

    doi = metadata.get("doi", "")
    source = metadata.get("source", "")
    if doi:
        source_cell = "[{}](https://doi.org/{})".format(doi, doi)
    elif source:
        source_cell = "[Web Link]({})".format(source)
    else:
        source_cell = "—"

    try:
        note_link = relative_posix(note_path, PAPERS_DIR)
    except Exception:
        note_link = note_path.name
    row = "| {} | {} | {} | {} | {} | [阅读笔记]({}) | {} |".format(
        today_iso(), title, journal, year, source_cell, note_link, status
    )

    content = INDEX_FILE.read_text(encoding="utf-8")
    lines = content.splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if "]({})".format(note_link) in line or "]({})".format(note_path.name) in line:
            lines[index] = row
            replaced = True
            break
    if not replaced:
        lines.append(row)
    INDEX_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"note": str(note_path), "row": row, "updated": replaced}


def list_workspace() -> dict:
    packs = []
    if RAW_DIR.exists():
        for paper_json in sorted(RAW_DIR.glob("*/paper.json")):
            try:
                payload = json.loads(paper_json.read_text(encoding="utf-8"))
                packs.append(
                    {
                        "slug": payload.get("slug", paper_json.parent.name),
                        "title": payload.get("title", ""),
                        "method": payload.get("method", ""),
                        "figures": (payload.get("stats") or {}).get("figures", 0),
                        "pack": str(paper_json.parent),
                    }
                )
            except Exception:
                continue
    notes = []
    for note in scan_notes():
        metadata = infer_note_metadata(note)
        notes.append(
            {
                "note": str(note),
                "title": metadata["title"],
                "doi": metadata["doi"],
                "status": metadata["status"],
            }
        )
    return {"packs": packs, "notes": notes}
