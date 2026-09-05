from __future__ import annotations


def discover_listed_urls(text: str) -> list[str]:
    urls = []
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if value.startswith(("http://", "https://")):
            urls.append(value)
    return list(dict.fromkeys(urls))

