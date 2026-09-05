"""Verified competitive-product context without manufacturing a net score."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable


VERIFIED_STATES = {"accepted", "corrected"}
OUTCOMES = {"subject_preferred", "parity", "compared_preferred", "mixed", "unclear"}


def eligible_product_ids_for_make(products: Iterable[dict], target_make: str) -> set[str]:
    target = target_make.strip().casefold()
    return {
        str(product["product_id"])
        for product in products
        if str(product.get("make", "")).strip().casefold() == target
        and str(product.get("verification_status", "")).strip().lower() in VERIFIED_STATES
    }


def build_competitive_summary(
    products: Iterable[dict],
    reviews: Iterable[dict],
    comparisons: Iterable[dict],
) -> list[dict]:
    product_map = {
        str(product["product_id"]): product
        for product in products
        if str(product.get("verification_status", "")).strip().lower() in VERIFIED_STATES
    }
    review_map = {
        str(review["review_id"]): review
        for review in reviews
        if str(review.get("verification_status", "")).strip().lower() in VERIFIED_STATES
    }
    grouped: dict[tuple[str, str, str], list[tuple[dict, dict]]] = defaultdict(list)

    for comparison in comparisons:
        if str(comparison.get("verification_status", "")).strip().lower() not in VERIFIED_STATES:
            continue
        review_id = str(comparison.get("review_id", ""))
        comparison_id = comparison.get("comparison_id", "<unknown>")
        match_set_id = str(comparison.get("match_set_id", "")).strip()
        match_basis = str(comparison.get("match_basis", "")).strip()
        evidence_locator = str(comparison.get("evidence_locator", "")).strip()
        if not match_set_id or not match_basis or not evidence_locator:
            raise ValueError(
                f"comparison {comparison_id} requires match_set_id, match_basis, and evidence_locator"
            )
        review = review_map.get(review_id)
        if review is None:
            raise ValueError(f"comparison {comparison_id} must reference a verified review")
        subject_id = str(comparison.get("subject_product_id", ""))
        compared_id = str(comparison.get("compared_product_id", ""))
        if subject_id == compared_id:
            raise ValueError(f"comparison {comparison_id} cannot compare a product with itself")
        if subject_id not in product_map or compared_id not in product_map:
            raise ValueError(f"comparison {comparison_id} references an unverified product")
        if str(review.get("product_id", "")) != subject_id:
            raise ValueError(
                f"comparison {comparison_id} subject product does not match its review subject"
            )
        outcome = str(comparison.get("comparative_outcome", ""))
        if outcome not in OUTCOMES:
            raise ValueError(f"unsupported comparative outcome: {outcome}")
        key = (match_set_id, subject_id, compared_id)
        grouped[key].append((comparison, review))

    rows = []
    for (match_set_id, subject_id, compared_id), evidence in sorted(grouped.items()):
        subject = product_map[subject_id]
        compared = product_map[compared_id]
        counts = {outcome: 0 for outcome in OUTCOMES}
        candidate_ids = set()
        match_bases = set()
        for comparison, review in evidence:
            counts[str(comparison["comparative_outcome"])] += 1
            candidate_ids.add(str(review.get("candidate_id", "")))
            match_bases.add(str(comparison["match_basis"]).strip())
        rows.append(
            {
                "match_set_id": match_set_id,
                "subject_product_id": subject_id,
                "subject_product": _product_name(subject),
                "compared_product_id": compared_id,
                "compared_product": _product_name(compared),
                "match_basis": " | ".join(sorted(match_bases)),
                "verified_comparison_count": len(evidence),
                "unique_reviewer_count": len(candidate_ids),
                "subject_preferred_count": counts["subject_preferred"],
                "parity_count": counts["parity"],
                "compared_preferred_count": counts["compared_preferred"],
                "mixed_count": counts["mixed"],
                "unclear_count": counts["unclear"],
                "evidence_status": "thin_evidence" if len(candidate_ids) < 3 else "descriptive_only",
                "human_interpretation_required": True,
            }
        )
    return rows


def write_competitive_summary(path: str | Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("no verified competitive observations to write")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _product_name(product: dict) -> str:
    return " ".join(str(value) for value in (product.get("make"), product.get("model"), product.get("model_number")) if value)
