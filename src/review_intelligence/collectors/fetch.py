"""Single-page HTTP retrieval with allowlist, robots, and size boundaries."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib import robotparser
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from ..deduplicate import content_sha256


DEFAULT_USER_AGENT = "ReviewIntelligenceResearchBot/0.1 (+contact-required-before-public-use)"


def fetch_page(
    url: str,
    allowed_hosts: set[str],
    user_agent: str = DEFAULT_USER_AGENT,
    max_bytes: int = 2_000_000,
    timeout_seconds: float = 15.0,
) -> dict:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise ValueError("only HTTP(S) sources are supported")
    host = (parts.hostname or "").lower()
    normalized_allowlist = {item.lower() for item in allowed_hosts}
    if host not in normalized_allowlist:
        raise PermissionError(f"host is not allowlisted: {host}")

    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    robots = robotparser.RobotFileParser()
    robots.set_url(robots_url)
    try:
        robots.read()
    except OSError as error:
        raise PermissionError(f"robots.txt could not be verified for {host}") from error
    if not robots.can_fetch(user_agent, url):
        raise PermissionError(f"robots.txt does not permit retrieval: {url}")

    request = Request(url, headers={"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"})
    with urlopen(request, timeout=timeout_seconds) as response:
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

