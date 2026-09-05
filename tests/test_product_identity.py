import unittest

from review_intelligence.product_identity import resolve_product_identity


PRODUCTS = [
    {
        "product_id": "p1",
        "make": "Northstar",
        "model": "Atlas",
        "model_number": "4000",
        "sku": "ATLAS-4000-A",
        "product_vertical": "computers",
        "category": "desktop",
        "verification_status": "accepted",
    }
]
ALIASES = [
    {"product_id": "p1", "alias_text": "Northstar Atlas", "alias_type": "marketing_name", "verification_status": "accepted"}
]


class ProductIdentityTests(unittest.TestCase):
    def test_structured_model_number_is_high_confidence_candidate(self):
        resolved = resolve_product_identity(
        {"product_name": "The new product", "product_make_raw": "Northstar", "product_model_raw": "Atlas", "product_model_number_raw": "4000"},
            PRODUCTS,
            ALIASES,
        )
        self.assertEqual(resolved["resolved_product_id"], "p1")
        self.assertEqual(resolved["resolved_make"], "Northstar")
        self.assertEqual(resolved["resolved_model"], "Atlas")
        self.assertEqual(resolved["resolved_model_number"], "4000")
        self.assertEqual(resolved["resolved_product_vertical"], "computers")
        self.assertEqual(resolved["resolved_category"], "desktop")
        self.assertEqual(resolved["resolution_method"], "structured_identifier")
        self.assertEqual(resolved["product_verification_status"], "candidate")

    def test_verified_alias_is_medium_confidence_candidate(self):
        resolved = resolve_product_identity(
            {"headline": "Northstar Atlas review"},
            PRODUCTS,
            ALIASES,
        )
        self.assertEqual(resolved["resolved_product_id"], "p1")
        self.assertEqual(resolved["resolution_method"], "verified_alias")
        self.assertEqual(resolved["resolution_confidence"], "medium")

    def test_unknown_identifier_is_detected_but_not_assigned(self):
        resolved = resolve_product_identity(
            {"headline": "Mystery product ZX-9900 review"},
            PRODUCTS,
            ALIASES,
        )
        self.assertIsNone(resolved["resolved_product_id"])
        self.assertEqual(resolved["detected_model_number"], "ZX-9900")
        self.assertEqual(resolved["resolution_confidence"], "unresolved")


if __name__ == "__main__":
    unittest.main()
