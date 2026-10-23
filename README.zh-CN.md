# geo-academic-reader 🌍

[![Version](https://img.shields.io/badge/version-0.0.1--pre-blue.svg)](https://github.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> 面向地球科学、地球物理、地质学及通用科学前沿的学术文献深度精读与图文 Markdown 自动化生成工具。专为 **VS Code 原生 Markdown 预览** 深度定制。

[English](README.md) | [简体中文](README.zh-CN.md)

---

## ✨ 核心亮点

- 🎯 **VS Code 原生极致体验**：
  - 数学公式采用标准 KaTeX 语法（`$...$` 和 `$$...$$`），VS Code 内置引擎直接高清渲染。
  - **完全不需要安装 Node.js 或 npm**，轻量零负担！
  - 完美支持 GitHub-Flavored Markdown (GFM) 警告框（`> [!NOTE]`, `> [!IMPORTANT]`, `> [!WARNING]`）。
- 🖼️ **高清插图本地化管理**：
  - 自动抓取并重写主流期刊 CDN（Nature, Science, AGU, Wiley, bioRxiv）的高清原图下载链接。
  - 图件本地持久化保存至相对目录（`./assets/<paper_slug>/fig_N.png`），告别图床失效与网络防盗链。
- ⚖️ **学术理性与防夸大铁律**：
  - 严格剔除营销号与夸大词汇，恪守学术中立，客观呈现本构模型假设、参数敏感性与实验边界。
  - 自动从 Crossref 抓取官方 APA 格式参考文献及 DOI 直链。
- 🩺 **智能跨平台环境诊断（Doctor）**：
  - 内置 `doctor.py`，自动识别 Windows、macOS 与 Linux。
  - 自动感知用户的包管理器（**Conda**、**uv**、**pip** 或虚拟环境 **venv**），输出量身定制的单行配置指令。
- ⚡ **Agent 与命令行一键部署**：
  - 既可以作为 AI Agent Skill（Antigravity、Claude Code、Cursor、VoltAgent）被自主调用，也可以作为独立命令行工具 `geo-reader` 在终端直接运行。

---

## 🚀 快速部署与首次安装

### 方式 1：一键安装向导（推荐）

克隆仓库后直接运行安装脚本：

```bash
git clone https://github.com/your-username/geo-academic-reader.git
cd geo-academic-reader

# macOS / Linux 用户：
./install.sh
# (或: python3 install.py)

# Windows (PowerShell) 用户：
.\install.ps1
# (或: python install.py)
```

安装向导会自动：
1. 检测当前激活的 Python 环境（Conda、uv 或 venv）。
2. 安装轻量依赖包（`requests`, `beautifulsoup4`, `pypdf`, `websockets`）。
3. 注册全局命令 `geo-reader` 与 `geo-doctor` 到系统环境变量。
4. 运行环境自检向导，验证就绪状态。

---

### 方式 2：手动安装

```bash
# 如果使用 uv（极速）：
uv pip install -r requirements.txt
uv pip install -e .

# 如果使用 Conda：
conda activate your_env
pip install -r requirements.txt
pip install -e .

# 如果使用标准 Python 虚拟环境：
python3 -m venv .venv
source .venv/bin/activate       # Windows 用户执行: .\.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

---

## 🧹 快速卸载与环境清理

当你需要移除本工具或清理测试环境时，可以使用内置的卸载脚本：

```bash
# 1. 常规卸载（自动卸载主包、移除全局命令 geo-reader、清理构建缓存与 __pycache__）：
python uninstall.py
# (macOS/Linux 执行: ./uninstall.sh，Windows 执行: .\uninstall.ps1)

# 2. 深度清理（额外卸载依赖包并删除本地 .venv 虚拟环境）：
python uninstall.py --purge --yes

# 3. 仅清理本地编译与缓存文件（保留安装状态）：
python uninstall.py --clean-only
```

---

## 📖 命令行使用指南

```bash
# 1. 通过 DOI 解析文献（支持 Nature, Science, AGU, Wiley, EPSL 等）
geo-reader --doi "10.1126/science.adz2675" --output ./output

# 2. 通过论文在线网页链接解析
geo-reader --url "https://www.nature.com/articles/s41586-026-10999-2" --output ./output

# 3. 通过本地 PDF 文件解析（抽取文本及内嵌图件）
geo-reader --pdf "/path/to/my_paper.pdf" --output ./output

# 4. 运行环境自检与引导程序
geo-doctor
```

输出目录结构示例：
```text
output/
├── Science_10.1126_science.adz2675.md    # 格式精美的 Markdown 全文
└── assets/
    └── Science_10.1126_science.adz2675/  # 提取的高清图件
        ├── fig_1.png
        └── fig_2.png
```

---

## 🔍 在 VS Code 中预览

1. 在 VS Code 中打开生成的 Markdown 文件：
   ```bash
   code ./output/<filename>.md
   ```
2. 调出富文本预览：
   - **Windows / Linux**：按下 `Ctrl + Shift + V`（或按 `Ctrl + K` 然后按 `V` 开启双栏对照）
   - **macOS**：按下 `Cmd + Shift + V`（或按 `Cmd + K` 然后按 `V` 开启双栏对照）
3. 即可在 VS Code 原生渲染环境下查看清晰的 KaTeX 数学公式、嵌入式图表与 GFM 警告框！

---

## 🤖 作为 AI Agent Skill 使用

将 `geo-academic-reader` 目录复制或符号链接至 Agent 的 skills 路径：
- **Antigravity / Cursor / Claude Code**：放入 `.agent/skills/geo-academic-reader` 或 `~/.gemini/antigravity/skills/geo-academic-reader`。
- Agent 将自动读取 `SKILL.md`，并在被问及“帮我精读论文”、“解析 DOI”、“生成 VS Code 图文笔记”时自主激活。

---

## 🌐 Chrome 浏览器调试模式 (CDP) 说明（可选）

- **无需启动 Chrome 的场景**：
  - 开放获取（Open Access）论文（bioRxiv, medRxiv, arXiv, PubMed Central）；
  - 本地 PDF 文献。
- **推荐启动 Chrome 9222 端口的场景**：
  - 存在严苛 Cloudflare 人机验证或付费墙（如 Science, Nature 付费全文）的高清原图抓取。
- **如何启动 Chrome 调试端口**：
  直接在终端运行 `geo-doctor`，程序会自动识别操作系统并输出专属于你系统的单行启动指令。

---

## 📁 仓库结构

```text
geo-academic-reader/
├── SKILL.md                 # Agent Skill 规范入口与触发条件
├── README.md                # 英文说明文档
├── README.zh-CN.md          # 简体中文说明文档
├── LICENSE                  # MIT 开源许可证
├── pyproject.toml           # 现代 Python 打包配置
├── setup.py                 # 传统构建支持
├── requirements.txt         # 极简依赖列表
├── doctor.py                # 跨平台环境诊断程序
├── install.py               # 跨平台一键安装程序
├── install.sh               # Unix/macOS 一键安装脚本
├── install.ps1              # Windows PowerShell 一键安装脚本
├── uninstall.py             # 跨平台一键卸载与环境清理程序
├── uninstall.sh             # Unix/macOS 一键卸载脚本
├── uninstall.ps1            # Windows PowerShell 一键卸载脚本
├── geo-academic-reader.yaml # 沙箱与网络白名单策略清单
├── LESSONS.md               # Agent 运行实战经验与 Token 预算优化
├── rules/                   # 渐进式按需载入的规则库
│   ├── JOURNALS.md          # 15+ 主流期刊抓取与高清大图规则
│   ├── MARKDOWN_SPEC.md     # VS Code GFM 警告框与 KaTeX 排版规范
│   └── TROUBLESHOOTING.md   # 故障排查与容灾降级指南
└── scripts/
    ├── config.py            # 全局配置与请求头
    ├── fetch_paper.py       # 文献文本与图件抽取引擎
    ├── generate_markdown.py # VS Code Markdown 模板合成器
    └── run_pipeline.py      # 命令行核心流水线
```

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
