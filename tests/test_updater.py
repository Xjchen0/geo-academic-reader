#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for version comparison and the preference-preserving updater."""

import io
import json
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import updater


def _release(tag, prerelease=False, draft=False):
    return {
        "tag_name": tag,
        "name": tag,
        "html_url": "https://example.invalid/{}".format(tag),
        "published_at": "2026-10-24T00:00:00Z",
        "prerelease": prerelease,
        "draft": draft,
        "body": "",
    }


class VersionTests(unittest.TestCase):
    def test_prerelease_sorts_before_final(self):
        self.assertLess(updater.parse_version("0.3.0-pre.1"), updater.parse_version("0.3.0"))
        self.assertLess(updater.parse_version("0.3.0"), updater.parse_version("0.3.1"))
        self.assertLess(updater.parse_version("0.3.1"), updater.parse_version("0.10.0"))

    def test_post_release_preview_does_not_offer_its_final_as_update(self):
        self.assertFalse(updater.is_newer("0.4.0", "0.4.0-pre"))
        self.assertTrue(updater.is_newer("0.4.1", "0.4.0-pre"))
        self.assertTrue(updater.is_newer("0.4.0-pre.2", "0.4.0-pre"))

    def test_preview_is_offered_only_on_the_prerelease_channel(self):
        self.assertFalse(updater.has_update("0.4.0-pre", "0.4.0"))
        self.assertTrue(updater.has_update("0.4.0-pre", "0.4.0", include_prerelease=True))
        self.assertFalse(updater.has_update("0.4.0", "0.4.0-pre"))

    def test_v_prefix_and_patch_bump(self):
        self.assertEqual(updater.compare_versions("v0.3.1", "0.3.1"), 0)
        self.assertEqual(updater.bump_patch("0.3.0"), "0.3.1")
        self.assertEqual(updater.bump_patch("0.3.0-pre.1"), "0.3.1")

    def test_invalid_version_is_rejected(self):
        with self.assertRaises(ValueError):
            updater.parse_version("not-a-version")


class ReleaseSelectionTests(unittest.TestCase):
    def test_stable_channel_ignores_prereleases(self):
        releases = [_release("v0.4.0-pre.1", prerelease=True), _release("v0.3.1")]
        chosen = updater.select_release(releases)
        self.assertEqual(chosen["tag_name"], "v0.3.1")

    def test_prerelease_channel_picks_highest(self):
        releases = [_release("v0.3.1"), _release("v0.4.0-pre.1", prerelease=True)]
        chosen = updater.select_release(releases, include_prerelease=True)
        self.assertEqual(chosen["tag_name"], "v0.4.0-pre.1")

    def test_drafts_are_ignored(self):
        releases = [_release("v0.9.0", draft=True), _release("v0.3.1")]
        self.assertEqual(updater.select_release(releases)["tag_name"], "v0.3.1")

    def test_prerelease_channel_prefers_the_newest_publication(self):
        final = _release("v0.4.0")
        final["published_at"] = "2026-10-20T00:00:00Z"
        preview = _release("v0.4.0-pre", prerelease=True)
        preview["published_at"] = "2026-10-25T00:00:00Z"
        self.assertEqual(
            updater.select_release([final, preview], include_prerelease=True)["tag_name"],
            "v0.4.0-pre",
        )
        self.assertEqual(updater.select_release([final, preview])["tag_name"], "v0.4.0")


class CacheTests(unittest.TestCase):
    def test_network_result_is_cached_and_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            guide = Path(temp) / ".geo-reader"
            guide.mkdir()
            with mock.patch.object(updater, "GUIDE_DIR", guide), \
                 mock.patch.object(updater, "CACHE_PATH", guide / "update-check.json"), \
                 mock.patch.object(updater, "fetch_releases", return_value=[_release("v0.3.1")]) as fetch:
                first = updater.check_for_update(current="0.3.0")
                self.assertTrue(first["has_update"])
                second = updater.check_for_update(current="0.3.0")
                self.assertEqual(second["source"], "cache")
                self.assertEqual(fetch.call_count, 1)

    def test_offline_is_graceful_and_exit_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            guide = Path(temp) / ".geo-reader"
            guide.mkdir()
            with mock.patch.object(updater, "GUIDE_DIR", guide), \
                 mock.patch.object(updater, "CACHE_PATH", guide / "update-check.json"), \
                 mock.patch.object(updater, "fetch_releases", side_effect=OSError("offline")):
                payload = updater.check_for_update(current="0.3.1")
            self.assertFalse(payload["reachable"])
            self.assertIn("跳过更新检查", updater.format_check(payload))


