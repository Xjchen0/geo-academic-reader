#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-line entry point for geo-academic-reader Pipeline.
Version: 0.0.1-pre (MIT License)
"""

import argparse
import sys
import os
from pathlib import Path

# Add current scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.config import slugify
from scripts.fetch_paper import (
    extract_doi,
    fetch_crossref_metadata,
    fetch_apa_citation,
    extract_from_local_pdf,
    fetch_web_paper
)
from scripts.generate_markdown import render_vscode_markdown

VERSION = "0.0.1-pre"

def print_welcome_guide():
    print(r"""
===================================================================
  🌍 geo-academic-reader (v0.0.1-pre)
  Scientific literature parser & VS Code rich-media Markdown generator
===================================================================

[Quick Start Examples]
  1. Parse via DOI:
     geo-reader --doi "10.1126/science.adz2675" --output ./output
     (or: python scripts/run_pipeline.py --doi "10.1126/science.adz2675")

  2. Parse via Paper URL:
     geo-reader --url "https://www.nature.com/articles/s41586-026-10999-2"

  3. Parse via Local PDF:
     geo-reader --pdf "/path/to/paper.pdf"

  4. Run Environment Diagnostic (Doctor):
     geo-doctor (or: python doctor.py)

Type 'geo-reader --help' for all options.
""")

def main():
    if len(sys.argv) == 1:
        print_welcome_guide()
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description=f"geo-academic-reader (v{VERSION}): Transform scientific papers into rich VS Code Markdown."
    )
    parser.add_argument("--version", "-v", action="version", version=f"geo-academic-reader v{VERSION}")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--doi", help="DOI of the paper (e.g. 10.1126/science.adz2675)")
    group.add_argument("--url", help="Direct URL to research article")
    group.add_argument("--pdf", help="Path to local PDF file")
    group.add_argument("--check-env", action="store_true", help="Run environment diagnostic (doctor.py)")

    parser.add_argument(
        "--output", "-o",
        default="./output",
        help="Output directory (default: ./output)"
    )

    args = parser.parse_args()

    if args.check_env:
        doctor_script = Path(__file__).parent.parent / "doctor.py"
        os.system(f"{sys.executable} {doctor_script}")
        return

    output_base = Path(args.output).resolve()
    output_base.mkdir(parents=True, exist_ok=True)

    print("\n🔍 [1/3] Parsing input source & metadata...")
    paper_data = {}

    if args.doi:
        doi = extract_doi(args.doi) or args.doi
        print(f"    Target DOI: {doi}")
        meta = fetch_crossref_metadata(doi)
        apa = fetch_apa_citation(doi)
        paper_data.update(meta)
        paper_data["apa_citation"] = apa
        paper_slug = slugify(f"{meta.get('journal', 'paper')}_{doi}")

    elif args.url:
        print(f"    Target URL: {args.url}")
        doi = extract_doi(args.url)
        paper_slug = slugify(f"web_{doi if doi else 'article'}")
        if doi:
            meta = fetch_crossref_metadata(doi)
            apa = fetch_apa_citation(doi)
            paper_data.update(meta)
            paper_data["apa_citation"] = apa
        else:
            paper_data["title"] = "Web Scientific Publication"
            paper_data["journal"] = "Online Source"

    elif args.pdf:
        pdf_path = Path(args.pdf).resolve()
        if not pdf_path.exists():
            print(f"❌ Error: Local PDF file not found: {pdf_path}")
            sys.exit(1)
        print(f"    Target PDF: {pdf_path.name}")
        paper_slug = slugify(pdf_path.stem)

    # Prepare assets directory
    assets_dir = output_base / "assets" / paper_slug
    assets_dir.mkdir(parents=True, exist_ok=True)

    print("\n📥 [2/3] Extracting text and downloading high-resolution figures...")
    if args.pdf:
        pdf_data = extract_from_local_pdf(Path(args.pdf), assets_dir)
        paper_data["title"] = paper_data.get("title") or pdf_data["title"]
        paper_data["full_text"] = pdf_data["full_text"]
        paper_data["figures"] = pdf_data["figures"]
    elif args.url:
        try:
            web_data = fetch_web_paper(args.url, assets_dir)
            paper_data["title"] = paper_data.get("title") or web_data["title"]
            paper_data["full_text"] = web_data["full_text"]
            paper_data["figures"] = web_data["figures"]
        except Exception as e:
            print(f"    ⚠️ Web extraction fallback: {e}")
            paper_data["figures"] = []

    print(f"    Found {len(paper_data.get('figures', []))} figure(s).")

    print("\n✍️  [3/3] Generating VS Code-optimized Markdown...")
    markdown_content = render_vscode_markdown(paper_data)

    output_file = output_base / f"{paper_slug}.md"
    output_file.write_text(markdown_content, encoding="utf-8")

    print("\n" + "="*60)
    print("🎉 Done! Article successfully generated:")
    print(f"   📄 Markdown: {output_file}")
    print(f"   🖼️  Assets:   {assets_dir}")
    print("\n💡 How to view in VS Code:")
    print(f"   1. Open the file in VS Code: code \"{output_file}\"")
    print("   2. Press Ctrl+Shift+V (Windows/Linux) or Cmd+Shift+V (Mac) to open Preview.")
    print("   3. KaTeX mathematical equations and figure graphics will render beautifully.")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
