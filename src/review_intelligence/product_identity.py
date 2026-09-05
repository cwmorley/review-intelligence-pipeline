"""Conservative make, model, model-number, and category resolution."""

from __future__ import annotations

import re
from typing import Iterable


VERIFIED_STATES = {"accepted", "corrected"}
RESOLVER_VERSION = "registry-v0.1"
MODEL_NUMBER_PATTERNS = (
    re.compile(r"\b(?=[A-Z0-9-]{4,}\b)(?=[A-Z0-9-]*\d)[A-Z]{1,8}(?:-[A-Z0-9]{1,8})+\b", re.IGNORECASE),
    re.compile(r"\b(?=[A-Z0-9]{4,}\b)(?=[A-Z0-9]*\d)[A-Z]{1,6}\d[A-Z0-9]{2,}\b", re.IGNORECASE),
)


def resolve_product_identity(record: dict, products: Iterable[dict], aliases: Iterable[dict]) -> dict:
    product_map = {
        str(product["product_id"]): product
        for product in products
        if str(product.get("verification_status", "")).strip().lower() in VERIFIED_STATES
    }
    verified_aliases = [
        alias
        for alias in aliases
        if str(alias.get("verification_status", "")).strip().lower() in VERIFIED_STATES
        and str(alias.get("product_id", "")) in product_map
    ]
    text_values = [
        record.get("product_make_raw"),
        record.get("product_model_raw"),
        record.get("product_model_number_raw"),
        record.get("product_sku_raw"),
        record.get("product_name"),
        record.get("headline"),
    ]
    combined_text = " | ".join(str(value) for value in text_values if value)

    identifier_values = {
        _normalize(record.get("product_model_number_raw")),
        _normalize(record.get("product_sku_raw")),
    } - {""}
    identifier_matches = set()
    for product_id, product in product_map.items():
        known = {_normalize(product.get("model_number")), _normalize(product.get("sku"))} - {""}
        if identifier_values & known:
            identifier_matches.add(product_id)
    for alias in verified_aliases:
        if str(alias.get("alias_type")) in {"model_number", "sku"} and _normalize(alias.get("alias_text")) in identifier_values:
            identifier_matches.add(str(alias["product_id"]))
    if len(identifier_matches) == 1:
        return _resolved(record, product_map[identifier_matches.pop()], "structured_identifier", "high", combined_text)
    if len(identifier_matches) > 1:
        return _unresolved(record, combined_text, "ambiguous_identifier")

    make = _normalize(record.get("product_make_raw"))
    model = _normalize(record.get("product_model_raw"))
    structured_matches = set()
    if make and model:
        for product_id, product in product_map.items():
            if make == _normalize(product.get("make")) and model == _normalize(product.get("model")):
                structured_matches.add(product_id)
    if len(structured_matches) == 1:
        return _resolved(record, product_map[structured_matches.pop()], "structured_make_model", "high", combined_text)
    if len(structured_matches) > 1:
        return _unresolved(record, combined_text, "ambiguous_make_model")

    normalized_text = f" {_normalize(combined_text)} "
    alias_matches = {
        str(alias["product_id"])
        for alias in verified_aliases
        if len(_normalize(alias.get("alias_text"))) >= 4
        and f" {_normalize(alias.get('alias_text'))} " in normalized_text
    }
    if len(alias_matches) == 1:
        return _resolved(record, product_map[alias_matches.pop()], "verified_alias", "medium", combined_text)
    if len(alias_matches) > 1:
        return _unresolved(record, combined_text, "ambiguous_alias")
    return _unresolved(record, combined_text, "no_registry_match")


def resolve_product_records(records: Iterable[dict], products: Iterable[dict], aliases: Iterable[dict]) -> list[dict]:
    product_rows = list(products)
    alias_rows = list(aliases)
    return [resolve_product_identity(record, product_rows, alias_rows) for record in records]


def _resolved(record: dict, product: dict, method: str, confidence: str, evidence_text: str) -> dict:
    return {
        **record,
        "resolved_product_id": product.get("product_id"),
        "resolved_make": product.get("make"),
        "resolved_model": product.get("model"),
        "resolved_model_number": product.get("model_number"),
        "resolved_variant": product.get("variant"),
        "resolved_sku": product.get("sku"),
        "resolved_product_vertical": product.get("product_vertical"),
        "resolved_category": product.get("category"),
        "resolution_method": method,
        "resolution_confidence": confidence,
        "resolver_version": RESOLVER_VERSION,
        "detected_model_number": (
            record.get("product_model_number_raw")
            or _detect_model_number(evidence_text)
            or product.get("model_number")
        ),
        "product_verification_status": "candidate",
    }


def _unresolved(record: dict, evidence_text: str, reason: str) -> dict:
    return {
        **record,
        "resolved_product_id": None,
        "resolved_make": record.get("product_make_raw"),
        "resolved_model": record.get("product_model_raw"),
        "resolved_model_number": None,
        "resolved_variant": None,
        "resolved_sku": record.get("product_sku_raw"),
        "resolved_product_vertical": None,
        "resolved_category": None,
        "resolution_method": reason,
        "resolution_confidence": "unresolved",
        "resolver_version": RESOLVER_VERSION,
        "detected_model_number": _detect_model_number(evidence_text),
        "product_verification_status": "candidate",
    }


def _normalize(value: object) -> str:
    if value is None:
        return ""
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", str(value).upper()).split())


def _detect_model_number(text: str) -> str | None:
    for pattern in MODEL_NUMBER_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None
