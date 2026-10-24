# PROMPTS — 可直接复制的指令

这个文件不是“咒语大全”，而是一组**带约束的任务描述**。核心原则只有一条：先要证据，再要解读；没有证据的地方，明确写“原文未提供”。

> **首次使用不需要运行设置脚本。** 在这个工作区里直接对 Agent 说 `开始使用`。Agent 会先用几个问题了解语言、环境、指令风格、浏览器策略、精读深度和引用格式，然后自己写入 `.geo-reader/profile.json`。以后每次任务都会沿用这份偏好；想修改时说 `重新设置偏好`。

---

## 0. 首次使用：一句话触发对话式引导

```text
开始使用。请先按 AGENTS.md 第 0 节和我确认偏好，再告诉我下一步可以做什么。
不要让我运行 --setup 之类的设置命令。
```

如果跳过引导、直接给论文，Agent 也必须先完成引导：

```text
精读 DOI 10.1038/s41467-026-69772-8。
如果 .geo-reader/profile.json 不存在，先用对话问我偏好并保存，再开始抽论文。
```

修改偏好：

```text
重新设置偏好。保留 .geo-reader/profile.json 里的 created_at，更新后告诉我有哪些变化。
```

---

## 1. 单篇精读（DOI）

```text
精读 DOI 10.1038/s41467-026-69772-8。

要求：
1. 先运行 python3 main.py --doi "10.1038/s41467-026-69772-8" 生成证据包；优先浏览器高清图，不要先抽 PDF 图。
2. 读取 .raw/<slug>/paper.json、fulltext.md、figures/manifest.json。
3. 按 templates/paper_note.md 写 papers/<slug>.md。
4. 图片只用 assets/<slug>/fig_XX.png，图注必须来自 manifest。
5. 不要编造公式、数据、结论；证据不足写“原文未提供”。
6. 把本文放进引用网络：写“文献坐标”表，至少 10 篇外部文献（每个都有 DOI），并单列竞争解释与后续检验。
7. 最后运行 --check-note --fix 和 --index，并把 warnings 原样告诉我。
```

---

## 1b. 经典文献深读（必须多篇对话）

```text
把 <DOI / URL / PDF> 当作一篇经典文献来读，不要只写单篇摘要。

要求：
1. 仍然是先抽证据包、再写笔记；锚定论文的每个结论都要有证据锚点。
2. 找到它的前史（它在回应谁）、同期竞争解释（至少两种）、以及发表后的检验或修正。
3. 在“文献坐标”里给出至少 5 行的引用表：年份 | 工作 | 核心贡献 | 与本文的关系。
4. 外部文献不少于 10 篇，每篇给 DOI；无法核验的条目标注“自动构造，需核对”。
5. 明确写出：本文的证据足以排除哪些竞争解释、不足以排除哪些。不要把“没有讨论”写成“已经排除”。
6. 如果某一段文献你查不到，直接说“这部分检索未覆盖”，不要用没读过的条目凑数。
7. 完成后运行 --check-note --fix；如果报 thin_reference_context，补齐文献而不是降低 note_depth。
```

---

## 2. 单篇精读（网页 URL）

```text
精读这篇论文：<URL>

先判断页面是否需要登录或人机验证。需要时用 --browser auto 启动 Chrome，并在警告里说明。
抽取完成后按模板写笔记。重点回答：作者的问题是什么、证据链是否闭合、哪张图支撑哪个结论、局限在哪里。
```

---

## 3. 只拿到 PDF

```text
精读 input_pdfs/<文件名>.pdf。

先抽取 PDF 文本和 DOI。如果 PDF 里有 DOI，优先用浏览器去出版社页面取高清图；只有浏览器失败时才用 PDF 内嵌图，并在笔记的“本文与证据包”一节说明图片来源。
如果 PDF 没有 DOI，明确告诉我：图件来自 PDF 内嵌位图，可能缺少图注。
```

批量：

```text
批量精读 input_pdfs/ 下的所有 PDF。

对每篇：
1. 运行 python3 main.py --pdf "<路径>"；
2. 写 papers/<slug>.md；
3. 运行 --check-note --fix 和 --index。

最后给我一张表：标题、年份、期刊、文本来源、图片来源、图件数、失败原因。
不要把所有全文一次性读进上下文；逐篇处理，每篇只保留结论和证据锚点。
```

---

## 4. 审稿式精读（更批判）

```text
按“审稿人”视角重读 papers/<slug>.md 和对应的 .raw/<slug>/ 证据包。

输出：
1. 作者的核心主张与最强证据；
2. 证据链中缺失的环节；
3. 方法假设、边界条件、参数敏感性；
4. 图表是否真的支持正文结论；
5. 如果需要复核，最值得先做的 3 个实验/观测。

不要重写整篇笔记；只给出一份可执行的修改清单。
```

---

## 5. 图片不显示 / 笔记体检

```text
运行 python3 main.py --check-note "papers/<slug>.md" --fix，然后：
1. 把仍存在的 error 逐条解释；
2. 检查对应文件是否真的是图片（magic bytes），而不是 HTML 错误页；
3. 不要为了“让预览变绿”而删除有问题的图；找不到就明确标注缺失。
```

