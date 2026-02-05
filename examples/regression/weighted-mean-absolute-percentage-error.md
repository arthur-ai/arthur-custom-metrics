# Weighted Mean Absolute Percentage Error (WMAPE)

## Overview

This metric tracks the **weighted mean absolute percentage error** for regression models. It measures:

* Volume-weighted percentage error
* Overall forecast accuracy across all scales
* Performance that accounts for magnitude importance
* Symmetric error measurement

WMAPE is calculated as the total absolute error divided by total actual values, making it a volume-weighted metric that naturally emphasizes larger values. Unlike MAPE, it doesn't suffer from asymmetry or division-by-zero issues.

**Formula**: (Σ|predicted - actual| / Σ|actual|) × 100

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{prediction_col}}` — predicted value
* `{{ground_truth_col}}` — actual/ground truth value
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates WMAPE as a volume-weighted percentage error.

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
  )
SELECT
  ts,
  (SUM(ABS(prediction - actual)) / NULLIF(SUM(ABS(actual)), 0)) * 100 AS wmape
FROM base
GROUP BY ts
ORDER BY ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `wmape` — weighted mean absolute percentage error (0-100+)

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

### Metric 1 — WMAPE

1. **Metric Name:** `wmape`
2. **Description:** `Weighted mean absolute percentage error`
3. **Value Column:** `wmape`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

### WMAPE Values

* **Excellent (< 10%)**: High accuracy across all volumes
* **Good (10-20%)**: Acceptable for most business cases
* **Fair (20-40%)**: Moderate accuracy, improvement needed
* **Poor (> 40%)**: Significant errors, especially on high-volume items

### Key Advantages of WMAPE

1. **No division by zero**: Uses sum of actuals, not individual divisions
2. **Volume-weighted**: Larger values naturally contribute more
3. **Symmetric**: Treats over/under-prediction equally
4. **Business-aligned**: Total error relative to total volume
5. **No asymmetry issue**: Unlike MAPE, doesn't over-penalize over-predictions
6. **Handles zeros**: Can include predictions where actual = 0

### WMAPE vs MAPE

**WMAPE < MAPE**:
- Better performance on high-volume items
- Errors on small items inflate MAPE
- Volume-weighted view is favorable
- **Good**: High-value predictions are accurate

**WMAPE ≈ MAPE**:
- Consistent accuracy across all scales
- Uniform error distribution
- Values are similar magnitude

**WMAPE > MAPE**:
- Worse performance on high-volume items
- Small-item errors are low, but big-item errors are high
- **Concerning**: Poor accuracy where it matters most

## WMAPE by Segment

Analyze performance across different segments:

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{segment_col}} AS segment,
      {{prediction_col}}::float AS prediction,
      {{ground_truth_col}}::float AS actual
    FROM {{dataset}}
    WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '30 days'
  )
SELECT
  segment,
  (SUM(ABS(prediction - actual)) / NULLIF(SUM(ABS(actual)), 0)) * 100 AS wmape,
  COUNT(*) AS prediction_count,
  SUM(ABS(actual)) AS total_volume,
  AVG(ABS(actual)) AS avg_volume
FROM base
GROUP BY segment
ORDER BY total_volume DESC;
```

**Use this to**:
- Identify which segments have poor WMAPE
- Understand if high-volume segments are well-forecasted
- Prioritize improvements based on business impact

## Related Metrics

* **Mean Absolute Percentage Error (MAPE)**: Unweighted average percentage error
* **Median Absolute Percentage Error (MdAPE)**: Robust to outliers, equal weighting
* **Mean Absolute Error (MAE)**: Absolute units (built-in)
* **Absolute Error**: Full distribution analysis

## When to Use WMAPE

**Prefer WMAPE when**:
- Volume/magnitude matters for business (most cases)
- Data includes wide range of scales ($10 to $10,000)
- Need symmetric metric (equal treatment of over/under-prediction)
- Want to avoid division-by-zero issues
- Reporting aggregate forecast accuracy
- High-volume accuracy is more important than small-volume

**Prefer MAPE when**:
- All predictions equally important (same scale)
- Need to treat each prediction equally
- Regulatory requirements specify unweighted metrics
- Small values are as critical as large values

**Prefer MdAPE when**:
- Outliers are common
- Need robust metric for SLAs
- Reporting typical performance vs total performance
