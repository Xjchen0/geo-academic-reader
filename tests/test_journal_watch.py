#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the publisher-page journal scan."""

import datetime
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import journal_watch as jw
from scripts.browser import BrowserChallenge


NATURE_PAGE = """
<article class="c-card">
  <h3 class="c-card__title"><a href="/articles/s41586-026-11111-1">Mantle mixing</a></h3>
  <time datetime="2026-10-21">21 October 2026</time>
</article>
<article class="c-card">
  <h3 class="c-card__title"><a href="/articles/s41586-026-22222-2">Core formation</a></h3>
  <time datetime="2026-10-20">20 October 2026</time>
</article>
"""

NGEO_PAGE = """
<article class="c-card">
  <h3 class="c-card__title"><a href="/articles/s41561-026-33333-3">Deep water cycle</a></h3>
  <time datetime="2026-10-22">22 October 2026</time>
</article>
<article class="c-card">
  <h3 class="c-card__title"><a href="/articles/s41561-026-44444-4">Craton growth</a></h3>
  <time datetime="2026-10-19">19 October 2026</time>
</article>
"""

SCIENCE_PAGE = """
<h4 class="to-section">21 October 2026</h4>
<h3 class="article-title"><a href="/doi/10.1126/science.abc123">First release paper</a></h3>
<h4 class="to-section">20 October 2026</h4>
<h3 class="article-title"><a href="/doi/10.1126/science.def456">Older release paper</a></h3>
"""

SCIENCE_CURRENT_PAGE = """
<h4 class="to-section">News</h4>
<h3 class="article-title"><a href="/doi/10.1126/science.news1">News item</a></h3>
<h4 class="to-section">Research Articles</h4>
<h3 class="article-title"><a href="/doi/10.1126/science.res1">Research paper</a></h3>
"""

SCIADV_PAGE = """
<h4 class="to-section">Neuroscience</h4>
<div class="card  "><h3 class="article-title"><a href="/doi/10.1126/sciadv.neur1">Brain paper</a></h3></div>
<h4 class="to-section">Earth, Environmental, Ecological, and Space Sciences</h4>
<div class="card  "><h3 class="article-title"><a href="/doi/10.1126/sciadv.earth1">Earth paper</a></h3><time>21 October 2026</time></div>
<div class="card "><h3 class="article-title"><a href="/doi/10.1126/sciadv.earth2">Second earth paper</a></h3></div>
"""

EPSL_PAGE = """
<div>
  <a href="https://doi.org/10.1016/j.epsl.2026.120418">doi</a>
  <a class="anchor article-content-title u-margin-xs-top anchor-primary"
     href="/science/article/pii/S0012821X26005984">Remagnetization fingerprints</a>
</div>
"""

AGU_PAGE = """
<div id="pane-recent">
  <div class="issue-item">
    <a href="/doi/10.1029/2026GL121695" title="Recent GRL paper" class="issue-item__title">x</a>
    <span><label>First Published:</label><span>&nbsp;21 October 2026</span></span>
  </div>
</div>
<div id="pane-cited">
  <div class="issue-item">
    <a href="/doi/10.1029/1999GL000001" title="Old cited paper" class="issue-item__title">x</a>
  </div>
</div>
"""

GEOLOGY_CURRENT_PAGE = """
<h3 class="customLink item-title">
  <a href="/gsa/geology/article/54/10/963/732263/Paper">Riverbed paper</a>
</h3>
<a href="/doi/10.1130/G54629.1">doi</a>
<a href="/geology/article-pdf/54/10/963/732263/G54629.1.pdf">pdf</a>
"""

GEOLOGY_EARLY_PAGE = """
<h2 class="al-subgroup-outer-id">October 21, 2026</h2>
<h5 class="al-title"><a href="/geology/article/doi/10.1130/G53093.1/12345">Early paper</a></h5>
<h2 class="al-subgroup-outer-id">October 20, 2026</h2>
<h5 class="al-title"><a href="/geology/article/doi/10.1130/G53094.1/12346">Second early paper</a></h5>
"""

GJI_PAGE = """
<div class="widget-dynamic-entry journalArticleItem">
  <span class="hfDoi" data-attribute="10.1093/gji/ggag453"></span>
  <a class="journal-link" href="/gji/advance-article/doi/10.1093/gji/ggag453/1">
    <div class="widget-dynamic-journal-title">Cyclic loading of MgO</div>
  </a>
</div>
"""

