#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified CLI for the geo-academic-reader workspace."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .config import (
    INPUT_PDFS_DIR,
    PROFILE_PATH,
    PROJECT_ROOT,
    is_tty,
    load_profile,
    profile_exists,
)
from .console import FAIL, configure_stdio
from .evidence import extract_evidence
from .journal_watch import (
    JournalConfigError,
    ScanError,
    init_user_config,
    render_console,
    scan as scan_journals,
    write_scan,
)
from .note_check import check_notes, index_note, list_workspace
from .onboarding import print_guide, print_profile, profile_summary
from .preflight import (
    GATE_SKIP_ENV,
    build_preflight,
    format_report,
    gate_status,
    write_marker,
)
from .thematic_review import (
    DEFAULT_MAX_REFS,
    build_working_set,
    parse_doi_list,
    render_console as render_review_console,
    write_working_set,
)
from .updater import check_for_update, format_check, format_update, update_workspace
from .version import __version__

BANNER = r"""
===================================================================
  geo-academic-reader v{version}
  Browser-first evidence packs -> agent-written VS Code notes
===================================================================
""".format(version=__version__)

MENU = r"""
  [1] 精读 DOI
  [2] 精读网页 URL
  [3] 精读本地 PDF（自动找 DOI，优先浏览器高清图）
  [4] 批量解析 input_pdfs/ 下的 PDF
  [5] 查看当前偏好（修改请在对话中说“重新设置偏好”）
  [6] 检查笔记图片与格式（可 --fix）
  [7] 把笔记登记到 papers/INDEX.md
  [8] 查看证据包与笔记列表
  [9] 查看快速上手与提示词
  [10] 环境自检 (doctor)
  [11] 检查更新 / 更新到最新版本
  [12] 抓取期刊网站新文献（只列候选，不自动精读）
  [13] 创建个人期刊清单 .geo-reader/journals.json
  [14] 会话前置检查（契约 / 环境 / 偏好，文献命令的前置条件）
  [15] 主题综述工作集（Crossref 逐条核验 + 人工复核清单）
  [0] 退出
"""


def _profile_summary(profile: dict) -> str:
    return profile_summary(profile)


def _run_doctor() -> int:
    return subprocess.call([sys.executable, str(PROJECT_ROOT / "doctor.py")])


def _run_preflight(args) -> int:
    """Record that the contract, environment and profile were checked."""
    report = build_preflight()
    marker = write_marker(report)
    if args.json:
        payload = dict(report)
        payload["marker"] = str(marker)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
        print("Marker    : {}".format(marker))
    return 0 if report.get("ok") else 1


def _is_literature_action(args) -> bool:
    return bool(
        args.doi
        or args.url
        or args.pdf
        or args.batch_pdfs
        or args.new_literature
        or args.thematic_review is not None
        or args.check_note is not None
        or args.index
    )


def _preflight_bypassed(args) -> bool:
    return bool(getattr(args, "no_preflight", False) or os.environ.get(GATE_SKIP_ENV))


def _gate_message(reason: str) -> str:
    return (
        "\n{} 会话前置检查未通过：{}\n"
        "   Agent 必须先读 AGENTS.md、MEMORY.md、LESSONS.md，再运行：\n"
        "     python3 main.py --preflight\n"
        "   仅当用户明确要求跳过时才用 --no-preflight（或 GEO_READER_SKIP_PREFLIGHT=1）。\n"
    ).format(FAIL, reason)


def _guard_literature(args) -> Optional[int]:
    """Return 2 when a literature command is attempted without a fresh preflight."""
    if not _is_literature_action(args) or _preflight_bypassed(args):
        return None
    status = gate_status()
    if status.get("allowed"):
        return None
    print(_gate_message(str(status.get("message", ""))))
    return 2


def _menu_gate() -> bool:
    if os.environ.get(GATE_SKIP_ENV):
        return True
    status = gate_status()
    if status.get("allowed"):
        return True
    print(_gate_message(str(status.get("message", ""))))
    print("   在菜单里先选 [14] 会话前置检查。\n")
    return False



