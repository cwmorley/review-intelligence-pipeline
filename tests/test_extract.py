import unittest

from review_intelligence.extract import extract_review_candidates


HTML = """
<html><head><script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Review",
  "url": "https://example.com/reviews/widget?utm_source=feed",
  "headline": "Widget review",
  "datePublished": "2026-08-10",
  "author": {"@type": "Person", "name": "Jamie Example"},
  "itemReviewed": {
    "@type": "Product",
    "name": "Widget X",
    "brand": {"@type": "Brand", "name": "Example Works"},
    "model": "Widget X Pro",
    "mpn": "WX-1000",
    "sku": "WX1000-BLK"
  },
  "reviewRating": {"ratingValue": "4", "bestRating": "5"}
}
</script></head></html>
"""


class ExtractTests(unittest.TestCase):
    def test_jsonld_is_candidate_not_verified_fact(self):
        records = extract_review_candidates(HTML, "https://example.com/reviews/widget")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["author_name"], "Jamie Example")
        self.assertEqual(records[0]["rating_value"], "4")
        self.assertEqual(records[0]["product_make_raw"], "Example Works")
        self.assertEqual(records[0]["product_model_raw"], "Widget X Pro")
        self.assertEqual(records[0]["product_model_number_raw"], "WX-1000")
        self.assertEqual(records[0]["product_sku_raw"], "WX1000-BLK")
        self.assertEqual(records[0]["verification_status"], "candidate")
        self.assertEqual(records[0]["canonical_url"], "https://example.com/reviews/widget")


if __name__ == "__main__":
    unittest.main()
