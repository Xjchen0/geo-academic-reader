# geo-academic-reader 🌍

[![Version](https://img.shields.io/badge/version-0.2.1-blue.svg)](https://github.com/Xjchen0/geo-academic-reader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> **面向 AI Agent 的“浏览器优先”文献工作区。** 脚本只负责收集证据，Agent 负责写作，内置体检负责在交付前拦住坏图片、占位段落和虚构公式。

[English](README.md) | [简体中文](README.zh-CN.md)

---

## 为什么会有这个项目

常见的“AI 读论文”流程有两个坏毛病：

1. **让脚本写综述。** 生成器会拼出看似专业的通用段落和示例公式，和论文本身没有关系。结果是每篇笔记都“看起来很深入”，实际信息量很低。
2. **把 PDF 当成图片来源。** PDF 里的位图经常分辨率低、跨页断裂、缺少图注，而出版社网页上其实有干净的高清原图。

0.2.1 通过拆分职责解决这两个问题：

- **脚本只抽取。** 产出正文、元数据、图注、图片来源和已下载图片组成的“证据包”，不写任何综述。
- **Agent 负责解读。** Agent 读取证据包，按 `templates/paper_note.md` 写 `papers/<slug>.md`，关键结论必须带证据锚点。
- **体检负责把关。** `--check-note` 检查图片路径、空文件、损坏文件、模板残留、夸大措辞和未闭合公式。

对于 DOI、网页 URL，以及**内含 DOI 的 PDF**，管线会优先启动 Chrome，从渲染后的出版社页面取最高可用分辨率的图。PDF 内嵌图只是回退方案，具体走了哪条路会记录在 manifest 里。

---

## 工作流

```text
DOI / URL / PDF
      │
      ▼
Chrome DevTools Protocol (CDP 9222)  ──►  渲染后的页面、高清图 URL
      │                                      （CDN 返回 403 时在页面内 fetch）
      ▼
.raw/<slug>/paper.json
.raw/<slug>/fulltext.md
.raw/<slug>/figures/manifest.json
assets/<slug>/fig_01.png ...
      │
      ▼
Agent（AGENTS.md + templates/paper_note.md）
      │
      ▼
papers/<slug>.md  ──►  --check-note --fix  ──►  --index  ──►  papers/INDEX.md
```

---

## 0.2.1 的主要变化

- **浏览器优先抽取。** `--browser auto` 会用独立配置启动 Chrome（9222 端口），等待 JavaScript 渲染，升级缩略图 URL；直连被拒时，在页面上下文里下载图片。
- **证据包取代自动生成的长文。** `main.py` 只写 `.raw/<slug>/` 和 `assets/<slug>/`，不再生成 `papers/<slug>.md`。
- **笔记体检。** `--check-note --fix` 修复常见的图片问题，包括“在原来的机器上能看、换个目录就全挂”的相对路径。
- **首次使用引导。** `--setup` 询问语言、编程环境、指令风格、浏览器策略、精读深度和引用格式，写入 `.geo-reader/profile.json`，供 `AGENTS.md` 读取。
- **打包修复。** `scripts/` 现在是正式包，提供 `geo-reader`、`geo-doctor`、`geo-setup` 三个入口。

---

## 环境要求

- Python **3.9+**
- `requests`、`beautifulsoup4`、`pypdf`、`websockets`（安装脚本会自动处理）
- **Google Chrome / Chromium / Microsoft Edge**：强烈建议安装，用于高清图和 JavaScript 渲染页面
- 可选：`pymupdf`（`pip install -r requirements-optional.txt`），用于更好的 PDF 图件裁剪与图注匹配

不需要 Node.js、npm，也不需要额外下载无头浏览器。

---

## 快速开始

```bash
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader

# macOS / Linux
./install.sh

# Windows PowerShell
.\install.ps1

# 任意平台，等价写法
python install.py
```

然后运行约一分钟的首次引导：

```bash
python3 main.py --setup
```

Windows 上如果 `python3` 不在 `PATH`，请改用 `python`。

引导会询问：

| 选项 | 可选值 | 作用 |
| :--- | :--- | :--- |
| 输出语言 | `zh-CN`、`en`、`bilingual` | Agent 写笔记使用的语言 |
| 主要环境 | VS Code、Cursor、Claude Code、Antigravity、Windsurf、纯 CLI | 写入偏好与欢迎指南 |
| 指令风格 | `guided`、`balanced`、`expert` | Agent 多久停下来确认一次 |
| 浏览器策略 | `auto`、`existing`、`off` | 自动启动 Chrome、只复用 9222、或完全不用浏览器 |
| 精读深度 | `brief`、`standard`、`deep` | 笔记长度与逐图解读的详细程度 |
| 引用格式 | APA、Nature、GB/T 7714 | 参考文献样式 |

配置保存在 `.geo-reader/profile.json`，本地摘要写入 `.geo-reader/WELCOME.md`。两者都会被 git 忽略。`AGENTS.md` 要求 Agent 在每次任务开始时读取该配置。之后可随时运行 `--reconfigure` 修改。

---

## 日常使用

### 1. 抽取证据包

```bash
# 通过 DOI
python3 main.py --doi "10.1038/s41467-026-69772-8"

# 通过出版社页面
python3 main.py --url "https://www.nature.com/articles/s41467-026-69772-8"

# 本地 PDF（若 PDF 内含 DOI，会尝试去出版社页面取高清图）
python3 main.py --pdf "input_pdfs/my_paper.pdf"

# 批量处理 input_pdfs/ 下的全部 PDF
python3 main.py --batch-pdfs
```

常用选项：

```bash
--browser auto       # 自动启动/复用 Chrome，浏览器优先（默认）
--browser existing   # 只使用已经在 9222 端口运行的 Chrome
--browser off        # 不用浏览器，只走 HTTP/PDF
--wait 6             # 页面加载后多等几秒
--max-figures 20     # 限制下载图件数量
--json               # 输出机器可读的结果
--quiet              # 减少进度输出
```

命令结束时会打印 slug、证据包路径、图件数量、抽取方式（例如 `text=browser; figures=browser`）以及所有警告。

### 2. 让 Agent 写笔记

对 Agent 说：

> 读取 `.raw/<slug>/` 里的证据包，按 `templates/paper_note.md` 写 `papers/<slug>.md`。只使用抽取到的正文和 manifest 中的图注，不要编造公式或结论。图片统一链接到 `../assets/<slug>/fig_XX.png`。最后运行 `--check-note --fix` 和 `--index`。

更多可直接复制的提示词见 [PROMPTS.md](PROMPTS.md)。

### 3. 体检并登记索引

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"
python3 main.py --list
```

`--check-note` 会检查：图片不存在、0 字节、不是有效图片、文件不在 `assets/` 下、相对路径不规范、模板占位内容、夸大措辞、`$$` 数量为奇数。`--fix` 只会在能确定目标时改写图片路径。加上 `--strict` 可以把警告当错误处理。

### 4. 在 VS Code 中预览

- macOS：`Cmd + Shift + V`
- Windows / Linux：`Ctrl + Shift + V`

工作区的 `.vscode/settings.json` 已开启原生 KaTeX 与 GFM 警告框，数学公式不需要额外插件。可选扩展见 [`.vscode/extensions.json`](.vscode/extensions.json)。

---

## 命令一览

```text
python3 main.py --setup                 首次使用引导
python3 main.py --reconfigure           修改偏好
python3 main.py --doi DOI               按 DOI 抽取
python3 main.py --url URL               按文章网页抽取
python3 main.py --pdf PATH              按本地 PDF 抽取
python3 main.py --batch-pdfs            批量处理 input_pdfs/
python3 main.py --check-note [NOTE]     检查单篇笔记，或检查 papers/*.md
python3 main.py --index NOTE            在 papers/INDEX.md 中新增/更新一行
python3 main.py --list                  列出证据包与笔记
python3 main.py --guide                 打印快速上手
python3 main.py --doctor                环境自检
python3 main.py                         交互式菜单（终端中）
```

执行 `pip install -e .` 后，还可以直接使用 `geo-reader`、`geo-doctor`、`geo-setup`。

---

## 工作区结构

```text
geo-academic-reader/
├── AGENTS.md                     Agent 行为契约、SOP 与写作红线
├── PROMPTS.md                    可直接复制的提示词
├── README.md / README.zh-CN.md
├── input_pdfs/                   原始 PDF 收件箱
├── papers/
│   ├── INDEX.md                  面向人的文献索引
│   └── <slug>.md                 Agent 撰写的精读笔记
├── assets/<slug>/fig_XX.png      笔记引用的本地图片
├── .raw/<slug>/                  证据包（git 忽略）
│   ├── paper.json
│   ├── fulltext.md
│   ├── figures/manifest.json
│   └── README.md
├── .geo-reader/                  本地偏好与 Chrome 配置（git 忽略）
├── templates/
│   ├── paper_note.md
│   └── literature_review.md
├── rules/                        期刊、Markdown、故障排查参考
├── scripts/                      抽取、体检、引导、CLI
├── main.py                       工作区入口
├── doctor.py                     环境诊断
├── install.py / install.sh / .ps1
└── uninstall.py / uninstall.sh / .ps1
```

### 证据包契约

`paper.json` 包含书目元数据、APA 引用及其来源、抽取方式、开放获取信息、警告、统计信息和其它文件的相对路径。

`fulltext.md` 是原始抽取文本；如果来源是 PDF，会带页码标记。它故意不做润色，因为它是证据，不是摘要。

`figures/manifest.json` 是图件的唯一事实来源：

| 字段 | 含义 |
| :--- | :--- |
| `id` | 稳定编号，如 `fig_01` |
| `label` | 能识别时的图号，如 `Figure 2` |
| `caption` | 网页或 PDF 中的图注 |
| `file` | `assets/<slug>/` 下的文件名 |
| `local_path` | 相对工作区根目录的路径 |
| `markdown_path` | 笔记中应使用的路径：`../assets/<slug>/fig_01.png` |
| `origin` / `download` | `browser`、`http` 或 `pdf`，以及字节的实际获取方式 |
| `method` | 每张图记录的抽取方式 |
| `source_url` | 原始图片 URL（若已知） |
| `page` | PDF 页码（若适用） |
| `width`、`height`、`bytes` | 图片尺寸与大小 |
| `is_body_figure` | 是否更像正文图，而不是页面装饰 |

以 manifest 为准。图注为空时，笔记应明确写“原文未提供图注”，不要替作者编标题。

---

## 图件与 VS Code 预览排查

“VS Code 预览里图片不显示”最常见的原因，是路径对某个文件有效、对另一个文件无效，例如在 `papers/<slug>.md` 里写了 `./assets/...` 或 `/Users/you/...`。笔记位于 `papers/`，正确写法是：

```markdown
![图 1：图注](../assets/<slug>/fig_01.png)
```

运行：

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
```

它会确认文件存在、非空、magic bytes 是有效图片，并且相对路径解析为 `../assets/<slug>/...`。如果图片缺失，但 `assets/` 下恰好只有一个同名文件，`--fix` 会改写链接；有多个候选时不会乱猜。

其它检查：

- 确认 `assets/<slug>/fig_01.png` 是真正的图片，而不是扩展名为 `.png` 的 HTML 错误页。
- 预览是旧的时候，在命令面板运行 **Markdown: Refresh Preview**。
- 从工作区根目录打开笔记，避免相对路径歧义。

---

## 范围与限制

- **这是访问辅助，不是绕过授权。** 浏览器优先使用的是你本机 Chrome 已有的会话，用于渲染页面和获取该会话本来就能访问的图片，不绕过付费墙或访问控制。请遵守出版社条款与所在机构的订阅许可。
- **Cloudflare / 人机验证。** 管线会等待并重试，但无法保证通过交互式验证。若被拦住，可以在启动的 Chrome 窗口里手动完成验证，再用 `--browser existing` 重试。
- **不是所有图都能拿到。** 有些出版社用专有阅读器加载图件，或只放在补充材料里，或图注结构特殊导致匹配失败。manifest 的 warnings 会说明失败原因。
- **PDF 只是回退。** 使用 `pypdf` 时，内嵌图可能分辨率低且缺少图注；安装 `pymupdf` 后可按图注邻近关系裁剪并提高渲染分辨率。没有文本层的扫描版 PDF 不会自动 OCR。
- **元数据可能不完整。** 刚上线的 DOI 可能还没进 Crossref；自动构造的 APA 会在 `paper.json` 里标明来源。
- **脚本不写综述。** 如果 `papers/<slug>.md` 不存在，这是正常的：Agent 还没写。

出版社适配细节见 [rules/JOURNALS.md](rules/JOURNALS.md)，故障处理见 [rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md)。

---

## 环境诊断

```bash
python3 main.py --doctor
# 或
python3 doctor.py
python3 doctor.py --json
python3 doctor.py --install
python3 doctor.py --launch-chrome
```

诊断内容包括 Python 版本、必需与可选依赖、Chrome 与 9222 状态、已保存的偏好、`.vscode/settings.json` 和工作区目录。

---

## 清理与卸载

```bash
# 卸载包与本地构建缓存
python3 uninstall.py

# 连同依赖和 .venv 一起清理
python3 uninstall.py --purge --yes
```

卸载不会删除你的 `papers/`、`assets/` 和 `.raw/` 内容。

---

## 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
