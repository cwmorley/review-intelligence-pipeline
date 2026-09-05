import unittest

from review_intelligence.deduplicate import canonicalize_url, exact_duplicate_groups


class DeduplicateTests(unittest.TestCase):
    def test_tracking_and_fragments_do_not_change_identity(self):
        left = "HTTPS://Example.COM:443/review/?utm_source=x&b=2&a=1#verdict"
        right = "https://example.com/review?a=1&b=2"
        self.assertEqual(canonicalize_url(left), canonicalize_url(right))

    def test_hash_and_url_groups_merge_transitively(self):
        records = [
            {"review_id": "a", "source_url": "https://example.com/a", "content_sha256": "one"},
            {"review_id": "b", "source_url": "https://example.com/b", "content_sha256": "one"},
            {"review_id": "c", "source_url": "https://example.com/b?utm_source=x", "content_sha256": "two"},
        ]
        self.assertEqual(exact_duplicate_groups(records), [["a", "b", "c"]])


if __name__ == "__main__":
    unittest.main()

