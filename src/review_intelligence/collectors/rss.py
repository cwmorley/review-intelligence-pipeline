from __future__ import annotations

from xml.etree import ElementTree


def discover_rss_urls(xml_text: str) -> list[str]:
    root = ElementTree.fromstring(xml_text)
    urls: list[str] = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1].lower()
        if tag == "link":
            href = element.attrib.get("href")
            value = (href or element.text or "").strip()
            relation = element.attrib.get("rel", "alternate")
            if value.startswith(("http://", "https://")) and relation == "alternate":
                urls.append(value)
    return list(dict.fromkeys(urls))