class PayloadCopyTests(unittest.TestCase):
    def test_copy_skips_user_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src"
            target = root / "dst"
            (source / "scripts").mkdir(parents=True)
            (source / "scripts" / "version.py").write_text('__version__ = "0.3.1"\n', encoding="utf-8")
            (source / "papers").mkdir()
            (source / "papers" / "upstream.md").write_text("upstream", encoding="utf-8")
            (source / ".geo-reader").mkdir()
            (source / ".geo-reader" / "profile.json").write_text("{}", encoding="utf-8")
            (source / "input_pdfs").mkdir()
            (source / "input_pdfs" / "paper.pdf").write_bytes(b"%PDF")
            (target / "papers").mkdir(parents=True)
            (target / "papers" / "mine.md").write_text("mine", encoding="utf-8")
            (target / ".geo-reader").mkdir()
            (target / ".geo-reader" / "profile.json").write_text('{"language": "zh-CN"}', encoding="utf-8")

            with mock.patch.object(updater, "PROJECT_ROOT", target):
                copied = updater._copy_payload(source, lambda *_a, **_k: None)

            self.assertIn("scripts", copied)
            self.assertNotIn("papers", copied)
            self.assertEqual((target / "papers" / "mine.md").read_text(encoding="utf-8"), "mine")
            self.assertFalse((target / "papers" / "upstream.md").exists())
            self.assertEqual(
                json.loads((target / ".geo-reader" / "profile.json").read_text(encoding="utf-8")),
                {"language": "zh-CN"},
            )
            self.assertEqual(
                (target / "scripts" / "version.py").read_text(encoding="utf-8"),
                '__version__ = "0.3.1"\n',
            )


