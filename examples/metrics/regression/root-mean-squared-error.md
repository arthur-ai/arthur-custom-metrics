# Root Mean Squared Error (RMSE)

## Overview

This metric tracks the **root mean squared error** for regression models. It measures:

* Overall prediction error magnitude with emphasis on larger errors
* Standard deviation of prediction errors
* Model accuracy in original units
* Performance comparison across models

RMSE is calculated as the square root of the mean of squared errors, giving more weight to larger errors than MAE.

**Formula**: √(Σ(predicted - actual)² / n)

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{prediction_col}}` — predicted value
* `{{ground_truth_col}}` — actual/ground truth value
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates RMSE by computing MSE first, then taking the square root.

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
  squared_errors AS (
    SELECT
      ts,
      POWER(prediction - actual, 2) AS squared_error
    FROM base
  )
SELECT
  ts,
  SQRT(AVG(squared_error)) AS rmse
FROM squared_errors
GROUP BY ts
ORDER BY ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `rmse` — root mean squared error

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

### Metric 1 — RMSE

1. **Metric Name:** `rmse`
2. **Description:** `Root mean squared error`
3. **Value Column:** `rmse`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

### RMSE Values

* **Lower RMSE**: Better model performance
* **RMSE in original units**: Easy to interpret (same units as target)
* **RMSE ≥ MAE**: Always true (equality only if all errors equal)
* **Large RMSE vs MAE gap**: Presence of large outlier errors

### Comparison with MAE

**RMSE > MAE indicates**:
- Some predictions have large errors
- Outliers or edge cases exist
- Model may need outlier handling

**RMSE ≈ MAE indicates**:
- Errors are relatively uniform
- Few extreme outliers
- Consistent model performance

### Trends Over Time

* **Increasing RMSE**: Model degradation or harder cases
* **Decreasing RMSE**: Model improvement
* **Stable RMSE**: Consistent performance
* **Spikes**: Data quality issues or outlier batches

## Related Metrics

* **Mean Squared Error (MSE)**: RMSE² (built-in)
* **Mean Absolute Error (MAE)**: Less sensitive to outliers (built-in)
* **Mean Absolute Percentage Error (MAPE)**: Percentage-based
* **Maximum Error**: Worst-case prediction error
