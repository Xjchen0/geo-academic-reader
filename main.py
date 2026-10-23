#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo-academic-reader: AI Agent Workspace Main Entry Point
Version: 0.0.1-pre (MIT License)

Runs single/batch paper parsing, extracts high-res figures to assets/,
generates VS Code Markdown in papers/, and automatically updates papers/INDEX.md.
"""

import sys
import os
import argparse
import datetime
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import slugify
from scripts.fetch_paper import (
    extract_doi,
    fetch_crossref_metadata,
    fetch_apa_citation,
    extract_from_local_pdf,
    fetch_web_paper
)
from scripts.generate_markdown import render_vscode_markdown

PAPERS_DIR = PROJECT_ROOT / "papers"
ASSETS_DIR = PROJECT_ROOT / "assets"
INPUT_PDFS_DIR = PROJECT_ROOT / "input_pdfs"
INDEX_FILE = PAPERS_DIR / "INDEX.md"

def ensure_workspace_dirs():
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_PDFS_DIR.mkdir(parents=True, exist_ok=True)

def update_library_index(title: str, journal: str, year: str, doi_or_source: str, md_filename: str):
    """Append newly parsed paper to papers/INDEX.md if not already present."""
    ensure_workspace_dirs()
    if not INDEX_FILE.exists():
        header = (
            "# 📚 Academic Literature Library Index (学术文献精读知识库索引)\n\n"
            "> This index is automatically maintained by AI Agents and the `main.py` pipeline.\n\n"
            "| 归档日期 (Date) | 论文标题 (Title) | 期刊 (Journal) | 年份 | DOI / 来源 | 本地精读笔记 (Notes) |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        )
        INDEX_FILE.write_text(header, encoding="utf-8")

    current_content = INDEX_FILE.read_text(encoding="utf-8")
    if md_filename in current_content:
        return  # Already indexed

    today = datetime.date.today().isoformat()
    clean_title = title.replace("|", "-").strip()
    clean_journal = journal.replace("|", "-").strip() if journal else "Journal"
    
    if doi_or_source.startswith("10."):
        source_link = f"[{doi_or_source}](https://doi.org/{doi_or_source})"
    elif doi_or_source.startswith("http"):
        source_link = f"[Web Link]({doi_or_source})"
    else:
        source_link = doi_or_source

    note_link = f"[阅读笔记]({md_filename})"
    new_row = f"| {today} | {clean_title} | {clean_journal} | {year} | {source_link} | {note_link} |\n"
    
    with open(INDEX_FILE, "a", encoding="utf-8") as f:
        f.write(new_row)
    print(f"    [✓] Updated library index: papers/INDEX.md")

def process_paper(source_type: str, source_val: str):
    """Core processing function for a single paper."""
    ensure_workspace_dirs()
    print(f"\n🔍 Processing [{source_type}]: {source_val}")
    paper_data = {}

    if source_type == "doi":
        doi = extract_doi(source_val) or source_val
        meta = fetch_crossref_metadata(doi)
        apa = fetch_apa_citation(doi)
        paper_data.update(meta)
        paper_data["apa_citation"] = apa
        paper_slug = slugify(f"{meta.get('journal', 'paper')}_{doi}")

    elif source_type == "url":
        doi = extract_doi(source_val)
        paper_slug = slugify(f"web_{doi if doi else 'article'}")
        if doi:
            meta = fetch_crossref_metadata(doi)
            apa = fetch_apa_citation(doi)
            paper_data.update(meta)
            paper_data["apa_citation"] = apa
        else:
            paper_data["title"] = "Web Scientific Publication"
            paper_data["journal"] = "Online Source"

    elif source_type == "pdf":
        pdf_path = Path(source_val).resolve()
        if not pdf_path.exists():
            print(f"❌ Error: Local PDF file not found: {pdf_path}")
            return
        paper_slug = slugify(pdf_path.stem)

    paper_assets_dir = ASSETS_DIR / paper_slug
    paper_assets_dir.mkdir(parents=True, exist_ok=True)

    print("📥 Extracting figures and text content...")
    if source_type == "pdf":
        pdf_data = extract_from_local_pdf(Path(source_val), paper_assets_dir)
        paper_data["title"] = paper_data.get("title") or pdf_data["title"]
        paper_data["full_text"] = pdf_data["full_text"]
        # Update relative path for markdown inside papers/
        for fig in pdf_data.get("figures", []):
            fig["rel_path"] = f"../assets/{paper_slug}/{fig['filename']}"
        paper_data["figures"] = pdf_data.get("figures", [])
    elif source_type == "url":
        try:
            web_data = fetch_web_paper(source_val, paper_assets_dir)
            paper_data["title"] = paper_data.get("title") or web_data["title"]
            paper_data["full_text"] = web_data["full_text"]
            for fig in web_data.get("figures", []):
                fig["rel_path"] = f"../assets/{paper_slug}/{fig['filename']}"
            paper_data["figures"] = web_data.get("figures", [])
        except Exception as e:
            print(f"    ⚠️ Web extraction warning: {e}")
            paper_data["figures"] = []

    print("✍️  Generating VS Code-optimized Markdown...")
    markdown_content = render_vscode_markdown(paper_data)

    md_filename = f"{paper_slug}.md"
    md_file_path = PAPERS_DIR / md_filename
    md_file_path.write_text(markdown_content, encoding="utf-8")

    # Update index
    title = paper_data.get("title", paper_slug)
    journal = paper_data.get("journal", "Academic")
    year = paper_data.get("year", "")
    update_library_index(title, journal, year, source_val, md_filename)

    print("\n" + "="*60)
    print("🎉 Done! Successfully added to your literature workspace:")
    print(f"   📄 Markdown: papers/{md_filename}")
    print(f"   🖼️  Assets:   assets/{paper_slug}/")
    print(f"   📚 Catalog:  papers/INDEX.md")
    print("="*60)

def batch_process_pdfs():
    """Scan input_pdfs/ and process all .pdf files."""
    ensure_workspace_dirs()
    pdf_files = list(INPUT_PDFS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"\n[!] No PDF files found in {INPUT_PDFS_DIR}.")
        print(f"    Place your .pdf papers into '{INPUT_PDFS_DIR.name}/' and run again.")
        return

    print(f"\n📂 Found {len(pdf_files)} PDF(s) in input_pdfs/. Batch processing...")
    for i, pdf in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf.name}")
        process_paper("pdf", str(pdf))
    print("\n🎉 Batch processing completed!")

def interactive_menu():
    """Interactive menu for human users."""
    print(r"""
