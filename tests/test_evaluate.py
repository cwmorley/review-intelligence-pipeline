import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from review_intelligence.cli import main
from review_intelligence.evaluate import (
    FlawedReplayProvider,
    GoldenReplayProvider,
    apply_thresholds,
    evaluate_provider,
    format_report_table,
    load_golden_set,
    parse_thresholds,
)
from review_intelligence.llm_extract import ProviderError


GOLDEN = Path(__file__).resolve().parents[1] / "evals" / "golden_reviews.json"


class EvaluateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_golden_set(GOLDEN)

    def test_golden_set_is_synthetic_and_bounded(self):
        payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertIs(payload["synthetic"], True)
        self.assertTrue(8 <= len(self.cases) <= 12)

    def test_perfect_provider_scores_one_with_no_rejections(self):
        report = evaluate_provider(self.cases, GoldenReplayProvider(self.cases))
        self.assertEqual(report["cases"], 10)
        self.assertEqual(set(report["metrics"].values()), {1.0})
        self.assertEqual(report["counts"]["rejected_total"], 0)
        self.assertEqual(report["counts"]["quotes_proposed"], 25)
        self.assertEqual(report["model_id"], "offline-golden-replay")

    def test_flawed_provider_metrics_reflect_each_known_defect(self):
        report = evaluate_provider(self.cases, FlawedReplayProvider(self.cases))
        # 4 of 10 verdicts flipped; 3 of 12 competitors dropped; 2 reviewed products
        # offered as competitors (grounded, so admitted); 5 invented products and
        # 5 altered quotes (ungrounded, so rejected).
        self.assertEqual(
            report["metrics"],
            {
                "verdict_accuracy": 0.6,
                "competitor_precision": 0.8182,
                "competitor_recall": 0.75,
                "competitor_precision_before_validation": 0.5625,
                "quote_grounding_rate": 0.8,
            },
        )
        self.assertEqual(report["counts"]["rejected_by_reason"], {"not_in_source": 5, "quote_not_in_source": 5})
        by_case = {row["case_id"]: row for row in report["case_results"]}
        self.assertEqual(by_case["cobalt-negative"]["competitors_unexpected"], ["northstar cobalt 3000"])
        self.assertEqual(by_case["beacon-mixed"]["competitors_missed"], ["boreal studio 5100"])

    def test_provider_errors_are_counted_and_undefined_metrics_fail_the_gate(self):
        def failing(system, user, schema):
            raise ProviderError("offline")

        report = evaluate_provider(self.cases, failing)
        self.assertEqual(report["counts"]["provider_errors"], 10)
        self.assertEqual(report["metrics"]["competitor_recall"], 0.0)
        self.assertIsNone(report["metrics"]["quote_grounding_rate"])
        results = apply_thresholds(report, {"quote_grounding_rate": 0.0})
        self.assertFalse(results[0]["passed"])
        self.assertIn("n/a", format_report_table(report))

    def test_threshold_parsing(self):
        self.assertEqual(parse_thresholds(["verdict_accuracy=0.9"]), {"verdict_accuracy": 0.9})
        for bad in ("verdict_accuracy", "made_up=0.5", "verdict_accuracy=1.5"):
            with self.assertRaises(ValueError):
                parse_thresholds([bad])

    def _run(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["llm-eval", "--golden", str(GOLDEN), *arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_writes_report_and_passes_gate_for_perfect_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            code, stdout, _ = self._run(
                "--provider", "offline-perfect", "--min", "verdict_accuracy=1.0", "--output", str(output)
            )
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertTrue(report["passed"])
        self.assertIn("verdict_accuracy", stdout)
        self.assertIn("pass", stdout)

    def test_cli_exits_nonzero_when_a_metric_is_below_its_floor(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            code, stdout, stderr = self._run(
                "--provider", "offline-flawed",
                "--min", "verdict_accuracy=0.9",
                "--min", "competitor_recall=0.7",
                "--output", str(output),
            )
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertFalse(report["passed"])
        self.assertEqual([item["passed"] for item in report["thresholds"]], [True, False])
        self.assertIn("FAIL", stdout)
        self.assertIn("Evaluation gate failed", stderr)

    def test_cli_without_floors_reports_but_does_not_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            code, _, _ = self._run("--provider", "offline-flawed", "--output", str(Path(directory) / "r.json"))
        self.assertEqual(code, 0)

    def test_live_provider_commands_refuse_to_run_without_configuration(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {}, clear=True):
            code, _, stderr = self._run("--provider", "anthropic", "--output", str(Path(directory) / "r.json"))
            self.assertEqual(code, 2)
            self.assertIn("ANTHROPIC_API_KEY, ANTHROPIC_MODEL", stderr)
            text = Path(directory) / "review.txt"
            text.write_text("A review.", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(["llm-extract", "--text", str(text), "--source-url", "https://example.com/r",
                             "--output", str(Path(directory) / "out.jsonl")])
            self.assertEqual(code, 2)
            self.assertFalse((Path(directory) / "out.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
