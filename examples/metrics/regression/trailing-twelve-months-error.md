# Trailing Twelve Months Error (TTM Error)

## Overview

This metric tracks the **mean absolute error over the trailing 12 months** on a rolling basis. It measures:

* Long-term prediction accuracy smoothed over annual cycles
* Model performance accounting for seasonality
* Stable accuracy metric for trend analysis
* Year-over-year performance comparison

TTM error provides a smoothed view of accuracy that accounts for seasonal variations, making it ideal for detecting genuine performance changes vs seasonal fluctuations.

**Formula**: Average of |predicted - actual| over last 365 days

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{prediction_col}}` — predicted value
* `{{ground_truth_col}}` — actual/ground truth value
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates the rolling 12-month mean absolute error.

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
  daily_errors AS (
    SELECT
      ts,
      AVG(ABS(prediction - actual)) AS daily_mae
    FROM base
    GROUP BY ts
  )
SELECT
  ts,
  AVG(daily_mae) OVER (
    ORDER BY ts
    ROWS BETWEEN 364 PRECEDING AND CURRENT ROW
  ) AS ttm_error
FROM daily_errors
ORDER BY ts;
```

**What this query returns**

* `ts` — timestamp (daily)
* `ttm_error` — mean absolute error over trailing 365 days (including current day)

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

### Metric 1 — TTM Error

1. **Metric Name:** `ttm_error`
2. **Description:** `Mean absolute error over trailing 12 months`
3. **Value Column:** `ttm_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

### TTM Error Trends

**Decreasing TTM Error**:
- Model performance improving over time
- Better handling of seasonal patterns
- **Good**: Sustained improvement

**Increasing TTM Error**:
- Model performance degrading
- Data drift or concept drift
- **Action**: Investigate and retrain

**Stable TTM Error**:
- Consistent long-term performance
- Seasonal variations smoothed out
- **Good**: Predictable accuracy

**Sudden Changes**:
- Significant model or data changes
- Major seasonal shift
- External factors affecting predictions
- **Action**: Investigate cause

**Seasonal Spikes Removed**:
- Unlike daily/monthly MAE, TTM smooths seasonality
- Provides cleaner trend signal
- Better for detecting real performance changes

## Advantages of TTM Error

1. **Seasonality-adjusted**: Includes full annual cycle
2. **Stable metric**: Less volatile than short-term metrics
3. **Year-over-year comparison**: Always comparing same calendar mix
4. **Trend detection**: Easier to spot genuine improvements/degradations
5. **Executive reporting**: Stable KPI for leadership dashboards

## Related Metrics

* **Mean Absolute Error (MAE)**: Short-term accuracy (built-in)
* **RMSE**: Short-term with outlier emphasis
* **Absolute Error**: Per-inference distribution (sketch)
* **End of Term Error**: Accuracy at specific milestones
* **Cumulative Error**: Running sum of bias

## When to Use TTM Error

**Use TTM error when**:
- Seasonality is significant in your domain
- Need stable metric for executive reporting
- Tracking long-term model performance trends
- Comparing year-over-year performance
- Strategic planning and forecasting
- Smoothing out short-term volatility

**Use short-term metrics (daily/weekly MAE) when**:
- Need rapid feedback on model changes
- Real-time operational decisions
- Detecting sudden issues quickly
- A/B testing models (need quick signal)
- Seasonality is minimal

**Use both**:
- TTM for strategic trends
- Daily/weekly for tactical monitoring
- Combined view shows full picture