def _print_extraction_summary(result: dict) -> None:
    print("\n" + "=" * 64)
    print("证据包已生成：{}".format(result["title"]))
    print("=" * 64)
    print("  Slug    : {}".format(result["slug"]))
    print("  DOI     : {}".format(result["doi"] or "—"))
    print("  文本    : {}".format(result["fulltext"]))
    print("  元数据  : {}".format(result["paper_json"]))
    print("  图件清单: {}".format(result["manifest"]))
    print("  图片目录: {}".format(result["assets_dir"]))
    print("  图件数量: {}".format(result["figures"]))
    print("  抽取方式: {}".format(result["method"]))
    if result.get("warnings"):
        print("  警告    :")
        for warning in result["warnings"]:
            print("    - {}".format(warning))
    print("\n下一步（由 Agent 完成，脚本不写综述）：")
    print("  1. 读取 {} 与 {}".format(result["paper_json"], result["fulltext"]))
    print("  2. 按 templates/paper_note.md 写 {}".format(result["next_note"]))
    print("     图片统一使用 assets/{}/fig_XX.png".format(result["slug"]))
    print("  3. python3 main.py --check-note {} --fix".format(result["next_note"]))
    print("  4. python3 main.py --index {}".format(result["next_note"]))
    print("=" * 64 + "\n")


def _run_extraction(source_type: str, value: str, args) -> int:
    profile = load_profile()
    browser = args.browser or profile.get("browser", "auto")
    try:
        result = extract_evidence(
            source_type,
            value,
            browser_mode=browser,
            wait_seconds=args.wait,
            max_figures=args.max_figures,
            quiet=args.json or args.quiet,
        )
    except Exception as exc:
        print("{} 抽取失败: {}".format(FAIL, exc))
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_extraction_summary(result)
    return 0


def _run_batch(args) -> int:
    pdfs = sorted(INPUT_PDFS_DIR.glob("*.pdf"))
    if not pdfs:
        print("input_pdfs/ 下没有 PDF。请先放入论文 PDF。")
        return 1
    failures = 0
    for index, pdf in enumerate(pdfs, 1):
        print("\n[{}/{}] {}".format(index, len(pdfs), pdf.name))
        if _run_extraction("pdf", str(pdf), args) != 0:
            failures += 1
    print("\n批量完成：{} 成功，{} 失败。".format(len(pdfs) - failures, failures))
    return 0 if failures == 0 else 1


def _run_journal_scan(args, days=None, limit=None, sort=None) -> int:
    """Open the configured journal pages; list candidates, never extract."""
    quiet = getattr(args, "json", False) or getattr(args, "quiet", False)
    try:
        payload = scan_journals(
            days=days if days is not None else getattr(args, "days", None),
            limit=limit if limit is not None else getattr(args, "limit", None),
            sort=sort if sort is not None else getattr(args, "sort", None),
            journal_keys=getattr(args, "journal", None),
            logger=None if quiet else (lambda line: print(line, flush=True)),
            translate=not getattr(args, "no_translate", False),
        )
        paths = write_scan(payload)
    except (JournalConfigError, ScanError) as exc:
        print("{} 期刊扫描失败: {}".format(FAIL, exc))
        return 1
    except Exception as exc:
        print("{} 期刊扫描失败: {}".format(FAIL, exc))
        return 1

    if args.json:
        result = dict(payload)
        result["files"] = {key: value for key, value in paths.items() if key != "markdown_text"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(render_console(payload))
    print("\n清单已写入：")
    print("  {}".format(paths["latest_markdown"]))
    print("  {}".format(paths["markdown"]))
    print("  {}".format(paths["json"]))
    if payload["total"] == 0:
        print("\n提示：没有解析到候选。检查上面的扫描告警；"
              "如果 Chrome 停在人机验证页，完成验证后重跑同一条命令。")
    return 0


def _run_journals_init(args) -> int:
    try:
        result = init_user_config(force=getattr(args, "force", False))
    except JournalConfigError as exc:
        print("{} {}".format(FAIL, exc))
        return 1
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["message"])
        print("路径：{}".format(result["path"]))
    return 0


