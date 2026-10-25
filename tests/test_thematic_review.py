# -*- coding: utf-8 -*-
"""Tests for the thematic-review route: Crossref verification + QA rules.

Runs with either ``python3 -m unittest discover tests`` or ``pytest tests``.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import thematic_review as tr
from scripts.cli import build_parser
from scripts.note_check import validate_note

THEMATIC_CODES = {
    "missing_anchor_paper",
    "anchor_not_in_references",
    "missing_competing_explanations",
    "missing_later_tests",
    "missing_factcheck_section",
    "missing_evidence_tiers",
    "thin_evidence_tiers",
}


def _entry(index: int) -> str:
    return (
        "{}. Author {} (2000). Title. *Journal*. "
        "[10.1000/ref{}](https://doi.org/10.1000/ref{})"
    ).format(index, index, index, index)


def _thematic_note(body: str = "", entries: int = 16, anchor: str = "10.1000/anchor") -> str:
    refs = "\n".join(_entry(index) for index in range(1, entries + 1))
    anchor_entry = (
        "1. Anchor Author (2003). The anchor paper. *Journal*. "
        "[{anchor}](https://doi.org/{anchor})"
    ).format(anchor=anchor)
    return (
        "---\n"
        "title: 主题综述测试\n"
        "doi: {anchor}\n"
        "anchor_doi: {anchor}\n"
        "note_type: 主题综述\n"
        "note_depth: deep\n"
        "---\n\n"
        "# 主题综述测试\n\n"
        "## 0. 文献坐标\n\n"
        "| 年份 | 工作 | 核心贡献 | 与本文的关系 |\n| :--- | :--- | :--- | :--- |\n"
        "| 1970 | A | 前史 | 前史 |\n| 1980 | B | 前史 | 前史 |\n| 1990 | C | 竞争 | 竞争 |\n"
        "| 2000 | D | 竞争 | 竞争 |\n| 2020 | E | 后续 | 后续 |\n\n"
        "{body}\n\n"
        "## 9. 参考文献\n\n{anchor_entry}\n{refs}\n"
    ).format(anchor=anchor, body=body, refs=refs, anchor_entry=anchor_entry)


GOOD_BODY = """## 1. 锚定论文

锚定论文是 10.1000/anchor。【直证】原文给出主结论。

## 2. 竞争解释

竞争解释一：浅部过程。【转述】另一篇综述如此表述。
竞争解释二：另一种机制。【推断】依据数据外推。

## 3. 后续检验

后续检验工作重新测量了同一条迹线。【评估】该检验支持锚定论文的结论。

## 4. 证据层级

【直证】原文可查；【转述】他人综述；【推断】外推；【评估】笔者判断；【未核实】待核。

## 5. 人工事实复核

