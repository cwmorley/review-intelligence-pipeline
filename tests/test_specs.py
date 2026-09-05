import unittest

from review_intelligence.specs import compare_product_specs


PRODUCTS = [
    {"product_id": "p1", "make": "Make A", "model": "Model A", "model_number": "100", "product_vertical": "appliances", "verification_status": "accepted"},
    {"product_id": "p2", "make": "Make B", "model": "Model B", "model_number": "200", "product_vertical": "appliances", "verification_status": "accepted"},
    {"product_id": "p3", "make": "Make C", "model": "Model C", "model_number": "300", "product_vertical": "cameras", "verification_status": "accepted"},
]
DEFINITIONS = [
    {"product_vertical": "appliances", "spec_key": "capacity", "display_name": "Capacity", "data_type": "number", "unit": "L", "required_for_match": "true", "match_weight": "1", "definition_version": "v1", "active": "true"},
    {"product_vertical": "appliances", "spec_key": "programmable", "display_name": "Programmable", "data_type": "boolean", "required_for_match": "false", "match_weight": "0.5", "definition_version": "v1", "active": "true"},
    {"product_vertical": "cameras", "spec_key": "mount", "display_name": "Mount", "data_type": "text", "required_for_match": "true", "match_weight": "1", "definition_version": "v1", "active": "true"},
]
VALUES = [
    {"product_id": "p1", "spec_key": "capacity", "value_number": "1.5", "unit": "L", "verification_status": "accepted"},
    {"product_id": "p2", "spec_key": "capacity", "value_number": "2.0", "unit": "L", "verification_status": "accepted"},
    {"product_id": "p1", "spec_key": "programmable", "value_boolean": "true", "verification_status": "accepted"},
]


class SpecTests(unittest.TestCase):
    def test_vertical_definitions_drive_comparison(self):
        rows = compare_product_specs("p1", "p2", PRODUCTS, DEFINITIONS, VALUES)
        by_key = {row["spec_key"]: row for row in rows}
        self.assertEqual(set(by_key), {"capacity", "programmable"})
        self.assertEqual(by_key["capacity"]["comparison_result"], "different")
        self.assertEqual(by_key["programmable"]["comparison_result"], "missing_compared")

    def test_cross_vertical_comparison_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "share a product vertical"):
            compare_product_specs("p1", "p3", PRODUCTS, DEFINITIONS, VALUES)

    def test_unit_mismatch_is_rejected(self):
        bad_values = [{"product_id": "p1", "spec_key": "capacity", "value_number": "1.5", "unit": "oz", "verification_status": "accepted"}]
        with self.assertRaisesRegex(ValueError, "requires unit L"):
            compare_product_specs("p1", "p2", PRODUCTS, DEFINITIONS, bad_values)

    def test_category_specific_specs_only_appear_when_applicable(self):
        products = [
            {"product_id": "desktop-1", "make": "A", "model": "D", "model_number": "1", "product_vertical": "computers", "category": "desktop", "verification_status": "accepted"},
            {"product_id": "desktop-2", "make": "B", "model": "D", "model_number": "2", "product_vertical": "computers", "category": "desktop", "verification_status": "accepted"},
            {"product_id": "laptop-1", "make": "A", "model": "L", "model_number": "3", "product_vertical": "computers", "category": "laptop", "verification_status": "accepted"},
            {"product_id": "laptop-2", "make": "B", "model": "L", "model_number": "4", "product_vertical": "computers", "category": "laptop", "verification_status": "accepted"},
        ]
        definitions = [
            {"product_vertical": "computers", "spec_key": "screen_type", "display_name": "Screen type", "data_type": "enum", "allowed_values": "ips|oled", "applies_to_category": "laptop", "required_for_match": "false", "match_weight": "0.5", "definition_version": "v1", "active": "true"}
        ]
        self.assertEqual(compare_product_specs("desktop-1", "desktop-2", products, definitions, []), [])
        laptop_rows = compare_product_specs("laptop-1", "laptop-2", products, definitions, [])
        self.assertEqual(len(laptop_rows), 1)
        self.assertEqual(laptop_rows[0]["comparison_result"], "missing_both")


if __name__ == "__main__":
    unittest.main()