def _run_thematic_review(args) -> int:
    """Topic route: verify a working set against Crossref, then hand back a
    fact-check sheet. The script never writes review prose."""
    profile = load_profile()
    mailto = str(profile.get("citation_contact") or "").strip()
    topic = str(getattr(args, "thematic_review", "") or "").strip()
    refs = str(getattr(args, "refs", "") or "").strip()
    anchor = str(getattr(args, "anchor_doi", "") or "").strip()

    if not topic and not refs and not anchor:
        print("用法：--thematic-review \"主题\" [--refs \"doi1,doi2\"] "
              "[--anchor-doi 10.xxxx/yyyy]")
        print("说明：主题综述走 Crossref 核验路线；--new-literature 走期刊页面扫描路线，两者不同。")
        return 1

    quiet = getattr(args, "json", False) or getattr(args, "quiet", False)
    logger = None if quiet else (lambda line: print(line, flush=True))
    try:
        payload = build_working_set(
            topic=topic,
            refs=parse_doi_list(refs),
            anchor=anchor,
            max_refs=getattr(args, "max_refs", DEFAULT_MAX_REFS),
            from_year=getattr(args, "from_year", None),
            to_year=getattr(args, "to_year", None),
            mailto=mailto,
            include_forward=not getattr(args, "no_forward", False),
            logger=logger,
        )
        paths = write_working_set(payload)
    except Exception as exc:
        print("{} 主题综述工作集生成失败: {}".format(FAIL, exc))
        return 1

    if getattr(args, "json", False):
        result = dict(payload)
        result["files"] = paths
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(render_review_console(payload))
    print("工作集已写入：")
    print("  {}".format(paths["candidates"]))
    print("  {}".format(paths["references"]))
    print("  {}".format(paths["factcheck"]))
    return 0


def _print_lists(payload: dict) -> None:
    print("\nEvidence packs (.raw/):")
    if not payload["packs"]:
        print("  (empty)")
    for pack in payload["packs"]:
        print("  - {} | {} | {} | figures={} | {}".format(
            pack["slug"], pack["title"], pack["method"], pack["figures"], pack["pack"]
        ))
    print("\nNotes (papers/):")
    if not payload["notes"]:
        print("  (empty)")
    for note in payload["notes"]:
        print("  - {} | {} | {}".format(note["status"], note["title"], note["note"]))


def _run_update_check(args) -> int:
    payload = check_for_update(
        include_prerelease=args.prerelease, refresh=args.refresh, timeout=8.0
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_check(payload))
    # A failed network check is not a task failure.
    return 0


def _run_update(args) -> int:
    payload = update_workspace(
        include_prerelease=args.prerelease,
        force=args.force,
        dry_run=args.dry_run,
        log=(lambda *_a, **_k: None) if (args.json or args.quiet) else print,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_update(payload))
    return 0 if not payload.get("error") else 1


def _notify_update_if_available(args) -> None:
    """One-line hint after a completed task; never blocks long or raises."""
    if getattr(args, "json", False) or getattr(args, "quiet", False):
        return
    if os.environ.get("GEO_READER_NO_UPDATE_CHECK"):
        return
    if not profile_exists():
        return
    try:
        payload = check_for_update(timeout=2.5)
    except Exception:
        return
    if payload.get("reachable") and payload.get("has_update"):
        print(
            "\n提示：发现新版本 {}（当前 {}）。运行 python3 main.py --update "
            "可在保留偏好的前提下更新。".format(
                payload.get("latest_version"), payload.get("current") or __version__
            )
        )


