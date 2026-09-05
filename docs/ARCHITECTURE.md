# Architecture

## Plain-language view

The architecture is designed to create a trustworthy history of product reviews without turning an automated score into an unquestionable answer.

In simple terms, the system does five things:

1. **Finds and organizes reviews.** It gathers permitted public review pages and records where and when each one was found.
2. **Figures out which product was actually reviewed.** It separates make, model, and model number, then attaches any useful specifications defined for that type of product.
3. **Records competitive context.** It logs which other products were compared, whether the comparison was meaningful, and what the reviewer concluded.
4. **Connects reviews to real review-program activity.** A private company record shows which products were offered or sent, including placements that never produced a review.
5. **Supports—not replaces—a human decision.** It summarizes reviewer history, likely coverage, competitive context, and uncertainty so a person can make a better-informed allocation decision.

## What goes in and what comes out

| What goes in | What the system does | What comes out |
|---|---|---|
| Public product reviews | Identifies the review, reviewer, product, rating, and competitors | Searchable, consistent review records |
| Product catalogs and alias lists | Resolves inconsistent names to make, model, and model number | Verified product identities |
| Custom specification tables | Compares the attributes that matter for that product vertical | Side-by-side product differences and missing information |
| Private review-unit history | Records offers, shipments, returned units, coverage, and noncoverage | A real denominator for coverage history |
| Human verification and corrections | Prevents uncertain extraction from silently becoming fact | Auditable accepted, corrected, and rejected records |
| Reviewer and outlet context | Combines coverage, reach, relevance, and favorability with uncertainty | Ranked decision support rather than an automatic verdict |

## Who this helps

- **Product and launch teams** can see how products were received and what competitive differences mattered.
- **Public-relations and review-program teams** can allocate limited products using more than memory or audience size.
- **Competitive-intelligence teams** can trace comparisons back to the exact review and product pair.
- **Marketing teams** can identify recurring strengths, weaknesses, and language across reviews.
- **Analysts and leaders** can distinguish verified evidence from estimates and see when the available history is too thin.

## Example

Suppose a reviewer gives Product A a lower score than Product B. The system should not immediately conclude that the reviewer dislikes the maker of Product A. It first asks:

- Were the exact products identified correctly?
- Were they in the same product category?
- Which specifications were the same or different?
- Was Product B actually tested head-to-head, merely mentioned, or used as a general alternative?
- Has this reviewer covered earlier products after receiving them?
- Is there enough history to draw a conclusion at all?

The architecture preserves those answers separately. That makes the resulting recommendation easier to understand, challenge, and improve.

## Technical architecture

### Evidence layers

The system keeps seven layers distinct:

1. **Source evidence** — the fetched representation, URL, retrieval time, and content hash.
2. **Extracted observation** — fields parsed from the source with a parser version and confidence.
3. **Product-identity candidate** — a proposed make, model, model number, optional variant/SKU, vertical, and category with method and confidence.
4. **Human-verified record** — an accepted or corrected review and product identity.
5. **Competitive observation** — a verified subject-versus-compared product claim tied to a precise location in a review.
6. **Model output** — posterior estimates, uncertainty, and a ranked decision-support view.
7. **Human decision and outcome** — allocation, reason, result, and later evidence.

A later layer never rewrites an earlier one. Corrections create new processing state while the original source record remains recoverable.

### Public and private inputs

#### Public review corpus

Collectors may discover and fetch material only from explicitly allowed domains. The processing layer extracts and normalizes review evidence. Public data can estimate favorability and provide ingredients for influence, but it cannot establish how often a supplied unit produced no review.

#### Product and alias registry

Every verified review must resolve to a product record. The universal registry is deliberately small: make, model, model number, optional variant and SKU, product vertical, broad category, launch date, lifecycle, and focal/competitive role.

The core schema does not contain computer-, vehicle-, appliance-, camera-, or other vertical-specific specifications.

Resolution follows an evidence ladder:

1. structured identifiers such as MPN, model number, or SKU;
2. structured make and model;
3. an accepted alias or publisher variant;
4. an unresolved model-number candidate routed to a human.

Even a high-confidence automated match remains `candidate` until verified. Product names are frequently inconsistent, model numbers can be reused across makes or lines, and retailer titles are often polluted by bundle information.

#### Customizable vertical specifications

Specifications live in two normalized tables outside the product identity:

- **Spec definitions** declare the vertical, stable key, display name, data type, unit, allowed values, whether the field is required for matching, optional match weight, and definition version.
- **Product spec values** attach verified typed values and provenance to individual products.

Adding or changing specifications for a vertical is therefore a data/configuration change rather than a core-schema change. A computer vertical can define CPU, storage, memory, and category-conditional laptop screen fields; a camera vertical might define sensor format and lens mount; a coffee-maker vertical might define brew method and capacity. None of those fields is privileged by the core system.

The comparison report shows each configured field as same, different, or missing. v0.1 does not collapse that profile into an opaque similarity score.

#### Competitive comparison log

A review can be about either a focal or competitive product. Comparisons are therefore directional: `subject_product_id` identifies the review's actual subject and `compared_product_id` identifies the referenced alternative. Outcomes are recorded relative to those roles, not relative to whichever brand operates the pipeline.

Each observation records comparison type, matched-set identifier, explicit matching basis, comparative outcome, and evidence locator. A mention is not equivalent to a benchmark, and a benchmark is not automatically a fair head-to-head comparison.

#### Private engagement ledger

Coverage requires a denominator. An engagement ledger records every eligible placement attempt, including noncoverage. Real ledgers may contain confidential logistics and relationship information and should not be committed to a public repository.

#### Candidate influence registry

Influence must be independent of how positively a source treated the focal brand. A separate registry supplies a bounded influence estimate, its effective date, and its basis. Audience, authority, citation, syndication, search longevity, and buyer alignment may contribute, but the public baseline accepts only a precomputed 0–1 score.

### Processing states

`verification_status` is one of:

- `candidate`
- `accepted`
- `corrected`
- `rejected`

Only `accepted` and `corrected` records may enter NRS calculations.

Product-identity and comparison records use the same verification states. An extracted model number can be useful for routing without being admitted as scoring evidence.

### Duplicate boundary

v0.1 groups exact duplicates using either identical content hashes or canonicalized URLs. It does not claim reliable fuzzy syndication detection. Suspected near-duplicates must be routed to human review until a labeled test set justifies automation.

### Decision boundary

NRS produces ranked evidence, not an autonomous allocation. A human decision must still consider product fit, editorial independence, logistics, regional availability, legal constraints, relationship context, and the exploration reserve.

NRS-EV can be scoped to a verified target-make product set so competitive reviews do not contaminate the focal make's coverage or favorability history. Competitive summaries remain descriptive until matched evidence is strong enough to justify a separate NRS-Delta model.

### Deferred components

- empirical-Bayes estimation of shared priors;
- hierarchical writer and product-cycle effects;
- matched-pair competitive differentials;
- learned influence models;
- unscored-verdict NLP;
- fuzzy syndication detection;
- CRM connectors;
- autonomous shipment or outreach actions.

These are hypotheses or possible extensions, not missing checkboxes that v0.1 must fill.
