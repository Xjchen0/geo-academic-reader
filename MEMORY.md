# MEMORY — 长期有效的决定

> 这是本工作区的长期记忆。Agent 每次会话必须先读 `AGENTS.md`，再读这一份，然后运行
> `python3 main.py --preflight`。这里只记录**跨版本仍然成立**的决定，不写流水账；
> 新的长期决定追加到对应小节，并在 `LESSONS.md` 记录它是怎么来的。

---

## 1. 两种文件夹，两种角色（P0）

同一个仓库可以以两种形态存在，行为不同：

| 角色 | 判定 | 允许的内容 | 不应该出现 |
| :--- | :--- | :--- | :--- |
| **代码仓库** | 没有 `.geo-reader/profile.json`，`papers/` 没有笔记，`.raw/` 没有证据包 | 代码、模板、文档、`journals.json`、空的 `papers/` 与 `papers/assets/` | 偏好、笔记、图片、证据包、投放的 PDF |
| **测试 / 使用工作区** | 上述任意一项存在 | 代码 + 本地偏好 + 笔记 + 图片 + 证据包 + `input_pdfs/` | — |

- 角色由 `python3 main.py --preflight` 自动判定（`Role: code repository` / `test workspace`），不要靠目录名猜。
- **测试产物不进入代码仓库**：`papers/*.md`、`papers/assets/*`、`input_pdfs/*.pdf`、
  `reading_list_*.md`、`.raw/`、`.geo-reader/` 都在 `.gitignore` 里。
- 代码仓库里只保留 `papers/.gitkeep` 与 `papers/assets/.gitkeep`，让目录结构可见但不携带数据。
- 要发布或提交代码时，先确认 `--preflight` 显示的是 `code repository`；在测试工作区里提交，
  只会把用户数据混进发布物。
- 升级只替换代码与文档，从不写入 `papers/`、`.raw/`、`.geo-reader/`、`input_pdfs/`。

## 2. 会话契约（P0）

1. 读 `AGENTS.md` → `MEMORY.md` → `LESSONS.md`。顺序不要颠倒：契约 → 决定 → 教训。
2. 运行 `python3 main.py --preflight`，与用户确认操作系统、Python、依赖、Chrome、编辑器。
3. 使用文献命令（`--doi`、`--url`、`--pdf`、`--batch-pdfs`、`--new-literature`、`--check-note`、`--index`）
   前，preflight 标记必须存在、版本一致、且不超过 24 小时。
4. 标记缺失或过期时 CLI 以退出码 2 拒绝执行。修复方式是**重新做检查**，不是绕过检查。
5. `--no-preflight` / `GEO_READER_SKIP_PREFLIGHT=1` 是逃生口，只在用户明确要求跳过时使用，
   并在回复里说明跳过了什么。
6. 标记只能证明“检查跑过”，不能证明“文档读过”。不要把标记当成读过 `AGENTS.md` 的借口；
   也不要为了通过检查而伪造 `preflight.json`。

## 3. 证据与解释分离（P0）

- 脚本只产出 `.raw/<slug>/`（`paper.json`、`fulltext.md`、`figures/manifest.json`）与图片；
  **脚本永远不写综述文字**。
- 笔记由 Agent 写，每个关键结论带证据锚点：PDF `（第 N 页）`，网页 `（原文 §节 第 N 段）`，图 `（图 N）`。
- 证据不足就写“原文未提供”，不要用通用段落、示例公式或模板结论补齐。
- `figures/manifest.json` 是图注与图件来源的唯一权威；笔记不能比 manifest 更自信。
- 浏览器优先：有网页版就打开；只有网页失败时才回退 HTTP/PDF，并在笔记与 manifest 中标注 `pdf`。

## 4. “找新文献”是页面清单，不是主题检索（P0）

- 只打开 `journals.json` / `.geo-reader/journals.json` 里配置的期刊页面。
- 不用 OpenAlex / WebSearch 按主题“补”列表，不从现有笔记或对话推断用户想看什么。
- 扫描后只呈现编号候选（英文原题 + 中文机译标题 + 期刊 + 日期 + DOI），然后停止；
  用户给出编号或 DOI 之前，不建证据包、不写笔记。
- 中文标题是机器翻译，仅供检索；英文原题才是准据。翻译失败写“暂缺”，不要编。
- 人机验证交给用户在打开的 Chrome 窗口完成；脚本不自动刷新。

## 5. 经典文献 = 引用网络（P0）

- `## 0. 文献坐标` 必须有 ≥5 行表：`年份 | 工作 | 核心贡献 | 与本文的关系`。
- 必须有**竞争解释**（≥2 种，写清各自判据）与**后续检验**（没查就写“检索未覆盖”）。
- 外部文献下限：`brief` 3、`standard` 6、`deep` 10、`经典文献综述` 15；锚定论文不计入。
- 每条外部文献给 DOI 或稳定链接；无法核验的标注“自动构造，需核对”。
- 数量是下限，不是目标。没读过的条目不许用来凑数。

## 6. 图片与 Markdown（P0）

- 图片只放在 `papers/assets/<slug>/`，笔记里只写 `assets/<slug>/fig_XX.png`。
- 禁止 `../assets/`、`./assets/`、绝对路径、`file://`、`<img>`。
- 提示块用带粗体标签的引用块（`> **一句话结论**`），不用 GitHub 告警语法
  （`> [!NOTE]` 在 VS Code 内置预览里只是普通文字）。
- 公式只写原文出现过的；`$$` 必须成对。

## 7. 发布与更新（P0）

- 版本以 `scripts/version.py` 为唯一来源；补丁修复升 patch，新能力升 minor。
- 标签不复用。预发布标签形如 `v0.4.0-pre`、`v0.4.0-pre.1`。
- `0.4.0-pre` 系列是在 `0.4.0` 之后发布的预览版，PEP 440 会把它们排在 `0.4.0` 之下。
  每新增一个这样的标签，都要在 `updater.POST_RELEASE_PREVIEWS` 补一条映射：
  稳定通道不提示“回退”，预发布通道按发布时间而不是版本号选最新。
  下一个正式版应从 `0.4.1` 或 `0.5.0` 起。
- 更新只覆盖 `UPGRADE_PATHS` 白名单；`.geo-reader/profile.json` 先备份后恢复。
- 工作树有未提交的**代码**改动或历史分叉时拒绝更新，绝不 `reset --hard`，绝不 force push。
- 发布前必须：`py_compile`、完整测试、`--check-note --fix`（若有笔记）、`--index`。
- 控制台输出属于契约的一部分：stdout/stderr 强制 UTF-8，控制台标记只用 ASCII，
  `subprocess.run(text=True)` 一律显式 `encoding="utf-8"`。中文 Windows 的管道默认是 cp936，
  不做这三件事，Agent 读到的是乱码，QA 报告甚至会直接崩在 emoji 上。

## 8. 本地数据

- `.geo-reader/` 与 `.raw/` 是本地的，被 git 忽略；`papers/` 是自包含的知识库。
- 用户偏好跨会话、跨版本保留；不要因为代码更新就删除或重建 `profile.json`。
- 期刊清单：`journals.json` 是出厂默认，`.geo-reader/journals.json` 是个人副本，更新时保留。

## 9. 什么时候改这份文件

- 当一个决定会影响**下一次会话**或**下一次发布**时，写进来。
- 当一个错误值得让所有后续 Agent 避免时，先写 `LESSONS.md`，再决定要不要提炼成这里的规则。
- 不要在这里记录一次性任务、临时路径、当天心情或未经验证的猜测。
