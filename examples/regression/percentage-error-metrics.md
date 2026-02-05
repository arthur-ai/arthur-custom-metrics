# Percentage Error Metrics (MAPE, MdAPE, Deviation Ratio)

## Overview

This metric tracks **percentage-based prediction errors** in multiple forms. It measures:

* **MAPE (Mean Absolute Percentage Error)**: Average percentage error magnitude
* **MdAPE (Median Absolute Percentage Error)**: Typical percentage error (robust to outliers)
* **Deviation Ratio**: Average signed relative error (shows bias direction)

All three metrics provide scale-independent views of prediction accuracy, making them ideal for comparing performance across different value ranges.

**Formulas**:
- MAPE: AVG(|predicted - actual| / |actual|) × 100
- MdAPE: median(|predicted - actual| / |actual|) × 100
- Deviation Ratio: AVG((predicted - actual) / actual)

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{prediction_col}}` — predicted value
* `{{ground_truth_col}}` — actual/ground truth value
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates all three percentage-based metrics per day.

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
      AND {{ground_truth_col}} != 0  -- Exclude zero actuals
  ),
  percentage_errors AS (
    SELECT
      ts,
      ABS((actual - prediction) / actual) * 100 AS ape,
      (prediction - actual) / actual AS signed_ratio
    FROM base
  )
SELECT
  ts,
  AVG(ape) AS mape,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ape) AS mdape,
  AVG(signed_ratio) AS deviation_ratio
FROM percentage_errors
GROUP BY ts
ORDER BY ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `mape` — mean absolute percentage error (0-100+%)
* `mdape` — median absolute percentage error (0-100+%, robust to outliers)
* `deviation_ratio` — average signed relative deviation (-1 to +1, typically)

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

### Metric 1 — MAPE

1. **Metric Name:** `mape`
2. **Description:** `Mean absolute percentage error`
3. **Value Column:** `mape`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 2 — MdAPE

1. **Metric Name:** `mdape`
2. **Description:** `Median absolute percentage error (robust to outliers)`
3. **Value Column:** `mdape`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 3 — Deviation Ratio

1. **Metric Name:** `deviation_ratio`
2. **Description:** `Average signed relative deviation (shows bias direction)`
3. **Value Column:** `deviation_ratio`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metrics

### MAPE (Mean Absolute Percentage Error)
* **Excellent (< 10%)**: High accuracy across predictions
* **Good (10-20%)**: Acceptable for most business cases
* **Fair (20-50%)**: Moderate accuracy, improvement needed
* **Poor (> 50%)**: Significant errors

**Sensitive to**: Outliers, small actual values

### MdAPE (Median Absolute Percentage Error)
* **Excellent (< 5%)**: Very accurate for typical predictions
* **Good (5-15%)**: Acceptable typical performance
* **Fair (15-30%)**: Moderate typical accuracy
* **Poor (> 30%)**: High typical error rate

**Advantage**: Robust to outliers, represents typical case

### Deviation Ratio
* **Near 0 (±0.05)**: Unbiased predictions
* **Positive (> 0)**: Systematic over-prediction (e.g., +0.1 = 10% over on average)
* **Negative (< 0)**: Systematic under-prediction (e.g., -0.1 = 10% under on average)
* **Large magnitude (|ratio| > 0.2)**: Significant systematic bias

**Unique feature**: Only metric that shows bias direction

## When to Use This Consolidated Metric

**Use this comprehensive percentage view when**:
- Need scale-independent accuracy metrics
- Want to detect both accuracy issues and bias
- Comparing models across different value ranges
- Reporting to stakeholders (percentages are intuitive)
- Need robust metric (MdAPE) alongside standard (MAPE)
- Require calibration information (Deviation Ratio)

**Benefits of consolidation**:
- Single query computes all three metrics efficiently
- Easy to compare outlier-sensitive (MAPE) vs robust (MdAPE)
- Bias information (Deviation Ratio) complements accuracy metrics
- Consistent time granularity across all metrics
- Reduced computational overhead
