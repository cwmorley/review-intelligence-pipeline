import unittest
from datetime import date

from review_intelligence.scoring import DataQualityError, score_candidates


def poor_and_promising():
    candidates = [{"candidate_id": name, "influence_score": .9} for name in ("poor", "promising")]
    reviews, engagements = [], []
    for name, count, rating in (("poor", 40, "2"), ("promising", 2, "9")):
        for index in range(count):
            rid = f"{name}-{index}"
            reviews.append(dict(candidate_id=name, review_id=rid, rating_value=rating, rating_scale="10", verification_status="accepted", published_date="2026-09-01"))
            engagements.append(dict(candidate_id=name, engagement_id=rid, eligible_for_coverage=True, coverage_observed=True, coverage_review_id=rid, decision_date="2026-09-01"))
    return candidates, reviews, engagements


class RankingPolicyTests(unittest.TestCase):
    def test_resolved_unfavorable_does_not_get_automatic_priority(self):
        scores = score_candidates(*poor_and_promising(), as_of=date(2026, 9, 4), half_life_days=None)
        self.assertEqual([s["candidate_id"] for s in scores], ["promising", "poor"])
        self.assertEqual(scores[1]["evidence_status"], "direction_resolved")
        self.assertLess(scores[1]["favorability_upper_95"], .5)
        self.assertEqual(scores[0]["evidence_status"], "direction_unresolved")
        self.assertGreater(scores[0]["expected_earned_value_lower_95"], scores[1]["expected_earned_value_lower_95"])

    def test_orphan_and_wrong_candidate_links_exclude_only_affected_candidate(self):
        for link in ("nonexistent", "promising-0", ""):
            candidates, reviews, engagements = poor_and_promising()
            engagements[0]["coverage_review_id"] = link
            violations = []
            scores = score_candidates(candidates, reviews, engagements, date(2026, 9, 4), violations=violations)
            self.assertEqual([s["candidate_id"] for s in scores], ["promising"])
            self.assertEqual(violations[0]["violation_code"], "coverage_success_unlinked")

    def test_bad_dates_are_candidate_violations_in_both_modes(self):
        for record_type, field in (("review", "published_date"), ("engagement", "decision_date")):
            for value, prefix in ((None, "missing"), ("2026-02-30", "invalid"), ("2026-09-05", "future")):
                with self.subTest(record_type=record_type, value=value):
                    candidates, reviews, engagements = poor_and_promising()
                    records = reviews if record_type == "review" else engagements
                    records[0][field] = value
                    violations = []
                    scores = score_candidates(candidates, reviews, engagements, date(2026, 9, 4), half_life_days=None, violations=violations)
                    self.assertEqual([s["candidate_id"] for s in scores], ["promising"])
                    self.assertEqual(violations[0]["violation_code"], f"{prefix}_{field}")
                    with self.assertRaises(DataQualityError):
                        score_candidates(candidates, reviews, engagements, date(2026, 9, 4), strict=True)

    def test_surrounding_date_whitespace_is_consistent(self):
        candidates, reviews, engagements = poor_and_promising()
        reviews[0]["published_date"] = " 2026-09-01 "
        engagements[0]["decision_date"] = " 2026-09-01 "
        self.assertEqual(len(score_candidates(candidates, reviews, engagements, date(2026, 9, 4), strict=True)), 2)
