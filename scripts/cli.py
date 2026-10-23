#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified CLI for the geo-academic-reader workspace."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .config import (
    INPUT_PDFS_DIR,
    PROFILE_CHOICES,
    PROJECT_ROOT,
    is_tty,
    load_profile,
    PROFILE_PATH,
)
from .evidence import extract_evidence
from .note_check import check_notes, index_note, list_workspace
from .onboarding import print_guide, run_wizard
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
  [5] 修改偏好 / 重新引导
  [6] 检查笔记图片与格式（可 --fix）
  [7] 把笔记登记到 papers/INDEX.md
  [8] 查看证据包与笔记列表
  [9] 查看快速上手与提示词
  [10] 环境自检 (doctor)
  [0] 退出
"""


def _profile_summary(profile: dict) -> str:
    return "语言={language} | 环境={ide} | 风格={style} | 浏览器={browser} | 深度={depth}".format(
        language=profile.get("language", "zh-CN"),
        ide=profile.get("ide", "vscode"),
        style=profile.get("style", "balanced"),
        browser=profile.get("browser", "auto"),
        depth=profile.get("note_depth", "deep"),
    )


def _run_doctor() -> int:
    return subprocess.call([sys.executable, str(PROJECT_ROOT / "doctor.py")])


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
    print("     图片统一使用 ../assets/{}/fig_XX.png".format(result["slug"]))
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
        print("❌ 抽取失败: {}".format(exc))
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


def interactive_menu() -> int:
    profile = load_profile()
    print(BANNER)
    print("当前偏好：{}".format(_profile_summary(profile)))
    print(MENU)
    try:
        choice = input("请选择 [0-10]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n已退出。")
        return 0

    if choice == "1":
        return _run_extraction("doi", input("DOI: ").strip(), _default_args())
    if choice == "2":
        return _run_extraction("url", input("URL: ").strip(), _default_args())
    if choice == "3":
        return _run_extraction("pdf", input("PDF 路径: ").strip(), _default_args())
    if choice == "4":
        return _run_batch(_default_args())
    if choice == "5":
        run_wizard()
        return 0
    if choice == "6":
        target = input("笔记路径（留空检查 papers/ 下全部）: ").strip()
        try:
            auto_fix = input("自动修复可判定的图片路径？[Y/n]: ").strip().lower() not in ("n", "no")
        except (KeyboardInterrupt, EOFError):
            auto_fix = False
        check_notes([Path(target)] if target else None, fix=auto_fix)
        return 0
    if choice == "7":
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
    if choice == "0":
        print("再见。")
        return 0
    print("无效输入。")
    return 1


class _Args:
    def __init__(self, browser=None, wait=4.0, max_figures=30, json=False, quiet=False):
        self.browser = browser
        self.wait = wait
        self.max_figures = max_figures
        self.json = json
        self.quiet = quiet


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
    group.add_argument("--setup", action="store_true", help="Run the first-use onboarding wizard")
    group.add_argument("--reconfigure", action="store_true", help="Re-run onboarding and overwrite preferences")
    group.add_argument("--doctor", action="store_true", help="Run doctor.py")
    group.add_argument("--check-note", nargs="?", const="", metavar="NOTE", help="Check image paths and placeholders in a note (or all papers/*.md)")
    group.add_argument("--index", metavar="NOTE", help="Append/update a note row in papers/INDEX.md")
    group.add_argument("--list", action="store_true", help="List evidence packs and notes")
    group.add_argument("--guide", action="store_true", help="Print the quick-start guide")

    parser.add_argument("--browser", choices=PROFILE_CHOICES["browser"], help="Browser policy (default: profile)")
    parser.add_argument("--no-browser", dest="browser", action="store_const", const="off", help="Alias for --browser off")
    parser.add_argument("--wait", type=float, default=4.0, help="Seconds to wait after page load (default: 4)")
    parser.add_argument("--max-figures", type=int, default=30, help="Maximum figures to download (default: 30)")
    parser.add_argument("--fix", action="store_true", help="With --check-note: rewrite broken image paths")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors in --check-note")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--quiet", action="store_true", help="Reduce progress output")

    # Onboarding overrides (also usable with --setup --non-interactive).
    parser.add_argument("--language", choices=PROFILE_CHOICES["language"])
    parser.add_argument("--ide", choices=PROFILE_CHOICES["ide"])
    parser.add_argument("--style", choices=PROFILE_CHOICES["style"])
    parser.add_argument("--depth", choices=PROFILE_CHOICES["note_depth"])
    parser.add_argument("--citation", choices=PROFILE_CHOICES["citation"])
    parser.add_argument("--agent")
    parser.add_argument("--citation-contact", dest="citation_contact")
    parser.add_argument("--non-interactive", action="store_true", help="Use defaults/overrides without prompting")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.setup or args.reconfigure:
        overrides = {
            "language": args.language,
            "ide": args.ide,
            "style": args.style,
            "browser": args.browser,
            "note_depth": args.depth,
            "citation": args.citation,
            "agent": args.agent,
            "citation_contact": args.citation_contact,
        }
        overrides = {key: value for key, value in overrides.items() if value}
        run_wizard(
            non_interactive=args.non_interactive or not is_tty(),
            overrides=overrides,
        )
        return 0

    if args.doctor:
        return _run_doctor()

    if args.check_note is not None:
        targets = [Path(args.check_note)] if args.check_note else None
        reports = check_notes(targets, fix=args.fix, strict=args.strict)
        if args.json:
            print(json.dumps(reports, ensure_ascii=False, indent=2))
        return 0 if all(report.get("errors", 0) == 0 for report in reports) else 1

    if args.index:
        result = index_note(Path(args.index))
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else
              "已更新 papers/INDEX.md\n{}".format(result["row"]))
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

    if args.doi:
        return _run_extraction("doi", args.doi, args)
    if args.url:
        return _run_extraction("url", args.url, args)
    if args.pdf:
        return _run_extraction("pdf", args.pdf, args)
    if args.batch_pdfs:
        return _run_batch(args)

    # No action selected.
    if len(sys.argv) == 1:
        if not PROFILE_PATH.exists():
            print(BANNER)
            print("检测到首次使用。建议先运行 1 分钟引导：python3 main.py --setup")
            if is_tty():
                try:
                    answer = input("现在进入引导？[Y/n]: ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    answer = "n"
                if answer not in ("n", "no"):
                    run_wizard()
                    return 0
        if is_tty():
            return interactive_menu()
        parser.print_help()
        print("\n非交互环境：请显式使用 --doi / --url / --pdf / --check-note 等参数。")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
