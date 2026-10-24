#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the session preflight contract and its gate."""

import datetime
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import preflight
from scripts.version import __version__


def _marker(checked_at=None, version=None, ok=True, profile=True):
    return {
        "version": version or __version__,
        "checked_at": (checked_at or datetime.datetime.now().astimezone()).isoformat(
            timespec="seconds"
        ),
        "ok": ok,
        "profile": {"exists": profile},
    }


class RoleTests(unittest.TestCase):
    def test_clean_tree_is_code_repository(self):
        self.assertEqual(preflight.classify_role(False, 0, 0), "code")

    def test_any_local_data_means_test_workspace(self):
        self.assertEqual(preflight.classify_role(True, 0, 0), "test")
        self.assertEqual(preflight.classify_role(False, 1, 0), "test")
        self.assertEqual(preflight.classify_role(False, 0, 1), "test")


class DocumentTests(unittest.TestCase):
    def test_missing_and_present_docs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "AGENTS.md").write_text("contract", encoding="utf-8")
            status = preflight.document_status(root)
            self.assertTrue(status["AGENTS.md"]["exists"])
            self.assertEqual(status["AGENTS.md"]["bytes"], 8)
            self.assertFalse(status["MEMORY.md"]["exists"])


class MarkerTests(unittest.TestCase):
    def test_fresh_marker_passes(self):
        self.assertTrue(preflight.marker_is_fresh(_marker(version="0.4.0"), version="0.4.0"))

    def test_stale_marker_is_rejected(self):
        old = datetime.datetime.now().astimezone() - datetime.timedelta(hours=25)
        self.assertFalse(preflight.marker_is_fresh(_marker(old, version="0.4.0"), version="0.4.0"))

    def test_version_mismatch_is_rejected(self):
        self.assertFalse(preflight.marker_is_fresh(_marker(version="0.3.9"), version="0.4.0"))

    def test_failed_marker_is_rejected(self):
        self.assertFalse(
            preflight.marker_is_fresh(_marker(ok=False, version="0.4.0"), version="0.4.0")
        )

    def test_missing_or_corrupt_marker_is_rejected(self):
        self.assertFalse(preflight.marker_is_fresh(None))
        self.assertFalse(preflight.marker_is_fresh({"checked_at": "not-a-date"}))


class GateTests(unittest.TestCase):
    def test_gate_allows_fresh_marker_with_profile(self):
        with mock.patch.object(preflight, "read_marker", return_value=_marker()):
            with mock.patch.object(preflight, "marker_is_fresh", return_value=True):
                self.assertTrue(preflight.gate_status()["allowed"])

    def test_gate_blocks_without_marker(self):
        with mock.patch.object(preflight, "read_marker", return_value=None):
            status = preflight.gate_status()
            self.assertFalse(status["allowed"])
            self.assertEqual(status["reason"], "preflight_missing")

    def test_gate_blocks_when_profile_was_missing_at_check_time(self):
        with mock.patch.object(preflight, "read_marker", return_value=_marker(profile=False)):
            with mock.patch.object(preflight, "marker_is_fresh", return_value=True):
                status = preflight.gate_status()
                self.assertFalse(status["allowed"])
                self.assertEqual(status["reason"], "profile_missing")


class RoundTripTests(unittest.TestCase):
    def test_write_and_read_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preflight.json"
            with mock.patch.object(preflight, "MARKER_PATH", path):
                preflight.write_marker({"version": "0.4.0", "ok": True})
                self.assertEqual(preflight.read_marker()["version"], "0.4.0")
                self.assertTrue(json.loads(path.read_text(encoding="utf-8"))["ok"])


if __name__ == "__main__":
    unittest.main()
