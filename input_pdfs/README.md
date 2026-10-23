# input_pdfs

把原始论文 PDF（`.pdf`）放到这个目录。

放入后，可以直接对 Agent 说：

> 批量精读 `input_pdfs/` 下的所有 PDF。先抽证据包，再按 `templates/paper_note.md` 写笔记，最后运行 `--check-note --fix` 和 `--index`。

或者使用终端：

```bash
python3 main.py --batch-pdfs
```

处理流程：

1. 提取 PDF 文本与 DOI；
2. 如果 PDF 内含 DOI，优先用 Chrome 打开出版社页面取高清图；
3. 浏览器失败时才回退到 PDF 内嵌图；
4. 证据包写入 `.raw/<slug>/`，图片写入 `papers/assets/<slug>/`；
5. **脚本不会生成 `papers/<slug>.md`**，综述由 Agent 基于证据包撰写；
6. 用 `--check-note` 和 `--index` 完成体检与索引登记。

注意：

- 扫描版 PDF 没有文本层，本项目不做 OCR。
- 安装 `pymupdf` 可改善 PDF 图件裁剪质量：`pip install -r requirements-optional.txt`。
- 请只处理你有权访问的文献。
