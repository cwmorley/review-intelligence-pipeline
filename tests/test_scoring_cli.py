import csv
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from review_intelligence.cli import main


class ScoringCliTests(unittest.TestCase):
    def _write_csv(self, path, fieldnames, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _inputs(self, root):
        candidates = root / "candidates.csv"
        reviews = root / "reviews.csv"
        engagements = root / "engagements.csv"
        self._write_csv(
            candidates,
            ["candidate_id", "candidate_name", "outlet_name", "influence_score", "active"],
            [
                {"candidate_id": "bad", "candidate_name": "Bad", "outlet_name": "B", "influence_score": "0.8", "active": "true"},
                {"candidate_id": "good", "candidate_name": "Good", "outlet_name": "G", "influence_score": "0.8", "active": "true"},
            ],
        )
        self._write_csv(
            reviews,
            ["review_id", "candidate_id", "verification_status", "rating_value", "rating_scale", "published_date"],
            [{"review_id": "rb", "candidate_id": "bad", "verification_status": "accepted", "rating_value": "9", "rating_scale": "10", "published_date": "2026-09-01"}],
        )
        self._write_csv(
            engagements,
            ["engagement_id", "candidate_id", "eligible_for_coverage", "coverage_observed", "coverage_review_id", "decision_date"],
            [{"engagement_id": "eb", "candidate_id": "bad", "eligible_for_coverage": "true", "coverage_observed": "true", "coverage_review_id": "rb", "decision_date": ""}],
        )
        return candidates, reviews, engagements

    def test_non_strict_cli_writes_scores_and_violation_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates, reviews, engagements = self._inputs(root)
            scores = root / "scores.csv"
            report = root / "violations.csv"

            exit_code = main([
                "score",
                "--candidates", str(candidates),
                "--reviews", str(reviews),
                "--engagements", str(engagements),
                "--as-of", "2026-09-04",
                "--data-quality-report", str(report),
                "--output", str(scores),
            ])

            self.assertEqual(exit_code, 0)
            with scores.open(encoding="utf-8") as handle:
                score_rows = list(csv.DictReader(handle))
            with report.open(encoding="utf-8") as handle:
                violations = list(csv.DictReader(handle))
            self.assertEqual(score_rows[0]["candidate_id"], "good")
            self.assertEqual(violations[0]["violation_code"], "missing_decision_date")

    def test_non_strict_cli_summarizes_when_report_is_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates, reviews, engagements = self._inputs(root)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = main([
                    "score",
                    "--candidates", str(candidates),
                    "--reviews", str(reviews),
                    "--engagements", str(engagements),
                    "--as-of", "2026-09-04",
                    "--output", str(root / "scores.csv"),
                ])
            self.assertEqual(exit_code, 0)
            self.assertIn("1 violation(s); 1 candidate(s) excluded", stderr.getvalue())

    def test_strict_cli_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates, reviews, engagements = self._inputs(root)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = main([
                    "score",
                    "--candidates", str(candidates),
                    "--reviews", str(reviews),
                    "--engagements", str(engagements),
                    "--as-of", "2026-09-04",
                    "--strict",
                    "--output", str(root / "scores.csv"),
                ])
            self.assertEqual(exit_code, 2)
            self.assertIn("missing_decision_date", stderr.getvalue())

    def test_all_excluded_writes_header_report_and_explicit_message(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates, reviews, engagements = self._inputs(root)
            with candidates.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self._write_csv(candidates, list(rows[0]), rows[:1])
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(["score", "--candidates", str(candidates), "--reviews", str(reviews),
                             "--engagements", str(engagements), "--as-of", "2026-09-04",
                             "--output", str(root / "scores.csv"),
                             "--data-quality-report", str(root / "violations.csv")])
            self.assertEqual(code, 0)
            self.assertIn("No rankable candidates remain", stderr.getvalue())
            with (root / "scores.csv").open() as handle:
                reader = csv.DictReader(handle)
                self.assertIn("rank_basis", reader.fieldnames)
                self.assertEqual(list(reader), [])
            with (root / "violations.csv").open() as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 1)


if __name__ == "__main__":
    unittest.main()
