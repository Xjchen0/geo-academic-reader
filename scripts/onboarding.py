#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""First-run onboarding: choose IDE, instruction style, language and depth."""

import argparse
import json
from pathlib import Path
from typing import Dict, Optional

from .browser import chrome_status, find_chrome
from .config import (
    DEFAULT_PROFILE,
    GUIDE_DIR,
    PROFILE_CHOICES,
    PROFILE_PATH,
    is_tty,
    load_profile,
    now_iso,
    save_profile,
)

CHOICE_LABELS = {
    "language": [
        ("zh-CN", "中文（推荐）"),
        ("en", "English"),
        ("bilingual", "中英双语"),
    ],
    "ide": [
        ("vscode", "VS Code + AI 插件"),
        ("cursor", "Cursor"),
        ("claude-code", "Claude Code"),
        ("antigravity", "Antigravity"),
        ("windsurf", "Windsurf"),
        ("cli", "只用终端 CLI"),
    ],
    "style": [
        ("guided", "引导式：每步解释并确认，适合第一次使用"),
        ("balanced", "平衡式：自动执行，遇到选择再询问（推荐）"),
        ("expert", "专家式：批量执行，最后统一汇报"),
    ],
    "browser": [
        ("auto", "自动启动 Chrome，浏览器优先取高清图（推荐）"),
        ("existing", "只复用已开着的 9222 调试端口"),
        ("off", "不启用浏览器，HTTP/PDF 回退"),
    ],
    "note_depth": [
        ("brief", "速览：1 页要点"),
        ("standard", "标准：问题—方法—结果—局限"),
        ("deep", "深度：逐图解读 + 证据锚点 + 局限（推荐）"),
    ],
    "citation": [
        ("apa", "APA"),
        ("nature", "Nature 风格"),
        ("gbt7714", "GB/T 7714"),
    ],
}

STYLE_HINTS = {
    "guided": "每次只推进一步；写笔记前先给提纲，关键结论先确认。",
    "balanced": "自主完成抽取与笔记；仅在浏览器、付费墙或范围选择时询问。",
    "expert": "批量执行，少打断；最终给出文件、证据包和未解决问题。",
}


def _ask_choice(key: str, default: str) -> str:
    options = CHOICE_LABELS[key]
    print("\n{}:".format({
        "language": "输出语言",
        "ide": "主要使用环境",
        "style": "Agent 指令风格",
        "browser": "浏览器策略",
        "note_depth": "精读深度",
        "citation": "引用格式",
    }[key]))
    for index, (value, label) in enumerate(options, 1):
        marker = " (默认)" if value == default else ""
        print("  [{}] {}{}".format(index, label, marker))
    raw = input("请选择 [1-{}]，直接回车使用默认: ".format(len(options))).strip()
    if not raw:
        return default
    if raw.isdigit() and 1 <= int(raw) <= len(options):
        return options[int(raw) - 1][0]
    if raw in PROFILE_CHOICES[key]:
        return raw
    print("  输入无效，使用默认值: {}".format(default))
    return default


def _ask_text(label: str, default: str) -> str:
    raw = input("\n{} [{}]: ".format(label, default)).strip()
    return raw or default


def run_wizard(non_interactive: bool = False, overrides: Optional[Dict[str, str]] = None) -> dict:
    overrides = overrides or {}
    current = load_profile()
    print("\n" + "=" * 64)
    print("  geo-academic-reader | 首次使用引导（约 1 分钟）")
    print("=" * 64)
    print("这份配置会写入 {}，AGENTS.md 会在每次任务开始时读取它。".format(PROFILE_PATH))

    profile = dict(current)
    for key in ("language", "ide", "style", "browser", "note_depth", "citation"):
        if non_interactive:
            profile[key] = overrides.get(key, current.get(key, DEFAULT_PROFILE[key]))
        else:
            profile[key] = _ask_choice(key, overrides.get(key, current.get(key, DEFAULT_PROFILE[key])))

    if not non_interactive:
        profile["agent"] = _ask_text("你的 Agent 名称（可留空）", profile.get("agent", "qoder"))
        profile["citation_contact"] = _ask_text(
            "Crossref/OpenAlex 联系邮箱（可选，用于礼貌请求）",
            profile.get("citation_contact", ""),
        )
    else:
        profile["agent"] = overrides.get("agent", profile.get("agent", "qoder"))
        profile["citation_contact"] = overrides.get("citation_contact", profile.get("citation_contact", ""))

    profile["created_at"] = profile.get("created_at") or now_iso()
    save_profile(profile)

    chrome = chrome_status()
    chrome_path = find_chrome()
    print("\n" + "-" * 64)
    print("环境检查")
    print("  Chrome 可执行文件: {}".format(chrome_path or "未找到"))
    print("  Chrome CDP 9222  : {}".format(
        "已运行 ({})".format(chrome.get("Browser", "Chrome")) if chrome else "未运行"
    ))
    if profile.get("browser") == "auto" and not chrome_path:
        print("  [!] 未找到 Chrome：将自动回退到 HTTP/PDF。安装 Chrome 后可获得更稳定的高清图。")

    write_welcome(profile)
    print("\n" + "=" * 64)
    print("配置完成")
    print("=" * 64)
    print("语言: {} | 环境: {} | 风格: {} | 浏览器: {} | 深度: {}".format(
        profile["language"], profile["ide"], profile["style"], profile["browser"], profile["note_depth"]
    ))
    print("Agent 行为提示: {}".format(STYLE_HINTS.get(profile["style"], "")))
    print("\n下一步：")
    print("  1. python3 main.py --doctor")
    print("  2. python3 main.py --doi \"10.1038/s41467-026-69772-8\"")
    print("  3. 让 Agent 读取 .raw/<slug>/ 并按 templates/paper_note.md 写 papers/<slug>.md")
    print("  4. python3 main.py --check-note papers/<slug>.md --fix")
    print("  5. python3 main.py --index papers/<slug>.md")
    print("\n提示词与常用指令见 PROMPTS.md；随时运行 python3 main.py --setup 重新配置。\n")
    return profile


