#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Windows console regressions: GBK code pages, emoji and Store stubs.

A Chinese Windows console encodes pipes with cp936/GBK. Two bugs came out of
that: ``--check-note`` died with ``UnicodeEncodeError`` before it could
print a report, and every Chinese line the CLI printed was unreadable to an
agent that decodes UTF-8. These tests pin the fixes.
"""

import io
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from scripts import console  # noqa: E402

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Characters that cannot be encoded in cp936/GBK. They may only appear in
# strings that are written to a file with an explicit encoding="utf-8".
GBK_UNSAFE_ALLOWLIST = {
    ("scripts/note_check.py", "\U0001f4da"),  # INDEX.md document title
}


def _gbk_unsafe_characters(text):
    found = set()
    for char in text:
        if ord(char) < 0x80:
            continue
        try:
            char.encode("gbk")
        except UnicodeEncodeError:
            found.add(char)
    return found


class ConfigureStdioTests(unittest.TestCase):
    def test_reconfigures_a_gbk_pipe_to_utf8(self):
        original = sys.stdout
        buffer = io.BytesIO()
        fake = io.TextIOWrapper(buffer, encoding="gbk", errors="strict")
        sys.stdout = fake
        try:
            self.assertEqual(fake.encoding.lower().replace("-", ""), "gbk")
            console.configure_stdio()
            self.assertEqual(fake.encoding.lower().replace("-", ""), "utf8")
        finally:
            sys.stdout = original
            fake.detach()

    def test_is_idempotent_and_never_raises(self):
        self.assertIsInstance(console.configure_stdio(), bool)
        self.assertIsInstance(console.configure_stdio(), bool)

    def test_survives_a_stream_without_reconfigure(self):
        original = sys.stdout

        class Bare:
            encoding = "gbk"

            def write(self, _):
                return 0

            def flush(self):
                pass

        sys.stdout = Bare()
        try:
            console.configure_stdio()
        finally:
            sys.stdout = original

    def test_markers_are_ascii(self):
        for marker in (console.OK, console.FAIL, console.WARN, console.INFO,
                       console.ARROW, console.NOTE):
            marker.encode("ascii")


class ConsoleSourceTests(unittest.TestCase):
    def test_no_unencodable_character_in_python_sources(self):
        offenders = []
        for path in sorted(PROJECT_ROOT.rglob("*.py")):
            if any(part in {".venv", "build", "dist", ".git", "__pycache__"}
                   for part in path.parts):
                continue
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            for char in _gbk_unsafe_characters(path.read_text(encoding="utf-8")):
                if (relative, char) in GBK_UNSAFE_ALLOWLIST:
                    continue
                offenders.append("{}: U+{:04X}".format(relative, ord(char)))
        self.assertEqual(
            offenders, [],
            "These characters crash on a cp936 console: {}".format(", ".join(offenders)),
        )


class NoteCheckPrintTests(unittest.TestCase):
    def test_report_prints_on_a_gbk_console(self):
        from scripts import note_check

        original = sys.stdout
        buffer = io.BytesIO()
        fake = io.TextIOWrapper(buffer, encoding="gbk", errors="strict")
        sys.stdout = fake
        try:
            console.configure_stdio()
            note_check.print_report({
                "note": "papers/demo.md",
                "images": 3,
                "errors": 0,
                "warnings": 0,
                "issues": [],
                "citations": {"external": 10, "target": 10, "depth": "deep",
                              "max_table_rows": 6, "external_dois": 10},
            })
            fake.flush()
            text = buffer.getvalue().decode("utf-8")
        finally:
            sys.stdout = original
            fake.detach()

        self.assertIn("papers/demo.md", text)
        self.assertIn("[OK]", text)


class StoreAliasTests(unittest.TestCase):
    def test_store_alias_launchers_returns_a_list(self):
        result = console.store_alias_launchers()
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIn("name", item)
            self.assertIn("path", item)

    def test_interpreter_is_store_alias_returns_bool(self):
        self.assertIsInstance(console.interpreter_is_store_alias(), bool)


if __name__ == "__main__":
    unittest.main()
