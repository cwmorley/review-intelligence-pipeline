import unittest

from review_intelligence.normalize import is_favorable, normalize_rating


class NormalizeTests(unittest.TestCase):
    def test_common_scales(self):
        self.assertEqual(normalize_rating("4/5"), 0.8)
        self.assertEqual(normalize_rating("80%"), 0.8)
        self.assertEqual(normalize_rating(8, 10), 0.8)
        self.assertEqual(normalize_rating("B-"), 0.8)

    def test_ambiguous_or_invalid_value_is_not_inferred(self):
        self.assertIsNone(normalize_rating(4))
        self.assertIsNone(normalize_rating("excellent"))
        self.assertIsNone(normalize_rating(11, 10))

    def test_favorable_boundary(self):
        self.assertTrue(is_favorable(0.8))
        self.assertFalse(is_favorable(0.799))
        self.assertIsNone(is_favorable(None))


if __name__ == "__main__":
    unittest.main()

