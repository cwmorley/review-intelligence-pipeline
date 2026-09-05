from __future__ import annotations

from xml.etree import ElementTree


def discover_sitemap_urls(xml_text: str) -> list[str]:
    root = ElementTree.fromstring(xml_text)
    urls = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].lower() == "loc" and element.text:
            value = element.text.strip()
            if value.startswith(("http://", "https://")):
                urls.append(value)
    return list(dict.fromkeys(urls))

