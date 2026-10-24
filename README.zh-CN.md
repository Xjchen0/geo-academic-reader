# geo-academic-reader

[![Version](https://img.shields.io/badge/version-0.4.0--pre.1-blue.svg)](https://github.com/Xjchen0/geo-academic-reader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> 把论文变成可长期维护的 Markdown 知识库，而不是一段会消失的聊天记录。

[English](README.md) | [简体中文](README.zh-CN.md)

geo-academic-reader 是给 AI Agent 用的**文献工作区**：脚本负责打开论文、取正文、下载高清图并记录来源；Agent 负责读证据、写笔记；一条质检命令在交付前检查图片、引用和排版。它面向地球科学、地球物理与地质学，也能处理一般科技论文。

**它适合**：想把精读沉淀成文件、需要引用网络、在意图件质量与可复核性的人。
**它不适合**：只想要一段摘要，或不打算让 Agent 读写本地文件的人。

---

## 30 秒了解

| 步骤 | 谁来做 | 产物 |
| :--- | :--- | :--- |
| 取证 | 脚本 | `.raw/<slug>/`：元数据、带页码的正文、图注清单、来源记录 |
| 解读 | Agent | `papers/<slug>.md`：带证据锚点的文献笔记 |
| 质检 | 脚本 | `--check-note --fix`：图片、模板残留、引用网络、Markdown 兼容性 |
| 沉淀 | 脚本 | `papers/assets/<slug>/` + `papers/INDEX.md`：自包含、可预览、可检索 |

脚本**从不撰写综述文字**。这是刻意的：一个能自动填满每一节的生成器，会让浅层笔记看起来像精读。

---

## 快速开始

```bash
git clone https://github.com/Xjchen0/geo-academic-reader.git
cd geo-academic-reader
./install.sh          # Windows: .\install.ps1   |   任意平台: python install.py
```

用 Agent（VS Code、Cursor、Claude Code、Antigravity、Windsurf 或终端）打开这个文件夹，然后说：

```text
开始使用
```

接下来 Agent 会：

1. 读 `AGENTS.md`、`MEMORY.md`、`LESSONS.md`，不靠猜；
2. 运行 `python3 main.py --preflight`，和你确认操作系统、Python、依赖包、Chrome 与编辑器；
3. 用几个问题了解你的偏好，写入 `.geo-reader/profile.json`；
4. 重跑 preflight，解锁文献命令；
5. 用几行带你认识目录，并给出一个可选的第一次练习。

**没有设置命令，没有向导，对话之前不写任何文件。** 想改偏好时说 `重新设置偏好`。

第一篇论文：

```text
精读 DOI 10.1038/s41467-026-69772-8
```

Agent 会抽取证据包、写笔记、运行 `--check-note --fix` 和 `--index`。可直接复制的提示词见 [PROMPTS.md](PROMPTS.md)。

---

## 首次使用：Agent 会和你确认什么

### 1. 环境：先确认，再动手

`python3 main.py --preflight` 输出一份清单，Agent 会用自然语言和你逐项确认：

| 检查项 | 正常 | 缺失时 |
| :--- | :--- | :--- |
| 契约文档 | `AGENTS.md`、`MEMORY.md`、`LESSONS.md` 都在 | 停下，从发布包恢复；不写空壳文件 |
| 系统与 Python | Python ≥ 3.9 | 给出升级路径，不继续 |
| 依赖包 | `requests`、`beautifulsoup4`、`pypdf`、`websockets` | 给出确切 `pip install` 命令，**问过你才装** |
| 浏览器 | Chrome / Chromium / Edge，CDP 9222 可选 | 询问安装浏览器，或接受 HTTP/PDF 回退（图件质量较低） |
| 编辑器 | 偏好里的编辑器，`.vscode/settings.json` | 提示如何创建，不擅自修改 |
| 工作区角色 | `code repository` 或 `test workspace` | 说明这个文件夹会不会携带本地数据 |

preflight 会写一个 **24 小时有效、与版本绑定** 的标记 `.geo-reader/preflight.json`。`--doi`、`--url`、`--pdf`、`--batch-pdfs`、`--new-literature`、`--check-note`、`--index` 都需要它；缺失或过期时 CLI 以退出码 2 拒绝执行。修复方式是重新检查，不是绕过。

> **为什么要有这道闸**
>
> Agent 很容易直接敲命令、跳过契约文档。标记让“没做检查”变成一次明确失败，而不是悄悄降级。它只能证明检查跑过，不能证明文档读过——所以文档里也写明了：不要伪造标记。

### 2. 偏好：七个问题

| 选项 | 取值 | 影响 |
| :--- | :--- | :--- |
| 语言 | `zh-CN`、`en`、`bilingual` | 笔记与回复语言 |
| 编辑器 | VS Code、Cursor、Claude Code、Antigravity、Windsurf、终端 | 排版约定与预览提示 |
| 指令风格 | `guided`、`balanced`、`expert` | 停下来确认的频率 |
| 浏览器策略 | `auto`、`existing`、`off` | 启动/复用 Chrome，或只用 HTTP/PDF |
| 精读深度 | `brief`、`standard`、`deep` | 一页速览、标准 IMRaD、逐图精读 |
| 引用格式 | `apa`、`nature`、`gbt7714` | 参考文献样式 |
| 期刊清单 | 内置 17 个期刊页面 / 区块，或自定义 | “找新文献”打开哪些页面 |

默认值为 `zh-CN`、VS Code、balanced、auto、deep、APA，期刊清单使用内置 `journals.json`；直接说“用默认值”也可以。偏好保存在本地并被 git 忽略，跨会话、跨版本保留。

### 3. 目录导览：你会用到什么

| 路径 | 作用 | 需要你关心吗 |
| :--- | :--- | :--- |
| `papers/<slug>.md` | 你阅读和引用的笔记 | 是 |
| `papers/assets/<slug>/` | 笔记的图库，与笔记同在 `papers/` 下 | 预览时自动加载 |
| `.raw/<slug>/` | 证据包：元数据、正文、图注、来源 | 复核结论时看 |
| `.geo-reader/profile.json` | 你的偏好 | 想改时让 Agent 改 |
| `.geo-reader/journal-scan/latest.md` | 最近一次“找新文献”的候选清单 | 是 |
| `templates/paper_note.md` | 笔记模板与写作红线 | 想自定义结构时看 |
| `journals.json` | 出厂期刊页面清单 | 一般不用改 |
| `MEMORY.md` / `LESSONS.md` | 长期决定与失败教训 | Agent 每次会读 |

### 4. 第一次练习：三选一

- **找新文献**：打开配置好的期刊页面，列出编号候选（英文原题 + 中文机译标题），然后等你选。
- **精读一篇**：给出 DOI / 链接 / PDF，生成证据包并写一篇笔记。
- **先看目录**：`python3 main.py --list`，了解现有证据包与笔记。

---

## 两个文件夹：代码仓库 vs 测试工作区

同一个仓库可以以两种角色存在。`--preflight` 会自动判定，并在 `Role:` 一行显示：

| 角色 | 判定 | 携带什么 | 不携带什么 |
| :--- | :--- | :--- | :--- |
| **代码仓库** | 无偏好、无笔记、无证据包 | 代码、模板、文档、`journals.json`、空的 `papers/` | 偏好、笔记、图片、证据包、PDF |
| **测试 / 使用工作区** | 上述任意一项存在 | 代码 + 偏好 + 笔记 + 图片 + 证据包 + `input_pdfs/` | — |

- `papers/*.md`、`papers/assets/*`、`input_pdfs/*.pdf`、`reading_list_*.md`、`.raw/`、`.geo-reader/` 都在 `.gitignore` 里。
- 代码仓库只保留 `papers/.gitkeep` 与 `papers/assets/.gitkeep`，目录结构可见，但不携带数据。
- 发布前先看 `Role:`：在测试工作区里提交，会把你的阅读数据混进发布物。
- 升级只替换代码与文档，**从不写入** `papers/`、`.raw/`、`.geo-reader/`、`input_pdfs/`。

**推荐用法**：同一个远程克隆两份。一份保持干净，只用于提交与发布；另一份用于日常阅读和测试。两者共享代码历史，但不共享本地偏好、笔记和证据包。

---

## 日常工作流

### 0. 找新文献：先列清单，然后停下

```bash
python3 main.py --new-literature
python3 main.py --new-literature --journal epsl --journal geology_early
python3 main.py --new-literature --days 3          # 可选：只看最近几天
python3 main.py --new-literature --no-translate    # 只要英文清单
python3 main.py --journals-init                    # 生成可编辑的个人期刊清单
```

扫描用 Chrome/CDP 逐页打开清单里的页面——Nature research-articles、Science First Release / Current、Science Advances、EPSL 卷期、AGU 各刊、Geology 当期与 early publication、GJI、PNAS Earth——按页面自己列出的条目解析标题、DOI 和日期，写到 `.geo-reader/journal-scan/latest.md` 并打印编号候选。

每条候选带一行**中文机译标题**，标明“机译，仅供检索”；英文原题才是准据。翻译缓存按英文标题去重，重跑只翻新条目；翻译失败的条目显示“暂缺”，不会编造。

这一步**只列清单**。Agent 不应在你回复编号或 DOI 之前抽取证据包或写笔记。遇到 Cloudflare 验证，在打开的 Chrome 窗口手动完成，再重跑同一条命令；脚本不会自动刷新。

### 1. 抽取证据包

```bash
python3 main.py --doi "10.1038/s41467-026-69772-8"
python3 main.py --url "https://www.nature.com/articles/s41467-026-69772-8"
python3 main.py --pdf "input_pdfs/my_paper.pdf"
python3 main.py --batch-pdfs
```

常用参数：`--browser auto|existing|off`、`--wait 6`、`--max-figures 20`、`--json`。命令输出 slug、文件路径、图件数量、实际抽取路线（如 `text=browser; figures=browser`）和警告；**不会生成笔记**。

### 2. 写笔记

把证据包和 `templates/paper_note.md` 交给 Agent。典型指令：

> 读取 `.raw/<slug>/`，按 `templates/paper_note.md` 写 `papers/<slug>.md`。只使用抽取到的正文和 manifest 图注；不要编造公式或结论。图片写 `assets/<slug>/fig_XX.png`。关键结论标注页码或章节。把论文放回引用网络：前史、竞争解释、后续检验，每条外部文献给出 DOI。最后运行 `--check-note --fix` 和 `--index`。

### 3. 质检与登记

```bash
python3 main.py --check-note "papers/<slug>.md" --fix
python3 main.py --index "papers/<slug>.md"
python3 main.py --list
```

`--check-note` 检查：图片是否存在、是否为零字节、magic bytes、路径是否在 `papers/assets/` 内、模板残留、夸大措辞、未闭合的 `$$`、GitHub 告警语法，以及引用网络（文献坐标、≥5 行引用表、外部文献数量、DOI 覆盖、重复 DOI）。`--fix` 只在目标明确时改写路径、迁移旧版图库，并把告警标记改成引用块。加 `--strict` 把警告视为错误。

### 4. 检查更新

```bash
python3 main.py --check-update        # 例如 0.3.3 → 0.4.0，或“已是最新”
python3 main.py --update --dry-run    # 只预览目标版本
python3 main.py --update              # 更新，保留现有资料
```

结果缓存 6 小时；访问不了 GitHub 时以退出码 0 结束，不会让一次阅读任务失败。git 仓库用 `git merge --ff-only <tag>`；没有 `.git` 时先浅克隆 + sparse checkout，再回退源码包。工作区有未提交的**代码**改动或历史分叉时拒绝更新，绝不 `reset --hard`。只有明确跟踪预发布时才加 `--prerelease`。

---

## 命令参考

```text
python3 main.py --preflight              契约文档 + 环境 + 偏好 + 工作区角色（写 24h 标记）
python3 main.py --no-preflight ...       本次跳过前置检查（仅在用户明确要求时）
python3 main.py --doi DOI                按 DOI 抽取证据包
python3 main.py --url URL                按文章链接抽取
python3 main.py --pdf PATH               从本地 PDF 抽取
python3 main.py --batch-pdfs             处理 input_pdfs/ 下全部 PDF
python3 main.py --new-literature         打开清单里的期刊页面，只列候选
python3 main.py --journals-init          生成 .geo-reader/journals.json
python3 main.py --check-note [NOTE]      检查单篇或全部笔记
python3 main.py --index NOTE             写入/更新 papers/INDEX.md
python3 main.py --list                   列出证据包与笔记
python3 main.py --profile [--json]       查看当前偏好
python3 main.py --guide                  打印快速上手
python3 main.py --check-update           检查 GitHub 新版本
python3 main.py --update                 更新代码，保留偏好、笔记与证据包
python3 main.py --doctor                 详细环境诊断
python3 main.py                          交互菜单（仅终端）
```

执行 `pip install -e .` 后也可以用 `geo-reader` 和 `geo-doctor`。

---

## 目录结构

```text
geo-academic-reader/
├── AGENTS.md                     Agent 会话契约、引导流程、标准作业程序
├── MEMORY.md                     跨版本有效的长期决定
├── LESSONS.md                    失败模式与修复经验
├── PROMPTS.md                    可复制的任务提示词
├── SKILL.md                      Skill 清单与精简契约
├── journals.json                 出厂期刊页面清单（解析器、URL、卷号）
├── input_pdfs/                   原始 PDF 投放区（本地，git 忽略）
├── papers/                      自包含知识库
│   ├── INDEX.md                  文献目录（本地生成）
│   ├── <slug>.md                 Agent 撰写的笔记
│   └── assets/<slug>/fig_XX.png  图库，与笔记同树
├── .raw/<slug>/                  证据包（本地，git 忽略）
│   ├── paper.json
│   ├── fulltext.md
│   ├── figures/manifest.json
│   └── README.md
├── .geo-reader/                  本地状态（git 忽略）
│   ├── profile.json              偏好
│   ├── preflight.json            会话标记（24h）
│   ├── journals.json             个人期刊清单（优先于出厂清单）
│   └── journal-scan/
│       ├── latest.md             最近一次编号候选清单
│       └── translations.json     中文标题缓存
├── templates/                    笔记与综述模板
├── rules/                        Markdown、期刊、排错参考
├── scripts/                      抽取、质检、preflight、CLI
├── main.py / doctor.py           工作区入口 / 环境诊断
└── install.* / uninstall.*
```

### 证据包契约

`paper.json`：书目元数据、APA 字符串及是否自动构造、抽取方式、开放获取信息、警告、统计与相对路径。
`fulltext.md`：带页码标记的原始抽取文本，是证据，不是摘要。
`figures/manifest.json`：图注与图件的唯一权威来源。

| 字段 | 含义 |
| :--- | :--- |
| `id` / `label` | 稳定标识（`fig_01`）与图号标签（`Figure 2`） |
| `caption` | 页面或 PDF 中的图注；为空时笔记必须如实说明 |
| `file` / `local_path` | 本地文件与相对工作区路径 |
| `markdown_path` | 笔记中使用的路径：`assets/<slug>/fig_01.png` |
| `origin` / `download` | `browser`、`http` 或 `pdf`，以及字节获取方式 |
| `source_url` / `page` | 原始图片地址与适用页码 |
| `width` / `height` / `bytes` | 尺寸与体积 |
| `is_body_figure` | 是否像正文图而非页面装饰 |

---

## 经典文献要放进引用网络

只复述一篇 PDF 的“经典文献精读”不是精读，是读书报告。每篇笔记都要有 `## 0. 文献坐标`：一张 `年份 | 工作 | 核心贡献 | 与本文的关系` 表、一段明确的**竞争解释**、一段**后续检验**。

| `note_depth` | 外部文献下限 | 典型用途 |
| :--- | :--- | :--- |
| `brief` | 3 | 一页速览 |
| `standard` | 6 | 默认单篇笔记 |
| `deep` | 10 | 经典文献深读 |
| `note_type: 经典文献综述` | 15 | 多篇综述 |

锚定论文本身不计入外部文献；只有 `## 参考文献` 下的条目才计数，每条尽量给 DOI。文献读不全就写清楚缺哪一块，不要为了凑数塞入没读过的条目。

---

## 图片路径与 VS Code 预览

VS Code 内置 Markdown 预览只允许从工作区目录加载本地图片；单文件窗口下只允许笔记所在目录。因此图库必须放在 `papers/` 内：

```markdown
![图 1：图注](assets/<slug>/fig_01.png)
*图 1：图注（来源：browser；原始链接：https://...）*
```

QA 会拒绝 `../assets/...`、`./assets/...`、绝对路径、`file://` 和 `<img>`。提示块使用 `> **一句话结论**` 这类带标签的引用块，因为 VS Code 不渲染 GitHub 的 `> [!NOTE]` 语法。

---

## 常见问题

| 现象 | 原因 | 处理 |
| :--- | :--- | :--- |
| 文献命令退出码 2 | preflight 标记缺失、过期或版本不符 | 运行 `python3 main.py --preflight`；不要用 `--no-preflight` 绕过 |
| 标记显示 `profile_missing` | preflight 早于偏好写入 | 完成引导、写入 profile，再重跑 preflight |
| `--preflight` 说文档缺失 | `AGENTS.md` / `MEMORY.md` / `LESSONS.md` 不在 | 从发布包恢复，不要写空壳 |
| 找不到 Chrome | 浏览器优先不可用 | 安装 Chrome，或接受 `--browser off` 与 PDF 回退 |
| Cloudflare 验证 | 需要人工确认 | 在打开的 Chrome 窗口完成验证，再重跑，脚本不自动刷新 |
| 图件为 0 | JS 查看器、付费墙或选择器失效 | 看 manifest 警告；重试 `--browser auto`；仍失败就如实报告 |
| 正文 < 800 字符 | 摘要页或付费墙 | 检查 `fulltext.md`，改用 OA PDF 或 `--url`，不要凭摘要写整篇 |
| 预览不显示图片 | 路径不在 `papers/` 内 | `--check-note --fix`；正确形式是 `assets/<slug>/...` |
| `thin_reference_context` | 只写了单篇摘要 | 补前史、竞争解释与后续检验，或降低 `note_depth` |
| `--check-update` 离线 | GitHub 不可达 | 不是错误；稍后 `--refresh`，或设 `GEO_READER_NO_UPDATE_CHECK=1` |
| `--update` 拒绝 | 有未提交的代码改动或历史分叉 | 提交或 `git stash`；绝不 `reset --hard` |
| 期刊列表为空 | 页面停用、解析器不匹配或卷号前进 | 检查 `enabled` / `url`；EPSL 更新 `volumes`；必要时修 `parser` |
| 中文标题“暂缺” | 翻译限流或服务不可用 | 重跑 `--new-literature`；缓存会复用已译条目，不要编造 |

更多：[rules/TROUBLESHOOTING.md](rules/TROUBLESHOOTING.md)、[rules/JOURNALS.md](rules/JOURNALS.md)、[LESSONS.md](LESSONS.md)。

---

## 诊断与清理

```bash
python3 main.py --preflight     # 会话契约 + 环境 + 偏好 + 工作区角色
python3 main.py --doctor        # 详细诊断
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
