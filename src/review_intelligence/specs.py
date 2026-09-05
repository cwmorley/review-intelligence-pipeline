"""Customizable per-vertical specifications kept outside core product identity."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .normalize import parse_bool


VERIFIED_STATES = {"accepted", "corrected"}
SUPPORTED_TYPES = {"text", "number", "boolean", "enum"}


def compare_product_specs(
    subject_product_id: str,
    compared_product_id: str,
    products: Iterable[dict],
    definitions: Iterable[dict],
    values: Iterable[dict],
) -> list[dict]:
    product_map = {
        str(product["product_id"]): product
        for product in products
        if str(product.get("verification_status", "")).strip().lower() in VERIFIED_STATES
    }
    if subject_product_id not in product_map or compared_product_id not in product_map:
        raise ValueError("both products must be verified registry records")
    subject = product_map[subject_product_id]
    compared = product_map[compared_product_id]
    subject_vertical = str(subject.get("product_vertical", "")).strip()
    compared_vertical = str(compared.get("product_vertical", "")).strip()
    if not subject_vertical or subject_vertical != compared_vertical:
        raise ValueError("products must share a product vertical for spec comparison")

    definition_map = {}
    for definition in definitions:
        if parse_bool(definition.get("active")) is not True:
            continue
        if str(definition.get("product_vertical", "")).strip() != subject_vertical:
            continue
        applicable_categories = {
            item.strip()
            for item in str(definition.get("applies_to_category", "")).split("|")
            if item.strip()
        }
        product_categories = {
            str(subject.get("category", "")).strip(),
            str(compared.get("category", "")).strip(),
        }
        if applicable_categories and not applicable_categories.intersection(product_categories):
            continue
        spec_key = str(definition.get("spec_key", "")).strip()
        if not spec_key:
            raise ValueError("active spec definitions require spec_key")
        if spec_key in definition_map:
            raise ValueError(f"duplicate active spec definition: {subject_vertical}/{spec_key}")
        data_type = str(definition.get("data_type", "")).strip()
        if data_type not in SUPPORTED_TYPES:
            raise ValueError(f"unsupported spec data type: {data_type}")
        definition_map[spec_key] = definition

    value_map: dict[tuple[str, str], object] = {}
    for value in values:
        if str(value.get("verification_status", "")).strip().lower() not in VERIFIED_STATES:
            continue
        product_id = str(value.get("product_id", "")).strip()
        if product_id not in {subject_product_id, compared_product_id}:
            continue
        spec_key = str(value.get("spec_key", "")).strip()
        definition = definition_map.get(spec_key)
        if definition is None:
            raise ValueError(f"verified value references undefined spec: {subject_vertical}/{spec_key}")
        key = (product_id, spec_key)
        if key in value_map:
            raise ValueError(f"duplicate verified product spec: {product_id}/{spec_key}")
        value_map[key] = _typed_value(value, definition)

    rows = []
    for spec_key, definition in sorted(definition_map.items()):
        subject_value = value_map.get((subject_product_id, spec_key))
        compared_value = value_map.get((compared_product_id, spec_key))
        rows.append(
            {
                "product_vertical": subject_vertical,
                "subject_product_id": subject_product_id,
                "subject_product": _product_name(subject),
                "compared_product_id": compared_product_id,
                "compared_product": _product_name(compared),
                "spec_key": spec_key,
                "display_name": definition.get("display_name", spec_key),
                "data_type": definition.get("data_type"),
                "unit": definition.get("unit", ""),
                "required_for_match": parse_bool(definition.get("required_for_match")) is True,
                "match_weight": float(definition.get("match_weight", 0)),
                "definition_version": definition.get("definition_version", ""),
                "applies_to_category": definition.get("applies_to_category", ""),
                "subject_value": subject_value,
                "compared_value": compared_value,
                "comparison_result": _comparison_result(subject_value, compared_value),
            }
        )
    return rows


def write_spec_comparison(path: str | Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("no active vertical specification definitions to compare")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _typed_value(value: dict, definition: dict) -> object:
    data_type = str(definition["data_type"])
    if data_type == "number":
        raw = value.get("value_number")
        if raw in (None, ""):
            raise ValueError(f"numeric spec {definition['spec_key']} requires value_number")
        expected_unit = str(definition.get("unit", "")).strip()
        supplied_unit = str(value.get("unit", "")).strip()
        if expected_unit and supplied_unit != expected_unit:
            raise ValueError(f"spec {definition['spec_key']} requires unit {expected_unit}")
        return float(raw)
    if data_type == "boolean":
        parsed = parse_bool(value.get("value_boolean"))
        if parsed is None:
            raise ValueError(f"boolean spec {definition['spec_key']} requires value_boolean")
        return parsed
    raw = str(value.get("value_text", "")).strip()
    if not raw:
        raise ValueError(f"{data_type} spec {definition['spec_key']} requires value_text")
    if data_type == "enum":
        allowed = {item.strip() for item in str(definition.get("allowed_values", "")).split("|") if item.strip()}
        if raw not in allowed:
            raise ValueError(f"spec {definition['spec_key']} value is outside its allowed values")
    return raw


def _comparison_result(subject: object, compared: object) -> str:
    if subject is None and compared is None:
        return "missing_both"
    if subject is None:
        return "missing_subject"
    if compared is None:
        return "missing_compared"
    return "same" if subject == compared else "different"


def _product_name(product: dict) -> str:
    return " ".join(str(value) for value in (product.get("make"), product.get("model"), product.get("model_number")) if value)
