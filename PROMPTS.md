# PROMPTS — 可直接复制的指令

这个文件不是“咒语大全”，而是一组**带约束的任务描述**。核心原则只有一条：先要证据，再要解读；没有证据的地方，明确写“原文未提供”。

> 首次使用请先运行 `python3 main.py --setup`。Agent 会读取 `.geo-reader/profile.json` 中的语言、风格和深度。

---

## 0. 开始之前：一句话确认工作区状态

```text
先运行 python3 main.py --list，告诉我当前有哪些证据包和笔记。
如果 .geo-reader/profile.json 不存在，先提示我运行 python3 main.py --setup，不要直接开始抽论文。
```

---

## 1. 单篇精读（DOI）

```text
精读 DOI 10.1038/s41467-026-69772-8。

要求：
1. 先运行 python3 main.py --doi "10.1038/s41467-026-69772-8" 生成证据包；优先浏览器高清图，不要先抽 PDF 图。
2. 读取 .raw/<slug>/paper.json、fulltext.md、figures/manifest.json。
3. 按 templates/paper_note.md 写 papers/<slug>.md。
4. 图片只用 ../assets/<slug>/fig_XX.png，图注必须来自 manifest。
5. 不要编造公式、数据、结论；证据不足写“原文未提供”。
6. 最后运行 --check-note --fix 和 --index，并把 warnings 原样告诉我。
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
按“路径错误 / 文件缺失 / 文件损坏 / 模板残留 / 夸大措辞”分类，先修最影响阅读的。
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
- 图片路径必须是 ../assets/<slug>/fig_XX.png；图注来自 manifest。
- 不写“颠覆一切”“彻底终结”“完美解决”“前所未有”等措辞。
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
| “图片随便放 assets 里” | 路径不一致导致预览失败 | “统一用 ../assets/<slug>/fig_XX.png，跑 --check-note” |
| “补几篇相关文献” | 容易产生不存在的引用 | “只使用工作区内已抽取的论文，或明确标注待补检索” |

---

## English quick prompts

**Single paper by DOI**

```text
Read DOI 10.1038/s41467-026-69772-8.

1. Run `python3 main.py --doi "10.1038/s41467-026-69772-8"` first. Prefer browser-extracted high-resolution figures; do not start from PDF figures.
2. Read `.raw/<slug>/paper.json`, `fulltext.md`, and `figures/manifest.json`.
3. Write `papers/<slug>.md` using `templates/paper_note.md`.
4. Use only `../assets/<slug>/fig_XX.png` for images, with captions from the manifest.
5. Do not invent formulas, data, or conclusions. Write "not provided" when evidence is missing.
6. Finish with `--check-note --fix` and `--index`, and report all warnings.
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
