# LLM Extraction

## Purpose

JSON-LD rarely carries a reviewer's verdict, the competing products named in the body, or the specific pros and cons. `llm_extract.py` asks a model to propose those fields from review body text. It is the only place in the pipeline where a model is called, and its output is an extracted observation: a `candidate` that a person must accept or correct before it means anything.

## Flow

```text
review text -> truncate to max_chars -> delimited as untrusted data -> provider
            -> deterministic validator -> candidate record + rejected list
```

A provider is any callable taking a system prompt, a user prompt, and a JSON schema, and returning a dict. Tests and CI use offline fakes. `AnthropicProvider` uses only `urllib` and requests schema-shaped JSON through forced tool use (`tool_choice` naming one tool).

## What the validator enforces

| Check | Reason code |
|---|---|
| Response is an object; fields have the right types | `not_an_object`, `invalid_type`, `invalid_item` |
| Verdict is `positive`, `mixed`, `negative`, or `unknown` | `invalid_verdict` |
| No fields beyond the schema | `unexpected_field` |
| Quote is an exact, whitespace-normalised substring of the text sent | `quote_not_in_source` |
| Quote is 12 to 300 characters; claim is at most 200 | `quote_too_short`, `quote_too_long`, `claim_too_long` |
| Product appears in the text, case-insensitively, on word boundaries | `not_in_source` |
| No repeats; at most N items per list | `duplicate`, `over_limit` |
| Provider failed or returned no complete tool call | `provider_error` |

Forced tool use is treated as a request for the right shape, not a guarantee. The validator is the only admission check.

Each record carries `verification_status: "candidate"`, `model_id`, `prompt_version`, a SHA-256 of the source text, the characters sent, and validator counts.

## Prompt injection

Review pages are untrusted. The text is sent inside `<review_text>` tags, a closing tag inside the text is defused, and the system prompt tells the model to treat the content as data. That instruction is a request to the model, not a control. The control is the validator: output that is not in the source is dropped whatever the model was persuaded to say.

## Known limits

- **Verdict is not grounded.** It is a judgment. A wrong or manipulated verdict passes as a candidate. It is never converted to a rating and never enters NRS.
- **Grounded is not the same as correct.** A real quote can be attached to the wrong claim. Text planted in the page is itself quotable. The reviewed product can be offered as a competitor; the flawed offline provider does this on purpose so the eval shows it.
- **`claim` is not grounded.** Each kept pro or con carries a short free-text claim next to its grounded quote. The claim is the model's paraphrase and is never checked against the source, so text planted in a page can dictate it. Do not show a claim without its quote beside it.
- **Exact matching is strict.** A quote with normalised punctuation or a product written differently from the text is rejected. That costs recall in exchange for precision.
- **Truncation.** Text beyond `max_chars` is not sent and cannot ground anything.

## Evaluation

`llm-eval` runs a provider over `evals/golden_reviews.json` and reports verdict accuracy, competitor precision and recall after validation, competitor precision before validation, quote grounding rate (grounded quotes over proposed quotes), and rejection counts by reason. `--min METRIC=FLOOR` exits 1 below a floor. A metric with no denominator is reported as `null` and fails any floor set on it.

| Offline provider | Verdict | Precision | Recall | Precision before validation | Grounding | Rejected |
|---|---|---|---|---|---|---|
| `offline-perfect` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| `offline-flawed` | 0.600 | 0.818 | 0.750 | 0.562 | 0.800 | 10 |

These rows describe scripted fakes. They show that the harness detects known defects and that the validator lifts competitor precision by removing invented products. They are not model results.

## Live use

```shell
export ANTHROPIC_API_KEY=...   # never commit
export ANTHROPIC_MODEL=...     # required; there is no default
python -m review_intelligence llm-eval --golden evals/golden_reviews.json --provider anthropic --output private/llm_eval_report.json
```

`ANTHROPIC_VERSION` overrides the `anthropic-version` header (default `2023-06-01`). No live run has been recorded in this repository. Record the model id, prompt version, and report before quoting any model metric.
