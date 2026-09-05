"""Net Reviewer Score baseline built from separate evidence streams."""

from __future__ import annotations

import csv
import warnings
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .normalize import is_favorable, normalize_rating, parse_bool
from .statistics import BetaEstimate, beta_posterior, effective_sample_size, recency_weight


VERIFIED_STATES = {"accepted", "corrected"}
EVIDENCE_TIERS = {
    "direction_resolved": 0,
    "direction_unresolved": 1,
    "insufficient_evidence": 2,
}
SCORE_FIELDS = [
    "rank",
    "candidate_id",
    "candidate_name",
    "outlet_name",
    "analysis_scope",
    "coverage_raw_n",
    "coverage_effective_n",
    "coverage_mean",
    "coverage_lower_95",
    "coverage_upper_95",
    "influence_score",
    "favorability_raw_n",
    "favorability_effective_n",
    "favorability_mean",
    "favorability_lower_95",
    "favorability_upper_95",
    "expected_earned_value",
    "expected_earned_value_lower_95",
    "score_variant",
    "nrs_ev_score",
    "nrs_ev_lower_95",
    "evidence_status",
    "rank_basis",
    "human_decision_required",
]
VIOLATION_FIELDS = [
    "record_type",
    "record_id",
    "candidate_id",
    "violation_code",
    "detail",
    "excluded_reason",
]


class DataQualityError(ValueError):
    """Raised when strict scoring encounters candidate-level evidence violations."""

    def __init__(self, violation: dict[str, str]):
        self.violation = violation
        super().__init__(
            f"{violation['violation_code']} in {violation['record_type']} "
            f"{violation['record_id']} for candidate {violation['candidate_id']}: "
            f"{violation['detail']}"
        )


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def score_candidates(
    candidates: Iterable[dict],
    reviews: Iterable[dict],
    engagements: Iterable[dict],
    as_of: date,
    half_life_days: float | None = 730.0,
    favorability_threshold: float = 0.8,
    eligible_product_ids: set[str] | None = None,
    analysis_scope: str = "all verified products",
    strict: bool = False,
    violations: list[dict[str, str]] | None = None,
) -> list[dict]:
    reviews_by_candidate: dict[str, list[dict]] = defaultdict(list)
    engagements_by_candidate: dict[str, list[dict]] = defaultdict(list)
    verified_reviews: dict[str, str] = {}
    for review in reviews:
        if eligible_product_ids is not None and str(review.get("product_id", "")) not in eligible_product_ids:
            continue
        if str(review.get("verification_status", "")).strip().lower() in VERIFIED_STATES:
            review_candidate = str(review.get("candidate_id", ""))
            reviews_by_candidate[review_candidate].append(review)
            review_id = str(review.get("review_id", "")).strip()
            if review_id:
                verified_reviews[review_id] = review_candidate
    for engagement in engagements:
        if eligible_product_ids is not None and str(engagement.get("product_id", "")) not in eligible_product_ids:
            continue
        if parse_bool(engagement.get("eligible_for_coverage")) is True:
            engagements_by_candidate[str(engagement.get("candidate_id", ""))].append(engagement)

    results = []
    collected_violations = violations if violations is not None else []
    for candidate in candidates:
        if parse_bool(candidate.get("active")) is False:
            continue
        candidate_id = str(candidate["candidate_id"])
        influence = _bounded_float(candidate.get("influence_score"), "influence_score")

        candidate_violations = _candidate_violations(
            candidate_id,
            reviews_by_candidate[candidate_id],
            engagements_by_candidate[candidate_id],
            verified_reviews,
            favorability_threshold,
        )
        if candidate_violations:
            if strict:
                raise DataQualityError(candidate_violations[0])
            collected_violations.extend(candidate_violations)
            continue

        coverage_observations: list[tuple[bool, float]] = []
        for engagement in engagements_by_candidate[candidate_id]:
            observed = _coverage_observed(engagement)
            weight = _weight_for_date(engagement.get("decision_date"), as_of, half_life_days)
            coverage_observations.append((observed, weight))

        favorability_observations: list[tuple[bool, float]] = []
        for review in reviews_by_candidate[candidate_id]:
            normalized = normalize_rating(review.get("rating_value"), review.get("rating_scale"))
            favorable = is_favorable(normalized, favorability_threshold)
            if favorable is None:
                continue
            weight = _weight_for_date(review.get("published_date"), as_of, half_life_days)
            favorability_observations.append((favorable, weight))

        coverage = beta_posterior(coverage_observations)
        favorability = beta_posterior(favorability_observations)
        expected_value = coverage.mean * influence * favorability.mean
        expected_value_lower = coverage.lower * influence * favorability.lower
        status = _evidence_status(coverage_observations, favorability_observations, favorability)
        results.append(
            {
                "candidate_id": candidate_id,
                "candidate_name": candidate.get("candidate_name", ""),
                "outlet_name": candidate.get("outlet_name", ""),
                "analysis_scope": analysis_scope,
                "coverage_raw_n": len(coverage_observations),
                "coverage_effective_n": effective_sample_size([weight for _, weight in coverage_observations]),
                "coverage_mean": coverage.mean,
                "coverage_lower_95": coverage.lower,
                "coverage_upper_95": coverage.upper,
                "influence_score": influence,
                "favorability_raw_n": len(favorability_observations),
                "favorability_effective_n": effective_sample_size([weight for _, weight in favorability_observations]),
                "favorability_mean": favorability.mean,
                "favorability_lower_95": favorability.lower,
                "favorability_upper_95": favorability.upper,
                "expected_earned_value": expected_value,
                "expected_earned_value_lower_95": expected_value_lower,
                "score_variant": "NRS-EV v0.1",
                "nrs_ev_score": 100.0 * expected_value,
                "nrs_ev_lower_95": 100.0 * expected_value_lower,
                "evidence_status": status,
                "rank_basis": f"evidence_tier:{status};lower_95",
                "human_decision_required": True,
            }
        )

    results.sort(
        key=lambda item: (
            EVIDENCE_TIERS[item["evidence_status"]],
            -item["expected_earned_value_lower_95"],
            item["candidate_id"],
        )
    )
    for rank, result in enumerate(results, start=1):
        result["rank"] = rank
    if violations is None and collected_violations:
        excluded_candidates = len({violation["candidate_id"] for violation in collected_violations})
        warnings.warn(
            f"{len(collected_violations)} data-quality violation(s) excluded "
            f"{excluded_candidates} candidate(s); pass a violations list to inspect details",
            RuntimeWarning,
            stacklevel=2,
        )
    return results


