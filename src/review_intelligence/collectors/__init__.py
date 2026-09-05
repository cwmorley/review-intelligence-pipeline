"""Controlled discovery and fetch helpers, not a universal crawler."""

from .rss import discover_rss_urls
from .sitemap import discover_sitemap_urls
from .url_list import discover_listed_urls

__all__ = ["discover_rss_urls", "discover_sitemap_urls", "discover_listed_urls"]

