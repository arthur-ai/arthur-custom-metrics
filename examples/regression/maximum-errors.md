# Maximum Errors (Absolute & Relative)

## Overview

This metric tracks **worst-case prediction errors** in both absolute and relative terms. It measures:

* **Maximum Error**: Worst absolute prediction error
* **Maximum Relative Error**: Worst percentage error

Both metrics identify the single worst prediction in each time period, critical for applications where even one bad prediction can have serious consequences.

**Formulas**:
- Maximum Error: max(|predicted - actual|)
- Maximum Relative Error: max(|predicted - actual| / |actual|) × 100

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{prediction_col}}` — predicted value
* `{{ground_truth_col}}` — actual/ground truth value
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates both maximum error types per day.

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
  MAX(ABS(prediction - actual)) AS max_error,
  MAX(
    CASE
      WHEN actual != 0 THEN ABS((prediction - actual) / actual) * 100
      ELSE NULL
    END
  ) AS max_relative_error
FROM base
GROUP BY ts
ORDER BY ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `max_error` — maximum absolute error (original units)
* `max_relative_error` — maximum percentage error (0-100+%, can exceed 100%)

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

### Metric 1 — Maximum Error

1. **Metric Name:** `max_error`
2. **Description:** `Maximum absolute error (worst prediction in absolute terms)`
3. **Value Column:** `max_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 2 — Maximum Relative Error

1. **Metric Name:** `max_relative_error`
2. **Description:** `Maximum percentage error (worst prediction in relative terms)`
3. **Value Column:** `max_relative_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metrics

### Maximum Error (Absolute)
- **Low max error**: Even worst predictions acceptable
- **High max error**: Some predictions very inaccurate
- **Max error >> MAE/RMSE**: Few outliers drag down performance
- **Original units**: Easy to understand business impact

### Maximum Relative Error (Percentage)
- **< 20%**: Worst predictions within 20%
- **20-50%**: Worst-case tolerable for most applications
- **50-100%**: Some predictions off by 50-100%
- **> 100%**: Worst predictions more than double/half actual

### Combined Analysis
- **High max error, Low max relative**: Errors on large values
- **Low max error, High max relative**: Errors on small values
- **Both high**: Consistent worst-case problems
- **Both low**: Reliable across all scales

## Related Metrics

* **Mean Absolute Error (MAE)**: Average magnitude (built-in)
* **RMSE**: Emphasizes larger errors
* **MAPE**: Average percentage error
* **Absolute Error (sketch)**: Full error distribution

## When to Use This Consolidated Metric

**Use maximum errors when**:
- Safety-critical applications (autonomous vehicles, medical, trading)
- Need worst-case performance guarantees
- Setting risk tolerance bounds
- Regulatory compliance requirements
- Understanding extreme performance boundaries
- Want both absolute and scale-independent worst-case views

**Benefits of consolidation**:
- Single query computes both worst-case metrics
- Easy to compare absolute vs relative worst-case
- Consistent time granularity
- Efficient for dashboards showing multiple worst-case perspectives
