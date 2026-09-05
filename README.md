# Review Intelligence Pipeline

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## What this does

This project turns scattered product reviews into a useful, searchable history of:

- which products were reviewed;
- who reviewed them and where;
- what rating or verdict each product received;
- which competing products were mentioned or compared;
- how the products differed;
- which review-unit placements produced coverage; and
- how certain—or uncertain—the available evidence really is.

The practical goal is to help product, marketing, public-relations, and competitive-intelligence teams make better decisions about reviews and product launches. It can help answer questions such as:

- Which reviewers regularly cover this kind of product?
- Which outlets actually publish after receiving a review unit?
- Was a poor result caused by reviewer behavior, a weaker product, or an unfair comparison?
- Which competitive products appear most often, and what advantages do reviewers identify?
- Are two products similar enough for a meaningful comparison?
- Where should a limited supply of review units go—and where is the evidence still too thin to know?

## Practical example

Imagine a company has ten products available for review but forty possible reviewers. Today, the decision might be made from memory, audience size, personal relationships, or a spreadsheet that records only successful coverage.

This system combines the public review history with the company's private record of product offers and placements. It identifies the exact make, model, and model number reviewed, records relevant specifications, logs competitive comparisons, and shows the strength and uncertainty of each reviewer's history. A person still makes the final decision, but the decision is based on organized evidence rather than incomplete recollection.

## Practical benefits

- **Less manual research:** Gather review history into one consistent structure instead of repeatedly searching the web and reconciling spreadsheets.
- **Better product identification:** Distinguish products with similar names by make, model, and model number.
- **Fairer reviewer assessment:** Avoid blaming a reviewer for results that may be explained by product quality, product differences, or the competitive set.
- **Better competitive intelligence:** See which products are compared, which attributes matter, and where competitors are perceived as stronger or weaker.
- **Smarter use of scarce review units:** Prioritize likely, relevant coverage while keeping uncertainty visible.
- **Reusable across industries:** Keep the same product identity and review framework while customizing specifications for computers, cameras, appliances, vehicles, instruments, or other verticals.
- **Explainable decisions:** Preserve where information came from, what was verified, what the model calculated, and what a person ultimately decided.
- **Learning across launches:** Compare expectations with actual coverage and outcomes so future decisions can improve.

## Technical overview

Under the hood, this is an evidence-first pipeline for collecting public product-review material, preserving its source, normalizing review records, resolving product identity, logging competitive context, and supporting human review-unit allocation decisions.

Net Reviewer Score (NRS) is the first decision model implemented on top of the pipeline. It is not the pipeline itself, and it is not yet a validated predictor of commercial return.

## Why this exists

Review programs frequently allocate expensive products using relationship memory, audience-size shortcuts, or a spreadsheet that records only what happened. That creates four problems:

1. Public review evidence is fragmented across outlets, authors, formats, product identities, and vertical-specific specifications.
2. Ratings, awards, and verdicts are not directly comparable.
3. Published reviews reveal outcomes but not the review units that produced no coverage.
4. A model trained only on past placements reinforces its own selection bias.

This project therefore separates two evidence streams:

- **Public review intelligence:** discovered pages, immutable source records, extracted fields, resolved product identities, normalized ratings, competitive comparisons, and duplicate groups.
- **Private engagement evidence:** units offered or sent, dates, outcomes, costs, and return status.

The streams join only at the decision layer. Public scraping cannot recover the denominator for coverage rate.

## Pipeline

```text
Permitted public sources             Private engagement ledger
          |                                      |
          v                                      v
Discovery -> fetch -> raw evidence          placement outcomes
          |                                      |
          v                                      |
Extract -> resolve product -> normalize -> deduplicate -> human verification
                              |
                              v
             coverage x influence x expected favorability
                              |
                              v
                   ranked decision support
```

No output authorizes a shipment, denies press access, or replaces human judgment.

## What v0.1 includes