PNAS_PAGE = """
<h2>Recent articles</h2>
<div class="card  ">
  <a href="/doi/10.1073/pnas.2608656123" title="Warm rain paper"></a>
  <a class="card__meta__type">Research Article</a>
  <span class="card__meta__date">October 21, 2026</span>
</div>
<h2>Trending</h2>
<div class="card  ">
  <a href="/doi/10.1073/pnas.1111111111" title="Old trending paper"></a>
</div>
"""


class CleanTests(unittest.TestCase):
    def test_escaped_inline_markup_is_removed(self):
        self.assertEqual(
            jw._clean(
                "NH&lt;sub&gt;4&lt;/sub&gt;-Smectites on the &lt;i&gt;Curiosity&lt;/i&gt; rover"
            ),
            "NH4-Smectites on the Curiosity rover",
        )

    def test_raw_inline_markup_is_removed(self):
        self.assertEqual(
            jw._clean("Revealed by <i>P</i>-Wave tomography"),
            "Revealed by P-Wave tomography",
        )


class DateTests(unittest.TestCase):
    def test_day_month_year(self):
        self.assertEqual(jw._parse_date("21 October 2026"), "2026-10-21")
        self.assertEqual(jw._parse_date("First Published: 21 October 2026"), "2026-10-21")

    def test_month_day_year(self):
        self.assertEqual(jw._parse_date("October 21, 2026"), "2026-10-21")
        self.assertEqual(jw._parse_date("2026-10-21"), "2026-10-21")
        self.assertEqual(jw._parse_date("First Release"), "")


class ParserTests(unittest.TestCase):
    def test_nature(self):
        items = jw.parse_nature(NATURE_PAGE, "https://www.nature.com/nature/research-articles")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["doi"], "10.1038/s41586-026-11111-1")
        self.assertEqual(items[0]["date"], "2026-10-21")
        self.assertEqual(
            items[0]["url"],
            "https://www.nature.com/articles/s41586-026-11111-1",
        )

    def test_science_first_release(self):
        items = jw.parse_science_first(SCIENCE_PAGE, "https://www.science.org/toc/science/0/0")
        self.assertEqual([item["doi"] for item in items], [
            "10.1126/science.abc123", "10.1126/science.def456"
        ])
        self.assertEqual(items[0]["date"], "2026-10-21")

    def test_science_current_only_research_articles(self):
        items = jw.parse_science_current(
            SCIENCE_CURRENT_PAGE, "https://www.science.org/toc/science/current"
        )
        self.assertEqual([item["title"] for item in items], ["Research paper"])

    def test_science_advances_only_earth_section(self):
        items = jw.parse_science_advances(
            SCIADV_PAGE, "https://www.science.org/toc/sciadv/current"
        )
        self.assertEqual([item["title"] for item in items], [
            "Earth paper", "Second earth paper"
        ])

    def test_epsl_uses_page_doi(self):
        items = jw.parse_epsl(
            EPSL_PAGE,
            "https://www.sciencedirect.com/journal/earth-and-planetary-science-letters/vol/699/suppl/C",
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["doi"], "10.1016/j.epsl.2026.120418")
        self.assertIn("/science/article/pii/S0012821X26005984", items[0]["url"])

    def test_epsl_does_not_invent_missing_doi(self):
        page = EPSL_PAGE.replace(
            '<a href="https://doi.org/10.1016/j.epsl.2026.120418">doi</a>', ""
        )
        items = jw.parse_epsl(page, "https://www.sciencedirect.com/x")
        self.assertEqual(items[0]["doi"], "")
        self.assertIn("/science/article/pii/", items[0]["url"])

    def test_agu_uses_recently_published_pane_only(self):
        items = jw.parse_agu(AGU_PAGE, "https://agupubs.onlinelibrary.wiley.com/journal/19448007")
        self.assertEqual([item["doi"] for item in items], ["10.1029/2026gl121695"])
        self.assertEqual(items[0]["date"], "2026-10-21")

    def test_geology_current(self):
        items = jw.parse_geology_current(
            GEOLOGY_CURRENT_PAGE, "https://pubs.geoscienceworld.org/geology/issue/current"
        )
        self.assertEqual(items[0]["doi"], "10.1130/g54629.1")
        self.assertEqual(items[0]["title"], "Riverbed paper")

    def test_geology_early_groups_dates(self):
        items = jw.parse_geology_early(
            GEOLOGY_EARLY_PAGE,
            "https://pubs.geoscienceworld.org/geology/early-publication",
        )
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["date"], "2026-10-21")
        self.assertEqual(items[1]["doi"], "10.1130/g53094.1")

    def test_gji(self):
        items = jw.parse_gji(GJI_PAGE, "https://academic.oup.com/gji")
        self.assertEqual(items[0]["doi"], "10.1093/gji/ggag453")
        self.assertEqual(items[0]["title"], "Cyclic loading of MgO")

    def test_pnas_stops_at_trending(self):
        items = jw.parse_pnas(PNAS_PAGE, "https://www.pnas.org/topic/earth-sci")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["doi"], "10.1073/pnas.2608656123")
        self.assertEqual(items[0]["kind"], "Research Article")
        self.assertEqual(items[0]["date"], "2026-10-21")


