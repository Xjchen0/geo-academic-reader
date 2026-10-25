# geo-academic-reader

[![Version](https://img.shields.io/badge/version-0.5.1-blue.svg)](https://github.com/Xjchen0/geo-academic-reader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> 把论文变成多年后还能用的 Markdown 知识库，而不是一条会消失的聊天记录。

[English](README.md) | [简体中文](README.zh-CN.md)

geo-academic-reader 是一个**给 AI Agent 用的文献工作区**。脚本负责打开论文、抓取正文、下载高清图件并记录来源；Agent 读这些证据来写笔记；一条 QA 命令在交付前检查图件、引用网络与 Markdown 兼容性。它为地球科学、地球物理与地质学而写，对一般科学同样适用。

**适合**：想要可积累成文件、带引用网络、图件质量可核验的精读。
**不适合**：只想要一段摘要，或者不希望 Agent 读写本地文件的场景。

---

## 1. 安装部署

### 1.1 环境要求

| 项目 | 版本 | 为什么 | 缺了怎么办 |
| :--- | :--- | :--- | :--- |
| Python | ≥ 3.9 | 运行 CLI 与 QA 引擎 | 先升级；低于 3.9 其它都跑不起来 |
| `requests`、`beautifulsoup4`、`pypdf`、`websockets` | 最新 | 抓取、解析、PDF 文本、Chrome 调试协议 | `pip install requests beautifulsoup4 pypdf websockets` |
| `pymupdf` | 可选 | 更快的 PDF 内嵌图提取 | `pip install pymupdf` |
| Chrome / Chromium / Edge | 任意较新版本 | **浏览器优先取图** | 装一个浏览器，或接受 `--browser off`（图件质量下降） |
| 一个 AI Agent | VS Code、Cursor、Claude Code、Antigravity、Windsurf 或终端 Agent | Agent 读契约、写笔记 | — |

`pymupdf` 是唯一可选依赖，其余都是必需的。

### 1.2 安装

```bash
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader
./install.sh          # macOS / Linux
```

```powershell
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader
.\install.ps1         # Windows
```

任意平台、不分 shell 的写法：

```bash
python install.py
```

安装器会检查 Python、装好依赖、报告浏览器情况、建好空的 `papers/` 目录。**它不会问你要 DOI、不会写偏好文件、不会造阅读数据**——那些都在下一步的对话里完成。

**如果你用 `uv` 管理 Python**（Windows 上推荐）：

```bash
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader
uv sync                          # 建 .venv/ 并装好项目本体和依赖
uv run python main.py --preflight
```

`uv sync` 读 `pyproject.toml`、解析依赖、把项目本身也装进去，所以 `uv run python main.py …` 不用手动激活环境。`install.py` 检测到 `uv` 时会自动改走 `uv sync`。`uv.lock` 被 git 忽略是刻意的：本项目支持 Python 3.9–3.12，也支持 pip 安装，依赖解析留给每台机器自己定——删掉它即可重新解析。

> **Windows 提示**
>
> 刚装好的 Windows 上，`PATH` 里的 `python` / `python3` 指向 Microsoft Store 占位符（`AppData\Local\Microsoft\WindowsApps\python3.exe`），它是个 0 字节的桩，**退出码 49** 且没有任何输出。用 `uv sync` + `uv run`，或者从 python.org 安装并勾选 **Add Python to PATH**。现在 `--preflight` 和 `doctor.py` 会直接点名这个占位符，不再只丢一个退出码 49。

可选：把 CLI 装进 `PATH`。

```bash
pip install -e .
geo-reader --preflight      # 与 python3 main.py 等价
geo-doctor                  # 详细诊断
```

### 1.3 验证安装

```bash
python3 main.py --preflight
```

```bash
uv run python main.py --preflight      # 用 uv 时
```

它打印一张检查表，并写入 `.geo-reader/preflight.json`：

| 检查项 | 正常 | 缺失时 |
| :--- | :--- | :--- |
| 契约文档 | `AGENTS.md`、`MEMORY.md`、`LESSONS.md` 都在 | 从发布版恢复；**绝不**写空占位文件 |
| 操作系统与 Python | Python ≥ 3.9 | 给出升级路径，不要继续 |
| 依赖包 | `requests`、`beautifulsoup4`、`pypdf`、`websockets` | 给出确切的 `pip install` 命令，**先问再装** |
| 浏览器 | Chrome / Chromium / Edge；CDP 9222 可选 | 询问是否安装，或接受 HTTP/PDF 回退（图件质量较低） |
| 编辑器 | profile 里的编辑器；`.vscode/settings.json` | 说明如何创建；不擅自改设置 |
| 工作区角色 | `code repository` 或 `test workspace` | 说明这个目录是否携带本地阅读数据 |

标记有效期 **24 小时**，且与版本绑定。`--doi`、`--url`、`--pdf`、`--batch-pdfs`、`--new-literature`、`--check-note`、`--index` 都需要它，否则 CLI 以退出码 2 终止。修法是**重跑检查**，而不是绕过它。

> **为什么要设这道门**
>
> Agent 往往先跑命令、后读契约。这个标记把"跳过了检查"变成一次显式失败，而不是一次无声的降级。它只能证明检查跑过，不能证明文档被读过——所以文档里也写着：绝不伪造标记。

### 1.4 部署为阅读工作区（推荐）

同一个仓库有两种角色，`--preflight` 会自动判断并打印在 `Role:` 行：

| 角色 | 判断依据 | 携带 | 不携带 |
| :--- | :--- | :--- | :--- |
| **代码仓库** | 没有 profile、没有笔记、没有证据包 | 代码、模板、文档、`journals.json`、空的 `papers/` | 偏好、笔记、图件、证据包、PDF |
| **测试 / 阅读工作区** | 上面任意一项存在 | 代码 + profile + 笔记 + 图件 + 证据包 + `input_pdfs/` | — |

- `papers/*.md`、`papers/assets/*`、`input_pdfs/*.pdf`、`reading_list_*.md`、`.raw/`、`.geo-reader/` 都在 git 忽略列表里。
- 代码仓库只保留 `papers/.gitkeep` 与 `papers/assets/.gitkeep`：结构在，数据不在。
- 更新只替换代码与文档，**绝不写入** `papers/`、`.raw/`、`.geo-reader/`、`input_pdfs/`。

**推荐部署**：把远程仓库克隆两次。一份保持干净，用来提交与发版；另一份用来日常阅读。两者共享代码历史，但绝不共享本地偏好、笔记或证据包。

---

## 2. 快速开始

在 Agent 里打开这个目录（VS Code、Cursor、Claude Code、Antigravity、Windsurf，或终端 Agent），然后说：

```text
开始使用
```

（英文也行：`Start`。）Agent 会：

1. 先读 `AGENTS.md`、`MEMORY.md`、`LESSONS.md`，而不是从命令行参数猜契约；
2. 运行 `python3 main.py --preflight`，用大白话跟你确认操作系统、Python、依赖包、Chrome、编辑器和工作区角色；
3. 问七个简短偏好问题，写入 `.geo-reader/profile.json`；
4. 重跑 preflight，解锁文献命令；
5. 用几行带你走一遍目录结构，然后给你**恰好一个**入门练习。

**没有设置脚本、没有向导，在那次对话之前不会写任何文件。** 之后说 `重新设置偏好` / `Reconfigure` 即可修改；偏好跨会话、跨版本持续保存。

### 2.1 它会问哪些偏好

| 选项 | 取值 | 作用 |
| :--- | :--- | :--- |
| 语言 | `zh-CN`、`en`、`bilingual` | 笔记与回复语言 |
| 编辑器 | VS Code、Cursor、Claude Code、Antigravity、Windsurf、终端 | 版式与预览建议 |
| 指令风格 | `guided`、`balanced`、`expert` | Agent 停下来确认的频率 |
| 浏览器策略 | `auto`、`existing`、`off` | 启动/复用 Chrome，或只用 HTTP/PDF |
| 精读深度 | `brief`、`standard`、`deep` | 一页简报、IMRaD、逐图精读 |
| 引用格式 | `apa`、`nature`、`gbt7714` | 参考文献风格 |
| 期刊清单 | 内置 17 个页面/栏目，或自定义 | "找新文献"会打开哪些页面 |

默认取 `zh-CN`、VS Code、balanced、auto、deep、APA 与内置 `journals.json`。"用默认值"是合法回答。

### 2.2 工作循环

```text
python3 main.py --doi "<DOI>"            →  .raw/<slug>/  +  papers/assets/<slug>/
        ↓  Agent 据此写笔记
papers/<slug>.md                          →  以 templates/paper_note.md 为骨架
        ↓
python3 main.py --check-note papers/<slug>.md --fix
python3 main.py --index papers/<slug>.md
```

第一篇论文：

```text
精读 DOI 10.1038/s41467-026-69772-8
```

Agent 抽取证据包、写好笔记，再跑 `--check-note --fix` 与 `--index`。所有任务的可复制指令见 [PROMPTS.md](PROMPTS.md)。

### 2.3 最后你会得到什么

```text
papers/
├── <slug>.md                 你读、你也引用的笔记
├── INDEX.md                  目录（由 --index 生成）
└── assets/<slug>/fig_01.png  图件库，放在 papers/ 内，VS Code 才能正常渲染
```

---

## 3. 两大核心功能

两个功能都由**自然语言**触发，不需要记命令。Agent 识别意图，再驱动脚本。

### 3.1 新文献分享 —— "找新文献"

**触发说法**：`找新文献` / `最近有什么新文章` / `看看期刊新文章` / "推荐文献"。

```text
找新文献。
```

流程：

1. Agent 运行 `python3 main.py --new-literature`，**只打开 `journals.json` / `.geo-reader/journals.json` 里配置的期刊页面**——Nature research-articles、Science First Release / Current、Science Advances、EPSL 各卷、AGU 五本、Geology 当期与 early publication、GJI、PNAS Earth（内置清单共 17 个页面/栏目）。
2. 每个页面按它自己列出的条目解析，结果写入 `.geo-reader/journal-scan/latest.md` 与 `latest.json`。
3. Agent 给出**编号候选**——英文原题、中文机译标题（标明是机译）、期刊、日期、DOI——然后**停下**。

```text
1. Nature — "Deep mantle convection beneath the Pacific"
   中文（机译）：太平洋之下的深部地幔对流
   2026-10-22 · https://doi.org/10.1038/s41586-026-00000-0
```

**这一轮只列清单。** 在你回复编号或 DOI 之前，不建证据包、不写笔记、不做抽取。你选定之后，Agent 才逐篇处理。

Agent 必须遵守的硬规则：

- 绝不按主题搜索，绝不从你的笔记或这段对话猜测"你可能想看什么"。期刊清单就是"新文献"的定义。
- 英文原题是准据，中文那行是供检索用的机译。
- 翻译缺失就写"暂缺"——绝不自己编一个标题。
- 遇到 Cloudflare / 人机验证页，交给**你**：在打开的 Chrome 窗口里手动点过，然后重跑同一条命令。脚本不自动刷新。

可调项：

```bash
python3 main.py --journals-init                  # 生成可编辑的期刊清单
python3 main.py --new-literature --journal epsl --journal geology_early
python3 main.py --new-literature --days 3        # 可选日期窗口；默认 0 = 页面列什么就是什么
python3 main.py --new-literature --no-translate  # 只要英文清单
```

### 3.2 经典文献分享 —— "经典文献精读"

**触发说法**：`把 <DOI / URL / PDF> 当作一篇经典文献来读` / `经典文献分享` / "深读这篇经典"。

```text
把 10.1073/pnas.2510972122 当作一篇经典文献来读。
```

经典文献笔记**不是一篇 PDF 的摘要**，而是一张引用网络：它继承了什么、它在反驳什么、后来的工作对它做了什么。

Agent 会：

1. 建立证据包（`--doi` / `--url` / `--pdf`）；
2. 找出它的**前史**（它在回应谁）、**同期的竞争解释**（至少两种，各自依赖什么判据）、以及**发表后的检验或修正**；
3. 写出 `## 0. 文献坐标`，含一张至少 5 行的 `年份 | 工作 | 核心贡献 | 与本文的关系` 表；
4. 引用至少 **10 篇**外部文献（综述为 **15 篇**），每篇给 DOI；无法核验的条目标注"自动构造，需核对"；
5. 明确写出**证据足以排除哪些竞争解释、不足以排除哪些**——"没有讨论"不等于"已经排除"；
6. 检索不到的部分直接说"这部分检索未覆盖"，不用没读过的条目凑数；
7. 从证据包嵌入**原文图件**，每张配一个 `> **读图要点**` 读图块；
8. 最后跑 `--check-note --fix` 与 `--index`。

各深度的外部文献下限：

| `note_depth` | 外部文献下限 | 典型用途 |
| :--- | :--- | :--- |
| `brief` | 3 | 一页简报 |
| `standard` | 6 | 默认单篇笔记 |
| `deep` | 10 | 经典文献深读 |
| `note_type: 经典文献综述` | 15 | 多篇综述 |

这里图件同样不是可选项：综述至少嵌入 **3** 张原文图，deep 笔记至少 **3** 张；缺图的综述会被 `--check-note` 以 `review_without_figures` 判为 error。

---

## 4. 为什么必须从 web 直取

这是本项目与"把 PDF 贴进聊天框"最不一样的地方。

**只有出版社网页上，图件、图注、补充材料与正式版本是同时存在的。** 其它一切都是二手拷贝。

| | 从 web 直取 | 只剩 PDF 的回退 |
| :--- | :--- | :--- |
| 分辨率 | 出版社原始资源（常为 1000–2000 px 宽） | 内嵌位图，常 ≤ 600 px，有时只是页面裁切 |
| 图注 | 完整图注，通常含各子图说明 | 缺失，或被拆在页面各处 |
| 补充材料 | 网页链接的图表与方法 | 没有 |
| 版本 | 正式发表版，含更正 | 你恰好下载到的那一版 |
| 来源标记 | `figures/manifest.json` 记为 `browser` 或 `http` | 记为 `pdf`——笔记里会明说 |

因此每篇论文都走一条严格的回退链：

1. **先用 Chrome/CDP**（`--browser auto`，默认）——Agent 打开真实文章页，取出版社自己的图片资源。
2. **再用直连 HTTP**——同样的资源，不用浏览器，浏览器失败时启用。
3. **最后才用 PDF 内嵌图**——前两者都失败时才用。此时笔记会明确说明，manifest 记 `origin: pdf`。

PDF 页面裁切绝不会被当成出版社原图；笔记里报告的来源只能是 `figures/manifest.json` 里记录的那一个——不允许猜测。

**为什么这对阅读本身重要：**

- 图往往是某个论断的**证据**。低分辨率或被裁过的图支撑不了"这个子图什么形状""这条曲线拐点在哪""误差棒有多宽"这类论断；照着它写的笔记就是在过度解读。
- 图注携带条件：样本量、投影方式、年龄模型、滤波参数。裁掉图注就等于裁掉条件。
- 浏览实时页面还能拿到**讨论部分的元数据**——后续版本、更正，以及引用网络需要的先行工作链接。

**我们对 Agent 的要求，也是对你的要求：**

- 只要论文有网页版，Agent 就必须用浏览器打开。页面出现人机验证时，它停下来请**你**点一下——不刷新、不猜测、不悄悄降级到更差的来源。只有真正只有 PDF 的论文才用 PDF 裁切。
- 如果正文少于 800 字符，或图件列表为空，Agent 如实报告，而不是照样写一篇综述。

---

## 5. 其它功能

全部都有可直接复制的指令，见 [PROMPTS.md](PROMPTS.md)。触发方式与契约都一样。

| 任务 | 触发说法 | 你会得到 |
| :--- | :--- | :--- |
| **单篇精读（DOI）** | `精读 DOI <doi>` | IMRaD 式笔记，逐图精读、证据锚点，并把这篇论文放进它的引用网络 |
| **单篇精读（URL）** | `精读这篇论文：<URL>` | 同上，并说明页面是否需要登录或人机验证 |
| **只有 PDF** | `精读 input_pdfs/<file>.pdf` | 从 PDF 里抽出 DOI；只要有 DOI，仍优先用浏览器取高清图 |
| **批量 PDF** | `批量精读 input_pdfs/ 下的所有 PDF` | 每篇一份笔记，逐篇处理，最后给一张标题/年份/期刊/正文来源/图片来源/图件数/失败原因汇总表 |
| **多篇综述** | `围绕"<主题>"做一篇文献综述` | 结构化综述：检索与纳入标准、共识/争议/证据强度分层、每篇给 DOI 与本地笔记链接、**至少 3 张原文图**并配读图块，证据不足处标注"待补检索" |
| **审稿式重读** | `按"审稿人"视角重读 papers/<slug>.md` | 一份可执行的修改清单，而不是重写：核心主张、最弱的一环、方法假设与边界条件、图表是否真的支持正文、以及最值得先做的三个核查 |
| **笔记体检** | `运行 --check-note --fix` | 逐条解释剩余 error，用 magic bytes 核验文件确实是图片，真正缺失的图标注出来而不是删掉 |
| **索引维护** | `检查 papers/ 下所有笔记` | 报告缺失的 front matter，重跑 `--index`，列出 `papers/INDEX.md` 中重复、缺失或 DOI 不一致的行 |
| **更新** | `检查更新` / `更新` | `--check-update`（缓存 6 小时，离线时退出码 0），你说"更新"后才 `--update`。偏好、笔记、图件、证据包、PDF 全部保留；工作区脏或历史分叉时拒绝，绝不 reset |
| **改偏好** | `重新设置偏好` | 重问那七个问题；保留 `created_at`，刷新 `updated_at` |

两条贯穿所有任务的结构性规则：

- **脚本永远不写综述正文。** 一个把每节都填满的生成器，会让浅笔记看起来像深读。脚本产出证据，Agent 负责写。
- **每个关键论断都带证据锚点**：PDF 用 `（第 3 页）`，网页用 `（原文 §Results 第 2 段）`，图件用 `（图 2）`。

---

## 6. Python 代码

整个系统约 6800 行、依赖极少的 Python。刻意分成"证据层"和"写作层"两层，两者永不混用。

### 6.1 入口

| 文件 | 职责 |
| :--- | :--- |
| `main.py` | `scripts/cli.py` 的薄封装 |
| `doctor.py` | 详细环境诊断，`--json`、`--install`、`--launch-chrome` |
| `install.py` / `install.sh` / `install.ps1` | 跨平台安装器 |
| `uninstall.py` | 删除包与构建缓存；绝不碰 `papers/` 与 `.raw/` |

### 6.2 模块地图

| 模块 | 行数 | 职责 |
| :--- | :--- | :--- |
| `scripts/cli.py` | 588 | 参数解析、命令分发、可读输出 |
| `scripts/fetch_paper.py` | 635 | Crossref 元数据、文章页正文、从 PDF 抽 DOI |
| `scripts/browser.py` | 599 | Chrome 调试协议客户端：启动、导航、等待、截图、抓图片资源 |
| `scripts/figures.py` | 260 | 图件发现与下载、`image_magic` 校验、manifest 写入 |
| `scripts/evidence.py` | 654 | 证据包组装：`paper.json`、`fulltext.md`、`figures/manifest.json`、`README.md` |
| `scripts/note_check.py` | 931 | QA 引擎：图件、图路径、模板残留、夸张措辞、`$$` 配平、GitHub 告警、引用网络、`--fix` |
| `scripts/journal_watch.py` | 1131 | 期刊页面解析器（`nature`、`science_*`、`epsl`、`agu`、`geology_*`、`gji`、`pnas`）与候选清单 |
| `scripts/translate.py` | 287 | 标题中文机译，带缓存与地学术语后编辑 |
| `scripts/updater.py` | 749 | 版本检查、快进更新、稀疏克隆回退、profile 备份与恢复 |
| `scripts/preflight.py` | 291 | 会话标记：文档、环境、profile、工作区角色 |
| `scripts/onboarding.py` | 156 | 偏好 schema 与问题集 |
| `scripts/config.py` | 165 | 路径、profile 取值、引用数量目标 |
| `scripts/version.py` | 3 | 版本号的唯一真相源 |

### 6.3 证据包契约

```text
.raw/<slug>/
├── paper.json            书目元数据、APA 串、抽取方式、警告、统计
├── fulltext.md           带页码标记的正文——是证据，不是摘要
├── figures/manifest.json 图注、来源、尺寸的唯一权威
└── README.md             人类可读的摘要与下一步提示
```

`figures/manifest.json` 字段：

| 字段 | 含义 |
| :--- | :--- |
| `id` / `label` | 稳定 id（`fig_01`）与图号标签（`Figure 2`） |
| `caption` | 来自网页或 PDF 的图注；若为空，笔记必须说明 |
| `file` / `local_path` | 本地文件与工作区相对路径 |
| `markdown_path` | 笔记里使用的路径：`assets/<slug>/fig_01.png` |
| `origin` / `download` | `browser`、`http` 或 `pdf`，以及取字节的方式 |
| `source_url` / `page` | 原始图片 URL 与适用页码 |
| `width` / `height` / `bytes` | 尺寸与体积 |
| `is_body_figure` | 是否像正文图件，而非页面装饰 |

### 6.4 QA 引擎

`scripts/note_check.py` 是把承诺变成可执行约束的那一块。

| 检查项 | 级别 | 强制的内容 |
| :--- | :--- | :--- |
| `missing_image`、`broken_image` | error | 引用的图都存在、非空、且有真实图片 magic bytes |
| `invalid_image_path` | error | 只允许 `papers/` 内的 `assets/<slug>/...`——绝不 `../assets/`、绝对路径、`file://` 或 `<img>` |
| `placeholder_prose`、`hype_words` | error | 无模板残留、无无法证实的最高级 |
| `unbalanced_display_math`、`github_alert_syntax` | error | `$$` 成对；用引用块而不是 `> [!NOTE]`（VS Code 不渲染后者） |
| `missing_related_context`、`missing_citation_table` | error | 必须有文献坐标一节与 ≥5 行的引用表 |
| `thin_reference_context`、`no_external_references` | error | 外部文献下限：brief 3、standard 6、deep 10、综述 15 |
| `references_without_doi`、`duplicate_reference_doi` | warning | 每篇外部文献要有 DOI；不得重复 |
| `review_without_figures` | error | 综述至少嵌入 3 张可用的原文图 |
| `note_without_figures` | warning | deep 笔记至少嵌入 3 张 |

`--fix` 只改没有歧义的东西：把旧的图件库迁进 `papers/assets/`、重写链接、把告警标记转成带标签的引用块。它绝不改写你的正文。

### 6.5 测试

```bash
python3 -m unittest discover tests -v
```

五个测试套覆盖解析器、QA 引擎、preflight 门禁、翻译缓存与更新器：

```text
tests/test_journal_watch.py   tests/test_note_check.py
tests/test_preflight.py       tests/test_translate.py
tests/test_updater.py
```

### 6.6 扩展方式

- **加一本期刊**：往 `.geo-reader/journals.json` 加一条——`key`、`name`、`parser`、`url`（或 `url_template` + `volumes`）、`enabled`。除非版式特殊，否则不用改代码。
- **加一个解析器**：在 `scripts/journal_watch.py` 里实现，并登记到解析器表。
- **加一条 QA 规则**：扩展 `scripts/note_check.py`，并在 `tests/test_note_check.py` 里加用例。规则是数据不是散文：每条问题都有 code、级别与行号。
- **改版本号**：只改 `scripts/version.py`；`pyproject.toml` 与 `setup.py` 与之镜像，发布前会三者比对。

---

## 7. 故障排查

| 现象 | 原因 | 处理 |
| :--- | :--- | :--- |
| 文献命令以退出码 2 终止 | 标记缺失、过期或来自别的版本 | 跑 `python3 main.py --preflight`；不要用 `--no-preflight` 绕过 |
| 标记提示 `profile_missing` | preflight 跑在 profile 存在之前 | 完成引导、写好 profile、重跑 preflight |
| preflight 报告文档缺失 | `AGENTS.md` / `MEMORY.md` / `LESSONS.md` 不在 | 从发布版恢复；不要造空文件 |
| 找不到 Chrome | 浏览器优先取图不可用 | 装 Chrome，或接受 `--browser off` 与 PDF 回退 |
| Cloudflare 人机验证 | 需要人工点 | 在打开的 Chrome 窗口里点完再重跑；不自动刷新 |
| 图件为 0 | JS 阅读器、付费墙或选择器漂移 | 读 manifest 的警告；重试 `--browser auto`；如实报告失败 |
| 正文少于 800 字符 | 只拿到摘要页或付费墙 | 查 `fulltext.md`；换 OA PDF 或 `--url`；**绝不**只凭摘要写完整综述 |
| 预览里图片不显示 | 路径跑到 `papers/` 外 | `--check-note --fix`；合法写法是 `assets/<slug>/...` |
| `thin_reference_context` | 笔记只写了一篇的摘要 | 补前史、竞争解释与后续检验，或降低 `note_depth` |
| `review_without_figures` | 综述没有原文图 | 对关键文献跑 `--doi`，嵌入 `assets/<slug>/fig_XX.png`，每张配 `> **读图要点**` |
| `--check-update` 提示离线 | 连不上 GitHub | 不是错误；用 `--refresh` 重试，或设 `GEO_READER_NO_UPDATE_CHECK=1` |
| `--update` 拒绝执行 | 代码区脏或历史分叉 | 提交或 `git stash`；绝不 `reset --hard` |
| 期刊清单为空 | 页面被禁用、解析器漂移或卷号过期 | 检查 `enabled` / `url`；更新 EPSL 的 `volumes`；修解析器 |
| 中文标题显示"暂缺" | 翻译限流或服务不可用 | 重跑 `--new-literature`；已译条目走缓存；绝不自己编 |
| `python` 以退出码 49 退出 | `PATH` 上是 Microsoft Store 占位符桩 | 用 `uv sync` + `uv run python main.py …`，或从 python.org 安装并勾选 **Add Python to PATH** |
| CLI 输出是乱码 | 控制台把管道按 GBK/cp936 编码 | 0.5.1 起已修（stdout 强制 UTF-8）；旧版本请设 `PYTHONIOENCODING=utf-8` |
| `UnicodeEncodeError: 'gbk' codec` | emoji 撞上 cp936 控制台 | 0.5.1 起已修（控制台标记改用 ASCII）；旧版本请设 `PYTHONIOENCODING=utf-8` |

更多：[rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md)、[rules/JOURNALS.md](rules/JOURNALS.md)、[rules/MARKDOWN_SPEC.md](rules/MARKDOWN_SPEC.md)、[LESSONS.md](LESSONS.md)。

---

## 8. 诊断与清理

```bash
python3 main.py --preflight     # 契约 + 环境 + profile + 角色
python3 main.py --doctor        # 详细诊断
python3 doctor.py --json
python3 doctor.py --install
python3 doctor.py --launch-chrome

python3 uninstall.py            # 删除包与构建缓存
python3 uninstall.py --purge --yes
```

卸载不会删除 `papers/`、`papers/assets/` 或 `.raw/`。

---

## 9. 许可证

[MIT](LICENSE)