===================================================================
  🌍 geo-academic-reader | AI Literature Workspace
===================================================================
  [1] 精读指定 DOI 论文 (Nature, Science, AGU, Wiley, etc.)
  [2] 精读指定在线网页文献 (URL)
  [3] 精读指定本地 PDF 文献
  [4] 批量解析 input_pdfs/ 目录下的所有 PDF
  [5] 运行环境自检 (Doctor)
  [6] 退出 (Exit)
===================================================================
    """)
    try:
        choice = input("请选择操作 [1-6]: ").strip()
        if choice == "1":
            doi = input("请输入论文 DOI (例如 10.1126/science.adz2675): ").strip()
            if doi:
                process_paper("doi", doi)
        elif choice == "2":
            url = input("请输入论文网页链接: ").strip()
            if url:
                process_paper("url", url)
        elif choice == "3":
            pdf_path = input("请输入本地 PDF 文件路径: ").strip()
            if pdf_path:
                process_paper("pdf", pdf_path)
        elif choice == "4":
            batch_process_pdfs()
        elif choice == "5":
            doctor_script = PROJECT_ROOT / "doctor.py"
            os.system(f"{sys.executable} {doctor_script}")
        elif choice in ["6", "q", "exit"]:
            print("再见！")
        else:
            print("无效输入。")
    except (KeyboardInterrupt, EOFError):
        print("\n已退出。")

def main():
    parser = argparse.ArgumentParser(
        description="geo-academic-reader: AI Agent Workspace Main Runner"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--doi", help="DOI of the target paper (e.g. 10.1126/science.adz2675)")
    group.add_argument("--url", help="Direct URL to academic research article")
    group.add_argument("--pdf", help="Path to a local PDF file")
    group.add_argument("--batch-pdfs", action="store_true", help="Process all PDFs in input_pdfs/ directory")
    group.add_argument("--doctor", action="store_true", help="Run environment diagnostic (doctor.py)")

    args = parser.parse_args()

    if args.doctor:
        doctor_script = PROJECT_ROOT / "doctor.py"
        os.system(f"{sys.executable} {doctor_script}")
    elif args.doi:
        process_paper("doi", args.doi)
    elif args.url:
        process_paper("url", args.url)
    elif args.pdf:
        process_paper("pdf", args.pdf)
    elif args.batch_pdfs:
        batch_process_pdfs()
    else:
        # Default to interactive menu
        interactive_menu()

if __name__ == "__main__":
    main()
