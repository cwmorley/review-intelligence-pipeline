"""Offline evaluation of LLM extraction against a labeled golden set."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .llm_extract import (
    DEFAULT_MAX_CHARS,
    DEFAULT_MAX_ITEMS,
    PROMPT_VERSION,
    VALIDATOR_VERSION,
    VERDICTS,
    Provider,
    extract_review_fields,
    normalize_whitespace,
)


GATEABLE_METRICS = (
    "verdict_accuracy",
    "competitor_precision",
    "competitor_recall",
    "competitor_precision_before_validation",
    "quote_grounding_rate",
)


def load_golden_set(path: str | Path) -> list[dict]:
    cases = json.loads(Path(path).read_text(encoding="utf-8"))["cases"]
    seen: set[str] = set()
    for case in cases:
        case_id = str(case.get("case_id") or "")
        expected = case.get("expected") or {}
        if not case_id or case_id in seen:
            raise ValueError(f"golden case ids must be present and unique: {case_id!r}")
        if not str(case.get("text") or "").strip():
            raise ValueError(f"golden case has no text: {case_id}")
        if expected.get("verdict") not in VERDICTS or not isinstance(expected.get("competing_products"), list):
            raise ValueError(f"golden case has invalid expected labels: {case_id}")
        seen.add(case_id)
    return cases


def evaluate_provider(
    cases: Iterable[dict],
    provider: Provider,
    max_chars: int = DEFAULT_MAX_CHARS,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> dict[str, Any]:
    """Run ``provider`` through the validated extractor and score the admitted output."""
    totals = Counter()
    rejections: Counter = Counter()
    rows = []
    for case in cases:
        record = extract_review_fields(case["text"], provider, max_chars=max_chars, max_items=max_items)
        expected = case["expected"]
        gold = {_key(name) for name in expected["competing_products"]}
        admitted = {_key(name) for name in record["competing_products_mentioned"]}
        # What the model proposed before grounding: admitted names plus ungrounded ones.
        proposed = admitted | {
            _key(item["value"])
            for item in record["rejected"]
            if item["field"] == "competing_products" and item["reason"] == "not_in_source"
        }
        reasons = Counter(item["reason"] for item in record["rejected"])
        rejections.update(reasons)
        verdict_correct = record["verdict"] == expected["verdict"]
        totals.update(
            cases=1,
            verdict_correct=int(verdict_correct),
            gold=len(gold),
            admitted=len(admitted),
            admitted_correct=len(admitted & gold),
            proposed=len(proposed),
            proposed_correct=len(proposed & gold),
            quotes_proposed=record["validation"]["quotes_proposed"],
            quotes_grounded=record["validation"]["quotes_grounded"],
            provider_errors=reasons["provider_error"],
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "expected_verdict": expected["verdict"],
                "verdict": record["verdict"],
                "verdict_correct": verdict_correct,
                "competitors_missed": sorted(gold - admitted),
                "competitors_unexpected": sorted(admitted - gold),
                "rejected": dict(sorted(reasons.items())),
            }
        )
    return {
        "model_id": str(getattr(provider, "model_id", None) or "unknown"),
        "prompt_version": PROMPT_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "cases": totals["cases"],
        "metrics": {
            "verdict_accuracy": _ratio(totals["verdict_correct"], totals["cases"]),
            "competitor_precision": _ratio(totals["admitted_correct"], totals["admitted"]),
            "competitor_recall": _ratio(totals["admitted_correct"], totals["gold"]),
            "competitor_precision_before_validation": _ratio(totals["proposed_correct"], totals["proposed"]),
            "quote_grounding_rate": _ratio(totals["quotes_grounded"], totals["quotes_proposed"]),
        },
        "counts": {
            "quotes_proposed": totals["quotes_proposed"],
            "quotes_grounded": totals["quotes_grounded"],
            "rejected_total": sum(rejections.values()),
            "rejected_by_reason": dict(sorted(rejections.items())),
            "provider_errors": totals["provider_errors"],
        },
        "case_results": rows,
    }


def parse_thresholds(values: Iterable[str]) -> dict[str, float]:
    floors: dict[str, float] = {}
    for value in values:
        name, separator, number = value.partition("=")
        if not separator or name not in GATEABLE_METRICS:
            raise ValueError(f"threshold must be METRIC=FLOOR with a metric in {', '.join(GATEABLE_METRICS)}: {value}")
        floors[name] = float(number)
        if not 0.0 <= floors[name] <= 1.0:
            raise ValueError(f"threshold floor must be between 0 and 1: {value}")
    return floors


def apply_thresholds(report: dict, floors: dict[str, float]) -> list[dict]:
    """Return one result per floor. An undefined metric fails rather than passing silently."""
    results = []
    for name, floor in sorted(floors.items()):
        value = report["metrics"][name]
        results.append({"metric": name, "floor": floor, "value": value, "passed": value is not None and value >= floor})
    return results


def format_report_table(report: dict) -> str:
    lines = [f"LLM extraction eval: {report['cases']} cases, model {report['model_id']}, prompt {report['prompt_version']}"]
    floors = {item["metric"]: item for item in report.get("thresholds", [])}
    for name, value in report["metrics"].items():
        shown = "n/a" if value is None else f"{value:.3f}"
        gate = floors.get(name)
        status = "" if gate is None else f"  floor {gate['floor']:.3f}  {'pass' if gate['passed'] else 'FAIL'}"
        lines.append(f"  {name:<40}{shown:>6}{status}")
    counts = report["counts"]
    reasons = ", ".join(f"{reason}={count}" for reason, count in counts["rejected_by_reason"].items()) or "none"
    lines.append(f"  {'rejected_items':<40}{counts['rejected_total']:>6}  ({reasons})")
    return "\n".join(lines)


class GoldenReplayProvider:
    """Offline provider that replays the golden labels. It checks the harness, not a model."""

    model_id = "offline-golden-replay"

    def __init__(self, cases: Iterable[dict]) -> None:
        self._cases = list(cases)

    def _case_index(self, user_prompt: str) -> int:
        for index, case in enumerate(self._cases):
            if case["text"] in user_prompt:
                return index
        raise LookupError("prompt does not contain a golden case text")

    def __call__(self, system: str, user: str, schema: dict) -> dict:
        expected = self._cases[self._case_index(user)]["expected"]
        return {
            "verdict": expected["verdict"],
            "competing_products": list(expected["competing_products"]),
            "pros": [dict(item) for item in expected.get("pros", [])],
            "cons": [dict(item) for item in expected.get("cons", [])],
        }


class FlawedReplayProvider(GoldenReplayProvider):
    """Offline provider with fixed, known defects so the metrics and validator have something to catch."""

    model_id = "offline-flawed-replay"
    HALLUCINATED_PRODUCT = "Zenith Quasar 9000"

    def __call__(self, system: str, user: str, schema: dict) -> dict:
        index = self._case_index(user)
        case = self._cases[index]
        output = super().__call__(system, user, schema)
        if index % 3 == 0:  # wrong verdict
            output["verdict"] = VERDICTS[(VERDICTS.index(output["verdict"]) + 1) % len(VERDICTS)]
        if index % 2 == 0:  # a product the text never mentions
            output["competing_products"].append(self.HALLUCINATED_PRODUCT)
        if index % 4 == 1:  # a missed competitor
            output["competing_products"] = output["competing_products"][1:]
        if index % 5 == 2:  # the reviewed product itself: grounded, but not a competitor
            output["competing_products"].append(case["subject_product"])
        if index % 2 == 1 and output["pros"]:  # a paraphrase presented as a quote
            output["pros"][0]["quote"] = output["pros"][0]["quote"].upper()
        return output


def _key(name: str) -> str:
    return normalize_whitespace(name).casefold()


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 4)
