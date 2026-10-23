# VS Code Markdown & KaTeX Specification

This document details the typography, mathematics, and layout specifications required to achieve optimal visual quality in modern VS Code Markdown Preview.

---

## 1. Mathematical Formulas (KaTeX)

VS Code natively bundles KaTeX. Follow these strict rules to avoid math rendering errors:

- **Inline Math**: Delimited by single dollar signs `$...$`.
  - **Correct**: `$E = mc^2$`, `$\alpha \in [0, 1]$`
  - **Caution**: Do **not** leave a space immediately after the opening `$` or before the closing `$`. Write `$x + y$`, not `$ x + y $`.
- **Display / Block Math**: Delimited by double dollar signs on their own lines:
  ```markdown
  $$
  \frac{\partial \mathbf{u}}{\partial t} + (\mathbf{u} \cdot \nabla)\mathbf{u} = -\frac{1}{\rho}\nabla p + \nu \nabla^2 \mathbf{u}
  $$
  ```
- **Dollar Currency Escaping**: Literal dollar signs in body text must be escaped with a backslash: `\$100` or enclosed in backticks `` `$100` ``.

---

## 2. GitHub-Flavored Markdown (GFM) Callout Alerts

Use standard GFM alerts to structure analytical insights:

```markdown
> [!NOTE] 研究背景与核心假说
> 用于总结文献试图解决的科学核心问题与前提假说。

> [!IMPORTANT] 关键方法与实验参数
> 用于标明实验组、对照组参数、关键约束条件或模拟物理边界。

> [!TIP] 图表精读指导
> 用于指导读者如何观察复杂的相图、微结构切片或高维参数云图。

> [!WARNING] 模型边界与未解不确定性
> 用于客观指出作者模型的适用范围、样品局限性或未解物理机制。
```

---

## 3. High-Resolution Figure Embedding

- Always store figure files in a dedicated subfolder `./assets/<paper_slug>/`.
- Embed images using standard relative markdown syntax:
  ```markdown
  ![图注简述](./assets/<paper_slug>/fig1.png)
  *图 1：实验测试装置示意图与典型应变-应力响应曲线*
  ```
- Immediately follow the image with an italicized, comprehensive caption explaining axes, colors, and key inflection points.

---

## 4. Academic Tone & Neutrality (防夸大铁律)

- **Forbidden Sentences**:
  - ❌ "本研究彻底终结了关于 XX 的百年争论"
  - ❌ "这一颠覆性发现颠覆了一切现存理论"
  - ❌ "完美解决了该领域的核心瓶颈"
- **Required Academic Neutrality**:
  - ✅ "该发现为理解 XX 提供了新的动力学约束，但其在高温高压极端条件下的普适性仍需进一步复核。"
  - ✅ "作者建立的模型在当前采样区域吻合良好，未来仍需扩大观测网络以验证区域非均质性的影响。"
