#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the ordered environment scan (uv -> conda -> venv -> python)."""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import environment as envmod


class ScanOrderTests(unittest.TestCase):
    def test_four_candidates_in_fixed_order(self):
        candidates = envmod.scan_environments()
        self.assertEqual(
            [c["kind"] for c in candidates],
            ["uv", "conda", "venv", "python"],
        )

    def test_order_constant_is_the_documented_one(self):
        self.assertEqual(envmod.ENVIRONMENT_ORDER, ("uv", "conda", "venv", "python"))

    def test_every_candidate_has_a_command_shape(self):
        for candidate in envmod.scan_environments():
            self.assertIn("kind", candidate)
            self.assertIn("available", candidate)
            self.assertIn("run_command", candidate)
            self.assertIn("setup_command", candidate)
            self.assertIn("detail", candidate)


class UvCandidateTests(unittest.TestCase):
    def test_uv_on_path_is_available_with_sync_setup(self):
        with mock.patch.object(envmod, "_which", side_effect=lambda n: "/usr/bin/uv" if n == "uv" else None):
            with mock.patch.object(envmod, "_run_version", return_value="uv 0.10.11"):
                with mock.patch.object(envmod, "_venv_executable", return_value=None):
                    candidate = envmod._uv_candidate(Path("/tmp/project"))
        self.assertTrue(candidate["available"])
        self.assertEqual(candidate["run_command"], "uv run python main.py")
        self.assertEqual(candidate["setup_command"], "uv sync")
        self.assertIn("0.10.11", candidate["version"])

    def test_uv_absent(self):
        with mock.patch.object(envmod, "_which", return_value=None):
            candidate = envmod._uv_candidate(Path("/tmp/project"))
        self.assertFalse(candidate["available"])


class CondaCandidateTests(unittest.TestCase):
    def test_active_conda_env_uses_plain_python(self):
        environ = {"CONDA_PREFIX": "/opt/conda/envs/geo", "CONDA_DEFAULT_ENV": "geo"}
        with mock.patch.dict(os.environ, environ, clear=False):
            with mock.patch.object(envmod, "_which", return_value="/opt/conda/bin/conda"):
                candidate = envmod._conda_candidate()
        self.assertTrue(candidate["available"])
        self.assertTrue(candidate["active"])
        self.assertEqual(candidate["run_command"], "python main.py")
        self.assertIn("geo", candidate["detail"])

    def test_conda_installed_but_not_active(self):
        environ = {k: v for k, v in os.environ.items() if k != "CONDA_PREFIX"}
        with mock.patch.dict(os.environ, environ, clear=True):
            with mock.patch.object(envmod, "_which", return_value="/opt/conda/bin/conda"):
                candidate = envmod._conda_candidate()
        self.assertTrue(candidate["available"])
        self.assertFalse(candidate["active"])
        self.assertIn("conda run", candidate["run_command"])

    def test_conda_absent(self):
        environ = {k: v for k, v in os.environ.items() if k != "CONDA_PREFIX"}
        with mock.patch.dict(os.environ, environ, clear=True):
            with mock.patch.object(envmod, "_which", return_value=None):
                candidate = envmod._conda_candidate()
        self.assertFalse(candidate["available"])


class VenvCandidateTests(unittest.TestCase):
    def test_project_local_venv_is_found(self):
        root = Path("/tmp/project")
        exe = root / ("Scripts" if envmod.WIN else "bin") / "python.exe"
        with mock.patch.object(envmod, "_venv_executable", return_value=str(exe)):
            with mock.patch.object(sys, "prefix", "/other"):
                with mock.patch.object(sys, "base_prefix", "/other"):
                    candidate = envmod._venv_candidate(root)
        self.assertTrue(candidate["available"])
        self.assertIn("main.py", candidate["run_command"])

    def test_activated_venv_is_detected(self):
        with mock.patch.object(envmod, "_venv_executable", return_value=None):
            with mock.patch.object(sys, "prefix", "/tmp/venv"):
                with mock.patch.object(sys, "base_prefix", "/usr"):
                    candidate = envmod._venv_candidate(Path("/tmp/project"))
        self.assertTrue(candidate["available"])
        self.assertTrue(candidate["active"])
        self.assertEqual(candidate["run_command"], "python main.py")

    def test_no_venv_anywhere(self):
        with mock.patch.object(envmod, "_venv_executable", return_value=None):
            with mock.patch.object(sys, "prefix", "/usr"):
                with mock.patch.object(sys, "base_prefix", "/usr"):
                    candidate = envmod._venv_candidate(Path("/tmp/project"))
        self.assertFalse(candidate["available"])