检查全部笔记：

```text
运行 python3 main.py --check-note --fix，汇总所有 error 和 warning。
按“路径错误 / 文件缺失 / 文件损坏 / 模板残留 / 夸大措辞 / GitHub 告警语法 / 引用网络不足”分类，先修最影响阅读的。
```

---

## 6. 多篇综述

```text
围绕“<主题>”做一篇文献综述。

先用 python3 main.py --list 查看已有证据包；只使用工作区内已抽取的论文，不要凭记忆补文献。
按 templates/literature_review.md 写作，要求：
- 明确检索与纳入标准；
- 区分共识、争议和证据强度；
- 每篇论文给出 DOI 与本地笔记链接；
- 证据不足的地方标注“待补检索”。
```

---

## 7. 维护索引与知识库

```text
检查 papers/ 下所有笔记：
1. 缺少 YAML front matter 的，按模板补齐 title/journal/year/doi/source；
2. 运行 --index 逐篇登记；
3. 报告 papers/INDEX.md 中重复、缺失或 DOI 不一致的行。
不要改写笔记正文。
```

---

## 8. 给 Agent 的硬约束（可附加到任何任务）

```text
工作区硬约束：
- 脚本只产出证据包；综述和笔记由你写，但只能基于 .raw/<slug>/ 中的证据。
- 禁止通用段落、示例公式、与本文无关的模板化结论。
- 每个关键结论后标注证据锚点：PDF 用（第 N 页），网页用（原文第 N 段/节）。
- 图片路径必须是 assets/<slug>/fig_XX.png（在 papers/ 内）；图注来自 manifest。
- 不写“颠覆一切”“彻底终结”“完美解决”“前所未有”等措辞。
- 经典文献不是单篇摘要：brief ≥3、standard ≥6、deep ≥10 篇外部文献，综述 ≥15 篇；每条外部文献给 DOI。
- 引用表至少 5 行，必须写竞争解释与后续检验；不要只列支持本文的工作。
- 不要用 > [!NOTE] 这类 GitHub 告警语法，VS Code 不渲染它；用 > **一句话结论** 加引用块。
- 交付前必须运行 --check-note --fix，再运行 --index。
- 如果正文少于 800 字符、图片为 0、或浏览器被人机验证拦截，先报告，不要硬写。
```

---

## 9. 常见误用

| 不要这样说 | 为什么 | 改成 |
| :--- | :--- | :--- |
| “帮我总结这篇论文” | 容易得到泛泛而谈的摘要 | “先抽证据包，再按模板写，逐图给证据锚点” |
| “把 PDF 里的图都截出来” | 位图可能低清、缺图注 | “PDF 有 DOI 时优先浏览器取高清图” |
| “公式写得漂亮一点” | 会诱发编造公式 | “只写原文出现的公式，并标页码” |
| “图片随便放 assets 里” | 路径不一致导致预览失败 | “统一用 assets/<slug>/fig_XX.png，跑 --check-note” |
| “补几篇相关文献” | 容易产生不存在的引用 | “只使用工作区内已抽取的论文，或明确标注待补检索” |
| “只读这一篇，别扯别的” | 经典文献的价值在它和谁对话 | “写文献坐标：前史、竞争解释、后续检验，至少 10 篇外部文献” |
| “文献数量凑够就行” | 装饰性引用比没有引用更糟 | “只写你真正读过的；读不全就说明缺哪一块” |

---

## English quick prompts

**First run (conversational onboarding)**

```text
Start. Follow AGENTS.md section 0: ask me about language, editor, instruction style,
browser policy, note depth, and citation format, then save .geo-reader/profile.json.
Do not ask me to run a setup script.
```

**Reconfigure**

```text
Reconfigure my preferences. Keep created_at in .geo-reader/profile.json and tell me what changed.
```

**Single paper by DOI**

```text
Read DOI 10.1038/s41467-026-69772-8.

1. Run `python3 main.py --doi "10.1038/s41467-026-69772-8"` first. Prefer browser-extracted high-resolution figures; do not start from PDF figures.
2. Read `.raw/<slug>/paper.json`, `fulltext.md`, and `figures/manifest.json`.
3. Write `papers/<slug>.md` using `templates/paper_note.md`.
4. Use only `assets/<slug>/fig_XX.png` for images, with captions from the manifest.
5. Do not invent formulas, data, or conclusions. Write "not provided" when evidence is missing.
6. Place the paper in its citation network: a citation table (>=5 rows), at least 10 external works with DOIs for a deep read, plus competing explanations and later tests.
7. Finish with `--check-note --fix` and `--index`, and report all warnings.
```

**Batch PDFs**

```text
Process every PDF in `input_pdfs/`, one at a time:
extract evidence, write the note from the template, run `--check-note --fix`, then `--index`.
At the end, return a table with title, year, journal, text source, figure source, figure count, and failures.
Keep each paper's full text out of the parent context.
```

**Fix preview images**

```text
Run `python3 main.py --check-note "papers/<slug>.md" --fix`.
Explain every remaining error, verify that each file is a real image (magic bytes), and mark genuinely missing figures instead of deleting them.
```