def write_scores(path: str | Path, scores: list[dict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCORE_FIELDS)
        writer.writeheader()
        for score in scores:
            writer.writerow({key: _format(value) for key, value in score.items()})


def write_data_quality_report(path: str | Path, violations: list[dict[str, str]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=VIOLATION_FIELDS)
        writer.writeheader()
        writer.writerows(violations)


def _candidate_violations(
    candidate_id: str,
    reviews: list[dict],
    engagements: list[dict],
    verified_reviews: dict[str, str],
    favorability_threshold: float,
) -> list[dict[str, str]]:
    violations = []
    for engagement in engagements:
        record_id = str(engagement.get("engagement_id", "")).strip() or "<unknown>"
        observed = _coverage_observed(engagement)
        linked_review = str(engagement.get("coverage_review_id", "")).strip()
        if observed and verified_reviews.get(linked_review) != candidate_id:
            violations.append(
                _violation(
                    "engagement",
                    record_id,
                    candidate_id,
                    "coverage_success_unlinked",
                    "coverage success must reference a verified review by the same candidate",
                )
            )
        if not observed and linked_review:
            violations.append(
                _violation(
                    "engagement",
                    record_id,
                    candidate_id,
                    "coverage_failure_linked",
                    "coverage failure cannot reference a coverage review",
                )
            )
        if not str(engagement.get("decision_date", "")).strip():
            violations.append(
                _violation(
                    "engagement",
                    record_id,
                    candidate_id,
                    "missing_decision_date",
                    "eligible engagement requires a decision date for recency weighting",
                )
            )

    for review in reviews:
        normalized = normalize_rating(review.get("rating_value"), review.get("rating_scale"))
        if is_favorable(normalized, favorability_threshold) is None:
            continue
        if not str(review.get("published_date", "")).strip():
            violations.append(
                _violation(
                    "review",
                    str(review.get("review_id", "")).strip() or "<unknown>",
                    candidate_id,
                    "missing_published_date",
                    "scored review requires a publication date for recency weighting",
                )
            )
    return violations


def _coverage_observed(engagement: dict) -> bool:
    observed = parse_bool(engagement.get("coverage_observed"))
    if observed is None:
        return bool(str(engagement.get("coverage_review_id", "")).strip())
    return observed


def _violation(
    record_type: str,
    record_id: str,
    candidate_id: str,
    violation_code: str,
    detail: str,
) -> dict[str, str]:
    return {
        "record_type": record_type,
        "record_id": record_id,
        "candidate_id": candidate_id,
        "violation_code": violation_code,
        "detail": detail,
        "excluded_reason": "candidate_excluded_due_to_data_quality_violation",
    }


def _weight_for_date(value: object, as_of: date, half_life_days: float | None) -> float:
    if not value:
        raise ValueError("dated evidence is required when scoring")
    observed = datetime.strptime(str(value), "%Y-%m-%d").date()
    return recency_weight((as_of - observed).days, half_life_days)


def _bounded_float(value: object, field: str) -> float:
    number = float(value)
    if not 0 <= number <= 1:
        raise ValueError(f"{field} must be between zero and one")
    return number


def _evidence_status(
    coverage_observations: list[tuple[bool, float]],
    favorability_observations: list[tuple[bool, float]],
    favorability: BetaEstimate,
) -> str:
    if not coverage_observations or not favorability_observations:
        return "insufficient_evidence"
    if favorability.lower <= 0.5 <= favorability.upper:
        return "direction_unresolved"
    return "direction_resolved"


def _format(value: object) -> object:
    return f"{value:.6f}" if isinstance(value, float) else value
