#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preference schema and help text.

There is deliberately no setup wizard. First-use onboarding is a conversation:
the agent reads AGENTS.md, asks the questions, and writes
.geo-reader/profile.json itself. Users never have to run a setup command.
"""

import json
from typing import Optional

from .config import PROFILE_CHOICES, PROFILE_PATH, load_profile

CHOICE_LABELS = {
    "language": [
        ("zh-CN", "中文"),
        ("en", "English"),
        ("bilingual", "中英双语"),
    ],
    "ide": [
        ("vscode", "VS Code"),
        ("cursor", "Cursor"),
        ("claude-code", "Claude Code"),
        ("antigravity", "Antigravity"),
        ("windsurf", "Windsurf"),
        ("cli", "只用终端"),
    ],
    "style": [
        ("guided", "引导式：每步解释并确认"),
        ("balanced", "平衡式：自动执行，遇到选择再询问"),
        ("expert", "专家式：批量执行，最后统一汇报"),
    ],
    "browser": [
        ("auto", "自动启动/复用 Chrome，浏览器优先取高清图"),
        ("existing", "只复用已开着的 9222 调试端口"),
        ("off", "不启用浏览器，HTTP/PDF 回退"),
    ],
    "note_depth": [
        ("brief", "速览：1 页要点"),
        ("standard", "标准：问题—方法—结果—局限"),
        ("deep", "深度：逐图解读 + 证据锚点 + 局限"),
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

PROFILE_QUESTIONS = [
    ("language", "笔记和回复使用哪种语言？"),
    ("ide", "你主要在哪个环境里阅读 Markdown？"),
    ("style", "你希望 Agent 如何推进工作？"),
    ("browser", "图片提取是否允许自动启动 Chrome？"),
    ("note_depth", "单篇笔记写到什么深度？"),
    ("citation", "参考文献用哪种格式？"),
]


def profile_summary(profile: Optional[dict] = None) -> str:
    profile = profile or load_profile()
    return (
        "语言={language} | 环境={ide} | 风格={style} | "
        "浏览器={browser} | 深度={depth} | 引用={citation}"
    ).format(
        language=profile.get("language", "zh-CN"),
        ide=profile.get("ide", "vscode"),
        style=profile.get("style", "balanced"),
        browser=profile.get("browser", "auto"),
        depth=profile.get("note_depth", "deep"),
        citation=profile.get("citation", "apa"),
    )


def print_profile(profile: Optional[dict] = None) -> None:
    profile = profile or load_profile()
    if not PROFILE_PATH.exists():
        print("尚未建立偏好（首次对话时由 Agent 引导，无需运行设置脚本）。")
        print("说明见 AGENTS.md 第 0 节；触发词：开始使用。")
        return
    print("配置文件: {}".format(PROFILE_PATH))
    print(profile_summary(profile))
    print()
    print(json.dumps(profile, ensure_ascii=False, indent=2))


def print_guide(profile: Optional[dict] = None) -> None:
    profile = profile or load_profile()
    print(r"""
===================================================================
  geo-academic-reader | 快速上手
===================================================================

0) 首次使用（对话式，不运行设置脚本）
   在这个工作区里对 Agent 说：开始使用
   Agent 会先读 AGENTS.md / MEMORY.md / LESSONS.md，运行 --preflight，
   和你确认操作系统、Python、依赖包、Chrome 与编辑器，然后再问语言、环境、
   指令风格、浏览器策略、精读深度、引用格式和期刊清单。
   偏好写入 .geo-reader/profile.json；写完后 Agent 会重跑 --preflight。
   以后每次任务都会沿用这份偏好；想修改时说：重新设置偏好。
   文献命令需要 24 小时内的 preflight 标记，过期后重跑 --preflight 即可。

1) 找新文献（只列清单，等待你选择）
   python3 main.py --new-literature
   python3 main.py --new-literature --journal epsl --journal geology_early
   python3 main.py --journals-init     # 生成可编辑的个人期刊清单

   用 Chrome 打开 journals.json（个人副本 .geo-reader/journals.json 优先）里的
   期刊页面，按页面列出的条目抓标题、DOI 和日期，并给每条附上中文机译标题，
   写成 .geo-reader/journal-scan/latest.md，并打印编号列表。
   中文标题仅供检索，英文原题为准；缓存见 .geo-reader/journal-scan/translations.json。
   默认 --days 0：页面列出什么就列什么；--days 3 才按日期过滤；
   --no-translate 只列英文。
   这一步不会抽取证据包；Agent 必须等你回复编号或 DOI 后再精读。

1b) 主题综述（先核验，再写）
   python3 main.py --thematic-review "<主题>" --anchor-doi "10.xxxx/yyyy"
   python3 main.py --thematic-review "<主题>" --refs "doi1,doi2" --from-year 1990

   与“找新文献”不同：这里回答“这个问题上文献证据怎么说”，
   不是“这些刊最近发了什么”。脚本用 Crossref 主题检索找候选，
   再逐条核验标题/作者/年份/期刊并抓摘要；从锚定论文的引用列表取前史，
   从 OpenAlex 取后续检验候选（每条仍要过 Crossref 核验）。
   产物在 .raw/reviews/<slug>/：candidates.md、references.json、factcheck.md。
   脚本不写正文；Agent 先过 factcheck.md，再按 templates/thematic_review.md 写笔记，
   关键论断标【直证】/【转述】/【推断】/【评估】/【未核实】。

2) 抽取证据包（脚本只产出证据，不写综述）
   python3 main.py --doi "10.1038/s41467-026-69772-8"
   python3 main.py --url "https://www.nature.com/articles/..."
   python3 main.py --pdf "input_pdfs/paper.pdf"
   python3 main.py --batch-pdfs

   浏览器策略：
     --browser auto       自动启动/复用 Chrome，浏览器优先取高清图（默认）
     --browser existing   只复用已开的 9222 端口
     --browser off        不走浏览器，HTTP/PDF 回退

3) 让 Agent 写笔记
   “读取 .raw/<slug>/ 的证据包，按 templates/paper_note.md 写 papers/<slug>.md；
     图片用 assets/<slug>/；不要编造公式或结论；最后运行 --check-note 和 --index。”

   图库位于 papers/assets/<slug>/，与笔记同在 papers/ 下。
   这样无论 VS Code 打开项目根、papers/ 还是单个 .md，预览都能显示图片。

4) 交付前检查
   python3 main.py --check-note papers/<slug>.md --fix
   python3 main.py --index papers/<slug>.md
   python3 main.py --list

5) 环境与会话检查
   python3 main.py --preflight     # 契约文档 + 环境 + 偏好 + 工作区角色（写 24h 标记）
   python3 main.py --doctor        # 更详细的环境诊断
   缺少依赖时先按提示安装；不要用 --no-preflight 绕过检查。

当前偏好{profile_note}：{summary}
更多提示词：PROMPTS.md
""".format(
        summary=profile_summary(profile),
        profile_note="" if PROFILE_PATH.exists() else "（尚未建立，显示默认值）",
    ))
