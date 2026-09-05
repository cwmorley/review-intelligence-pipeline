import unittest

from review_intelligence.competitive import build_competitive_summary, eligible_product_ids_for_make


PRODUCTS = [
    {"product_id": "p1", "make": "Northstar", "model": "One", "model_number": "100", "verification_status": "accepted"},
    {"product_id": "p2", "make": "Rival", "model": "Two", "model_number": "200", "verification_status": "accepted"},
    {"product_id": "p3", "make": "Northstar", "model": "Three", "model_number": "300", "verification_status": "candidate"},
]


class CompetitiveTests(unittest.TestCase):
    def test_target_make_excludes_unverified_products(self):
        self.assertEqual(eligible_product_ids_for_make(PRODUCTS, "northSTAR"), {"p1"})

    def test_verified_comparisons_roll_up_without_inventing_delta(self):
        reviews = [
            {"review_id": "r1", "candidate_id": "c1", "product_id": "p1", "verification_status": "accepted"},
            {"review_id": "r2", "candidate_id": "c2", "product_id": "p1", "verification_status": "corrected"},
        ]
        comparisons = [
            {"comparison_id": "x1", "review_id": "r1", "subject_product_id": "p1", "compared_product_id": "p2", "match_set_id": "m1", "match_basis": "same segment", "evidence_locator": "verdict", "comparative_outcome": "subject_preferred", "verification_status": "accepted"},
            {"comparison_id": "x2", "review_id": "r2", "subject_product_id": "p1", "compared_product_id": "p2", "match_set_id": "m1", "match_basis": "same segment", "evidence_locator": "benchmark table", "comparative_outcome": "mixed", "verification_status": "accepted"},
        ]
        row = build_competitive_summary(PRODUCTS, reviews, comparisons)[0]
        self.assertEqual(row["verified_comparison_count"], 2)
        self.assertEqual(row["unique_reviewer_count"], 2)
        self.assertEqual(row["subject_preferred_count"], 1)
        self.assertEqual(row["mixed_count"], 1)
        self.assertEqual(row["evidence_status"], "thin_evidence")

    def test_unverified_review_cannot_support_comparison(self):
        with self.assertRaisesRegex(ValueError, "must reference a verified review"):
            build_competitive_summary(
                PRODUCTS,
                [{"review_id": "r1", "candidate_id": "c1", "product_id": "p1", "verification_status": "candidate"}],
                [{"comparison_id": "x1", "review_id": "r1", "subject_product_id": "p1", "compared_product_id": "p2", "match_set_id": "m1", "match_basis": "same segment", "evidence_locator": "verdict", "comparative_outcome": "subject_preferred", "verification_status": "accepted"}],
            )

    def test_comparison_requires_matching_basis_and_source_location(self):
        with self.assertRaisesRegex(ValueError, "requires match_set_id, match_basis, and evidence_locator"):
            build_competitive_summary(
                PRODUCTS,
                [{"review_id": "r1", "candidate_id": "c1", "product_id": "p1", "verification_status": "accepted"}],
                [{"comparison_id": "x1", "review_id": "r1", "subject_product_id": "p1", "compared_product_id": "p2", "match_set_id": "m1", "match_basis": "", "evidence_locator": "", "comparative_outcome": "subject_preferred", "verification_status": "accepted"}],
            )

    def test_competitor_can_be_the_review_subject(self):
        row = build_competitive_summary(
            PRODUCTS,
            [{"review_id": "r3", "candidate_id": "c3", "product_id": "p2", "verification_status": "accepted"}],
            [{"comparison_id": "x3", "review_id": "r3", "subject_product_id": "p2", "compared_product_id": "p1", "match_set_id": "m1", "match_basis": "same segment", "evidence_locator": "comparison table", "comparative_outcome": "subject_preferred", "verification_status": "accepted"}],
        )[0]
        self.assertEqual(row["subject_product_id"], "p2")
        self.assertEqual(row["compared_product_id"], "p1")
        self.assertEqual(row["subject_preferred_count"], 1)


if __name__ == "__main__":
    unittest.main()
