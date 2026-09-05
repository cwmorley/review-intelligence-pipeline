import unittest
from datetime import date

from review_intelligence.scoring import score_candidates


class ScoringTests(unittest.TestCase):
    def test_streams_join_only_at_candidate(self):
        candidates = [{"candidate_id": "c1", "candidate_name": "A", "outlet_name": "O", "influence_score": 0.8}]
        reviews = [
            {"review_id": "r1", "candidate_id": "c1", "published_date": "2026-01-01", "rating_value": "4", "rating_scale": "5", "verification_status": "accepted"},
            {"review_id": "r2", "candidate_id": "c1", "published_date": "2026-01-02", "rating_value": "5", "rating_scale": "5", "verification_status": "candidate"},
        ]
        engagements = [
            {"candidate_id": "c1", "decision_date": "2026-01-01", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": "r1"},
            {"candidate_id": "c1", "decision_date": "2026-01-02", "eligible_for_coverage": "true", "coverage_observed": "false"},
            {"candidate_id": "c1", "decision_date": "2026-01-03", "eligible_for_coverage": "false", "coverage_observed": "false"},
        ]
        score = score_candidates(candidates, reviews, engagements, date(2026, 9, 4), half_life_days=None)[0]
        self.assertEqual(score["coverage_raw_n"], 2)
        self.assertEqual(score["favorability_raw_n"], 1)
        self.assertAlmostEqual(score["coverage_mean"], 0.5)
        self.assertAlmostEqual(score["favorability_mean"], 2 / 3)
        self.assertAlmostEqual(score["expected_earned_value"], 0.5 * 0.8 * (2 / 3))
        self.assertEqual(score["score_variant"], "NRS-EV v0.1")
        self.assertAlmostEqual(score["nrs_ev_score"], 100 * 0.5 * 0.8 * (2 / 3))
        self.assertTrue(score["human_decision_required"])

    def test_missing_private_denominator_is_insufficient(self):
        score = score_candidates(
            [{"candidate_id": "c1", "candidate_name": "A", "outlet_name": "O", "influence_score": 0.8}],
            [{"review_id": "r1", "candidate_id": "c1", "published_date": "2026-01-01", "rating_value": "5", "rating_scale": "5", "verification_status": "accepted"}],
            [],
            date(2026, 9, 4),
            half_life_days=None,
        )[0]
        self.assertEqual(score["evidence_status"], "insufficient_evidence")

    def test_unverified_coverage_link_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must reference a verified review"):
            score_candidates(
                [{"candidate_id": "c1", "candidate_name": "A", "outlet_name": "O", "influence_score": 0.8}],
                [{"review_id": "r1", "candidate_id": "c1", "published_date": "2026-01-01", "rating_value": "5", "rating_scale": "5", "verification_status": "candidate"}],
                [{"engagement_id": "e1", "candidate_id": "c1", "decision_date": "2026-01-02", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": "r1"}],
                date(2026, 9, 4),
                half_life_days=None,
            )

    def test_product_scope_filters_both_evidence_streams(self):
        candidates = [{"candidate_id": "c1", "candidate_name": "A", "outlet_name": "O", "influence_score": 1}]
        reviews = [
            {"review_id": "r1", "candidate_id": "c1", "product_id": "p1", "published_date": "2026-01-01", "rating_value": "5", "rating_scale": "5", "verification_status": "accepted"},
            {"review_id": "r2", "candidate_id": "c1", "product_id": "p2", "published_date": "2026-01-02", "rating_value": "1", "rating_scale": "5", "verification_status": "accepted"},
        ]
        engagements = [
            {"engagement_id": "e1", "candidate_id": "c1", "product_id": "p1", "decision_date": "2026-01-01", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": "r1"},
            {"engagement_id": "e2", "candidate_id": "c1", "product_id": "p2", "decision_date": "2026-01-02", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": "r2"},
        ]
        score = score_candidates(
            candidates,
            reviews,
            engagements,
            date(2026, 9, 4),
            half_life_days=None,
            eligible_product_ids={"p1"},
            analysis_scope="target make: Northstar",
        )[0]
        self.assertEqual(score["coverage_raw_n"], 1)
        self.assertEqual(score["favorability_raw_n"], 1)
        self.assertEqual(score["analysis_scope"], "target make: Northstar")


if __name__ == "__main__":
    unittest.main()