class ConfigTests(unittest.TestCase):
    def _write_config(self, payload):
        directory = tempfile.mkdtemp()
        path = Path(directory) / "journals.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _entry(self, **overrides):
        entry = {
            "key": "nature",
            "name": "Nature",
            "parser": "nature",
            "url": "https://www.nature.com/nature/research-articles",
        }
        entry.update(overrides)
        return entry

    def test_load_and_defaults(self):
        path = self._write_config(
            {"version": 2, "defaults": {"days": 0, "limit": 0, "sort": "journal"},
             "journals": [self._entry()]}
        )
        config = jw.load_config(path)
        self.assertEqual(config["defaults"], {"days": 0, "limit": 0, "sort": "journal"})
        self.assertEqual(config["journals"][0]["wait"], 5.0)

    def test_duplicate_key(self):
        path = self._write_config({"journals": [self._entry(), self._entry()]})
        with self.assertRaises(jw.JournalConfigError):
            jw.load_config(path)

    def test_legacy_issn_list_is_rejected_with_migration_hint(self):
        path = self._write_config(
            {"version": 1, "journals": [{
                "key": "nature", "name": "Nature", "issn": "0028-0836",
            }]}
        )
        with self.assertRaises(jw.JournalConfigError) as caught:
            jw.load_config(path)
        self.assertIn("journals-init --force", str(caught.exception))

    def test_unknown_parser(self):
        path = self._write_config({"journals": [self._entry(parser="nope")]})
        with self.assertRaises(jw.JournalConfigError):
            jw.load_config(path)

    def test_missing_url(self):
        path = self._write_config({"journals": [self._entry(url="")]})
        with self.assertRaises(jw.JournalConfigError):
            jw.load_config(path)

    def test_volume_template_requires_volumes(self):
        path = self._write_config(
            {"journals": [self._entry(
                parser="epsl", url="", url_template="https://example.org/vol/{volume}"
            )]}
        )
        with self.assertRaises(jw.JournalConfigError):
            jw.load_config(path)

    def test_page_urls_expand_volumes(self):
        path = self._write_config(
            {"journals": [self._entry(
                parser="epsl", url="",
                url_template="https://example.org/vol/{volume}",
                volumes=[699, 698],
            )]}
        )
        entry = jw.load_config(path)["journals"][0]
        self.assertEqual(
            jw.page_urls(entry),
            ["https://example.org/vol/699", "https://example.org/vol/698"],
        )


