# Normalized Mean Absolute Deviation (Normalized MAD)

## Overview

This metric tracks the **mean absolute error normalized by the mean of actual values**. It measures:

* Scale-independent error magnitude
* Relative prediction accuracy
* Error as a proportion of typical values
* Comparable accuracy across different scales

Normalized MAD divides MAE by the mean of actuals, making it a dimensionless metric that enables comparison across datasets with different scales.

**Formula**: MAE / mean(|actual|)

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{prediction_col}}` — predicted value
* `{{ground_truth_col}}` — actual/ground truth value
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates the MAE normalized by the mean of absolute actuals.

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_col}}::float AS prediction,
      {{ground_truth_col}}::float AS actual
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
      AND {{prediction_col}} IS NOT NULL
      AND {{ground_truth_col}} IS NOT NULL
  ),
  daily_stats AS (
    SELECT
      ts,
      AVG(ABS(prediction - actual)) AS mae,
      AVG(ABS(actual)) AS mean_absolute_actual
    FROM base
    GROUP BY ts
  )
SELECT
  ts,
  mae / NULLIF(mean_absolute_actual, 0) AS normalized_mad
FROM daily_stats
ORDER BY ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `normalized_mad` — MAE divided by mean of absolute actuals (0 to ∞, typically 0 to 1)

## Aggregate Arguments

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp_Col`
3. **Description:** `Column parameter: timestamp_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Prediction Column

1. **Parameter Key:** `prediction_col`
2. **Friendly Name:** `Prediction_Col`
3. **Description:** `Column parameter: prediction_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `int`, `float`
8. **Tag Hints:** `prediction`

### Argument 3 — Ground Truth Column

1. **Parameter Key:** `ground_truth_col`
2. **Friendly Name:** `Ground_Truth_Col`
3. **Description:** `Column parameter: ground_truth_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `int`, `float`
8. **Tag Hints:** `ground_truth`

### Argument 4 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Normalized MAD

1. **Metric Name:** `normalized_mad`
2. **Description:** `Mean absolute error normalized by mean of absolute actuals`
3. **Value Column:** `normalized_mad`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

### Normalized MAD Values

* **Excellent (< 0.05)**: Errors < 5% of typical values
* **Good (0.05-0.15)**: Errors 5-15% of typical values
* **Fair (0.15-0.30)**: Errors 15-30% of typical values
* **Poor (> 0.30)**: Errors > 30% of typical values

### Key Characteristics

**Scale-independent**:
- Compare models across different data scales
- $10 items and $10,000 items on same metric
- Enables cross-domain comparison

**Different from MAPE**:
- MAPE: Average of individual percentage errors
- Normalized MAD: Ratio of aggregate statistics
- More stable when actuals vary widely

**Similar to coefficient of variation**:
- CV measures variability in data: σ / μ
- Normalized MAD measures error relative to scale: MAE / mean(|actual|)

**Interpretation as percentage**:
- 0.10 = 10% (error is 10% of typical value)
- Similar interpretation to MAPE but different calculation

## Normalized MAD vs MAPE

Compare the two scale-independent metrics:

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_col}}::float AS prediction,
      {{ground_truth_col}}::float AS actual
    FROM {{dataset}}
    WHERE {{ground_truth_col}} != 0
  ),
  daily_metrics AS (
    SELECT
      ts,
      AVG(ABS((actual - prediction) / actual)) * 100 AS mape,
      AVG(ABS(prediction - actual)) / NULLIF(AVG(ABS(actual)), 0) AS normalized_mad_recalc
    FROM base
    GROUP BY ts
  )
SELECT
  ts,
  mape,
  normalized_mad_recalc * 100 AS normalized_mad_pct,
  mape - (normalized_mad_recalc * 100) AS mape_vs_nmad_diff
FROM daily_metrics
WHERE ts >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY ts;
```

**Pattern**:
- MAPE ≈ Normalized MAD: Actuals are similar magnitude
- MAPE > Normalized MAD: Small actuals inflate MAPE
- MAPE < Normalized MAD: Unusual (rare)

## Related Metrics

* **Mean Absolute Error (MAE)**: Absolute error in original units (built-in)
* **MAPE**: Per-prediction percentage error
* **WMAPE**: Volume-weighted percentage error
* **Coefficient of Variation**: Variability of actuals (not error)

## When to Use Normalized MAD

**Use normalized MAD when**:
- Need scale-independent error metric
- Comparing models across different scales
- Mixed magnitude data ($10 to $10,000)
- Prefer aggregate ratio over individual percentages
- Want stable metric less sensitive to outliers than MAPE

**Use MAPE when**:
- Need per-prediction percentage errors
- Standard metric in your industry
- Actuals are relatively uniform in scale

**Use MAE when**:
- Absolute error in original units matters
- Working with single consistent scale
- No need for scale independence

**Use WMAPE when**:
- Need volume-weighted percentage error
- High-volume items more important
- Want symmetric error treatment
