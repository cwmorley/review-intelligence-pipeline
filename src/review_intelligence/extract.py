"""Bounded JSON-LD extraction that produces unverified candidate records."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from typing import Any

from .deduplicate import canonicalize_url


PARSER_VERSION = "jsonld-v0.2"


class _JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture = False
        self._chunks: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): (value or "") for key, value in attrs}
        if tag.lower() == "script" and attr_map.get("type", "").lower() == "application/ld+json":
            self._capture = True
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._capture:
            self.blocks.append("".join(self._chunks))
            self._capture = False


def extract_review_candidates(html: str, source_url: str) -> list[dict[str, Any]]:
    parser = _JsonLdParser()
    parser.feed(html)
    records: list[dict[str, Any]] = []
    for block in parser.blocks:
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        for node in _walk_nodes(payload):
            node_type = node.get("@type")
            types = {node_type} if isinstance(node_type, str) else set(node_type or [])
            if not types.intersection({"Review", "NewsArticle", "Article", "TechArticle"}):
                continue
            rating = node.get("reviewRating") if isinstance(node.get("reviewRating"), dict) else {}
            author = node.get("author")
            author_name = author.get("name") if isinstance(author, dict) else author
            item = node.get("itemReviewed")
            product_name = item.get("name") if isinstance(item, dict) else None
            product_make = _entity_name(item.get("brand")) if isinstance(item, dict) else None
            if product_make is None and isinstance(item, dict):
                product_make = _entity_name(item.get("manufacturer"))
            records.append(
                {
                    "source_url": source_url,
                    "canonical_url": canonicalize_url(str(node.get("url") or source_url)),
                    "headline": node.get("headline") or node.get("name"),
                    "author_name": author_name,
                    "published_date": node.get("datePublished"),
                    "product_name": product_name,
                    "product_make_raw": product_make,
                    "product_model_raw": item.get("model") if isinstance(item, dict) else None,
                    "product_model_number_raw": item.get("mpn") if isinstance(item, dict) else None,
                    "product_sku_raw": item.get("sku") if isinstance(item, dict) else None,
                    "product_identity_source": "jsonld.itemReviewed" if isinstance(item, dict) else None,
                    "rating_value": rating.get("ratingValue"),
                    "rating_scale": rating.get("bestRating"),
                    "parser_version": PARSER_VERSION,
                    "verification_status": "candidate",
                }
            )
    return records


def _walk_nodes(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_nodes(child)


def _entity_name(value: Any) -> str | None:
    if isinstance(value, dict):
        candidate = value.get("name")
        return str(candidate).strip() if candidate else None
    if value:
        return str(value).strip()
    return None
