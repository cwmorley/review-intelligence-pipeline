"""Single-page HTTP retrieval with allowlist, robots, and size boundaries."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib import robotparser
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..deduplicate import content_sha256


DEFAULT_USER_AGENT = "ReviewIntelligenceResearchBot/0.1 (+contact-required-before-public-use)"


class AllowlistRedirectHandler(HTTPRedirectHandler):
    """Refuse any redirect hop whose scheme or host is outside the allowlist."""

    def __init__(self, allowed_hosts: set[str]) -> None:
        self._allowed_hosts = {item.lower() for item in allowed_hosts}

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _require_allowed(newurl, self._allowed_hosts, "redirect target")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _require_allowed(url: str, normalized_allowlist: set[str], label: str) -> None:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme not in {"http", "https"} or host not in normalized_allowlist:
        raise PermissionError(f"{label} is not allowlisted: {parts.scheme}://{host}")


def fetch_page(
    url: str,
    allowed_hosts: set[str],
    user_agent: str = DEFAULT_USER_AGENT,
    max_bytes: int = 2_000_000,
    timeout_seconds: float = 15.0,
    opener=None,
) -> dict:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise ValueError("only HTTP(S) sources are supported")
    host = (parts.hostname or "").lower()
    normalized_allowlist = {item.lower() for item in allowed_hosts}
    if host not in normalized_allowlist:
        raise PermissionError(f"host is not allowlisted: {host}")

    # One opener serves robots.txt and the page, so both get the allowlist on
    # every redirect hop, the same timeout, and the same User-Agent.
    opener = opener or build_opener(AllowlistRedirectHandler(normalized_allowlist))
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    robots = robotparser.RobotFileParser()
    robots.set_url(robots_url)
    try:
        robots_request = Request(robots_url, headers={"User-Agent": user_agent})
        with opener.open(robots_request, timeout=timeout_seconds) as robots_response:
            _require_allowed(robots_response.geturl() or robots_url, normalized_allowlist, "robots.txt response URL")
            robots.parse(robots_response.read(max_bytes).decode("utf-8", errors="replace").splitlines())
    except HTTPError as error:
        # Same policy as RobotFileParser.read(): 401/403 forbid everything, other 4xx mean no rules.
        if error.code in (401, 403):
            robots.disallow_all = True
        elif 400 <= error.code < 500:
            robots.allow_all = True
        else:
            raise PermissionError(f"robots.txt could not be verified for {host}") from error
    except PermissionError:
        raise
    except OSError as error:
        raise PermissionError(f"robots.txt could not be verified for {host}") from error
    if not robots.can_fetch(user_agent, url):
        raise PermissionError(f"robots.txt does not permit retrieval: {url}")

    request = Request(url, headers={"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"})
    # robots.txt is checked for the requested URL; a same-allowlist redirect
    # target is not re-checked against its own robots.txt.
    with opener.open(request, timeout=timeout_seconds) as response:
        _require_allowed(response.geturl() or url, normalized_allowlist, "final response URL")
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"unsupported content type: {content_type}")
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise ValueError(f"source exceeds max_bytes={max_bytes}")
        return {
            "source_url": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "http_status": getattr(response, "status", 200),
            "content_type": content_type,
            "content_sha256": content_sha256(payload),
            "byte_count": len(payload),
            "body": payload,
        }


