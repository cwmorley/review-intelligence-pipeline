"""Exact and canonical duplicate detection; fuzzy matching is out of scope."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMS = {"gclid", "fbclid", "mc_cid", "mc_eid"}


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    host = (parts.hostname or "").lower()
    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        host = f"{host}:{port}"
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMS
    ]
    query.sort()
    return urlunsplit((scheme, host, path, urlencode(query), ""))


def content_sha256(content: bytes | str) -> str:
    payload = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(payload).hexdigest()


def exact_duplicate_groups(records: list[dict]) -> list[list[str]]:
    """Group records sharing a content hash or canonical URL."""
    by_key: dict[tuple[str, str], list[str]] = defaultdict(list)
    for record in records:
        record_id = str(record["review_id"])
        digest = str(record.get("content_sha256") or "").strip().lower()
        url = str(record.get("canonical_url") or record.get("source_url") or "").strip()
        if digest:
            by_key[("hash", digest)].append(record_id)
        if url:
            by_key[("url", canonicalize_url(url))].append(record_id)

    groups: list[set[str]] = []
    for ids in by_key.values():
        if len(set(ids)) < 2:
            continue
        new_group = set(ids)
        overlapping = [group for group in groups if group & new_group]
        for group in overlapping:
            new_group |= group
            groups.remove(group)
        groups.append(new_group)
    return [sorted(group) for group in sorted(groups, key=lambda item: sorted(item))]