class PythonCandidateTests(unittest.TestCase):
    def test_store_alias_is_not_usable_python(self):
        alias = r"C:\Users\x\AppData\Local\Microsoft\WindowsApps\python3.exe"

        def fake_which(name):
            return alias if name in ("python", "python3") else None

        with mock.patch.object(envmod, "_which", side_effect=fake_which):
            candidate = envmod._python_candidate()
        self.assertFalse(candidate["available"])
        self.assertIn("Store", candidate["detail"])

    def test_usable_python(self):
        with mock.patch.object(envmod, "_which", side_effect=lambda n: "/usr/bin/python3" if n == "python3" else None):
            candidate = envmod._python_candidate()
        self.assertTrue(candidate["available"])
        self.assertIn("main.py", candidate["run_command"])


class ActiveEnvironmentTests(unittest.TestCase):
    def test_system_python(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(sys, "prefix", "/usr"):
                with mock.patch.object(sys, "base_prefix", "/usr"):
                    active = envmod.active_environment()
        self.assertEqual(active["kind"], "system")

    def test_conda_wins_over_venv(self):
        with mock.patch.dict(os.environ, {"CONDA_PREFIX": "/opt/conda/envs/geo"}, clear=False):
            active = envmod.active_environment()
        self.assertEqual(active["kind"], "conda")


class RecommendationTests(unittest.TestCase):
    def _patched(self, candidates, active, packages):
        return mock.patch.multiple(
            envmod,
            scan_environments=mock.DEFAULT,
            active_environment=mock.Mock(return_value=active),
            probe_modules=mock.Mock(return_value=packages),
        )

    def test_active_conda_env_with_dependencies_wins(self):
        packages = {"present": ["requests"], "missing": [], "ok": True}
        with mock.patch.object(envmod, "scan_environments", return_value=[]):
            with mock.patch.object(envmod, "active_environment", return_value={
                "kind": "conda", "name": "geo", "prefix": "/opt/geo", "executable": "/opt/geo/bin/python"
            }):
                with mock.patch.object(envmod, "probe_modules", return_value=packages):
                    detected = envmod.detect_environment()
        self.assertEqual(detected["recommended"]["kind"], "conda")
        self.assertEqual(detected["recommended"]["run_command"], "python main.py")

    def test_uv_is_recommended_when_nothing_is_active(self):
        packages = {"present": [], "missing": ["requests"], "ok": False}
        uv = {"kind": "uv", "available": True, "run_command": "uv run python main.py",
              "setup_command": "uv sync", "detail": "uv available"}
        with mock.patch.object(envmod, "scan_environments", return_value=[uv]):
            with mock.patch.object(envmod, "active_environment", return_value={
                "kind": "system", "name": "", "prefix": "/usr", "executable": "/usr/bin/python3"
            }):
                with mock.patch.object(envmod, "probe_modules", return_value=packages):
                    detected = envmod.detect_environment()
        self.assertEqual(detected["recommended"]["kind"], "uv")
        self.assertTrue(detected["notes"], "missing dependencies should produce a note")

    def test_no_environment_at_all_still_returns_something(self):
        with mock.patch.object(envmod, "scan_environments", return_value=[]):
            with mock.patch.object(envmod, "active_environment", return_value={
                "kind": "system", "name": "", "prefix": "/usr", "executable": "/usr/bin/python3"
            }):
                with mock.patch.object(envmod, "probe_modules", return_value={
                    "present": [], "missing": ["requests"], "ok": False
                }):
                    detected = envmod.detect_environment()
        self.assertEqual(detected["recommended"]["kind"], "python")
        self.assertIn("main.py", detected["recommended"]["run_command"])


class ReportTests(unittest.TestCase):
    def test_report_lists_every_candidate(self):
        detected = {
            "candidates": [
                {"kind": "uv", "available": True, "active": False, "detail": "ok"},
                {"kind": "conda", "available": False, "active": False, "detail": "none"},
            ],
            "recommended": {"run_command": "uv run python main.py", "reason": "uv", "setup_command": "uv sync"},
        }
        text = envmod.format_environment_report(detected)
        self.assertIn("uv", text)
        self.assertIn("conda", text)
        self.assertIn("uv run python main.py", text)
        self.assertIn("uv sync", text)


if __name__ == "__main__":
    unittest.main()