def interactive_menu() -> int:
    profile = load_profile()
    print(BANNER)
    if not profile_exists():
        print("尚未建立偏好：本次使用默认值。通过 Agent 使用时，请先说「开始使用」。")
    status = gate_status()
    print("Preflight : {}".format(
        "READY" if status.get("allowed") else "BLOCKED — 文献命令前先运行 [14]"
    ))
    print("当前偏好：{}".format(_profile_summary(profile)))
    print(MENU)
    try:
        choice = input("请选择 [0-15]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n已退出。")
        return 0

    if choice == "1":
        if not _menu_gate():
            return 2
        return _run_extraction("doi", input("DOI: ").strip(), _default_args())
    if choice == "2":
        if not _menu_gate():
            return 2
        return _run_extraction("url", input("URL: ").strip(), _default_args())
    if choice == "3":
        if not _menu_gate():
            return 2
        return _run_extraction("pdf", input("PDF 路径: ").strip(), _default_args())
    if choice == "4":
        if not _menu_gate():
            return 2
        return _run_batch(_default_args())
    if choice == "5":
        print_profile(profile)
        return 0
    if choice == "6":
        if not _menu_gate():
            return 2
        target = input("笔记路径（留空检查 papers/ 下全部）: ").strip()
        try:
            auto_fix = input("自动修复可判定的图片路径？[Y/n]: ").strip().lower() not in ("n", "no")
        except (KeyboardInterrupt, EOFError):
            auto_fix = False
        check_notes([Path(target)] if target else None, fix=auto_fix)
        return 0
    if choice == "7":
        if not _menu_gate():
            return 2
        target = input("笔记路径: ").strip()
        if target:
            print(index_note(Path(target)))
        return 0
    if choice == "8":
        _print_lists(list_workspace())
        return 0
    if choice == "9":
        print_guide(profile)
        return 0
    if choice == "10":
        return _run_doctor()
    if choice == "11":
        _run_update_check(_default_args())
        try:
            answer = input("现在更新到最新版本？[y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            answer = ""
        if answer in ("y", "yes"):
            return _run_update(_default_args())
        return 0
    if choice == "12":
        if not _menu_gate():
            return 2
        raw = input("日期过滤（天，留空=按页面当前列表）: ").strip()
        days = int(raw) if raw.isdigit() and int(raw) > 0 else None
        return _run_journal_scan(_default_args(), days=days)
    if choice == "13":
        return _run_journals_init(_default_args())
    if choice == "14":
        return _run_preflight(_default_args())
    if choice == "15":
        if not _menu_gate():
            return 2
        topic = input("主题（可留空，只用 --refs/锚定论文）: ").strip()
        anchor = input("锚定论文 DOI（可留空）: ").strip()
        refs = input("其它 DOI，逗号分隔（可留空）: ").strip()
        args = _default_args()
        args.thematic_review = topic
        args.anchor_doi = anchor
        args.refs = refs
        return _run_thematic_review(args)
    if choice == "0":
        print("再见。")
        return 0
    print("无效输入。")
    return 1


class _Args:
    def __init__(self, browser=None, wait=4.0, max_figures=30, json=False, quiet=False,
                 prerelease=False, refresh=False, force=False, dry_run=False,
                 days=None, limit=None, sort=None, journal=None, no_translate=False,
                 no_preflight=False, thematic_review=None, refs="", anchor_doi="",
                 max_refs=DEFAULT_MAX_REFS, from_year=None, to_year=None,
                 no_forward=False):
        self.browser = browser
        self.wait = wait
        self.max_figures = max_figures
        self.json = json
        self.quiet = quiet
        self.prerelease = prerelease
        self.refresh = refresh
        self.force = force
        self.dry_run = dry_run
        self.days = days
        self.limit = limit
        self.sort = sort
        self.journal = journal
        self.no_translate = no_translate
        self.no_preflight = no_preflight
        self.thematic_review = thematic_review
        self.refs = refs
        self.anchor_doi = anchor_doi
        self.max_refs = max_refs
        self.from_year = from_year
        self.to_year = to_year
        self.no_forward = no_forward


def _default_args() -> _Args:
    return _Args()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="geo-reader",
        description=(
            "geo-academic-reader: browser-first evidence extraction + VS Code note QA. "
            "The pipeline writes .raw/<slug>/ evidence packs; the agent writes papers/<slug>.md."
        ),
    )
    parser.add_argument("--version", action="version", version="geo-academic-reader {}".format(__version__))

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--doi", help="DOI of the paper")
    group.add_argument("--url", help="Direct URL to the article")
    group.add_argument("--pdf", help="Path to a local PDF")
    group.add_argument("--batch-pdfs", action="store_true", help="Process all PDFs in input_pdfs/")
    group.add_argument("--doctor", action="store_true", help="Run doctor.py")
    group.add_argument("--preflight", action="store_true", help="Check contract docs, environment and profile; writes a 24 h marker required by literature commands")
    group.add_argument("--check-note", nargs="?", const="", metavar="NOTE", help="Check image paths and placeholders in a note (or all papers/*.md)")
    group.add_argument("--index", metavar="NOTE", help="Append/update a note row in papers/INDEX.md")
    group.add_argument("--list", action="store_true", help="List evidence packs and notes")
    group.add_argument("--profile", action="store_true", help="Show the saved preferences (or whether onboarding is still pending)")
    group.add_argument("--guide", action="store_true", help="Print the quick-start guide")
    group.add_argument("--check-update", action="store_true", help="Check GitHub for a newer release (cached for 6 h)")
    group.add_argument("--update", action="store_true", help="Update the workspace, preserving profile, notes and evidence packs")
    group.add_argument("--new-literature", action="store_true", help="Open the configured journal pages and print numbered candidates; never extracts")
    group.add_argument(
        "--thematic-review",
        nargs="?",
        const="",
        metavar="TOPIC",
        help=(
            "Build a thematic-review working set: Crossref topic search + per-item "
            "verification + a human fact-check sheet. Never writes review prose"
        ),
    )

    parser.add_argument("--journals-init", action="store_true", help="Create .geo-reader/journals.json for editing")
    parser.add_argument("--days", type=int, help="Optional date filter for dated entries; 0 = page as-is (default: journals.json)")
    parser.add_argument("--limit", type=int, help="Maximum candidates to list; 0 = all (default: journals.json)")
    parser.add_argument("--journal", action="append", metavar="KEY", help="Only scan this journal key (repeatable)")
    parser.add_argument("--sort", choices=["journal", "date"], help="Group candidates by journal or list them by date")
    parser.add_argument("--no-translate", action="store_true", help="Skip Chinese titles in the new-literature scan")

    parser.add_argument("--refs", metavar="DOIS", help="With --thematic-review: comma-separated DOIs or a file holding them")
    parser.add_argument("--anchor-doi", metavar="DOI", help="With --thematic-review: the anchor paper of the review")
    parser.add_argument("--max-refs", type=int, default=DEFAULT_MAX_REFS, help="With --thematic-review: maximum verified references (default: 25)")
    parser.add_argument("--from-year", type=int, help="With --thematic-review: earliest publication year")
    parser.add_argument("--to-year", type=int, help="With --thematic-review: latest publication year")
    parser.add_argument("--no-forward", action="store_true", help="With --thematic-review: skip forward-citation lookup")

    parser.add_argument("--browser", choices=["auto", "existing", "off"], help="Browser policy (default: profile)")
    parser.add_argument("--no-browser", dest="browser", action="store_const", const="off", help="Alias for --browser off")
    parser.add_argument("--wait", type=float, default=4.0, help="Seconds to wait after page load (default: 4)")
    parser.add_argument("--max-figures", type=int, default=30, help="Maximum figures to download (default: 30)")
    parser.add_argument("--fix", action="store_true", help="With --check-note: rewrite broken paths and migrate legacy assets/")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors in --check-note")
    parser.add_argument("--refresh", action="store_true", help="With --check-update: ignore the cached result")
    parser.add_argument("--prerelease", action="store_true", help="Include GitHub prereleases when checking for updates")
    parser.add_argument("--dry-run", action="store_true", help="With --update: show the target version without changing files")
    parser.add_argument("--force", action="store_true", help="With --update: reinstall even when up to date; with --journals-init: overwrite the user copy")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--quiet", action="store_true", help="Reduce progress output")
    parser.add_argument(
        "--no-preflight",
        action="store_true",
        help="Skip the session preflight gate for this command (only with explicit user consent)",
    )
    return parser


