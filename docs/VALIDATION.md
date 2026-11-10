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
| LLM output is admitted only when grounded in the source text | Tested offline with fake providers, including an injected-instruction case | Audit of rejected and admitted items from recorded live runs |
| The LLM extracts verdicts, competitors, pros, and cons accurately | Not measured; no live model run is recorded in this repository | A recorded `llm-eval` run per model and prompt version on the synthetic set, then on 50–100 manually labeled real reviews |
| Only verified reviews enter scoring | Tested | Regression tests and production audit logs |
| Coverage can be inferred from public reviews | Rejected | Coverage requires an engagement denominator |
| NRS improves allocation quality | Unproven | Retrospective usefulness test, followed by prospective or quasi-experimental evidence |
| NRS improves commercial return | Unproven | Multiple-cycle outcome evidence with product and selection effects controlled |

## LLM extraction: what has and has not been verified

Verified offline, by unit tests that make no network call:

- quotes are admitted only as exact, whitespace-normalised substrings of the text sent to the model;
- competing products are admitted only on a case-insensitive, word-boundary match in that text;
- wrong types, unknown verdicts, unexpected fields, duplicates, and items over the limit are rejected with reason codes, and provider failures produce an empty candidate rather than an exception;
- an instruction planted in the review text does not get ungrounded output admitted, and cannot change `verification_status`;
- the evaluation metrics and the `--min` gate return the expected values for a perfect and a deliberately flawed offline provider;
- the Anthropic client builds the documented request and parses a `tool_use` response, using a fake transport.

Not verified:

- no request has been sent to a live model from this repository, so the request format is checked against documentation only;
- no model's verdict accuracy, competitor precision or recall, or quote grounding rate has been measured;
- the golden set is ten synthetic texts written alongside the validator. It is a regression fixture, not evidence about real reviews;
- the validator cannot check that a verdict is right, that a quote supports its claim, or that a grounded product is a competitor rather than the reviewed product. Those remain human verification steps.

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
