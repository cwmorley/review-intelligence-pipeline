# Synthetic launch example

`synthetic_scores.csv` is generated from the four synthetic CSV files in `data/`.

`synthetic_extracted.jsonl` is generated from `data/synthetic_review_page.html` and shows the intentionally unverified output of the JSON-LD processing layer.

`synthetic_product_resolution.jsonl` shows the universal make, model, model number, optional SKU, vertical, and category proposed from structured identifiers and the verified registry. The proposed identity still requires human acceptance.

`synthetic_competitive_summary.csv` rolls up verified subject-versus-compared product observations. It is descriptive evidence, not NRS-Delta and not a causal product-performance claim.

`synthetic_spec_comparison.csv` applies the active `computers` spec definition to one product pair. The same engine also accepts the example camera and coffee-maker definitions without changing the core product schema.

`synthetic_laptop_spec_comparison.csv` demonstrates category-specific laptop fields: screen type, size, resolution, refresh rate, brightness, and touchscreen status. Those fields are automatically omitted from the desktop comparison.

It demonstrates ranking mechanics and uncertainty reporting. It does not demonstrate predictive validity, actual reviewer behavior, or realized commercial value. A production implementation must keep its populated engagement ledger private and must preserve human review before allocation decisions.