def write_welcome(profile: dict) -> Path:
    GUIDE_DIR.mkdir(parents=True, exist_ok=True)
    path = GUIDE_DIR / "WELCOME.md"
    lines = [
        "# Welcome to geo-academic-reader",
        "",
        "This file is generated by `python3 main.py --setup`. It is local to your machine.",
        "",
        "## Your profile",
        "",
        "```json",
        json.dumps(profile, ensure_ascii=False, indent=2),
        "```",
        "",
        "## How the agent should behave",
        "",
        "- Language: {}".format(profile.get("language")),
        "- Instruction style: {} — {}".format(
            profile.get("style"), STYLE_HINTS.get(profile.get("style", ""), "")
        ),
        "- Browser policy: {}".format(profile.get("browser")),
        "- Note depth: {}".format(profile.get("note_depth")),
        "- Citation style: {}".format(profile.get("citation")),
        "",
        "## First task",
        "",
        "```text",
        "精读 DOI 10.1038/s41467-026-69772-8。先产出证据包，再按 templates/paper_note.md 写笔记，",
        "最后运行 --check-note 和 --index。不要使用 PDF 内嵌图，除非浏览器抽取失败。",
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def print_guide(profile: Optional[dict] = None) -> None:
    profile = profile or load_profile()
    print(r"""
===================================================================
  geo-academic-reader | 快速上手
===================================================================

1) 首次配置 / 修改偏好
   python3 main.py --setup
   python3 main.py --reconfigure

2) 抽取证据包（不会生成综述）
   python3 main.py --doi "10.1038/s41467-026-69772-8"
   python3 main.py --url "https://www.nature.com/articles/..."
   python3 main.py --pdf "input_pdfs/paper.pdf"
   python3 main.py --batch-pdfs

   浏览器策略：
     --browser auto       自动启动/复用 Chrome，浏览器优先取高清图（默认）
     --browser existing   只复用已开的 9222 端口
     --browser off        不走浏览器，HTTP/PDF 回退

3) 让 Agent 写笔记
   把下面这句话发给 Agent：
   “读取 .raw/<slug>/ 的证据包，按 templates/paper_note.md 写 papers/<slug>.md；
     图片用 ../assets/<slug>/；不要编造公式或结论；最后运行 --check-note 和 --index。”

4) 交付前检查
   python3 main.py --check-note papers/<slug>.md --fix
   python3 main.py --index papers/<slug>.md
   python3 main.py --list

5) 环境自检
   python3 main.py --doctor

当前偏好：语言={language} | 风格={style} | 浏览器={browser} | 深度={depth}
更多提示词：PROMPTS.md
""".format(
        language=profile.get("language", "zh-CN"),
        style=profile.get("style", "balanced"),
        browser=profile.get("browser", "auto"),
        depth=profile.get("note_depth", "deep"),
    ))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="geo-academic-reader onboarding wizard")
    parser.add_argument("--non-interactive", action="store_true", help="Use defaults/overrides without prompting")
    parser.add_argument("--language", choices=PROFILE_CHOICES["language"])
    parser.add_argument("--ide", choices=PROFILE_CHOICES["ide"])
    parser.add_argument("--style", choices=PROFILE_CHOICES["style"])
    parser.add_argument("--browser", choices=PROFILE_CHOICES["browser"])
    parser.add_argument("--depth", choices=PROFILE_CHOICES["note_depth"])
    parser.add_argument("--citation", choices=PROFILE_CHOICES["citation"])
    parser.add_argument("--agent")
    parser.add_argument("--citation-contact", dest="citation_contact")
    args = parser.parse_args(argv)

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
    run_wizard(non_interactive=args.non_interactive or not is_tty(), overrides=overrides)


if __name__ == "__main__":
    main()