已复核条目见主题综述工作底稿；未复核部分标注【未核实】。
"""


class TitleMatchTests(unittest.TestCase):
    """A DOI that resolves is not necessarily the DOI you meant.

    A hallucinated reference was caught in the field because the DOI
    resolved to a real conference abstract on a related topic, while the
    note credited it to a different paper. Only the title gives it away.
    """

    def test_identical_titles_match(self):
        self.assertTrue(tr.titles_match("The stability of grounding lines",
                                         "The stability of grounding lines"))

    def test_punctuation_and_dashes_do_not_break_the_match(self):
        self.assertTrue(
            tr.titles_match("core-mantle boundary", "core–mantle boundary")
        )

    def test_a_subtitle_still_matches(self):
        self.assertTrue(
            tr.titles_match(
                "Marine-based ice sheets and sea-level rise",
                "Marine-based ice sheets and sea-level rise",
            )
        )

    def test_a_different_paper_does_not_match(self):
        self.assertFalse(
            tr.titles_match(
                "Marine-based ice sheets and sea-level rise",
                "Hysteresis of the Antarctic ice sheet with a coupled climate-ice-sheet model",
            )
        )

    def test_an_empty_expectation_never_fails(self):
        self.assertTrue(tr.titles_match("", "Anything at all"))


class RefSpecTests(unittest.TestCase):
    def test_a_plain_doi_list_still_parses(self):
        self.assertEqual(
            tr.parse_ref_specs("10.1000/a, 10.1000/b"),
            [("10.1000/a", ""), ("10.1000/b", "")],
        )

    def test_a_titled_entry_keeps_its_title(self):
        found = tr.parse_ref_specs("10.1000/a|The stability of grounding lines")
        self.assertEqual(found, [("10.1000/a", "The stability of grounding lines")])

    def test_one_titled_entry_per_line(self):
        text = (
            "10.1000/a|First paper, with a comma\n"
            "10.1000/b|Second paper\n"
        )
        found = tr.parse_ref_specs(text)
        self.assertEqual(found[0], ("10.1000/a", "First paper, with a comma"))
        self.assertEqual(found[1], ("10.1000/b", "Second paper"))

    def test_an_ambiguous_titled_line_drops_the_title_instead_of_guessing(self):
        found = tr.parse_ref_specs("10.1000/a 10.1000/b|Only one title")
        self.assertEqual(len(found), 2)
        self.assertTrue(all(title == "" for _doi, title in found))

    def test_a_file_of_references_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "refs.txt"
            path.write_text(
                "10.1000/a|First paper\n10.1000/b\n", encoding="utf-8"
            )
            found = tr.parse_ref_specs(str(path))
            self.assertEqual(found[0], ("10.1000/a", "First paper"))
            self.assertEqual(found[1], ("10.1000/b", ""))


class VerifyTitleTests(unittest.TestCase):
    def _verify(self, metadata, expected=""):
        with mock.patch.object(tr, "fetch_crossref_metadata", return_value=metadata):
            return tr.verify_doi("10.1000/a", expected_title=expected)

    def test_a_matching_title_stays_verified(self):
        entry = self._verify(
            {"doi": "10.1000/a", "title": "The stability of grounding lines",
             "abstract": "", "error": ""},
            expected="The stability of grounding lines",
        )
        self.assertTrue(entry["verified"])
        self.assertTrue(entry["title_match"])
        self.assertEqual(entry["status"], "verified")

    def test_a_mismatching_title_is_rejected(self):
        entry = self._verify(
            {"doi": "10.1000/a", "title": "Hysteresis of the Antarctic ice sheet",
             "abstract": "", "error": ""},
            expected="Marine-based ice sheets and sea-level rise",
        )
        self.assertFalse(entry["verified"])
        self.assertFalse(entry["title_match"])
        self.assertEqual(entry["status"], "title_mismatch")
        self.assertIn("标题不匹配", entry["error"])

    def test_no_expectation_means_no_title_check(self):
        entry = self._verify({"doi": "10.1000/a", "title": "Any title", "error": ""})
        self.assertTrue(entry["verified"])
        self.assertIsNone(entry["title_match"])


class DoiHelpersTests(unittest.TestCase):
    def test_normalise_doi_strips_prefix_and_trailing_punctuation(self):
        self.assertEqual(
            tr.normalise_doi("https://doi.org/10.1038/S41561-026-02006-0."),
            "10.1038/s41561-026-02006-0",
        )
        self.assertEqual(tr.normalise_doi("doi:10.1000/x"), "10.1000/x")
        self.assertEqual(tr.normalise_doi(""), "")

    def test_parse_doi_list_accepts_a_comma_list_and_dedupes(self):
        found = tr.parse_doi_list("10.1000/a, 10.1000/b; 10.1000/a")
        self.assertEqual(found, ["10.1000/a", "10.1000/b"])

    def test_parse_doi_list_reads_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dois.txt"
            path.write_text("10.1000/a\n10.1000/b\n", encoding="utf-8")
            self.assertEqual(tr.parse_doi_list(str(path)), ["10.1000/a", "10.1000/b"])

    def test_parse_doi_list_ignores_non_doi_tokens(self):
        self.assertEqual(tr.parse_doi_list("not a doi, 10.1000/a"), ["10.1000/a"])


class VerifyTests(unittest.TestCase):
    def _verify(self, metadata):
        with mock.patch.object(tr, "fetch_crossref_metadata", return_value=metadata):
            return tr.verify_doi("10.1000/a")

    def test_abstract_makes_the_entry_direct_evidence(self):
        entry = self._verify(
            {
                "title": "T",
                "authors": ["A B"],
                "journal": "J",
                "year": "2001",
                "abstract": "the abstract",
                "doi": "10.1000/a",
                "type": "journal-article",
            }
        )
        self.assertTrue(entry["verified"])
        self.assertTrue(entry["abstract_available"])
        self.assertEqual(entry["default_tier"], "direct")

    def test_metadata_without_abstract_is_reported_evidence(self):
        entry = self._verify(
            {
                "title": "T",
                "authors": [],
                "journal": "J",
                "year": "2001",
                "abstract": "",
                "doi": "10.1000/a",
                "type": "journal-article",
            }
        )
        self.assertTrue(entry["verified"])
        self.assertFalse(entry["abstract_available"])
        self.assertEqual(entry["default_tier"], "reported")

    def test_a_failed_lookup_stays_unverified(self):
        entry = self._verify({"doi": "10.1000/a", "error": "404 Not Found (Crossref)"})
        self.assertFalse(entry["verified"])
        self.assertEqual(entry["default_tier"], "unverified")

    def test_a_missing_doi_is_reported_as_not_found(self):
        entry = self._verify(
            {"doi": "10.1000/a", "error": "404 Not Found", "error_kind": "not_found"}
        )
        self.assertFalse(entry["verified"])
        self.assertEqual(entry["status"], "not_found")

    def test_a_rate_limited_lookup_is_reported_as_retryable(self):
        entry = self._verify(
            {"doi": "10.1000/a", "error": "HTTP 429", "error_kind": "rate_limited"}
        )
        self.assertFalse(entry["verified"])
        self.assertEqual(entry["status"], "temporarily_unavailable")

    def test_a_record_without_a_title_is_not_counted_as_verified(self):
        entry = self._verify(
            {"doi": "10.1000/a", "error": "Crossref 未提供标题", "error_kind": "incomplete"}
        )
        self.assertFalse(entry["verified"])
        self.assertEqual(entry["status"], "incomplete")


class WorkingSetTests(unittest.TestCase):
    def _build(self, **kwargs):
        search = {
            "topic": "hotspots",
            "total": 2,
            "items": [
                {"doi": "10.1000/topic", "title": "Topic hit", "year": "2005",
                 "journal": "J", "abstract": "", "relevance_rank": 1},
            ],
            "query": "query.bibliographic=hotspots",
        }
        predecessors = [{"doi": "10.1000/prev", "year": "1990", "title": "",
                         "journal": "Old"}]
        forward = [{"doi": "10.1000/next", "title": "Later test", "year": "2015",
                    "journal": "New"}]
        verified = {
            "10.1000/anchor": {"doi": "10.1000/anchor", "verified": True, "error": "",
                               "title": "Anchor", "authors": ["A"], "journal": "J",
                               "year": "2003", "abstract": "abs",
                               "abstract_available": True, "type": "journal-article",
                               "default_tier": "direct", "roles": []},
            "10.1000/topic": {"doi": "10.1000/topic", "verified": True, "error": "",
                              "title": "Topic hit", "authors": ["B"], "journal": "J",
                              "year": "2005", "abstract": "", "abstract_available": False,
                              "type": "journal-article", "default_tier": "reported",
                              "roles": []},
            "10.1000/prev": {"doi": "10.1000/prev", "verified": True, "error": "",
                             "title": "Prev", "authors": ["C"], "journal": "Old",
                             "year": "1990", "abstract": "", "abstract_available": False,
                             "type": "journal-article", "default_tier": "reported",
                             "roles": []},
            "10.1000/next": {"doi": "10.1000/next", "verified": True, "error": "",
                             "title": "Later", "authors": ["D"], "journal": "New",
                             "year": "2015", "abstract": "", "abstract_available": False,
                             "type": "journal-article", "default_tier": "reported",
                             "roles": []},
        }
        with mock.patch.object(tr, "search_crossref_topic", return_value=search), \
                mock.patch.object(tr, "fetch_reference_dois", return_value=predecessors), \
                mock.patch.object(tr, "fetch_forward_citations", return_value=forward), \
                mock.patch.object(tr, "verify_doi", side_effect=lambda doi, mailto="", expected_title="": dict(
                    verified[doi], roles=[])):
            return tr.build_working_set(**kwargs)

    def test_the_anchor_is_verified_and_listed_first(self):
        payload = self._build(topic="hotspots", anchor="10.1000/anchor", max_refs=10)
        self.assertEqual(payload["references"][0]["doi"], "10.1000/anchor")
        self.assertIn("anchor", payload["references"][0]["roles"])

    def test_the_network_carries_predecessor_and_later_test_roles(self):
        payload = self._build(topic="hotspots", anchor="10.1000/anchor", max_refs=10)
        by_doi = {entry["doi"]: entry for entry in payload["references"]}
        self.assertIn("predecessor", by_doi["10.1000/prev"]["roles"])
        self.assertIn("later_test", by_doi["10.1000/next"]["roles"])

    def test_the_verification_budget_is_respected(self):
        payload = self._build(topic="hotspots", anchor="10.1000/anchor", max_refs=2)
        self.assertEqual(len(payload["references"]), 2)
        self.assertTrue(payload["candidates"])

    def test_user_supplied_dois_are_kept(self):
        payload = self._build(
            topic="", refs=["10.1000/topic"], anchor="10.1000/anchor", max_refs=10
        )
        by_doi = {entry["doi"]: entry for entry in payload["references"]}
        self.assertIn("user_supplied", by_doi["10.1000/topic"]["roles"])

    def test_the_route_is_recorded_as_a_topic_route(self):
        payload = self._build(topic="hotspots", anchor="10.1000/anchor", max_refs=10)
        self.assertEqual(payload["query"]["route"], "thematic-review")
        self.assertIn("query.bibliographic", payload["query"]["topic_query"])


class ReportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _payload(self):
        return {
            "generated_at": "2026-10-25T10:00:00+08:00",
            "topic": "hotspots",
            "anchor_doi": "10.1000/anchor",
            "max_refs": 25,
            "query": {"route": "thematic-review", "topic_query": "query.bibliographic=hotspots",
                      "topic_total": 42, "topic_error": "", "predecessors_found": 3,
                      "forward_citations_found": 2, "include_forward": True},
            "evidence_tiers": {
                tier: {"label": tr.EVIDENCE_TIER_LABELS[tier], "help": tr.EVIDENCE_TIER_HELP[tier]}
                for tier in tr.EVIDENCE_TIERS
            },
            "references": [
                {"doi": "10.1000/anchor", "verified": True, "title": "Anchor",
                 "authors": ["A B"], "journal": "J", "year": "2003", "abstract": "the text",
                 "abstract_available": True, "type": "journal-article",
                 "default_tier": "direct", "roles": ["anchor"]},
            ],
            "candidates": [
                {"doi": "10.1000/cand", "verified": False, "title": "",
                 "authors": [], "journal": "Old", "year": "1990", "abstract": "",
                 "abstract_available": False, "type": "", "default_tier": "unverified",
                 "roles": ["predecessor"]},
            ],
        }

    def test_candidates_markdown_states_the_route_difference(self):
        text = tr.render_candidates_md(self._payload())
        self.assertIn("主题检索", text)
        self.assertIn("--new-literature", text)
        self.assertIn("10.1000/anchor", text)
        self.assertIn("【直证】", text)

    def test_factcheck_sheet_has_the_human_rows(self):
        text = tr.render_factcheck_md(self._payload())
        self.assertIn("人工事实复核", text)
        self.assertIn("10.1000/anchor", text)
        self.assertIn("论断级复核", text)
        self.assertIn("【未核实】", text)

    def test_write_working_set_creates_three_files(self):
        paths = tr.write_working_set(self._payload(), self.tmp_path / "review")
        for key in ("candidates", "references", "factcheck"):
            self.assertTrue(Path(paths[key]).is_file(), key)
        payload = self._payload()
        tr.write_working_set(payload, self.tmp_path / "review")
        self.assertIn("10.1000/anchor", Path(paths["references"]).read_text(encoding="utf-8"))

    def test_console_summary_names_the_route(self):
        text = tr.render_console(self._payload())
        self.assertIn("主题综述", text)
        self.assertIn("不是期刊页面扫描", text)

    def test_unverified_entries_show_why_they_failed(self):
        payload = self._payload()
        payload["candidates"][0].update(
            {"status": "not_found", "error": "404 Not Found", "error_kind": "not_found"}
        )
        text = tr.render_candidates_md(payload)
        self.assertIn("未核验原因", text)
        self.assertIn("DOI 不存在", text)

    def test_the_factcheck_sheet_lists_the_unverified_entries(self):
        payload = self._payload()
        payload["candidates"][0].update(
            {"status": "temporarily_unavailable", "error": "HTTP 429",
             "error_kind": "rate_limited"}
        )
        text = tr.render_factcheck_md(payload)
        self.assertIn("未能核验的条目", text)
        self.assertIn("10.1000/cand", text)
        self.assertIn("接口暂时不可用", text)


class CliTests(unittest.TestCase):
    def test_thematic_review_is_its_own_action(self):
        parser = build_parser()
        args = parser.parse_args(["--thematic-review", "hotspots"])
        self.assertEqual(args.thematic_review, "hotspots")
        self.assertEqual(args.max_refs, tr.DEFAULT_MAX_REFS)

    def test_thematic_review_without_a_topic_is_allowed(self):
        args = build_parser().parse_args(["--thematic-review"])
        self.assertEqual(args.thematic_review, "")

    def test_it_cannot_be_combined_with_a_single_paper_extraction(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--thematic-review", "hotspots", "--doi", "10.1000/x"])

    def test_the_scan_and_the_review_are_different_commands(self):
        parser = build_parser()
        self.assertTrue(parser.parse_args(["--new-literature"]).new_literature)
        self.assertIsNone(parser.parse_args(["--new-literature"]).thematic_review)


class ThematicNoteRuleTests(unittest.TestCase):
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

    def test_a_complete_thematic_note_passes_the_thematic_rules(self):
        report = validate_note(self._write(_thematic_note(GOOD_BODY)))
        self.assertFalse(THEMATIC_CODES & self._codes(report))

    def test_a_missing_anchor_paper_is_an_error(self):
        text = _thematic_note(GOOD_BODY).replace("anchor_doi: 10.1000/anchor\n", "")
        text = text.replace("## 1. 锚定论文", "## 1. 主题")
        report = validate_note(self._write(text))
        self.assertIn("missing_anchor_paper", self._codes(report))

    def test_an_anchor_missing_from_the_reference_list_is_an_error(self):
        text = _thematic_note(GOOD_BODY).replace("anchor_doi: 10.1000/anchor", "anchor_doi: 10.1000/elsewhere")
        report = validate_note(self._write(text))
        self.assertIn("anchor_not_in_references", self._codes(report))

    def test_missing_competing_explanations_is_an_error(self):
        text = _thematic_note(GOOD_BODY).replace("竞争解释", "另一种说法")
        report = validate_note(self._write(text))
        self.assertIn("missing_competing_explanations", self._codes(report))

    def test_missing_later_tests_is_an_error(self):
        text = _thematic_note(GOOD_BODY).replace("后续检验", "后续展望")
        report = validate_note(self._write(text))
        self.assertIn("missing_later_tests", self._codes(report))

    def test_missing_factcheck_section_is_an_error(self):
        text = _thematic_note(GOOD_BODY).replace("人工事实复核", "备注")
        report = validate_note(self._write(text))
        self.assertIn("missing_factcheck_section", self._codes(report))

    def test_missing_evidence_tiers_is_an_error(self):
        body = "\n".join(
            line for line in GOOD_BODY.splitlines()
            if "【" not in line
        )
        report = validate_note(self._write(_thematic_note(body)))
        self.assertIn("missing_evidence_tiers", self._codes(report))

    def test_one_tier_only_is_a_warning(self):
        body = GOOD_BODY.replace("【转述】", "转述").replace("【推断】", "推断")
        body = body.replace("【评估】", "评估").replace("【未核实】", "未核实")
        report = validate_note(self._write(_thematic_note(body)))
        codes = self._codes(report)
        self.assertIn("thin_evidence_tiers", codes)
        self.assertNotIn("missing_evidence_tiers", codes)

    def test_a_classic_note_is_not_touched_by_the_thematic_rules(self):
        text = (
            "---\ntitle: T\ndoi: 10.1000/anchor\nnote_type: 经典文献\nnote_depth: brief\n"
            "---\n\n# T\n\n## 0. 文献坐标\n\n"
            "| 年份 | 工作 | 与本文的关系 |\n| :--- | :--- | :--- |\n"
            "| 1970 | A | 前史 |\n| 1980 | B | 前史 |\n| 1990 | C | 竞争 |\n"
            "| 2000 | D | 竞争 |\n| 2020 | E | 后续 |\n\n"
            "## 9. 参考文献\n\n" + "\n".join(_entry(i) for i in range(1, 4)) + "\n"
        )
        report = validate_note(self._write(text))
        self.assertFalse(THEMATIC_CODES & self._codes(report))


if __name__ == "__main__":
    unittest.main()
