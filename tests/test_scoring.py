import unittest
from datetime import date

from review_intelligence.scoring import DataQualityError, score_candidates


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
        with self.assertRaisesRegex(DataQualityError, "must reference a verified review"):
            score_candidates(
                [{"candidate_id": "c1", "candidate_name": "A", "outlet_name": "O", "influence_score": 0.8}],
                [{"review_id": "r1", "candidate_id": "c1", "published_date": "2026-01-01", "rating_value": "5", "rating_scale": "5", "verification_status": "candidate"}],
                [{"engagement_id": "e1", "candidate_id": "c1", "decision_date": "2026-01-02", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": "r1"}],
                date(2026, 9, 4),
                half_life_days=None,
                strict=True,
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

    def test_resolved_deep_record_ranks_above_unresolved_thin_record(self):
        candidates = [
            {"candidate_id": "thin", "candidate_name": "Perfect 2/2", "outlet_name": "T", "influence_score": "0.9", "active": "true"},
            {"candidate_id": "deep", "candidate_name": "Proven 30/40", "outlet_name": "B", "influence_score": "0.9", "active": "true"},
        ]
        reviews = []
        engagements = []
        for index in range(2):
            review_id = f"rt{index}"
            reviews.append({"review_id": review_id, "candidate_id": "thin", "product_id": "p", "verification_status": "accepted", "rating_value": "9", "rating_scale": "10", "published_date": "2026-09-01"})
            engagements.append({"engagement_id": f"et{index}", "candidate_id": "thin", "product_id": "p", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": review_id, "decision_date": "2026-09-01"})
        for index in range(40):
            coverage_observed = index < 30
            review_id = f"rd{index}"
            reviews.append({"review_id": review_id, "candidate_id": "deep", "product_id": "p", "verification_status": "accepted", "rating_value": "9" if coverage_observed else "5", "rating_scale": "10", "published_date": "2026-09-01"})
            engagements.append({"engagement_id": f"ed{index}", "candidate_id": "deep", "product_id": "p", "eligible_for_coverage": "true", "coverage_observed": "true" if coverage_observed else "false", "coverage_review_id": review_id if coverage_observed else "", "decision_date": "2026-09-01"})

        scores = score_candidates(candidates, reviews, engagements, date(2026, 9, 4), half_life_days=None)

        self.assertEqual([score["candidate_id"] for score in scores], ["deep", "thin"])
        self.assertEqual(scores[0]["evidence_status"], "direction_resolved")
        self.assertEqual(scores[1]["evidence_status"], "direction_unresolved")
        self.assertGreater(scores[1]["nrs_ev_score"], scores[0]["nrs_ev_score"])
        self.assertIn("lower_95", scores[0]["rank_basis"])

    def test_insufficient_evidence_never_outranks_resolved_direction(self):
        candidates = [
            {"candidate_id": "resolved", "candidate_name": "Resolved", "outlet_name": "R", "influence_score": "0.1", "active": "true"},
            {"candidate_id": "insufficient", "candidate_name": "Insufficient", "outlet_name": "I", "influence_score": "1.0", "active": "true"},
        ]
        reviews = []
        engagements = []
        for index in range(8):
            review_id = f"rr{index}"
            reviews.append({"review_id": review_id, "candidate_id": "resolved", "verification_status": "accepted", "rating_value": "9", "rating_scale": "10", "published_date": "2026-09-01"})
            engagements.append({"engagement_id": f"er{index}", "candidate_id": "resolved", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": review_id, "decision_date": "2026-09-01"})

        scores = score_candidates(candidates, reviews, engagements, date(2026, 9, 4), half_life_days=None)

        self.assertEqual([score["candidate_id"] for score in scores], ["resolved", "insufficient"])
        self.assertLess(scores[0]["expected_earned_value"], scores[1]["expected_earned_value"])
        self.assertEqual(scores[0]["evidence_status"], "direction_resolved")
        self.assertEqual(scores[1]["evidence_status"], "insufficient_evidence")

    def test_malformed_candidate_is_reported_without_blocking_others(self):
        candidates = [
            {"candidate_id": "bad", "candidate_name": "Bad", "outlet_name": "B", "influence_score": "0.8", "active": "true"},
            {"candidate_id": "good", "candidate_name": "Good", "outlet_name": "G", "influence_score": "0.8", "active": "true"},
        ]
        reviews = [{"review_id": "rb", "candidate_id": "bad", "verification_status": "accepted", "rating_value": "9", "rating_scale": "10", "published_date": "2026-09-01"}]
        engagements = [{"engagement_id": "eb", "candidate_id": "bad", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": "rb", "decision_date": ""}]
        violations = []

        scores = score_candidates(candidates, reviews, engagements, date(2026, 9, 4), half_life_days=None, violations=violations)

        self.assertEqual([score["candidate_id"] for score in scores], ["good"])
        self.assertEqual(violations[0]["violation_code"], "missing_decision_date")
        self.assertEqual(violations[0]["candidate_id"], "bad")
        self.assertEqual(violations[0]["excluded_reason"], "candidate_excluded_due_to_data_quality_violation")

    def test_malformed_candidate_raises_in_strict_mode(self):
        with self.assertRaisesRegex(DataQualityError, "missing_decision_date"):
            score_candidates(
                [{"candidate_id": "bad", "candidate_name": "Bad", "outlet_name": "B", "influence_score": "0.8", "active": "true"}],
                [{"review_id": "rb", "candidate_id": "bad", "verification_status": "accepted", "rating_value": "9", "rating_scale": "10", "published_date": "2026-09-01"}],
                [{"engagement_id": "eb", "candidate_id": "bad", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": "rb", "decision_date": ""}],
                date(2026, 9, 4),
                half_life_days=None,
                strict=True,
            )

    def test_linked_failure_and_missing_review_date_have_stable_codes(self):
        violations = []
        scores = score_candidates(
            [{"candidate_id": "bad", "candidate_name": "Bad", "outlet_name": "B", "influence_score": "0.8", "active": "true"}],
            [{"review_id": "rb", "candidate_id": "bad", "verification_status": "accepted", "rating_value": "9", "rating_scale": "10", "published_date": ""}],
            [{"engagement_id": "eb", "candidate_id": "bad", "eligible_for_coverage": "true", "coverage_observed": "false", "coverage_review_id": "rb", "decision_date": "2026-09-01"}],
            date(2026, 9, 4),
            half_life_days=None,
            violations=violations,
        )

        self.assertEqual(scores, [])
        self.assertEqual(
            {violation["violation_code"] for violation in violations},
            {"coverage_failure_linked", "missing_published_date"},
        )

    def test_ordering_is_deterministic(self):
        candidates = [
            {"candidate_id": "b", "candidate_name": "B", "outlet_name": "O", "influence_score": "0.8", "active": "true"},
            {"candidate_id": "a", "candidate_name": "A", "outlet_name": "O", "influence_score": "0.8", "active": "true"},
        ]
        first = score_candidates(candidates, [], [], date(2026, 9, 4), half_life_days=None)
        second = score_candidates(candidates, [], [], date(2026, 9, 4), half_life_days=None)
        self.assertEqual([score["candidate_id"] for score in first], ["a", "b"])
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
