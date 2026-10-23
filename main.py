#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workspace entry point.

The pipeline produces an evidence pack under .raw/<slug>/.
It intentionally does not write a literature review; use templates/paper_note.md.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
