#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the Chinese-title cache and post-editing."""

import json
import tempfile
import unittest
from pathlib import Path

from scripts import translate as tr


class PostEditTests(unittest.TestCase):
    def test_clean_strips_escaped_inline_markup(self):
        self.assertEqual(
            tr._clean("NH&lt;sub&gt;4&lt;/sub&gt;-Smectites"),
            "NH4-Smectites",
        )

    def test_fugacity_is_corrected(self):
        self.assertEqual(
            tr._post_edit(
                "Progressive oxidative weathering raised sub-arc mantle fugacity",
                "渐进氧化风化提高了亚弧地幔逸散性",
            ),
            "渐进氧化风化提高了弧下地幔逸度",
        )

    def test_unrelated_title_is_untouched(self):
        self.assertEqual(
            tr._post_edit("A new mineral from Mars", "来自火星的一种新矿物"),
            "来自火星的一种新矿物",
        )

    def test_rule_only_fires_for_matching_english(self):
        self.assertEqual(
            tr._post_edit("Mantle convection", "地幔分层"),
            "地幔分层",
        )
        self.assertEqual(
            tr._post_edit("Craton delamination", "克拉通分层"),
            "克拉通拆沉",
        )


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.cache = self.directory / "translations.json"

    def test_translates_missing_titles_and_reuses_cache(self):
        calls = []

        def fake(title):
            calls.append(title)
            return "译文：" + title

        first, meta = tr.translate_titles(
            ["Mantle mixing", "Core formation"], self.cache, translator=fake
        )
        self.assertEqual(len(calls), 2)
        self.assertEqual(first["Mantle mixing"], "译文：Mantle mixing")
        self.assertEqual(meta["translated"], 2)
        self.assertEqual(meta["missing"], 0)

        calls.clear()
        second, meta = tr.translate_titles(
            ["Mantle mixing", "Core formation", "New paper"], self.cache, translator=fake
        )
        self.assertEqual(calls, ["New paper"])
        self.assertEqual(meta["cached"], 2)
        self.assertEqual(meta["translated"], 1)
        self.assertEqual(second["New paper"], "译文：New paper")

    def test_failed_title_is_reported_and_not_cached(self):
        def broken(title):
            raise tr.TranslationError("rate limited")

        mapping, meta = tr.translate_titles(
            ["Mantle mixing"], self.cache, translator=broken
        )
        self.assertEqual(mapping, {})
        self.assertEqual(meta["missing"], 1)
        self.assertTrue(meta["error"])
        self.assertFalse(self.cache.exists())

    def test_duplicate_titles_are_translated_once(self):
        calls = []

        def fake(title):
            calls.append(title)
            return "译文"

        mapping, meta = tr.translate_titles(
            ["Same title", " Same  title ", "Same title"],
            self.cache,
            translator=fake,
        )
        self.assertEqual(calls, ["Same title"])
        self.assertEqual(mapping["Same title"], "译文")
        self.assertEqual(meta["translated"], 1)

    def test_cache_file_is_valid_json(self):
        tr.translate_titles(["One"], self.cache, translator=lambda title: "一")
        payload = json.loads(self.cache.read_text(encoding="utf-8"))
        self.assertEqual(payload["titles"]["One"], "一")
        self.assertEqual(payload["version"], tr.CACHE_VERSION)


if __name__ == "__main__":
    unittest.main()
