# Validation Status

## Current state

The repository is a synthetic v0.1 implementation. Unit tests validate limited deterministic software behavior. They do not validate the business model, source coverage, or real-world allocation quality.

| Claim | Current status | Evidence required |
|---|---|---|
| Supported numeric ratings normalize correctly | Tested for the documented formats | Expand a labeled format corpus and keep 100% accuracy for admitted formats |
| Exact URLs and content hashes deduplicate deterministically | Tested | Labeled canonical/duplicate fixtures |
| Fuzzy syndication can be automated safely | Not implemented | Precision/recall against a representative labeled corpus |
| JSON-LD extraction works across publications | Specified, not validated | 50–100 manually labeled public review pages across source families |
| Make, model, and model number resolve accurately | Tested on synthetic structured and alias cases | A labeled cross-make corpus including reused model numbers, retailer titles, and regional variants |
| Product vertical and category assignment are reliable | Registry-driven, not externally validated | Human-audited definitions and inter-rater checks |
| Vertical spec tables are configurable without core-schema changes | Implemented and tested | At least two materially different real vertical configurations |
| Typed spec values and units are enforced | Tested on synthetic number, boolean, text, and enum definitions | Labeled production values and failure-case fixtures |
| Competitive comparisons are directionally logged | Tested on synthetic verified links | A labeled corpus distinguishing mentions, benchmarks, alternatives, and head-to-head tests |
| Competitive logging isolates product effects | Unproven | Repeated matched reviewers and product sets across multiple cycles |
| Only verified reviews enter scoring | Tested | Regression tests and production audit logs |
| Coverage can be inferred from public reviews | Rejected | Coverage requires an engagement denominator |
| NRS improves allocation quality | Unproven | Retrospective usefulness test, followed by prospective or quasi-experimental evidence |
| NRS improves commercial return | Unproven | Multiple-cycle outcome evidence with product and selection effects controlled |

## Initial acceptance thresholds

Before high-confidence automatic admission:

- 100% normalization accuracy for explicitly supported numeric formats;
- at least 95% precision for review-versus-nonreview classification;
- at least 95% accuracy for claimed high-confidence author, date, make, model, and model-number fields;
- zero unverified records entering NRS calculations;
- zero unresolved product identities entering product-scoped calculations;
- zero competitive observations admitted without a verified review, two verified product identities, a match basis, and an evidence locator;
- explicit human routing for ambiguity.

## First real test

Apply the pipeline retrospectively to one completed launch cycle using an authorized private engagement ledger and a manually verified public-review corpus. Ask whether the ranked output reveals a decision-relevant pattern that experienced operators did not already know.

If it does not, retain the corpus and processing utility but do not promote NRS as a product or validated allocation method.
