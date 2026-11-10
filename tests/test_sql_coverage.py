import importlib.util
import unittest
from datetime import date
from pathlib import Path

from review_intelligence.scoring import read_csv, score_candidates

ROOT = Path(__file__).resolve().parents[1]


def load_runner():
    spec = importlib.util.spec_from_file_location("run_coverage_rate", ROOT / "sql" / "run_coverage_rate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SqlCoverageTests(unittest.TestCase):
    def test_sql_coverage_matches_python_scoring_on_synthetic_data(self):
        data = ROOT / "data"
        python_rows = score_candidates(
            candidates=read_csv(data / "synthetic_candidates.csv"),
            reviews=read_csv(data / "synthetic_reviews.csv"),
            engagements=read_csv(data / "synthetic_engagements.csv"),
            as_of=date(2026, 9, 4),
            half_life_days=None,
            strict=True,
        )
        sql_rows = {row["candidate_id"]: row for row in load_runner().coverage_rates(data)}
        self.assertEqual(set(sql_rows), {row["candidate_id"] for row in python_rows})
        for row in python_rows:
            sql = sql_rows[row["candidate_id"]]
            self.assertEqual(sql["placements_offered"], row["coverage_raw_n"])
            self.assertAlmostEqual(sql["coverage_posterior_mean"], row["coverage_mean"], places=12)
            # Python reports the posterior mean; recover its success count to check the raw rate.
            covered = round(row["coverage_mean"] * (row["coverage_raw_n"] + 2) - 1)
            self.assertEqual(sql["placements_covered"], covered)
            self.assertAlmostEqual(sql["coverage_rate"], covered / row["coverage_raw_n"])
        self.assertAlmostEqual(sum(row["share_of_placements"] for row in sql_rows.values()), 1.0)
        self.assertEqual(sql_rows["cand-workgrid"]["placements_offered"], 3)  # the ineligible placement is not offered


if __name__ == "__main__":
    unittest.main()
