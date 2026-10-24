# geo-academic-reader

[![Version](https://img.shields.io/badge/version-0.3.1-blue.svg)](https://github.com/Xjchen0/geo-academic-reader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> 面向 AI Agent 的文献工作区：**浏览器优先取证据**、**Agent 撰写笔记**、**Markdown 在 VS Code 中稳定渲染**。

[English](README.md) | [简体中文](README.zh-CN.md)

---

## 它做什么

输入 DOI、出版社链接或本地 PDF，它会产出**证据包**：元数据、带页码锚点的正文、带来源的图注，以及下载好的图片。Agent 读取证据包，写出文献笔记。你得到的是一个可长期维护的 Markdown 知识库，而不是一段聊天记录。

系统刻意拆成三层：

| 层 | 职责 | 产物 |
| :--- | :--- | :--- |
| 脚本 | 抓取、渲染、下载、记录来源 | `.raw/<slug>/`、`papers/assets/<slug>/` |
| Agent | 解读证据、撰写笔记 | `papers/<slug>.md` |
| 质检 | 校验路径、图片、提示块、引用网络、措辞、公式与模板残留 | `--check-note`、`--index` |

脚本从不撰写综述文字。这是有意为之：能自动填满每一节的生成器，会让浅层笔记看起来像精读。

---

## 为什么浏览器优先

- 出版社页面能提供图序、图注和分面结构；PDF 抽取经常切碎多分面图，或完全丢失图注。
- 初始 DOM 里的缩略图地址（`/w400/`、`.medium.gif`）会在下载前改写为 `full`、`w1200` 或 `large` 版本。
- CDN 对直接 HTTP 返回 403 时，会在页面上下文中用 `fetch()` 重新取图，复用浏览器会话与 referer。
- PDF 内嵌图仍然保留为回退方案；一旦使用，manifest 和笔记都会注明。

这里的“访问”不是绕过。流水线使用你本机已有的浏览器会话，不破解付费墙，也不回避人机验证。

---

## 环境要求

- Python **3.9+**
- `requests`、`beautifulsoup4`、`pypdf`、`websockets`
- **Google Chrome、Chromium 或 Microsoft Edge** —— 强烈推荐，用于 JavaScript 页面与高清图
- 可选：`pymupdf`，用于更准确的 PDF 图件裁剪

不需要 Node.js，也不需要额外下载无头浏览器。

---

## 快速开始

```bash
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader
./install.sh          # Windows: .\install.ps1   |   任意平台: python install.py
```

用你的 Agent（VS Code、Cursor、Claude Code、Antigravity、Windsurf 或终端 Agent）打开这个文件夹，然后说：

```text
开始使用
```

这就是全部的新手引导。Agent 会按 `AGENTS.md` 第 0 节问六个简短问题，把答案写入 `.geo-reader/profile.json`，并在后续会话中沿用。**没有设置命令，没有向导，对话之前不写入任何文件** —— 新克隆的仓库不带使用痕迹。之后想修改，说 `重新设置偏好` 即可。

接着抽取第一篇论文：

```bash
python3 main.py --doi "10.1038/s41467-026-69772-8"
```

让 Agent 根据证据包写笔记，最后执行：

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"
```

可直接复制的提示词见 [PROMPTS.md](PROMPTS.md)。

---

## 第一次对话

Agent 会分一到两批询问：

| 选项 | 取值 | 影响 |
| :--- | :--- | :--- |
| 语言 | `zh-CN`、`en`、`bilingual` | 笔记与回复语言 |
| 环境 | VS Code、Cursor、Claude Code、Antigravity、Windsurf、终端 | 排版约定与预览建议 |
| 指令风格 | `guided`、`balanced`、`expert` | 停下来确认的频率 |
| 浏览器策略 | `auto`、`existing`、`off` | 是否启动 Chrome、复用 9222，或只用 HTTP/PDF |
| 精读深度 | `brief`、`standard`、`deep` | 一页速览、标准 IMRaD、逐图精读 |
| 引用格式 | `apa`、`nature`、`gbt7714` | 参考文献样式 |

默认值为 `zh-CN`、VS Code、balanced、auto、deep、APA；直接说“用默认值”也可以。偏好保存在本地并被 git 忽略。Agent 每次任务前用 `python3 main.py --profile --json` 检查；只要文件存在，就不会重复引导。

---

## 日常工作流

### 1. 抽取证据包

```bash
python3 main.py --doi "10.1038/s41467-026-69772-8"
python3 main.py --url "https://www.nature.com/articles/s41467-026-69772-8"
python3 main.py --pdf "input_pdfs/my_paper.pdf"
python3 main.py --batch-pdfs
```

常用参数：

```bash
--browser auto       # 启动/复用 Chrome，浏览器优先（默认）
--browser existing   # 只复用已监听 9222 的 Chrome
--browser off        # 仅 HTTP/PDF
--wait 6             # 为 JavaScript 或人机验证多等一会
--max-figures 20     # 限制下载图件数量
--json               # 机器可读摘要
```

命令会输出 slug、证据文件路径、图件数量、实际抽取路线（如 `text=browser; figures=browser`）以及警告。它不会生成笔记。

### 2. 写笔记

把证据包路径和 `templates/paper_note.md` 交给 Agent。一条典型指令：

> 读取 `.raw/<slug>/`，按 `templates/paper_note.md` 写 `papers/<slug>.md`。只使用抽取到的正文和 manifest 图注；不要编造公式或结论。图片链接写 `assets/<slug>/fig_XX.png`。关键结论标注页码或章节。把论文放回引用网络：前史、竞争解释、后续检验，每条外部文献给出 DOI。最后运行 `--check-note --fix` 和 `--index`。

### 3. 质检

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"
python3 main.py --list
```

`--check-note` 会检查图片是否存在、是否为零字节、magic bytes 是否为图片、是否符合规范图库布局，同时检查模板残留、夸大措辞、未闭合的 `$$` 和引用网络：是否有文献坐标章节、引用表是否 ≥5 行、参考文献是否带 DOI、外部文献数量是否达到 `note_depth` 要求（3 / 6 / 10，综述 15）。GitHub 告警语法会被判为错误，因为 VS Code 只会把它当普通文字显示。`--fix` 会改写路径、迁移旧版图库，并把告警标记改成带粗体标签的引用块。加 `--strict` 可把警告视为错误。

### 4. 检查更新

```bash
python3 main.py --check-update              # 例如 0.3.1 → 0.3.2，或“已是最新”
python3 main.py --update --dry-run          # 只预览目标版本
python3 main.py --update                    # 更新，同时保留现有资料
```

`--check-update` 读取 GitHub Releases，结果缓存 6 小时；访问不了 GitHub 时以退出码 0 结束，不会让一次正常的阅读任务失败。`--update` 在 git 仓库里使用 `git merge --ff-only <tag>`，没有 `.git` 时下载对应 tag 的源码包，只覆盖代码与文档，不会写入 `papers/`、`.raw/`、`.geo-reader/` 或 `input_pdfs/`。`.geo-reader/profile.json` 会先备份到 `.geo-reader/backups/`，异常时自动恢复。工作区有未提交的代码改动，或本地历史与上游分叉时，会拒绝更新而不是覆盖。只有明确要跟踪预发布时才加 `--prerelease`。

版本策略以小版本为主：修复、文档或小范围改进默认 `0.3.0 → 0.3.1`；新增能力默认升 minor，除非另有要求。

### 5. 预览

打开 `papers/<slug>.md`，按 `Cmd+Shift+V`（macOS）或 `Ctrl+Shift+V`。原生 KaTeX 开箱可用，无需插件。提示块使用纯 Markdown 引用块加粗标签（`> **一句话结论**`），因为 VS Code 内置预览不渲染 GitHub 告警语法。

---

## 经典文献要放进引用网络

只复述一篇 PDF 的“经典文献精读”不是精读，是读书报告。每篇笔记都要有 `## 0. 文献坐标`：一张 `年份 | 工作 | 核心贡献 | 与本文的关系` 表、一段明确的**竞争解释**、一段**后续检验**。`--check-note` 的要求是：

| `note_depth` | 外部文献下限 | 典型用途 |
| :--- | :--- | :--- |
| `brief` | 3 | 一页速览 |
| `standard` | 6 | 默认单篇笔记 |
| `deep` | 10 | 经典文献深读 |
| `note_type: 经典文献综述` | 15 | 多篇综述 |

锚定论文本身不计入外部文献。只有 `## 参考文献` 下的条目才计数，每条外部文献尽量给出 DOI。文献读不全就写清楚缺哪一块，不要为了凑数塞入没读过的条目 —— 这条检查存在的意义正是防止这种“装饰性引用”。

---

## 图片路径与 VS Code 预览

VS Code 内置 Markdown 预览只允许从工作区目录加载本地图片；单文件窗口下只允许笔记所在目录。因此，当用户只打开 `papers/` 或单篇笔记时，放在项目根目录的 `assets/` 会全部失效。与此同时，在编辑器里悬停链接却可能仍显示缩略图 —— 悬停通过另一条路径直接读磁盘。这就是“链接能悬停预览、渲染区却是空图”的根因。

本工作区把图库放在**笔记所在的目录树内**：

```text
papers/
├── INDEX.md
├── <slug>.md
└── assets/
    └── <slug>/
        ├── fig_01.png
        └── fig_02.png
```

笔记中的相对链接为：

```markdown
![图 1：图注](assets/<slug>/fig_01.png)
*图 1：图注（来源：browser；原始链接：https://...）*
```

无论工作区根是项目根、`papers/`，还是单个 `.md` 文件，预览都能显示。QA 会拒绝 `../assets/...`、`./assets/...`、绝对路径、`file://` 和 `<img>` 标签。

### 从 0.2.1 升级

旧版把图片放在项目根 `assets/`，笔记里写 `../assets/...`。执行：

```bash
python3 main.py --check-note --fix
```

`--fix` 会把图片复制到 `papers/assets/<slug>/`，改写笔记链接，并同步 `figures/manifest.json` 与 `paper.json`。旧目录会保留，不会丢文件；确认预览正常后可以自行删除。

---

## 命令参考

```text
python3 main.py --doi DOI               按 DOI 抽取证据包
python3 main.py --url URL               按文章链接抽取
python3 main.py --pdf PATH              从本地 PDF 抽取
python3 main.py --batch-pdfs            处理 input_pdfs/ 下全部 PDF
python3 main.py --check-note [NOTE]     检查单篇或全部笔记
python3 main.py --index NOTE            写入/更新 papers/INDEX.md
python3 main.py --list                  列出证据包与笔记
python3 main.py --profile [--json]      查看当前偏好
python3 main.py --guide                 打印快速上手
python3 main.py --check-update          检查 GitHub 新版本（缓存 6 小时）
python3 main.py --update                更新代码，保留偏好、笔记与证据包
python3 main.py --doctor                环境自检
python3 main.py                         交互菜单（仅终端）
```

执行 `pip install -e .` 后，也可以用 `geo-reader` 和 `geo-doctor`。

---

## 目录结构

```text
geo-academic-reader/
├── AGENTS.md                     Agent 契约、引导流程、标准作业程序
├── PROMPTS.md                    可复制的任务提示词
├── SKILL.md                      Skill 清单与精简契约
├── input_pdfs/                   原始 PDF 投放区
├── papers/
│   ├── INDEX.md                  文献目录
│   ├── <slug>.md                 Agent 撰写的笔记
│   └── assets/<slug>/fig_XX.png  图库，与笔记同树
├── .raw/<slug>/                  证据包（被 git 忽略）
│   ├── paper.json
│   ├── fulltext.md
│   ├── figures/manifest.json
│   └── README.md
├── .geo-reader/                  本地偏好与 Chrome 配置（被 git 忽略）
├── templates/                    笔记与综述模板
├── rules/                        Markdown、期刊、排错参考
├── scripts/                      抽取、质检、偏好定义、CLI
├── main.py                       工作区入口
├── doctor.py                     环境诊断
└── install.* / uninstall.*
```

### 证据包契约

`paper.json` 保存书目元数据、APA 字符串及其是否自动构造、抽取方式、开放获取信息、警告、统计与相对路径。

`fulltext.md` 是带页码标记的原始抽取文本，是证据，不是摘要。

`figures/manifest.json` 是图件的唯一权威来源：

| 字段 | 含义 |
| :--- | :--- |
| `id` | 稳定标识，如 `fig_01` |
| `label` | 可识别时的图号标签，如 `Figure 2` |
| `caption` | 页面或 PDF 中的图注 |
| `file` | `papers/assets/<slug>/` 下的文件名 |
| `local_path` | 相对工作区的路径 |
| `markdown_path` | 笔记中使用的路径：`assets/<slug>/fig_01.png` |
| `origin` / `download` | `browser`、`http` 或 `pdf`，以及字节获取方式 |
| `source_url` | 原始图片地址 |
| `page` | 适用时的 PDF 页码 |
| `width`、`height`、`bytes` | 尺寸与体积 |
| `is_body_figure` | 是否像正文图而非页面装饰 |

图注为空时，笔记必须如实说明，不能替它编一个标题。

---

## 范围与限制

- **付费墙仍然是付费墙。** 浏览器优先只渲染你当前会话本来就能访问的内容。
- **人机验证需要人工介入。** 流水线会等待和重试；遇到验证码时，在启动的 Chrome 窗口里完成，再用 `--browser existing` 重试。
- **并非所有图都能取回。** 专有查看器、仅补充材料提供的图、特殊图注结构都可能失败。manifest 会记录失败原因，而不是隐藏。
- **PDF 回退质量较低。** 内嵌位图可能被切分或缺失图注；`pymupdf` 能改善裁剪。扫描版 PDF 不做 OCR。
- **元数据可能不完整。** 新 DOI 可能尚未进入 Crossref；自动构造的引用会在 `paper.json` 中标注。
- **脚本不写综述。** 缺少 `papers/<slug>.md` 说明 Agent 还没写，而不是抽取失败。

期刊适配细节：[rules/JOURNALS.md](rules/JOURNALS.md)。故障恢复：[rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md)。实践经验：[LESSONS.md](LESSONS.md)。

---

## 诊断与清理

```bash
python3 main.py --doctor        # Python、依赖、Chrome、CDP 9222、偏好、VS Code 配置
python3 doctor.py --json
python3 doctor.py --install
python3 doctor.py --launch-chrome

python3 uninstall.py            # 移除包与构建缓存
python3 uninstall.py --purge --yes
```

卸载不会删除 `papers/`、`papers/assets/` 与 `.raw/` 中的内容。

---

## 许可证

[MIT](LICENSE)
