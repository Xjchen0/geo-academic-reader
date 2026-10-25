# -*- coding: utf-8 -*-
"""Tests for the polite HTTP JSON client.

Runs with either ``python3 -m unittest discover tests`` or ``pytest tests``.
"""

import unittest
from unittest import mock

from scripts import http_json


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self):
        if self._payload is None:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload


class FakeSession:
    """A session whose responses are scripted, one per call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        if not self.responses:
            raise AssertionError("unexpected extra request")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class RequestJsonTests(unittest.TestCase):
    def setUp(self):
        http_json.reset_rate_limit()

    def test_a_successful_call_returns_the_payload(self):
        session = FakeSession([FakeResponse(200, {"message": {"title": ["T"]}})])
        result = http_json.request_json(
            "https://example.org", session=session, delay=0, retries=2
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["message"]["title"], ["T"])
        self.assertEqual(result["attempts"], 1)

    def test_a_rate_limited_call_is_retried(self):
        session = FakeSession([
            FakeResponse(429, None, text="slow down"),
            FakeResponse(200, {"message": {}}),
        ])
        slept = []
        result = http_json.request_json(
            "https://example.org",
            session=session,
            sleeper=slept.append,
            backoff=2.0,
            retries=3,
            delay=0,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(len(session.calls), 2)
        self.assertTrue(slept)

    def test_a_persistent_rate_limit_reports_the_kind(self):
        session = FakeSession([
            FakeResponse(429, None, text="slow down"),
            FakeResponse(429, None, text="slow down"),
        ])
        result = http_json.request_json(
            "https://example.org",
            session=session,
            sleeper=lambda _s: None,
            backoff=1.0,
            retries=2,
            delay=0,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["kind"], http_json.KIND_RATE_LIMITED)
        self.assertEqual(result["status"], 429)
        self.assertTrue(http_json.is_transient(result["kind"]))

    def test_a_missing_record_is_not_retried(self):
        session = FakeSession([FakeResponse(404, None, text="not found")])
        result = http_json.request_json(
            "https://example.org",
            session=session,
            sleeper=lambda _s: None,
            retries=4,
            delay=0,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["kind"], http_json.KIND_NOT_FOUND)
        self.assertEqual(len(session.calls), 1)
        self.assertFalse(http_json.is_transient(result["kind"]))

    def test_a_non_json_body_is_reported_instead_of_raising(self):
        session = FakeSession([FakeResponse(200, None, text="<html>429 Too Many</html>")])
        result = http_json.request_json(
            "https://example.org",
            session=session,
            sleeper=lambda _s: None,
            retries=1,
            delay=0,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["kind"], http_json.KIND_BAD_JSON)
        self.assertIn("不是 JSON", result["error"])

    def test_a_network_error_is_retried_and_reported(self):
        session = FakeSession([IOError("boom"), IOError("boom")])
        result = http_json.request_json(
            "https://example.org",
            session=session,
            sleeper=lambda _s: None,
            retries=2,
            delay=0,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["kind"], http_json.KIND_NETWORK)
        self.assertTrue(http_json.is_transient(result["kind"]))

    def test_retry_after_is_honoured(self):
        session = FakeSession([
            FakeResponse(429, None, text="", headers={"Retry-After": "7"}),
            FakeResponse(200, {"message": {}}),
        ])
        slept = []
        http_json.request_json(
            "https://example.org",
            session=session,
            sleeper=slept.append,
            retries=3,
            delay=0,
        )
        self.assertIn(7.0, slept)

    def test_calls_are_spaced_out(self):
        session = FakeSession([
            FakeResponse(200, {"a": 1}),
            FakeResponse(200, {"b": 2}),
        ])
        slept = []
        http_json.request_json(
            "https://example.org",
            session=session,
            sleeper=slept.append,
            delay=0.25,
            retries=1,
        )
        http_json.request_json(
            "https://example.org",
            session=session,
            sleeper=slept.append,
            delay=0.25,
            retries=1,
        )
        # The gap is applied between requests, so a second call waits for the
        # courtesy delay to expire. That is what keeps a 25-item
        # verification run out of the throttled bucket.
        self.assertTrue(any(value > 0 for value in slept))


class HeaderTests(unittest.TestCase):
    def test_the_user_agent_names_the_project(self):
        headers = http_json.build_headers()
        self.assertIn("geo-academic-reader", headers["User-Agent"])

    def test_a_mailto_is_added_when_the_user_gave_one(self):
        headers = http_json.build_headers("reader@example.org")
        self.assertIn("mailto:reader@example.org", headers["User-Agent"])
        self.assertEqual(headers["From"], "reader@example.org")

    def test_the_mailto_is_also_sent_as_a_query_parameter(self):
        session = FakeSession([FakeResponse(200, {})])
        http_json.request_json(
            "https://example.org",
            params={"query": "x"},
            mailto="reader@example.org",
            session=session,
            delay=0,
            retries=1,
        )
        self.assertEqual(session.calls[0]["params"]["mailto"], "reader@example.org")


class FetchCrossrefMetadataTests(unittest.TestCase):
    """The Crossref helper must never raise and must name the failure."""

    def _fetch(self, response):
        from scripts import fetch_paper

        session = FakeSession([response])
        with mock.patch.object(fetch_paper.requests, "get", session.get):
            return fetch_paper.fetch_crossref_metadata("10.1000/x")

    def test_a_resolved_doi_returns_metadata(self):
        result = self._fetch(
            FakeResponse(200, {"message": {"title": ["The title"], "issued": {"date-parts": [[2020]]}}})
        )
        self.assertEqual(result["title"], "The title")
        self.assertEqual(result["year"], "2020")
        self.assertEqual(result["error"], "")

    def test_a_missing_doi_reports_not_found(self):
        result = self._fetch(FakeResponse(404, None, text="404"))
        self.assertTrue(result["error"])
        self.assertEqual(result["error_kind"], http_json.KIND_NOT_FOUND)

    def test_a_record_without_a_title_is_not_verified(self):
        result = self._fetch(FakeResponse(200, {"message": {"issued": {"date-parts": [[2020]]}}}))
        self.assertTrue(result["error"])
        self.assertEqual(result["error_kind"], "incomplete")
        self.assertEqual(result.get("title", ""), "")


if __name__ == "__main__":
    unittest.main()
