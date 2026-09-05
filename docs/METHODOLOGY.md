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

## Recency weighting

When a half-life is configured:

```text
weight = 0.5 ^ (age_days / half_life_days)
```

Effective sample size is:

```text
n_eff = (sum(weights) ^ 2) / sum(weight ^ 2)
```

The system reports both raw observations and effective sample size. It does not pretend a heavily decayed history contains the same evidence as an equally sized current sample.

## Selection bias and exploration

Repeatedly allocating only to candidates with the highest observed expected value creates self-confirming data. A later allocation policy should reserve a bounded portion of units for high-uncertainty, relevant candidates—potentially using Thompson sampling.

v0.1 reports uncertainty but does not autonomously assign the exploration reserve.

## Outcome validation

A higher calculated score is not proof of greater commercial value. Validation requires prospective or quasi-experimental comparison across multiple product cycles, with product identity, product attributes, fit, timing, and competitive set separated from source behavior.
