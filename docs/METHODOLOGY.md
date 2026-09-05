# Net Reviewer Score Methodology

## Decision question

Given a scarce review unit, which candidate offers the strongest evidence-adjusted opportunity for relevant coverage while preserving editorial independence and deliberate exploration?

## Baseline components

For candidate `i`:

```text
Expected Earned Value_i = Coverage_i x Influence_i x Favorability_i
Net Reviewer Score_i    = 100 x Expected Earned Value_i
```

All three inputs are bounded between 0 and 1.

The 0–100 output is therefore a presentation index, not a percentage probability and not a validated forecast of revenue or sales lift.

## Nomenclature

The current formula is not mathematically net because it contains no subtraction. To preserve the project's lineage without preserving that ambiguity:

- **NRS-EV** names the implemented absolute expected-earned-value index.
- **NRS-Delta** is reserved for a future matched competitive differential.

NRS-Delta must compare genuinely matched product identities, timing, reviewer observations, and whichever vertical-specific specifications have been explicitly selected for that analysis. It must be reported separately and must not be hidden inside NRS-EV.

## Product scope and competitive context

A reviewer-level history is not interpretable without product context. Apparent favorability can change because of the product itself, its category, variant, age, positioning, vertical-specific attributes, or the competitive set.

The baseline therefore resolves each review to a verified product registry and can restrict both reviews and engagement history to a target make. Competitive products remain in the same corpus, but they do not silently enter the target make's NRS-EV calculation.

Competitive observations are logged separately with:

- the product that is actually the review subject;
- the product being compared;
- the make, model, model number, vertical, and category of both;
- the applicable customizable specification profile for that vertical;
- whether the comparison is a head-to-head test, benchmark, alternative, or mention;
- the basis for considering the products matched;
- the directional outcome and precise evidence location;
- verification status.

This supports later decomposition of reviewer effect versus product effect. v0.1 produces a descriptive comparison summary but does not estimate NRS-Delta.

### Coverage

Coverage is estimated from the engagement ledger:

```text
coverage success = an eligible engagement produced a verified review
coverage failure = an eligible engagement did not produce a verified review
```

Offers that were never delivered, canceled placements, and ineligible engagements require explicit policy before inclusion. They should not be silently treated as coverage failures.

The implementation enforces the evidence link: a coverage success must reference an accepted or corrected review record attributed to the same candidate.

### Influence

Influence is supplied independently of brand treatment. It must not use awards or positive ratings given to the focal brand, because that would entangle influence with favorability.

### Favorability

The baseline treats a normalized rating of at least `0.8` as favorable. An explicit 8/10, 4/5, or 80% therefore maps to a favorable observation. The original rating and scale remain stored.

Unscored text is not converted into a numeric rating in v0.1.

## Beta posterior

Coverage and favorability use Beta priors with weighted Bernoulli evidence:

```text
alpha_posterior = alpha_prior + weighted_successes
beta_posterior  = beta_prior  + weighted_failures
```

The default prior is `Beta(1, 1)`, a uniform prior. This is a transparent baseline, not the planned empirical-Bayes model.

The implementation reports posterior means and equal-tail credible intervals. If the favorability interval crosses `0.5`, the direction is reported as unresolved.

## Evidence-adjusted ranking

The reported NRS-EV index remains the point estimate described above. The ranking adopts a conservative decision policy; sorting by posterior mean is not itself a statistical error. Candidates with observations in both evidence streams are ordered by:

```text
expected_earned_value_lower_95 = coverage_lower_95 x influence x favorability_lower_95
```

Candidates lacking either evidence stream appear afterward, ordered by the same quantity. Candidate ID breaks ties. `rank_basis` records this availability gate and marginal-bound product. `evidence_status` remains visible but resolved direction gets no automatic priority: a resolved interval can indicate consistently unfavorable reviews. Availability means observations exist, not that their quantity, recency, representativeness, or relevance is sufficient for allocation.

The output preserves both the point estimate and this lower-bound value. The latter combines lower endpoints of marginal equal-tail 95% intervals; it is not the exact 95% interval or quantile of the product. Its existing `_lower_95` field names refer to those input endpoints. Influence is still treated as a supplied scalar; this calculation does not quantify uncertainty in that input or model misspecification.

The 30/40 synthetic example outranks 2/2 under this policy, while a well-observed unfavorable reviewer receives no categorical advantage over a promising uncertain reviewer. Those are regression checks of a stated ordering rule, not evidence of superior real-world allocation. The rule is conservative and not an exploration policy; see [Selection bias and exploration](#selection-bias-and-exploration).

### Data-quality handling

`score_candidates` still returns a list of ranked rows. A supplied `violations` list receives record type, ID, candidate ID, stable code, detail, and exclusion reason; without it, exclusions emit a warning. The CLI writes the optional report or prints a summary. Any supported violation excludes the entire affected active candidate, preserving unaffected candidates. Non-strict runs return zero, including an all-excluded run, which writes a header-only score file and an explicit no-candidates message. `strict=True` / `--strict` raises or returns nonzero at the first supported violation.

`coverage_success_unlinked` covers empty, orphaned, unverified, or other-candidate review links; `coverage_failure_linked` covers links on a reported failure. Scored evidence dates have `missing_`, `invalid_`, or `future_` codes followed by `decision_date` or `published_date`. Dates are required even when decay is disabled so the as-of boundary remains checkable. This is not a general CSV/schema repair system: file errors, invalid global options, or malformed candidate metadata may still stop a run.

### Interpretation of the probability product

Favorability uses all accepted or corrected rated reviews in the selected product scope, not only reviews linked to eligible placements. Publication and favorability need not be independent for the identity `P(published and favorable) = P(published) * P(favorable | published)` to hold. Applying this index to future placements nonetheless assumes the observed review sample represents the relevant conditional favorability. Separate Beta estimates and their multiplied means do not establish that assumption or model shared uncertainty between the streams. Selection effects and product/candidate differences remain validation concerns.

## Recency weighting

When a half-life is configured:

```text
weight = 0.5 ^ (age_days / half_life_days)
```

Effective sample size is:

```text
n_eff = (sum(weights) ^ 2) / sum(weight ^ 2)
```

The system reports raw observations and Kish effective sample size. Kish effective sample size measures weight concentration, not total decayed evidence: multiplying every weight by the same factor leaves it unchanged. The Beta update uses the sum of weights as its evidence mass, so equally old observations weaken that update even if the reported effective sample size still equals the raw count. Do not interpret this field as the number of equivalent current observations.

## Selection bias and exploration

Repeatedly allocating only to candidates with the highest observed expected value creates self-confirming data. A later allocation policy should reserve a bounded portion of units for high-uncertainty, relevant candidates—potentially using Thompson sampling.

v0.1 reports uncertainty but does not autonomously assign the exploration reserve.

## Outcome validation

A higher calculated score is not proof of greater commercial value. Validation requires prospective or quasi-experimental comparison across multiple product cycles, with product identity, product attributes, fit, timing, and competitive set separated from source behavior.
