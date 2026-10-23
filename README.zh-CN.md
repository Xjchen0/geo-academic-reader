# geo-academic-reader 🌍

[![Version](https://img.shields.io/badge/version-0.0.1--pre-blue.svg)](https://github.com/Xjchen0/geo-academic-reader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> **专为 AI Agent（智能编程与研究助手）量身定制的学术文献工作区模板。** 专攻地球科学、地球物理、地质学及通用前沿科学。克隆或下载本工作区后，直接使用 VS Code 配合你的 AI Agent（Cursor、Claude Code、Antigravity、Windsurf、Copilot 等）打开，让 Agent 自主帮你抓取、精读、解析文献并构建个人图文学术知识库。

[English](README.md) | [简体中文](README.zh-CN.md)

---

## 🤖 专为 AI Agent 打造的工作区架构

将本项目下载后作为独立文件夹使用，你的 AI 助手将立即获得整套学术精读流水线支持：

- 🧠 **预置 `AGENTS.md`**：受到 Antigravity、Cursor、Claude Code、Windsurf 和 Copilot 原生支持。AI 一进工作区即可识别规范，懂得如何抽取文献、排版 KaTeX 公式、提取插图并维护目录。
- 📥 **`input_pdfs/` 收件箱**：将你的科研 PDF 原文拖入该目录，直接对 AI 说：*“帮我精读 `input_pdfs/` 下的所有论文并整理要点”*。
- 📚 **`papers/` 与 `papers/INDEX.md` 知识库**：每次解析的文献都会在 `papers/` 生成结构化 Markdown 笔记，并在 `papers/INDEX.md` 自动生成一行索引，逐渐积累成个人科研知识库。
- 🖼️ **`assets/` 高清插图归档**：原始高清图件自动下载并按文献 slug 分类存储，采用相对路径链接，离线也能随时阅读。
- ⚙️ **`.vscode/` 原生预览优化**：内置工作区配置，自动开启原生 KaTeX 数学公式渲染（`$...$` 和 `$$...$$`）与 GFM 警告框。**完全无需安装 Node.js 或 npm！**

---

## 📁 工作区目录结构

```text
geo-academic-reader/                    # 项目工作区根目录
├── AGENTS.md                           # AI Agent 工作区行为准则与 SOP 规约
├── .vscode/                            # VS Code 工作区预设（预览、KaTeX、折行配置）
│   ├── settings.json                   # 原生 KaTeX 公式与排版规则
│   └── extensions.json                 # 推荐安装的 Markdown 扩展
├── input_pdfs/                         # PDF 收件箱（把需要读的 PDF 扔这里）
│   └── README.md
├── papers/                             # 你的个人文献精读知识库
│   └── INDEX.md                        # 全局文献目录索引表（自动更新）
├── assets/                             # 提取的高清原图集中存放处
├── main.py                             # 统一的工作区执行入口（支持交互式菜单）
├── doctor.py                           # 跨平台环境诊断与引导程序
├── install.py / install.sh / .ps1      # 一键环境初始化向导
├── uninstall.py / uninstall.sh / .ps1  # 一键卸载与环境清理脚本
├── rules/                              # 模块化规则库
│   ├── JOURNALS.md                     # 15+ 主流期刊抓取与高清大图 CDN 规则
│   ├── MARKDOWN_SPEC.md                # VS Code GFM 警告框与 KaTeX 排版规范
│   └── TROUBLESHOOTING.md              # 故障排查与容灾降级指南
├── LESSONS.md                          # Token 预算优化与长论文分块经验
├── requirements.txt                    # 极简纯 Python 依赖列表
├── SKILL.md                            # Agent Skill 规范（供技能型运行时识别）
└── scripts/                            # 底层核心流水线脚本
```

---

## 🚀 快速上手 (人机双用)

### 1. 初始化工作区环境

```bash
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader

# macOS / Linux 用户运行：
./install.sh
# (Windows PowerShell 用户运行: .\install.ps1，或: python install.py)
```

---

### 2. 在工作区中精读文献

你可以**通过向 AI Agent 发送自然语言指令**，或者**在终端直接运行命令行**：

#### 💬 方式 A：对你的 AI Agent 说（Cursor / Claude Code / Antigravity）
在 VS Code 中打开该工作区，直接向 AI 提问：
- *“帮我精读 DOI 为 `10.1126/science.adz2675` 的论文，输出到 `papers/` 目录下。”*
- *“解析 `input_pdfs/` 下的这篇论文，把其中的图表和核心假说梳理出来。”*
- *“查看 `papers/INDEX.md`，告诉我当前库里有哪些文献。”*

#### 💻 方式 B：终端命令行与交互式菜单
```bash
# 1. 打开交互式控制台菜单：
python main.py

# 2. 通过 DOI 解析文献：
python main.py --doi "10.1126/science.adz2675"

# 3. 通过论文网页直链解析：
python main.py --url "https://www.nature.com/articles/s41586-026-10999-2"

# 4. 批量解析 input_pdfs/ 目录下的所有 PDF：
python main.py --batch-pdfs

# 5. 解析指定的本地 PDF：
python main.py --pdf "input_pdfs/my_paper.pdf"
```

---

### 3. 在 VS Code 中预览

1. 打开生成的文献笔记：`code papers/<文献文件名>.md`
2. 调出原生富文本预览：
   - **Windows / Linux**：按下 `Ctrl + Shift + V`（或 `Ctrl + K` 然后按 `V`）
   - **macOS**：按下 `Cmd + Shift + V`（或 `Cmd + K` 然后按 `V`）
3. 查看清晰的 KaTeX 数学公式、嵌入式图表与 GFM 警告框！

---

## 🧹 卸载与环境清理

```bash
# 常规卸载（清理包与构建缓存）：
python uninstall.py

# 深度清理（额外卸载依赖并删除本地 .venv 虚拟环境）：
python uninstall.py --purge --yes
```

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
