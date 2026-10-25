# -*- coding: utf-8 -*-
"""Tests for the note QA rules added in 0.3.0-pre.1.

Runs with either ``python3 -m unittest discover tests`` or ``pytest tests``.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.note_check import fix_note, validate_note

FRONT = """---
title: Test paper
doi: 10.1000/anchor
note_type: 经典文献
note_depth: {depth}
---

# Test paper

## 0. 文献坐标

| 年份 | 工作 | 与本文的关系 |
| :--- | :--- | :--- |
| 1970 | A | 前史 |
| 1980 | B | 前史 |
| 1990 | C | 竞争 |
| 2000 | D | 竞争 |
| 2020 | E | 后续 |

{body}
"""

REFS = """## 9. 参考文献

{entries}
"""

CITATION_CODES = {
    "missing_related_context",
    "missing_reference_section",
    "no_external_references",
    "thin_reference_context",
    "missing_citation_table",
    "references_without_doi",
    "duplicate_reference_doi",
}


def _entry(index: int) -> str:
    return (
        "{}. Author {} (2000). Title. *Journal*. "
        "[10.1000/ref{}](https://doi.org/10.1000/ref{})"
    ).format(index, index, index, index)


class NoteCheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, text: str) -> Path:
        note = self.tmp_path / "note.md"
        note.write_text(text, encoding="utf-8")
        return note

    @staticmethod
    def _codes(report: dict) -> set:
        return {issue["code"] for issue in report["issues"]}

    def test_github_alert_syntax_is_an_error(self):
        body = "> [!NOTE]\n> hello\n"
        note = self._write(
            FRONT.format(depth="deep", body=body) + REFS.format(entries=_entry(1))
        )
        report = validate_note(note)
        self.assertIn("github_alert_syntax", self._codes(report))
        self.assertGreaterEqual(report["errors"], 1)

    def test_fix_rewrites_alerts_with_a_quoted_blank_line(self):
        body = "> [!NOTE]\n> hello\n"
        note = self._write(
            FRONT.format(depth="deep", body=body) + REFS.format(entries=_entry(1))
        )
        result = fix_note(note)
        text = note.read_text(encoding="utf-8")
        self.assertNotIn("> [!NOTE]", text)
        self.assertIn("> **要点**\n>\n> hello", text)
        self.assertEqual(result["fixed_alerts"], 1)

    def test_thin_reference_context_warns_at_deep_depth(self):
        note = self._write(FRONT.format(depth="deep", body="") + REFS.format(entries=_entry(1)))
        report = validate_note(note)
        self.assertIn("thin_reference_context", self._codes(report))
        self.assertEqual(report["citations"]["target"], 10)
        self.assertEqual(report["citations"]["external"], 1)

    def test_full_reference_network_passes(self):
        entries = "\n".join(_entry(index) for index in range(1, 11))
        note = self._write(FRONT.format(depth="deep", body="") + REFS.format(entries=entries))
        report = validate_note(note)
        self.assertFalse(CITATION_CODES & self._codes(report))
        self.assertEqual(report["citations"]["external"], 10)

    def test_missing_reference_section_is_an_error(self):
        note = self._write(FRONT.format(depth="brief", body=""))
        report = validate_note(note)
        self.assertIn("missing_reference_section", self._codes(report))

    def test_missing_related_context_is_an_error(self):
        note = self._write(
            "---\ntitle: T\ndoi: 10.1000/anchor\nnote_depth: brief\n---\n\n# T\n"
            + REFS.format(entries="\n".join(_entry(i) for i in range(1, 5)))
        )
        report = validate_note(note)
        self.assertIn("missing_related_context", self._codes(report))


class ReviewFigureTests(unittest.TestCase):
    """A review must be illustrated: text-only digests are not reviews."""

    PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.assets = self.tmp_path / "assets" / "slug"
        self.assets.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _review(self, figure_count: int) -> Path:
        images = ""
        for index in range(1, figure_count + 1):
            name = "fig_{:02d}.png".format(index)
            (self.assets / name).write_bytes(self.PNG)
            images += "![图 {}：说明](assets/slug/{})\n".format(index, name)
        entries = "\n".join(_entry(index) for index in range(1, 16))
        text = (
            "---\ntitle: Review\ndoi: 10.1000/anchor\nnote_type: 经典文献综述\n"
            "note_depth: deep\n---\n\n# Review\n\n## 0. 文献坐标\n\n"
            "| 年份 | 工作 | 与本文的关系 |\n| :--- | :--- | :--- |\n"
            "| 1970 | A | 前史 |\n| 1980 | B | 前史 |\n| 1990 | C | 竞争 |\n"
            "| 2000 | D | 竞争 |\n| 2020 | E | 后续 |\n\n" + images
            + "\n## 9. 参考文献\n\n" + entries + "\n"
        )
        note = self.tmp_path / "note.md"
        note.write_text(text, encoding="utf-8")
        return note

    def test_review_without_figures_is_an_error(self):
        report = validate_note(self._review(0))
        codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("review_without_figures", codes)
        self.assertEqual(report["citations"]["is_review"], True)
        self.assertEqual(report["citations"]["figure_target"], 3)

    def test_illustrated_review_passes_the_figure_rule(self):
        report = validate_note(self._review(3))
        codes = {issue["code"] for issue in report["issues"]}
        self.assertNotIn("review_without_figures", codes)
        self.assertEqual(report["embedded_images"], 3)

    def test_broken_image_links_do_not_count_as_figures(self):
        note = self._review(3)
        text = note.read_text(encoding="utf-8")
        for index in range(1, 4):
            (self.assets / "fig_{:02d}.png".format(index)).unlink()
        note.write_text(text, encoding="utf-8")
        report = validate_note(note)
        codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("review_without_figures", codes)
        self.assertIn("missing_image", codes)


if __name__ == "__main__":
    unittest.main()
