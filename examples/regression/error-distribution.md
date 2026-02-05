# Error Distribution (Per-Inference)

## Overview

This metric tracks **per-inference errors in multiple forms** for regression models. It measures:

* **Absolute Error**: Magnitude of each error
* **Forecast Error**: Signed error (direction + magnitude)
* **Absolute Percentage Error**: Scale-independent error for each prediction

All three error types are calculated per-inference and stored as sketches, enabling percentile analysis, distribution visualization, and outlier detection.

**Formulas**:
- Absolute Error: |predicted - actual|
- Forecast Error: predicted - actual
- Absolute Percentage Error: |predicted - actual| / |actual| × 100

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{prediction_col}}` — predicted value
* `{{ground_truth_col}}` — actual/ground truth value
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates all three error types per inference.

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_col}}::float AS prediction,
      {{ground_truth_col}}::float AS actual
    FROM {{dataset}}
  )
SELECT
  ts,
  ABS(prediction - actual) AS absolute_error,
  prediction - actual AS forecast_error,
  CASE
    WHEN actual != 0 THEN ABS((prediction - actual) / actual) * 100
    ELSE NULL
  END AS absolute_percentage_error
FROM base
ORDER BY ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `absolute_error` — absolute magnitude of error
* `forecast_error` — signed error (positive = over-prediction, negative = under-prediction)
* `absolute_percentage_error` — percentage error (NULL for zero actuals)

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

### Metric 1 — Absolute Error

1. **Metric Name:** `absolute_error`
2. **Description:** `Magnitude of prediction error (unsigned)`
3. **Value Column:** `absolute_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Sketch`
6. **Dimension Column:** `-`

### Metric 2 — Forecast Error

1. **Metric Name:** `forecast_error`
2. **Description:** `Signed prediction error (positive = over-prediction)`
3. **Value Column:** `forecast_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Sketch`
6. **Dimension Column:** `-`

### Metric 3 — Absolute Percentage Error

1. **Metric Name:** `absolute_percentage_error`
2. **Description:** `Percentage error per inference (scale-independent)`
3. **Value Column:** `absolute_percentage_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Sketch`
6. **Dimension Column:** `-`

## Interpreting the Metrics

**Note**: All three metrics use [Apache DataSketches](https://datasketches.apache.org/) format, enabling efficient percentile and distribution queries on per-inference errors.

### Absolute Error (Sketch)
- **Distribution analysis**: Query percentiles (P50, P95, P99) dynamically
- **Magnitude only**: No indication of over vs under-prediction
- **Original units**: Same units as predictions/actuals
- **Quantile queries**: Calculate median, quartiles, or any percentile without custom SQL

### Forecast Error (Sketch)
- **Signed distribution**: Shows over-prediction (+) vs under-prediction (-)
- **Bias detection**: Query median for robust bias estimate
- **Symmetric analysis**: Check distribution symmetry with quartiles
- **Quantile queries**: P25/P75 show error spread, P50 shows typical bias

### Absolute Percentage Error (Sketch)
- **Scale-independent**: Compare across different value ranges
- **Per-prediction %**: Stores individual percentage errors for percentile analysis
- **Distribution queries**: Calculate P95 error, histogram bins, or any quantile
- **Outlier detection**: Query P99 to identify worst-case % errors

## Related Metrics

* **Mean Absolute Error (MAE)**: Built-in aggregate of absolute_error
* **MAPE**: Aggregate of absolute_percentage_error
* **Maximum Error**: MAX(absolute_error)
* **Maximum Relative Error**: MAX(absolute_percentage_error)

## When to Use This Consolidated Metric

**Use this comprehensive error distribution when**:
- Need full error analysis capability
- Want to understand both magnitude and direction
- Require scale-independent and absolute error views
- Building dashboards that show multiple error perspectives
- Investigating outliers and error patterns

**Benefits of consolidation**:
- Single query computes all three error types efficiently
- Consistent row-level granularity across all metrics
- Easy to correlate errors across different dimensions
- Reduced computational overhead vs separate queries
