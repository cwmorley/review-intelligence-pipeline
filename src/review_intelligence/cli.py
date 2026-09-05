from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .competitive import build_competitive_summary, eligible_product_ids_for_make, write_competitive_summary
from .extract import extract_review_candidates
from .product_identity import resolve_product_records
from .scoring import DataQualityError, read_csv, score_candidates, write_data_quality_report, write_scores
from .specs import compare_product_specs, write_spec_comparison


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="review-intelligence")
    subcommands = parser.add_subparsers(dest="command", required=True)
    score = subcommands.add_parser("score", help="calculate the transparent NRS baseline")
    score.add_argument("--reviews", required=True)
    score.add_argument("--engagements", required=True)
    score.add_argument("--candidates", required=True)
    score.add_argument("--products")
    score.add_argument("--target-make")
    score.add_argument("--as-of", required=True, help="YYYY-MM-DD")
    score.add_argument("--half-life-days", type=float, default=730.0)
    score.add_argument("--favorability-threshold", type=float, default=0.8)
    score.add_argument("--data-quality-report", help="CSV destination for candidate-level evidence violations")
    score.add_argument("--strict", action="store_true", help="stop on the first data-quality violation")
    score.add_argument("--output", required=True)
    extract = subcommands.add_parser("extract", help="extract unverified candidates from a saved HTML file")
    extract.add_argument("--html", required=True)
    extract.add_argument("--source-url", required=True)
    extract.add_argument("--output", required=True, help="JSON Lines destination")
    competitive = subcommands.add_parser("competitive-report", help="summarize verified matched-product observations")
    competitive.add_argument("--products", required=True)
    competitive.add_argument("--reviews", required=True)
    competitive.add_argument("--comparisons", required=True)
    competitive.add_argument("--output", required=True)
    resolve = subcommands.add_parser("resolve-products", help="resolve make, model, model number, and category candidates")
    resolve.add_argument("--input", required=True, help="extracted JSON Lines input")
    resolve.add_argument("--products", required=True)
    resolve.add_argument("--aliases", required=True)
    resolve.add_argument("--output", required=True)
    spec_report = subcommands.add_parser("spec-report", help="compare customizable specs for two products in one vertical")
    spec_report.add_argument("--subject-product", required=True)
    spec_report.add_argument("--compared-product", required=True)
    spec_report.add_argument("--products", required=True)
    spec_report.add_argument("--definitions", required=True)
    spec_report.add_argument("--values", required=True)
    spec_report.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "score":
        if bool(args.products) != bool(args.target_make):
            raise SystemExit("--products and --target-make must be supplied together")
        product_ids = None
        scope = "all verified products"
        if args.products:
            products = read_csv(args.products)
            product_ids = eligible_product_ids_for_make(products, args.target_make)
            if not product_ids:
                raise SystemExit(f"no verified products found for target make: {args.target_make}")
            scope = f"target make: {args.target_make}"
        violations = []
        try:
            scores = score_candidates(
                candidates=read_csv(args.candidates),
                reviews=read_csv(args.reviews),
                engagements=read_csv(args.engagements),
                as_of=datetime.strptime(args.as_of, "%Y-%m-%d").date(),
                half_life_days=args.half_life_days,
                favorability_threshold=args.favorability_threshold,
                eligible_product_ids=product_ids,
                analysis_scope=scope,
                strict=args.strict,
                violations=violations,
            )
        except DataQualityError as error:
            print(f"Data quality error: {error}", file=sys.stderr)
            return 2
        write_scores(args.output, scores)
        excluded_candidates = len({violation["candidate_id"] for violation in violations})
        if args.data_quality_report:
            write_data_quality_report(args.data_quality_report, violations)
            print(f"Wrote {len(violations)} data-quality violations to {args.data_quality_report}")
        else:
            print(
                f"Data quality: {len(violations)} violation(s); "
                f"{excluded_candidates} candidate(s) excluded.",
                file=sys.stderr,
            )
        if not scores:
            print("No rankable candidates remain; the score file contains only its header.", file=sys.stderr)
        print(f"Wrote {len(scores)} evidence-adjusted candidate scores to {args.output}")
    elif args.command == "extract":
        html = Path(args.html).read_text(encoding="utf-8")
        records = extract_review_candidates(html, args.source_url)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")
        print(f"Wrote {len(records)} unverified extraction candidates to {args.output}")
    elif args.command == "competitive-report":
        rows = build_competitive_summary(
            products=read_csv(args.products),
            reviews=read_csv(args.reviews),
            comparisons=read_csv(args.comparisons),
        )
        write_competitive_summary(args.output, rows)
        print(f"Wrote {len(rows)} verified competitive match summaries to {args.output}")
    elif args.command == "resolve-products":
        records = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
        resolved = resolve_product_records(records, read_csv(args.products), read_csv(args.aliases))
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in resolved), encoding="utf-8")
        print(f"Wrote {len(resolved)} product-identity candidates to {args.output}")
    elif args.command == "spec-report":
        rows = compare_product_specs(
            subject_product_id=args.subject_product,
            compared_product_id=args.compared_product,
            products=read_csv(args.products),
            definitions=read_csv(args.definitions),
            values=read_csv(args.values),
        )
        write_spec_comparison(args.output, rows)
        print(f"Wrote {len(rows)} vertical specification comparisons to {args.output}")
    return 0
