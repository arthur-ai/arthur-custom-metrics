# Mean Absolute Deviation (MAD)

## Overview

This metric tracks the **mean absolute deviation of predictions from their mean**. It measures:

* Prediction variability and consistency
* How much predictions fluctuate
* Stability of model outputs
* Dispersion of prediction values

MAD measures the average distance of predictions from the mean prediction, indicating how consistent or variable the model's outputs are. This complements error metrics by revealing prediction stability.

**Formula**: AVG(|prediction - mean(predictions)|)

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{prediction_col}}` — predicted value
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates the mean absolute deviation of predictions.

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_col}}::float AS prediction
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
      AND {{prediction_col}} IS NOT NULL
  ),
  daily_stats AS (
    SELECT
      ts,
      prediction,
      AVG(prediction) OVER (PARTITION BY ts) AS mean_prediction
    FROM base
  )
SELECT
  ts,
  AVG(ABS(prediction - mean_prediction)) AS mad
FROM daily_stats
GROUP BY ts
ORDER BY ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `mad` — mean absolute deviation of predictions (same units as predictions)

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

### Argument 3 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — MAD

1. **Metric Name:** `mad`
2. **Description:** `Mean absolute deviation of predictions from their mean`
3. **Value Column:** `mad`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

### MAD Values

**Low MAD**:
- Predictions are clustered near the mean
- Consistent model outputs
- Low variability
- **Good for**: Stable predictions needed

**High MAD**:
- Predictions are spread out
- Variable model outputs
- High dispersion
- **Good for**: Diverse prediction ranges expected

**MAD ≈ 0**:
- All predictions nearly identical
- Extremely consistent (possibly too consistent)
- **Warning**: May indicate model not adapting to inputs

**Increasing MAD over time**:
- Predictions becoming more variable
- Model behavior changing
- **Action**: Investigate cause

**Decreasing MAD over time**:
- Predictions becoming less variable
- Model converging to narrower range
- **Action**: Verify still responsive to input changes

## Relationship to Standard Deviation

**MAD vs Standard Deviation**:
- MAD: Average absolute distance from mean
- StdDev: RMS distance from mean (√(AVG((x - mean)²)))
- For normal distribution: MAD ≈ 0.8 × StdDev
- MAD is more robust to outliers

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_col}}::float AS prediction
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
  ),
  daily_stats AS (
    SELECT
      ts,
      prediction,
      AVG(prediction) OVER (PARTITION BY ts) AS mean_prediction
    FROM base
  )
SELECT
  ts,
  AVG(ABS(prediction - mean_prediction)) AS mad,
  STDDEV(prediction) AS std_dev,
  AVG(ABS(prediction - mean_prediction)) / NULLIF(STDDEV(prediction), 0) AS mad_to_std_ratio
FROM daily_stats
GROUP BY ts
ORDER BY ts;
```

**Expected ratio**: ~0.8 for normal distribution

## Related Metrics

* **Mean Absolute Error (MAE)**: Error magnitude (built-in)
* **RMSE**: Error with outlier emphasis
* **Absolute Error**: Per-inference error distribution (sketch)
* **Standard Deviation**: Prediction dispersion (more sensitive to outliers)

## Domain-Specific Interpretation

**Demand Forecasting**:
- High MAD: Wide prediction range (uncertain demand)
- Low MAD: Narrow prediction range (stable demand)

**Price Prediction**:
- High MAD: Model predicts diverse price points
- Low MAD: Model predictions clustered (may lack nuance)

**Energy Load**:
- High MAD: Variable load predictions (challenging conditions)
- Low MAD: Stable load predictions (predictable patterns)

## When to Use MAD (Predictions)

**Use MAD when**:
- Monitoring prediction consistency
- Detecting model behavior changes
- Validating model deployment (compare pre/post MAD)
- Understanding prediction spread
- Need robust variability measure

**Don't use MAD for**:
- Measuring prediction accuracy (use MAE, RMSE instead)
- Direct comparison with actuals (MAD doesn't use actuals)
- Error magnitude assessment

**Use MAE (built-in) for**:
- Prediction error measurement
- Accuracy assessment
- Model performance evaluation

Note: This metric measures internal consistency of predictions, not their accuracy against ground truth.
