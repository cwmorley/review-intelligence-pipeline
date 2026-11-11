import unittest
from email.message import Message
from unittest import mock
from urllib.request import Request

from review_intelligence.collectors import fetch
from review_intelligence.collectors.fetch import AllowlistRedirectHandler, fetch_page


URL = "https://reviews.example.com/atlas"
ALLOWED = {"reviews.example.com"}


class StubResponse:
    def __init__(self, body=b"<html></html>", content_type="text/html", final_url=URL):
        self._body = body
        self._final_url = final_url
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.status = 200

    def read(self, amount=-1):
        return self._body if amount < 0 else self._body[:amount]

    def geturl(self):
        return self._final_url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


ROBOTS_ALLOW = b"User-agent: *\nAllow: /\n"
ROBOTS_DISALLOW = b"User-agent: *\nDisallow: /\n"


class StubOpener:
    """Serves robots.txt and the page. Page requests and robots requests are recorded apart."""

    def __init__(self, response, robots_body=ROBOTS_ALLOW):
        self.response = response
        self.robots_body = robots_body
        self.requests = []
        self.robots_requests = []
        self.timeouts = []

    def open(self, request, timeout=None):
        self.timeouts.append(timeout)
        if request.full_url.endswith("/robots.txt"):
            self.robots_requests.append(request)
            return StubResponse(self.robots_body, "text/plain", final_url=request.full_url)
        self.requests.append(request)
        return self.response


class FetchPageTests(unittest.TestCase):
    """No network: robots.txt and the page are both served by the stub opener."""

    def test_allowed_page_returns_evidence_record(self):
        opener = StubOpener(StubResponse(b"<html>ok</html>"))
        record = fetch_page(URL, ALLOWED, opener=opener)
        self.assertEqual(record["body"], b"<html>ok</html>")
        self.assertEqual(record["byte_count"], 15)
        self.assertEqual(len(record["content_sha256"]), 64)
        self.assertEqual(len(opener.requests), 1)
        self.assertEqual(len(opener.robots_requests), 1)
        self.assertEqual(opener.timeouts, [15.0, 15.0])

    def test_non_http_scheme_is_rejected_before_any_request(self):
        opener = StubOpener(StubResponse())
        with self.assertRaises(ValueError):
            fetch_page("file:///etc/passwd", ALLOWED, opener=opener)
        self.assertEqual(opener.requests, [])

    def test_host_outside_allowlist_is_rejected_before_any_request(self):
        opener = StubOpener(StubResponse())
        with self.assertRaises(PermissionError):
            fetch_page("https://other.example.net/atlas", ALLOWED, opener=opener)
        self.assertEqual(opener.requests, [])

    def test_robots_disallow_is_respected(self):
        opener = StubOpener(StubResponse(), robots_body=ROBOTS_DISALLOW)
        with self.assertRaisesRegex(PermissionError, "does not permit"):
            fetch_page(URL, ALLOWED, opener=opener)
        self.assertEqual(opener.requests, [])
        self.assertEqual(len(opener.robots_requests), 1)

    def test_unsupported_content_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported content type"):
            fetch_page(URL, ALLOWED, opener=StubOpener(StubResponse(content_type="application/pdf")))

    def test_size_cap_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "max_bytes=10"):
            fetch_page(URL, ALLOWED, max_bytes=10, opener=StubOpener(StubResponse(b"x" * 11)))
        self.assertEqual(fetch_page(URL, ALLOWED, max_bytes=10, opener=StubOpener(StubResponse(b"x" * 10)))["byte_count"], 10)

    def test_response_that_ended_on_another_host_is_rejected(self):
        opener = StubOpener(StubResponse(final_url="https://other.example.net/landing"))
        with self.assertRaisesRegex(PermissionError, "final response URL"):
            fetch_page(URL, ALLOWED, opener=opener)

    def test_redirect_handler_checks_host_and_scheme_on_every_hop(self):
        handler = AllowlistRedirectHandler(ALLOWED)
        request = Request(URL)
        for target in ("https://other.example.net/x", "ftp://reviews.example.com/x"):
            with self.assertRaises(PermissionError):
                handler.redirect_request(request, None, 302, "Found", Message(), target)
        followed = handler.redirect_request(request, None, 302, "Found", Message(), "https://REVIEWS.example.com/atlas-2")
        self.assertEqual(followed.full_url, "https://REVIEWS.example.com/atlas-2")

    def test_default_opener_is_built_with_the_allowlist_handler(self):
        with mock.patch.object(fetch, "build_opener", return_value=StubOpener(StubResponse())) as build:
            fetch_page(URL, ALLOWED)
        handler = build.call_args.args[0]
        self.assertIsInstance(handler, AllowlistRedirectHandler)
        with self.assertRaises(PermissionError):
            handler.redirect_request(Request(URL), None, 301, "Moved", Message(), "https://other.example.net/x")


if __name__ == "__main__":
    unittest.main()
