import unittest

from review_intelligence.collectors import discover_listed_urls, discover_rss_urls, discover_sitemap_urls


class CollectorTests(unittest.TestCase):
    def test_url_list(self):
        text = "# approved\nhttps://example.com/a\nhttps://example.com/a\nnot-a-url"
        self.assertEqual(discover_listed_urls(text), ["https://example.com/a"])

    def test_rss_and_sitemap(self):
        rss = '<rss><channel><item><link>https://example.com/r</link></item></channel></rss>'
        sitemap = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/s</loc></url></urlset>'
        self.assertEqual(discover_rss_urls(rss), ["https://example.com/r"])
        self.assertEqual(discover_sitemap_urls(sitemap), ["https://example.com/s"])


if __name__ == "__main__":
    unittest.main()

