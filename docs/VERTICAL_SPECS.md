# Customizable Vertical Specifications

## Core identity stays universal

Every product uses the same small identity contract:

```text
make -> model -> model number (when available)
```

The registry also carries an optional variant and SKU, product vertical, broad category, lifecycle metadata, provenance, and verification status. It does not gain new columns when a new vertical is added.

Examples:

| Make | Model | Model number | Vertical | Category |
|---|---|---|---|---|
| Dell | XPS | 4000 | computers | desktop |
| Example Camera Co. | ViewPro | VP-7 | cameras | mirrorless camera |
| Example Kitchen | DailyBrew | DB100 | coffee_makers | drip coffee maker |

Model number may be null when the manufacturer does not publish one. Unknown is preferable to an invented identifier.

## Definition table

`spec-definition.schema.json` defines fields that are meaningful within a vertical. Each row supplies:

- `product_vertical`
- `spec_key`
- `display_name`
- `data_type`: `text`, `number`, `boolean`, or `enum`
- optional unit and allowed values
- optional category applicability inside the vertical
- whether the spec is required for a valid match
- optional match weight
- definition version and active state

The definition is configuration data. Adding a camera, vehicle, appliance, musical-instrument, or cosmetics spec does not require changing Python code or the core product schema.

The synthetic `computers` definition includes CPU; HDD/storage size and type; memory size, type, and speed; and list price. Screen fields apply only when either compared product is categorized as a laptop: screen type, size, resolution, refresh rate, brightness, and touchscreen status.

## Value table

`product-spec.schema.json` stores one verified value per product and spec key. Values remain typed and preserve their source URL and verification state.

```text
product_id | spec_key       | value       | unit
-----------|----------------|-------------|-----
p-100      | capacity       | 1.5         | L
p-100      | programmable   | true        |
p-200      | sensor_format  | full_frame  |
```

## Comparison behavior

Two products must share a vertical before their specification profiles can be compared. The report evaluates every active definition for that vertical and emits:

- `same`
- `different`
- `missing_subject`
- `missing_compared`
- `missing_both`

v0.1 does not collapse those rows into an automatic compatibility or similarity score. Different verticals will need different policies for tolerances, equivalence, and importance, and those policies require domain evidence rather than universal guesses.

## Change control

Definitions are versioned. A changed definition creates a new analytical context; it must not silently rewrite the meaning of historical product comparisons. Real values and matching rules require the same accepted/corrected verification boundary as review evidence.
