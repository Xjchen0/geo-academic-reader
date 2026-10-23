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
        "issues": issues,
        "errors": sum(1 for issue in issues if issue["severity"] == "error"),
        "warnings": sum(1 for issue in issues if issue["severity"] == "warning"),
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
        "migrated": migrated,
        "dry_run": dry_run,
        "report": validate_note(note_path) if (changed or migrated) and not dry_run else report,
    }


def print_report(report: dict) -> None:
    note = report.get("note", "")
    print("\n📝 {}".format(note))
    print("   图片: {} | 错误: {} | 警告: {}".format(
        report.get("images", 0), report.get("errors", 0), report.get("warnings", 0)
    ))
    issues = report.get("issues", [])
    if not issues:
        print("   ✓ 未发现问题")
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
                print("   → 已修复 {} 处路径".format(len(result["fixed"])))
            if result.get("migrated"):
                print("   → 已迁移 {} 张图片到 papers/assets/".format(len(result["migrated"])))
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