def main(argv=None) -> int:
    # A Chinese Windows console encodes pipes with cp936/GBK. Without this
    # the CLI dies with UnicodeEncodeError on the first non-GBK character,
    # which used to kill the QA gate before it could print a report.
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.preflight:
        return _run_preflight(args)

    blocked = _guard_literature(args)
    if blocked is not None:
        return blocked

    if (args.doi or args.url or args.pdf or args.batch_pdfs) and not args.json:
        if not profile_exists():
            print("提示：本次使用了 --no-preflight 且尚未建立偏好，因此采用默认值。\n")

    if args.doctor:
        return _run_doctor()

    if args.check_note is not None:
        targets = [Path(args.check_note)] if args.check_note else None
        reports = check_notes(targets, fix=args.fix, strict=args.strict)
        if args.json:
            print(json.dumps(reports, ensure_ascii=False, indent=2))
        code = 0 if all(report.get("errors", 0) == 0 for report in reports) else 1
        _notify_update_if_available(args)
        return code

    if args.index:
        result = index_note(Path(args.index))
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else
              "已更新 papers/INDEX.md\n{}".format(result["row"]))
        _notify_update_if_available(args)
        return 0

    if args.list:
        payload = list_workspace()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            _print_lists(payload)
        return 0

    if args.guide:
        print_guide(load_profile())
        return 0

    if args.profile:
        if args.json:
            print(json.dumps(
                {
                    "path": str(PROFILE_PATH),
                    "exists": profile_exists(),
                    "values": load_profile() if profile_exists() else None,
                },
                ensure_ascii=False,
                indent=2,
            ))
        else:
            print_profile(load_profile())
        return 0

    if args.check_update:
        return _run_update_check(args)
    if args.update:
        return _run_update(args)

    if args.journals_init:
        return _run_journals_init(args)
    if args.new_literature:
        return _run_journal_scan(args)
    if args.thematic_review is not None:
        code = _run_thematic_review(args)
        _notify_update_if_available(args)
        return code

    if args.doi:
        code = _run_extraction("doi", args.doi, args)
        _notify_update_if_available(args)
        return code
    if args.url:
        code = _run_extraction("url", args.url, args)
        _notify_update_if_available(args)
        return code
    if args.pdf:
        code = _run_extraction("pdf", args.pdf, args)
        _notify_update_if_available(args)
        return code
    if args.batch_pdfs:
        code = _run_batch(args)
        _notify_update_if_available(args)
        return code

    # No action selected.
    if len(sys.argv) == 1:
        if not profile_exists():
            print(BANNER)
            print("首次使用：这个工作区还没有偏好记录。")
            print("请在对话里对 Agent 说「开始使用」，它会用几个问题了解你的偏好；")
            print("不需要运行任何设置脚本。说明见 AGENTS.md 第 0 节。")
            print("\n也可以直接给出论文 DOI / URL / PDF 路径，Agent 会先完成引导，")
            print("再运行 python3 main.py --preflight 解锁文献命令。")
            return 0
        if is_tty():
            return interactive_menu()
        parser.print_help()
        print("\n非交互环境：请显式使用 --doi / --url / --pdf / --new-literature / --check-note 等参数。")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