- bounded RSS, sitemap, and URL-list discovery helpers;
- an allowlist-based HTTP fetcher that checks `robots.txt`;
- basic JSON-LD review extraction;
- structured make, model, model-number, optional variant, SKU, and MPN extraction;
- conservative product resolution using a verified product-and-alias registry;
- a universal `make → model → model number` identity hierarchy;
- customizable specification definitions and values for each product vertical;
- synthetic computer specifications including CPU; HDD/storage size and type; memory size, type, and speed; and category-conditional laptop screen specifications;
- deterministic URL canonicalization and exact duplicate detection;
- rating normalization with the original rating retained;
- Beta posterior estimates and credible intervals;
- recency weighting and effective sample size;
- a 0–100 NRS-EV baseline combining coverage probability, brand-independent influence, and expected favorability;
- verified subject-versus-compared product logging and descriptive competitive summaries;
- synthetic data and standard-library tests.

## What v0.1 deliberately does not claim

- that NRS improves sales, coverage, sentiment, or ROI;
- that text sentiment can safely replace an explicit score;
- that every publication permits automated collection;
- that the collectors are a universal crawler;
- that outlet influence has one objectively correct definition;
- that one composite score should automatically determine access or allocation;
- that the current baseline implements the planned hierarchical product-cycle model or empirical-Bayes prior estimation.

See [VALIDATION.md](docs/VALIDATION.md) for the evidence required before those claims can change.

See [VERTICAL_SPECS.md](docs/VERTICAL_SPECS.md) for the universal product identity and customizable per-vertical specification model.

## Quick start

The project uses only the Python standard library.

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
review-intelligence score `
  --reviews data/synthetic_reviews.csv `
  --engagements data/synthetic_engagements.csv `
  --candidates data/synthetic_candidates.csv `
  --products data/synthetic_products.csv `
  --target-make Northstar `
  --as-of 2026-09-04 `
  --output examples/synthetic_scores.csv
```

The synthetic files describe fictional outlets, reviewers, products, and placements. They are examples of data shape, not claims about real people or organizations.

To exercise the processing boundary without live collection, run `review-intelligence extract` against a saved HTML fixture. Extracted records are always marked `candidate`; the scoring layer ignores them until a human changes the verification status to `accepted` or `corrected`.

```powershell
review-intelligence extract `
  --html data/synthetic_review_page.html `
  --source-url https://example.com/reviews/northstar-atlas `
  --output examples/synthetic_extracted.jsonl

review-intelligence resolve-products `
  --input examples/synthetic_extracted.jsonl `
  --products data/synthetic_products.csv `
  --aliases data/synthetic_product_aliases.csv `
  --output examples/synthetic_product_resolution.jsonl

review-intelligence competitive-report `
  --products data/synthetic_products.csv `
  --reviews data/synthetic_reviews.csv `
  --comparisons data/synthetic_comparisons.csv `
  --output examples/synthetic_competitive_summary.csv

review-intelligence spec-report `
  --subject-product product-atlas `
  --compared-product competitor-aether `
  --products data/synthetic_products.csv `
  --definitions data/synthetic_spec_definitions.csv `
  --values data/synthetic_product_specs.csv `
  --output examples/synthetic_spec_comparison.csv
```

## Repository map

- `src/review_intelligence/collectors/` — controlled source discovery and fetching
- `src/review_intelligence/extract.py` — bounded JSON-LD extraction
- `src/review_intelligence/product_identity.py` — conservative product identity and category resolution
- `src/review_intelligence/competitive.py` — verified competitive-comparison summaries
- `src/review_intelligence/specs.py` — configurable per-vertical specification comparisons
- `src/review_intelligence/normalize.py` — rating and value normalization
- `src/review_intelligence/deduplicate.py` — canonical URL and exact-duplicate grouping
- `src/review_intelligence/statistics.py` — Beta posterior and effective-sample-size calculations
- `src/review_intelligence/scoring.py` — NRS baseline decision-support output
- `schemas/` — machine-readable evidence contracts, including universal product identity and customizable vertical specs
- `data/` — synthetic demonstration data
- `docs/` — architecture, methodology, governance, and validation boundaries
- `tests/` — deterministic unit tests

## Publication status

This is a public portfolio demonstration built entirely with fictional products, reviewers, outlets, placements, and source URLs. Populated production engagement ledgers, private correspondence, contact information, and copyrighted source archives do not belong in this repository.

This project is open source under the [Apache License 2.0](LICENSE). It may be used, modified, and distributed—including commercially—subject to the license's notice, attribution, and other terms. The license includes an explicit patent grant and does not provide a warranty.
