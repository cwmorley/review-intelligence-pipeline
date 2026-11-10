import unittest
from datetime import date

from review_intelligence.scoring import score_candidates


def review(review_id, url, digest="", candidate="c1"):
    return {
        "review_id": review_id, "candidate_id": candidate, "source_url": url, "content_sha256": digest,
        "published_date": "2026-01-01", "rating_value": "9", "rating_scale": "10", "verification_status": "accepted",
    }


CANDIDATES = [{"candidate_id": "c1", "influence_score": "0.8"}, {"candidate_id": "c2", "influence_score": "0.8"}]


class ScoringDuplicateTests(unittest.TestCase):
    def _score(self, reviews, **kwargs):
        engagements = [{"engagement_id": "e1", "candidate_id": "c1", "decision_date": "2026-01-01", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": reviews[-1]["review_id"]}]
        scores = score_candidates(CANDIDATES, reviews, engagements, date(2026, 9, 4), half_life_days=None, strict=True, **kwargs)
        return {score["candidate_id"]: score for score in scores}

    def test_same_review_under_five_urls_counts_once(self):
        reviews = [review(f"r{index}", f"https://example.com/reviews/atlas?utm_source=feed{index}") for index in range(5)]
        duplicates = []
        scores = self._score(reviews, duplicates=duplicates)
        self.assertEqual(scores["c1"]["favorability_raw_n"], 1)
        self.assertEqual(duplicates, [["r0", "r1", "r2", "r3", "r4"]])
        # A coverage link to a collapsed duplicate still resolves to a verified review.
        self.assertEqual(scores["c1"]["coverage_raw_n"], 1)

    def test_identical_content_hash_counts_once_and_distinct_reviews_are_kept(self):
        reviews = [
            review("r1", "https://example.com/a", "same"),
            review("r2", "https://example.com/b", "same"),
            review("r3", "https://example.com/c", "other"),
            review("r4", "", ""),
        ]
        self.assertEqual(self._score(reviews)["c1"]["favorability_raw_n"], 3)

    def test_same_url_for_different_candidates_is_not_collapsed(self):
        reviews = [review("r1", "https://example.com/a"), review("r2", "https://example.com/a", candidate="c2")]
        scores = self._score(reviews[::-1])
        self.assertEqual(scores["c1"]["favorability_raw_n"], 1)
        self.assertEqual(scores["c2"]["favorability_raw_n"], 1)


if __name__ == "__main__":
    unittest.main()
