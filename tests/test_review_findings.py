"""Regression tests for defects found by an independent review on 2026-11-10.

Each test failed against the code as first written. No test touches the network.
"""

import email.message
import http.client
import unittest
import urllib.request
from unittest import mock

from review_intelligence import llm_extract
from review_intelligence.collectors.fetch import fetch_page
from review_intelligence.evaluate import GoldenReplayProvider, evaluate_provider
from review_intelligence.llm_extract import EXTRACTION_SCHEMA, AnthropicProvider, ProviderError


# ---------------------------------------------------------------------------
# Finding 1: _urlopen_transport only wraps errors raised by urlopen() itself.
# Errors raised while reading the body escape as raw exceptions, so one
# dropped connection kills a whole llm-eval run instead of becoming a
# provider_error rejection.
# ---------------------------------------------------------------------------


class _BodyReadFails:
    """Context manager returned by a patched urlopen whose read() raises."""

    def __init__(self, error):
        self._error = error

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        raise self._error


class TransportErrorTests(unittest.TestCase):
    def test_errors_while_reading_the_body_become_provider_errors(self):
        provider = AnthropicProvider(api_key="test-key", model="test-model")
        for error in (
            ConnectionResetError(104, "Connection reset by peer"),
            http.client.IncompleteRead(b"{\"stop_reason\""),
        ):
            with self.subTest(error=type(error).__name__):
                with mock.patch.object(llm_extract, "urlopen", return_value=_BodyReadFails(error)):
                    with self.assertRaises(ProviderError):
                        provider("system text", "user text", EXTRACTION_SCHEMA)


# ---------------------------------------------------------------------------
# Finding 2: fetch_page retrieves robots.txt with RobotFileParser.read(), which
# calls urllib.request.urlopen directly: no allowlist on redirect hops, no
# timeout, and the default Python User-Agent. The guarded opener is only used
# for the page itself.
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, url, body, content_type):
        self.url = url
        self.status = 200
        self._body = body
        self.headers = email.message.Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def geturl(self):
        return self.url

    def read(self, amount=-1):
        if amount is None or amount < 0:
            return self._body
        return self._body[:amount]


class _FakeOpener:
    """Serves robots.txt and one HTML page; records every URL and timeout it was asked for."""

    def __init__(self):
        self.opened = []

    def open(self, request, timeout=None):
        url = request.full_url if isinstance(request, urllib.request.Request) else str(request)
        self.opened.append((url, timeout))
        if url.endswith("/robots.txt"):
            return _FakeResponse(url, b"User-agent: *\nAllow: /\n", "text/plain")
        return _FakeResponse(url, b"<html><body>review body</body></html>", "text/html")


class RobotsFetchGuardTests(unittest.TestCase):
    def test_robots_txt_is_fetched_through_the_guarded_opener_with_a_timeout(self):
        opener = _FakeOpener()
        direct_calls = []

        def unguarded_urlopen(url, *args, **kwargs):
            direct_calls.append(url if isinstance(url, str) else url.full_url)
            return _FakeResponse(str(url), b"User-agent: *\nAllow: /\n", "text/plain")

        with mock.patch.object(urllib.request, "urlopen", unguarded_urlopen):
            fetch_page("https://reviews.example/atlas", {"reviews.example"}, timeout_seconds=7.0, opener=opener)

        # robots.txt must not bypass the allowlisted opener.
        self.assertEqual(direct_calls, [])
        robots_requests = [(url, timeout) for url, timeout in opener.opened if url.endswith("/robots.txt")]
        self.assertEqual(robots_requests, [("https://reviews.example/robots.txt", 7.0)])


# ---------------------------------------------------------------------------
# Finding 3: a provider failure or an invalid verdict collapses to "unknown"
# and is then scored as a correct verdict whenever the gold label is "unknown".
# ---------------------------------------------------------------------------


def _case(case_id, text, verdict="unknown"):
    return {
        "case_id": case_id,
        "subject_product": "Northstar Atlas 4000",
        "text": text,
        "expected": {"verdict": verdict, "competing_products": [], "pros": [], "cons": []},
    }


class VerdictAccuracyTests(unittest.TestCase):
    TEXT = "The Northstar Atlas 4000 arrived this morning. Our full review follows next week."

    def test_provider_error_is_not_a_correct_unknown_verdict(self):
        def failing(system, user, schema):
            raise ProviderError("provider returned HTTP 529")

        report = evaluate_provider([_case("no-verdict", self.TEXT)], failing)
        self.assertEqual(report["counts"]["provider_errors"], 1)
        self.assertEqual(report["metrics"]["verdict_accuracy"], 0.0)

    def test_invalid_verdict_is_not_a_correct_unknown_verdict(self):
        def glowing(system, user, schema):
            return {"verdict": "glowing", "competing_products": [], "pros": [], "cons": []}

        report = evaluate_provider([_case("no-verdict", self.TEXT)], glowing)
        self.assertEqual(report["counts"]["rejected_by_reason"].get("invalid_verdict"), 1)
        self.assertEqual(report["metrics"]["verdict_accuracy"], 0.0)


# ---------------------------------------------------------------------------
# Finding 4: GoldenReplayProvider looks for the full case text inside the user
# prompt. With --max-chars below the text length the prompt holds a prefix, the
# lookup raises LookupError, and llm-eval dies with a traceback instead of a report.
# ---------------------------------------------------------------------------


class OfflineReplayTruncationTests(unittest.TestCase):
    def test_offline_replay_survives_max_chars_truncation(self):
        case = _case(
            "atlas-positive",
            "The Northstar Atlas 4000 is the easiest desktop recommendation we have made this year. "
            "Next to the Aether Pro 4100 it finished our export test a few minutes sooner.",
            verdict="positive",
        )
        case["expected"]["competing_products"] = ["Aether Pro 4100"]
        report = evaluate_provider([case], GoldenReplayProvider([case]), max_chars=40)
        self.assertEqual(report["cases"], 1)
        self.assertEqual(report["counts"]["provider_errors"], 0)
        self.assertEqual(report["metrics"]["verdict_accuracy"], 1.0)
        # The competitor lies beyond the cut, so it cannot be grounded.
        self.assertEqual(report["case_results"][0]["competitors_missed"], ["aether pro 4100"])


if __name__ == "__main__":
    unittest.main()
