# input_pdfs

Place raw scientific paper PDFs (`.pdf`) into this folder.

When an AI Agent is active in this workspace, you can simply say:
- "Please read all PDFs in `input_pdfs/` and summarize them into `papers/`."
- Or in the terminal, run:
  ```bash
  python main.py --batch-pdfs
  ```
The agent and pipeline will automatically parse texts and high-resolution figures, output structured Markdown reviews to `papers/`, save figures to `assets/`, and update `papers/INDEX.md`.