class ScanTests(unittest.TestCase):
    @staticmethod
    def distinct_pages(entry, url):
        return NATURE_PAGE if entry["key"] == "nature" else NGEO_PAGE

    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.config = self.directory / "journals.json"
        self.config.write_text(
            json.dumps(
                {
                    "defaults": {"days": 0, "limit": 0, "sort": "journal"},
                    "journals": [
                        {
                            "key": "nature", "name": "Nature", "parser": "nature",
                            "url": "https://example.org/nature",
                        },
                        {
                            "key": "ngeo", "name": "Nature Geoscience", "parser": "nature",
                            "url": "https://example.org/ngeo",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_scan_numbers_and_groups(self):
        payload = jw.scan(
            config_file=self.config, fetcher=self.distinct_pages
        )
        self.assertEqual(payload["total"], 4)
        self.assertEqual([group["name"] for group in payload["groups"]],
                         ["Nature", "Nature Geoscience"])
        self.assertEqual([item["index"] for item in payload["candidates"]], [1, 2, 3, 4])
        self.assertEqual(payload["scanned"], 2)
        self.assertEqual(payload["pages"], 2)

    def test_scan_dedupes_same_doi(self):
        def fetcher(entry, url):
            return NATURE_PAGE

        payload = jw.scan(config_file=self.config, fetcher=fetcher)
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["total_found"], 2)

    def test_limit_is_round_robin(self):
        payload = jw.scan(
            config_file=self.config, fetcher=self.distinct_pages, limit=2
        )
        self.assertEqual(payload["total"], 2)
        self.assertEqual({item["journal_key"] for item in payload["candidates"]},
                         {"nature", "ngeo"})
        self.assertTrue(payload["truncated"])

    def test_days_filters_dated_entries_only(self):
        undated = """
        <article class="c-card">
          <h3 class="c-card__title"><a href="/articles/undated">Undated</a></h3>
        </article>
        """

        def fetcher(entry, url):
            return (NATURE_PAGE if entry["key"] == "nature" else NGEO_PAGE) + undated

        payload = jw.scan(
            config_file=self.config, fetcher=fetcher,
            days=1, today=datetime.date(2026, 10, 24),
        )
        self.assertEqual(payload["window"]["filtered"], 4)
        self.assertTrue(all(item["title"] == "Undated" for item in payload["candidates"]))
        self.assertTrue(any(item["sort_date"] == "" for item in payload["candidates"]))

    def test_error_and_challenge_status(self):
        def fetcher(entry, url):
            if entry["key"] == "nature":
                raise BrowserChallenge("请完成人机验证")
            raise RuntimeError("network down")

        payload = jw.scan(config_file=self.config, fetcher=fetcher)
        statuses = {status["key"]: status for status in payload["journals"]}
        self.assertEqual(statuses["nature"]["status"], "challenge")
        self.assertEqual(statuses["ngeo"]["status"], "error")
        self.assertEqual(payload["total"], 0)

    def test_unknown_journal_key(self):
        with self.assertRaises(jw.ScanError):
            jw.scan(config_file=self.config, fetcher=lambda e, u: "", journal_keys=["x"])

    def test_translation_is_rendered_next_to_the_english_title(self):
        payload = jw.scan(
            config_file=self.config,
            fetcher=lambda entry, url: NATURE_PAGE,
            translate=True,
            translator=lambda title: "中文 " + title,
        )
        self.assertTrue(all(item["title_zh"] for item in payload["candidates"]))
        self.assertEqual(payload["translation"]["translated"], 2)
        markdown = jw.render_markdown(payload)
        self.assertIn("中文（机译）：中文 Mantle mixing", markdown)
        self.assertIn("仅供检索", markdown)
        console = jw.render_console(payload)
        self.assertIn("中文：中文 Mantle mixing", console)

    def test_scan_without_translation_has_no_chinese_line(self):
        payload = jw.scan(
            config_file=self.config, fetcher=lambda entry, url: NATURE_PAGE
        )
        self.assertFalse(payload["translation"]["enabled"])
        self.assertNotIn("中文（机译）", jw.render_markdown(payload))

    def test_render_stops_before_extraction(self):
        payload = jw.scan(
            config_file=self.config,
            fetcher=lambda entry, url: NATURE_PAGE,
            limit=1,
        )
        markdown = jw.render_markdown(payload)
        self.assertIn("候选清单，尚未精读", markdown)
        self.assertIn("不会触发任何抽取或写作", markdown)
        self.assertIn("回复要精读的编号", markdown)
        self.assertNotIn("--doi \"<选中的 DOI>\"", markdown.replace("`", ""))

        console = jw.render_console(payload)
        self.assertIn("脚本不会自动抽取", console)
        self.assertIn("[1]", console)

    def test_write_scan_writes_latest(self):
        payload = jw.scan(
            config_file=self.config,
            fetcher=lambda entry, url: NATURE_PAGE,
        )
        scan_dir = self.directory / "scan"
        with mock.patch.object(jw, "SCAN_DIR", scan_dir), \
                mock.patch.object(jw, "LATEST_MD", scan_dir / "latest.md"), \
                mock.patch.object(jw, "LATEST_JSON", scan_dir / "latest.json"):
            paths = jw.write_scan(payload)
        self.assertTrue(Path(paths["latest_markdown"]).is_file())
        self.assertTrue(Path(paths["latest_json"]).is_file())
        self.assertIn("候选清单", Path(paths["latest_markdown"]).read_text(encoding="utf-8"))


class InitTests(unittest.TestCase):
    def test_does_not_overwrite(self):
        directory = Path(tempfile.mkdtemp())
        shipped = directory / "journals.json"
        user = directory / "user" / "journals.json"
        shipped.write_text('{"journals": []}', encoding="utf-8")
        user.parent.mkdir()
        user.write_text('{"user": true}', encoding="utf-8")
        with mock.patch.object(jw, "DEFAULT_JOURNALS_PATH", shipped), \
                mock.patch.object(jw, "USER_JOURNALS_PATH", user):
            result = jw.init_user_config()
        self.assertFalse(result["created"])
        self.assertIn('"user": true', user.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
