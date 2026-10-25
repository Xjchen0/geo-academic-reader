# Note Writing Style

The note is read by two people at once: a colleague who knows the field, and a student who
entered it last month. The style has to serve both. That means **plain academic prose with
research logic and a little tutorial patience** — never jargon as a substitute for explanation,
never enthusiasm as a substitute for evidence.

This is a contract, not a suggestion. `--check-note` enforces the mechanical part (no hype words,
a labelled opening takeaway); the rest is the agent's judgement.

---

## 1. The four requirements, in one line each

| Requirement | What it means | What it forbids |
| :--- | :--- | :--- |
| **平实** (plain) | Every term is explained the first time it appears; every number carries its unit and condition | An acronym used three times before it is defined; adjectives standing in for numbers |
| **逻辑** (logical) | Question → evidence → mechanism → boundary, in that order, with the joins visible | A results list with no argument; a conclusion that appears before its support |
| **教程** (tutorial) | A newcomer can follow the argument and learn the vocabulary of the subfield | Assuming the reader knows the field's shorthand, its standard figures, its standard controversies |
| **克制** (restrained) | Claims are bounded; unknowns are named | Superlatives, "this settles it", confidence the evidence does not carry |

The four pull against each other. Tutorial patience can become padding; plainness can become
vagueness; restraint can become timidity. Resolve it this way: **explain more, claim less.**
A paragraph may be long if it is doing work; it may never be long because it is hedging.

---

## 2. 平实 — plain

**Define on first use.** The standard form is Chinese term, English in parentheses, one clause of
meaning:

> 海洋型冰盖失稳（marine-based ice sheet instability, MISI）指接地线退到地形向海一侧后无法再稳住。

The same term may be shortened afterwards. Do not define it again.

**Numbers carry units, conditions and error bars.**

- Not: "模拟分辨率很高" → "水平分辨率 16 km，垂向 10 层，摩擦系数由现代冰厚与冰速反演"。
- Not: "误差在 0.3 K 以内" → "RSB 的 R-tipping 间隙最大 0.3 K（±2σ 黏度集合，累计间隙最大 0.5 K）"。

**Replace adjectives with measurements.** "非常负的反馈"、"显著的差异" → the actual number or
the actual comparison.

**Keep sentences short enough to check.** If a sentence has more than one "而且" or "但是", split
it. Chinese scientific prose that reads well in a paper often reads badly in a note because the
note has to be *read*, not skimmed.

**Say what you did not find.** "检索未覆盖"、"原文未提供" is a complete and honest answer. A
guessed value is not.

---

## 3. 逻辑 — research logic

Every section of a note answers one question, and the reader can say which:

| Section | Question it answers |
| :--- | :--- |
| `## 0. 文献坐标` | Where does this work sit in the field's conversation? |
| `## 1. 科学问题与假说` | What did the authors claim, and on what assumptions? |
| `## 2. 数据与方法` | What was measured or simulated, and how? |
| `## 3. 结果与图表逐图解读` | What was found, and what does each figure actually show? |
| `## 4. 机制与讨论` | How do the pieces connect, and where is the chain weakest? |
| `## 5. 局限性与不确定性` | Under what conditions does the conclusion stop holding? |

Two rules make the logic visible:

1. **Mark the strength of each link.** 【直证】 (in the paper), 【转述】 (second-hand),
   【推断】 (the authors' inference), 【评估】 (your judgement), 【未核实】 (not checked).
2. **Never let a conclusion float free of its support.** The sentence before a claim names where
   the claim comes from: "图 3f 的抬升亏缺超过 100 m（原文 §R-tipping …）"。

**Distinguish the three voices.** The paper's finding, the authors' inference, and your own
assessment must be visibly different. A note that merges them reads as confident and is not.

---

## 4. 教程 — a little tutorial patience

The reader may be new to the subfield. Three habits make the difference:

**Give the vocabulary once, in context.** The first time a field-specific term appears, say what
it is and why it matters — not in a glossary at the end, but where it is needed.

**Tell the reader how to look at a figure.** A `> **读图要点**` block does more than describe axes;
it says what to notice and what the figure *cannot* settle:

> 该图支持的是"机制假说本身"，不是任何数值结论；它不支持"西边更危险"，恰恰相反。

**Give the shortest path through a result.** After a dense paragraph, one sentence is often enough:
"换句话说，黏度决定了岩石抬升来不来得及稳住退缩。" That is the tutorial sentence — it costs one
line and it is the line a newcomer is looking for.

**Do not over-explain.** Tutorial means the reader is never lost, not that everything is
re-derived. If the paper's own framing is clear, do not paraphrase it a second time.

---

## 5. 克制 — restraint

**Forbidden** (and checked by `--check-note` as `hyperbole`): 颠覆一切, 彻底终结, 空前重大突破,
完美解决, 前所未有, and similar.

**Required**:

- State boundary conditions: what the conclusion holds *within*.
- State sample limits, parameter sensitivity and model assumptions.
- Distinguish **direct evidence**, **author inference** and **your own assessment** — and label them.
- When the anchor paper cannot rule out a rival explanation, say so: "**不能排除**"。
- When you did not search for later work, write "检索未覆盖" rather than implying none exists.
- In the review section, separate "共识" from "争议" from "证据不足", and say which is which.

**Calibrate the verbs.** "表明" for what the data show, "提示" for what they suggest, "作者认为"
for what the authors claim, "我判断" for what you conclude. Using them interchangeably is how a
note becomes over-confident.

---

## 6. Language details

| Rule | Example |
| :--- | :--- |
| Chinese term first, English in parentheses on first use | 速率诱导倾覆（rate-induced tipping, R-tipping） |
| No author "we" | Write 「作者」or「本文」, never 「我们」 |
| Numbers in Arabic numerals with units | 16 km、0.3 K、2σ、±1.5 m |
| Latin names italic, abbreviations plain | *Nature Geoscience*, MISI, GIA |
| Use the full name at first mention in the reference list | Every entry: authors, year, title, journal, DOI |
| Evidence anchors are part of the sentence | 「…（第 3 页）」not a footnote dumped at the end |
| Use the note's callout labels | `> **一句话结论**`, `> **关键前提**`, `> **读图要点**`, `> **边界条件与未解问题**`, `> **机制链条**`, `> **检索局限**` |

**Mixed-language notes** (`language: bilingual`) keep the English term in parentheses and the
body in the note's main language. Do not write two parallel paragraphs.

---

## 7. A quick self-check before delivery

Run through this before `--check-note`:

1. Could a student in this subfield read the note and follow the argument without outside help?
2. Is every term explained the first time it appears?
3. Does every number have a unit and a condition?
4. Can I point at the support of every strong claim?
5. Are my own assessments marked as mine?
6. Have I named the limits and the unknowns?
7. Is the opening takeaway a labelled blockquote a reader can quote?

If any answer is "no", fix that paragraph before delivering. `--check-note` catches the
mechanical part (hype words, missing opening takeaway, broken figures); it cannot catch a note
that is technically correct and impossible to follow.