class UpdateFlowTests(unittest.TestCase):
    def _tarball(self, version="0.3.1") -> bytes:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            def add(name, content):
                data = content.encode("utf-8")
                info = tarfile.TarInfo(name="geo-academic-reader-{}/{}".format(version, name))
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))

            add("scripts/version.py", '__version__ = "{}"\n'.format(version))
            add("papers/from-upstream.md", "should not be copied")
            add(".geo-reader/profile.json", '{"language": "en"}')
        return buffer.getvalue()

    def test_update_preserves_profile_notes_and_raw(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            (project / "papers").mkdir(parents=True)
            (project / "papers" / "mine.md").write_text("my note", encoding="utf-8")
            (project / ".raw" / "pack").mkdir(parents=True)
            (project / ".raw" / "pack" / "paper.json").write_text("{}", encoding="utf-8")
            (project / "input_pdfs").mkdir()
            (project / "input_pdfs" / "mine.pdf").write_bytes(b"%PDF")
            guide = project / ".geo-reader"
            guide.mkdir()
            profile = guide / "profile.json"
            original = '{"language": "zh-CN", "created_at": "2026-01-01T00:00:00+08:00"}'
            profile.write_text(original, encoding="utf-8")

            check = {
                "reachable": True,
                "has_update": True,
                "current": "0.3.0",
                "latest_version": "0.3.1",
                "latest_tag": "v0.3.1",
            }
            with mock.patch.object(updater, "PROJECT_ROOT", project), \
                 mock.patch.object(updater, "GUIDE_DIR", guide), \
                 mock.patch.object(updater, "CACHE_PATH", guide / "update-check.json"), \
                 mock.patch.object(updater, "PROFILE_PATH", profile), \
                 mock.patch.object(updater, "check_for_update", return_value=check), \
                 mock.patch.object(updater, "_git_available", return_value=False), \
                 mock.patch.object(updater.shutil, "which", return_value=None), \
                 mock.patch.object(updater, "_download_tarball", return_value=self._tarball()):
                result = updater.update_workspace(log=lambda *_a, **_k: None)

            self.assertTrue(result["updated"], result)
            self.assertEqual(result["method"], "tarball")
            self.assertEqual(profile.read_text(encoding="utf-8"), original)
            self.assertEqual((project / "papers" / "mine.md").read_text(encoding="utf-8"), "my note")
            self.assertFalse((project / "papers" / "from-upstream.md").exists())
            self.assertEqual((project / ".raw" / "pack" / "paper.json").read_text(encoding="utf-8"), "{}")
            self.assertTrue((project / "scripts" / "version.py").is_file())
            self.assertTrue(list((guide / "backups").glob("profile-*.json")))

    def test_dirty_git_tree_is_refused_without_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "papers").mkdir()
            (project / "papers" / "mine.md").write_text("my note", encoding="utf-8")
            guide = project / ".geo-reader"
            guide.mkdir()
            profile = guide / "profile.json"
            profile.write_text('{"language": "zh-CN"}', encoding="utf-8")
            check = {
                "reachable": True,
                "has_update": True,
                "current": "0.3.0",
                "latest_version": "0.3.1",
                "latest_tag": "v0.3.1",
            }
            with mock.patch.object(updater, "PROJECT_ROOT", project), \
                 mock.patch.object(updater, "GUIDE_DIR", guide), \
                 mock.patch.object(updater, "CACHE_PATH", guide / "update-check.json"), \
                 mock.patch.object(updater, "PROFILE_PATH", profile), \
                 mock.patch.object(updater, "check_for_update", return_value=check), \
                 mock.patch.object(updater, "_git_available", return_value=True), \
                 mock.patch.object(updater, "_git_tracked_changes", return_value=" M main.py"):
                result = updater.update_workspace(log=lambda *_a, **_k: None)

            self.assertFalse(result["updated"])
            self.assertIn("未提交", result["error"])
            self.assertEqual(profile.read_text(encoding="utf-8"), '{"language": "zh-CN"}')

    @unittest.skipUnless(shutil.which("git"), "git is required")
    def test_git_checkout_fast_forwards_and_keeps_untracked_data(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "repo"
            project.mkdir()

            def git(*args):
                subprocess.run(
                    ["git"] + list(args), cwd=str(project), check=True,
                    capture_output=True, text=True,
                )

            git("init")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "Test")
            (project / "version.txt").write_text("0.3.0\n", encoding="utf-8")
            git("add", "version.txt")
            git("commit", "-m", "old")
            git("tag", "v0.3.0")
            (project / "version.txt").write_text("0.3.1\n", encoding="utf-8")
            git("add", "version.txt")
            git("commit", "-m", "new")
            git("tag", "v0.3.1")
            git("checkout", "--detach", "v0.3.0")

            (project / "papers").mkdir()
            (project / "papers" / "mine.md").write_text("my note", encoding="utf-8")
            guide = project / ".geo-reader"
            guide.mkdir()
            profile = guide / "profile.json"
            profile.write_text('{"language": "zh-CN"}', encoding="utf-8")

            check = {
                "reachable": True,
                "has_update": True,
                "current": "0.3.0",
                "latest_version": "0.3.1",
                "latest_tag": "v0.3.1",
            }
            with mock.patch.object(updater, "PROJECT_ROOT", project), \
                 mock.patch.object(updater, "GUIDE_DIR", guide), \
                 mock.patch.object(updater, "CACHE_PATH", guide / "update-check.json"), \
                 mock.patch.object(updater, "PROFILE_PATH", profile), \
                 mock.patch.object(updater, "check_for_update", return_value=check):
                result = updater.update_workspace(log=lambda *_a, **_k: None)

            self.assertTrue(result["updated"], result)
            self.assertEqual(result["method"], "git")
            self.assertEqual((project / "version.txt").read_text(encoding="utf-8"), "0.3.1\n")
            self.assertEqual(profile.read_text(encoding="utf-8"), '{"language": "zh-CN"}')
            self.assertEqual((project / "papers" / "mine.md").read_text(encoding="utf-8"), "my note")


if __name__ == "__main__":
    unittest.main()
