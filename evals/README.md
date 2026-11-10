# Synthetic evaluation set for LLM extraction

`golden_reviews.json` holds ten invented review texts with expected labels. Every product, outlet, and sentence is fictional and reuses the repository's synthetic catalog (Northstar, Aether, Boreal, Forge, Vector). It is a regression fixture, not a sample of real reviews.

Each case carries the expected verdict, the competing products the text names, and reference pros and cons with verbatim quotes. The set deliberately includes a preview with no verdict, a review with no competitors, an instruction injected into the review body, lowercase words that resemble product makes, and irregular whitespace.

```shell
python -m review_intelligence llm-eval --golden evals/golden_reviews.json --provider offline-perfect --output examples/llm_eval_report.json --min verdict_accuracy=1.0 --min quote_grounding_rate=1.0
```

The two offline providers replay these labels (one faithfully, one with fixed defects). They exercise the validator, the metrics, and the threshold gate. They say nothing about how any model performs; that requires `--provider anthropic` and a recorded run.
