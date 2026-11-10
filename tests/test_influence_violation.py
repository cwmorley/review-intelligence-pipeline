import unittest
from datetime import date

from review_intelligence.scoring import DataQualityError, score_candidates


def inputs(bad_value):
    candidates = [
        {"candidate_id": "bad", "influence_score": bad_value},
        {"candidate_id": "good", "influence_score": "0.8"},
    ]
    reviews = [
        {"review_id": f"r-{name}", "candidate_id": name, "published_date": "2026-01-01", "rating_value": "9", "rating_scale": "10", "verification_status": "accepted"}
        for name in ("bad", "good")
    ]
    engagements = [
        {"engagement_id": f"e-{name}", "candidate_id": name, "decision_date": "2026-01-01", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": f"r-{name}"}
        for name in ("bad", "good")
    ]
    return candidates, reviews, engagements


class InfluenceViolationTests(unittest.TestCase):
    def test_unusable_influence_excludes_only_that_candidate(self):
        for value in ("", None, "high", "1.5", "-0.1", "nan"):
            with self.subTest(value=value):
                violations = []
                scores = score_candidates(*inputs(value), as_of=date(2026, 9, 4), violations=violations)
                self.assertEqual([score["candidate_id"] for score in scores], ["good"])
                self.assertEqual(len(violations), 1)
                self.assertEqual(violations[0]["violation_code"], "invalid_influence_score")
                self.assertEqual(violations[0]["record_type"], "candidate")
                self.assertEqual(violations[0]["candidate_id"], "bad")

    def test_strict_mode_raises_data_quality_error(self):
        with self.assertRaisesRegex(DataQualityError, "invalid_influence_score"):
            score_candidates(*inputs(""), as_of=date(2026, 9, 4), strict=True)


if __name__ == "__main__":
    unittest.main()
