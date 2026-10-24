#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the journal new-literature scan.

The scan must be a *listing* step: it reads only the configured journal list,
never the notes or the conversation, and it never extracts evidence.
"""

import datetime
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import journal_watch


TODAY = datetime.date(2026, 10, 24)


def _config(journals, keyword_sets=None, defaults=None):
    return {
        "version": 1,
        "defaults": defaults or {"days": 7, "limit": 20, "sort": "date"},
        "keyword_sets": keyword_sets or {},
        "journals": journals,
    }


def _write_config(directory, payload):
    path = Path(directory) / "journals.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _item(doi, title, published=(2026, 10, 20), created="2026-10-20T00:00:00Z",
          abstract=""):
    return {
        "DOI": doi,
        "title": [title],
        "published": {"date-parts": [list(published)]},
        "created": {"date-time": created},
        "author": [{"given": "Ada", "family": "Lovelace"}],
        "abstract": abstract,
        "type": "journal-article",
    }


class ConfigTests(unittest.TestCase):
    def test_keyword_set_is_resolved(self):
        with tempfile.TemporaryDirectory() as temp:
            path = _write_config(temp, _config(
                [{"key": "nature", "name": "Nature", "issn": "0028-0836",
                  "keyword_set": "geo", "keywords": ["extra"]}],
                {"geo": ["earth*", "mars"]},
            ))
            config = journal_watch.load_config(path)
            entry = config["journals"][0]
            self.assertEqual(entry["keywords"], ["extra", "earth*", "mars"])
            self.assertTrue(entry["enabled"])

    def test_duplicate_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = _write_config(temp, _config([
                {"key": "same", "name": "A", "issn": "1234-5678"},
                {"key": "same", "name": "B", "issn": "8765-4321"},
            ]))
            with self.assertRaises(journal_watch.JournalConfigError):
                journal_watch.load_config(path)

    def test_missing_issn_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = _write_config(temp, _config([
                {"key": "broken", "name": "Broken"},
            ]))
            with self.assertRaises(journal_watch.JournalConfigError):
                journal_watch.load_config(path)

    def test_unknown_keyword_set_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = _write_config(temp, _config([
                {"key": "j", "name": "J", "issn": "1234-5678",
                 "keyword_set": "nope"},
            ]))
            with self.assertRaises(journal_watch.JournalConfigError):
                journal_watch.load_config(path)


class FilterTests(unittest.TestCase):
    def test_keyword_is_a_whole_word_unless_starred(self):
        title = {"title": ["Scientists put a salt marsh in a giant wave machine"]}
        self.assertFalse(journal_watch._matches_keywords(title, ["mars"]))
        self.assertTrue(journal_watch._matches_keywords(title, ["mars*"]))
        core = {"title": ["A core research skill"]}
        self.assertTrue(journal_watch._matches_keywords(core, ["core"]))
        score = {"title": ["A polygenic score for height"]}
        self.assertFalse(journal_watch._matches_keywords(score, ["core"]))
        self.assertTrue(journal_watch._matches_keywords(
            {"title": ["Volcanic degassing"]}, ["volcan*"]))

    def test_noise_titles_are_dropped(self):
        for title in (
            "Correction to: A paper",
            "Author Correction: A paper",
            "Editorial: Looking back",
            "Daily briefing: A new result",
            "Mineralogical Society of America",
            "Société Française de Minéralogie et de Cristallographie",
        ):
            self.assertTrue(journal_watch._is_noise(title), title)
        self.assertFalse(journal_watch._is_noise(
            "Association between mantle temperature and volcanism"))

    def test_nature_news_doi_is_dropped(self):
        entry = {"key": "nature", "name": "Nature", "publisher": "", "issn": ""}
        item = _item("10.1038/d41586-026-00001-1", "Earth inside out")
        self.assertIsNone(journal_watch._build_candidate(item, entry, TODAY))
        research = _item("10.1038/s41586-026-00001-1", "Earth inside out")
        self.assertIsNotNone(
            journal_watch._build_candidate(research, entry, TODAY))

    def test_future_issue_date_falls_back_to_created(self):
        item = _item("10.1016/j.epsl.2026.1", "A paper", published=(2027, 1),
                     created="2026-10-24T08:00:00Z")
        display, sortable = journal_watch._best_date(item, TODAY)
        self.assertEqual(display, "2026-10-24")
        self.assertEqual(sortable, "2026-10-24")


class ScanTests(unittest.TestCase):
    def _entries(self):
        return [
            {"key": "j1", "name": "Journal One", "issn": "1111-1111",
             "publisher": "", "enabled": True, "keywords": ["earth*", "mars"]},
            {"key": "j2", "name": "Journal Two", "issn": "2222-2222",
             "publisher": "", "enabled": True, "keywords": []},
        ]

    def _scan(self, temp, responses, limit=20, sort="date", journal_keys=None):
        path = _write_config(temp, _config(self._entries()))

        def fetcher(entry, since, until, rows, mailto):
            return list(responses.get(entry["key"], [])), None

        return journal_watch.scan(
            days=7, limit=limit, sort=sort, journal_keys=journal_keys,
            config_file=path, today=TODAY, fetcher=fetcher,
        )

    def test_scan_dedupes_and_drops_noise(self):
        with tempfile.TemporaryDirectory() as temp:
            responses = {
                "j1": [
                    _item("10.1/a", "Earth's inner core"),
                    _item("10.1/a", "Earth's inner core"),  # duplicate DOI
                    _item("10.1/b", "Correction to: Earth's core"),
                    _item("10.1/c", "Salt marsh methane"),
                    _item("10.1/d", "Mars quakes today"),
                ],
                "j2": [
                    _item("10.2/x", "A different paper"),
                    _item("10.1/a", "Earth's inner core"),  # cross-journal dupe
                ],
            }
            payload = self._scan(temp, responses)
            dois = [item["doi"] for item in payload["candidates"]]
            self.assertEqual(dois.count("10.1/a"), 1)
            self.assertIn("10.1/d", dois)
            self.assertIn("10.2/x", dois)
            self.assertNotIn("10.1/b", dois)
            self.assertNotIn("10.1/c", dois)
            self.assertEqual(payload["total"], 3)

    def test_limit_is_round_robin_across_journals(self):
        with tempfile.TemporaryDirectory() as temp:
            responses = {
                "j1": [
                    _item("10.1/{}".format(n), "Earth paper {}".format(n),
                          published=(2026, 10, 20 - n))
                    for n in range(4)
                ],
                "j2": [
                    _item("10.2/{}".format(n), "Other paper {}".format(n),
                          published=(2026, 10, 20 - n))
                    for n in range(4)
                ],
            }
            payload = self._scan(temp, responses, limit=4)
            self.assertEqual(payload["total"], 4)
            self.assertEqual(payload["total_found"], 8)
            self.assertTrue(payload["truncated"])
            counts = {}
            for item in payload["candidates"]:
                counts[item["journal_key"]] = counts.get(item["journal_key"], 0) + 1
            self.assertEqual(counts, {"j1": 2, "j2": 2})

    def test_sort_by_journal_groups_in_config_order(self):
        with tempfile.TemporaryDirectory() as temp:
            responses = {
                "j1": [_item("10.1/a", "Earth paper", published=(2026, 10, 19))],
                "j2": [_item("10.2/b", "Other paper", published=(2026, 10, 20))],
            }
            payload = self._scan(temp, responses, sort="journal")
            self.assertEqual([group["key"] for group in payload["groups"]],
                             ["j1", "j2"])
            self.assertEqual([item["index"] for item in payload["candidates"]],
                             [1, 2])

    def test_journal_key_filter_and_unknown_key(self):
        with tempfile.TemporaryDirectory() as temp:
            responses = {"j1": [_item("10.1/a", "Earth paper")],
                         "j2": [_item("10.2/b", "Other paper")]}
            payload = self._scan(temp, responses, journal_keys=["j2"])
            self.assertEqual([item["journal_key"] for item in payload["candidates"]],
                             ["j2"])
            with self.assertRaises(journal_watch.ScanError):
                self._scan(temp, responses, journal_keys=["missing"])

    def test_errors_are_reported_without_losing_other_journals(self):
        with tempfile.TemporaryDirectory() as temp:
            path = _write_config(temp, _config(self._entries()))

            def fetcher(entry, since, until, rows, mailto):
                if entry["key"] == "j1":
                    return [], "HTTP 429"
                return [_item("10.2/b", "Other paper")], None

            payload = journal_watch.scan(
                days=7, limit=20, config_file=path, today=TODAY, fetcher=fetcher)
            status = {entry["key"]: entry for entry in payload["journals"]}
            self.assertEqual(status["j1"]["status"], "error")
            self.assertEqual(status["j1"]["error"], "HTTP 429")
            self.assertEqual(status["j2"]["status"], "ok")
            self.assertEqual(payload["total"], 1)


class RenderTests(unittest.TestCase):
    def test_markdown_numbers_items_and_stops_before_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            path = _write_config(temp, _config([
                {"key": "j1", "name": "Journal One", "issn": "1111-1111"},
            ]))

            def fetcher(entry, since, until, rows, mailto):
                return [_item("10.1/a", "Earth's core", abstract="An abstract.")], None

            payload = journal_watch.scan(
                days=7, limit=20, config_file=path, today=TODAY, fetcher=fetcher)
            markdown = journal_watch.render_markdown(payload)
            self.assertIn("**[1] Earth's core**", markdown)
            self.assertIn("10.1/a", markdown)
            self.assertIn("不得建立证据包", markdown)
            self.assertIn("不会触发任何抽取", markdown)
            self.assertIn("--doi", markdown)

    def test_write_scan_creates_latest_files(self):
        with tempfile.TemporaryDirectory() as temp:
            scan_dir = Path(temp) / "journal-scan"
            with mock.patch.object(journal_watch, "SCAN_DIR", scan_dir), \
                 mock.patch.object(journal_watch, "LATEST_MD", scan_dir / "latest.md"), \
                 mock.patch.object(journal_watch, "LATEST_JSON", scan_dir / "latest.json"):
                paths = journal_watch.write_scan({
                    "window": {"from": "2026-10-17", "to": "2026-10-24", "days": 7},
                    "config": "journals.json", "sort": "date", "limit": 20,
                    "scanned": 1, "total_found": 0, "total": 0,
                    "truncated": False, "journals": [], "groups": [],
                    "candidates": [],
                })
                self.assertTrue(Path(paths["markdown"]).is_file())
                self.assertTrue(Path(paths["json"]).is_file())
                self.assertTrue((scan_dir / "latest.md").is_file())


class InitTests(unittest.TestCase):
    def test_init_does_not_overwrite_existing_user_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            default = Path(temp) / "journals.json"
            user = Path(temp) / ".geo-reader" / "journals.json"
            default.write_text('{"journals": []}', encoding="utf-8")
            user.parent.mkdir()
            user.write_text('{"mine": true}', encoding="utf-8")
            with mock.patch.object(journal_watch, "DEFAULT_JOURNALS_PATH", default), \
                 mock.patch.object(journal_watch, "USER_JOURNALS_PATH", user):
                result = journal_watch.init_user_config()
                self.assertFalse(result["created"])
                self.assertEqual(user.read_text(encoding="utf-8"), '{"mine": true}')


if __name__ == "__main__":
    unittest.main()
