# Cumulative Error

## Overview

This metric tracks the **cumulative sum of signed prediction errors** over time. It measures:

* Systematic bias (consistent over/under-prediction)
* Net error accumulation
* Direction of forecast bias
* Whether errors cancel out or compound

Cumulative error reveals systematic biases that other metrics miss. While MAE and RMSE measure magnitude, cumulative error shows whether your model consistently predicts too high or too low.

**Formula**: Σ(predicted - actual)

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{prediction_col}}` — predicted value
* `{{ground_truth_col}}` — actual/ground truth value
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates the cumulative sum of signed errors.

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
  daily_error AS (
    SELECT
      ts,
      SUM(prediction - actual) AS net_error
    FROM base
    GROUP BY ts
  )
SELECT
  ts,
  SUM(net_error) OVER (ORDER BY ts ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_error
FROM daily_error
ORDER BY ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `cumulative_error` — running sum of signed errors (can be positive or negative)

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

### Metric 1 — Cumulative Error

1. **Metric Name:** `cumulative_error`
2. **Description:** `Running sum of signed prediction errors`
3. **Value Column:** `cumulative_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

### Cumulative Error Patterns

**Positive and Increasing**:
- Model consistently over-predicts
- Systematic upward bias
- **Action**: Recalibrate predictions downward

**Negative and Decreasing**:
- Model consistently under-predicts
- Systematic downward bias
- **Action**: Recalibrate predictions upward

**Oscillating Around Zero**:
- Errors cancel out over time
- No systematic bias
- **Good**: Model is well-calibrated

**Stable Near Zero**:
- Minimal net error accumulation
- Balanced predictions
- **Excellent**: Unbiased model

**Sudden Changes**:
- Shift in model behavior
- Data distribution change
- Model update or drift
- **Action**: Investigate cause of shift

**Accelerating Growth**:
- Bias worsening over time
- Model degradation
- **Critical**: Immediate investigation needed

## Related Metrics

* **Mean Absolute Error (MAE)**: Magnitude without direction (built-in)
* **RMSE**: Emphasizes larger errors
* **Forecast Error**: Similar concept, often for specific forecast horizons
* **Deviation Ratio**: Normalized version of cumulative error

## When to Use Cumulative Error

**Use cumulative error when**:
- Need to detect systematic bias
- Monitoring for model drift
- Balancing inventory/capacity planning
- Budget variance tracking
- Ensuring long-term calibration

**Don't rely solely on cumulative error when**:
- Error magnitude matters more than direction
- Errors canceling out is acceptable
- Need robust metric (cumulative grows unbounded)
- Short time horizons (not enough data to accumulate)
