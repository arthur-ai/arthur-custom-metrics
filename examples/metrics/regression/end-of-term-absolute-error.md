# End of Term Absolute Error

## Overview

This metric tracks the **absolute prediction error at specific term boundaries** (e.g., end of quarter, end of year). It measures:

* Accuracy of predictions at critical business milestones
* Performance for key reporting periods
* Planning accuracy for term-end targets
* Error magnitude at decision points

Unlike continuous error metrics, end-of-term error focuses on accuracy at specific high-stakes moments when predictions matter most for business decisions and reporting.

**Formula**: |predicted - actual| at term end dates

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{prediction_col}}` — predicted value
* `{{ground_truth_col}}` — actual/ground truth value
* `{{term_boundary}}` — term boundary type (literal: 'month', 'quarter', 'year')
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates absolute error only for the last day of each term (month, quarter, or year).

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_col}}::float AS prediction,
      {{ground_truth_col}}::float AS actual,
      {{timestamp_col}} AS full_timestamp
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
      AND {{prediction_col}} IS NOT NULL
      AND {{ground_truth_col}} IS NOT NULL
  ),
  term_ends AS (
    SELECT
      ts,
      prediction,
      actual,
      CASE
        WHEN '{{term_boundary}}' = 'month' THEN
          ts = (DATE_TRUNC('month', ts) + INTERVAL '1 month' - INTERVAL '1 day')::date
        WHEN '{{term_boundary}}' = 'quarter' THEN
          ts = (DATE_TRUNC('quarter', ts) + INTERVAL '3 months' - INTERVAL '1 day')::date
        WHEN '{{term_boundary}}' = 'year' THEN
          ts = (DATE_TRUNC('year', ts) + INTERVAL '1 year' - INTERVAL '1 day')::date
        ELSE FALSE
      END AS is_term_end
    FROM base
  )
SELECT
  ts,
  ABS(prediction - actual) AS end_of_term_error
FROM term_ends
WHERE is_term_end = TRUE
ORDER BY ts;
```

**What this query returns**

* `ts` — term end date (last day of month/quarter/year)
* `end_of_term_error` — absolute error at term boundary

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

### Argument 4 — Term Boundary

1. **Parameter Key:** `term_boundary`
2. **Friendly Name:** `Term_Boundary`
3. **Description:** `Type of term boundary: 'month', 'quarter', or 'year'`
4. **Parameter Type:** `Literal`
5. **Default Value:** `month`

### Argument 5 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — End of Term Error

1. **Metric Name:** `end_of_term_error`
2. **Description:** `Absolute prediction error at term boundaries`
3. **Value Column:** `end_of_term_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

### End of Term Error Patterns

**Consistently Low**:
- Good accuracy at critical milestones
- Reliable for term-end planning
- **Good**: Trustworthy predictions for reporting

**Consistently High**:
- Poor accuracy at term boundaries
- Planning targets frequently missed
- **Action**: Improve end-of-term forecasting

**Increasing Over Time**:
- Degrading prediction quality at milestones
- Model drift or data shift
- **Action**: Investigate and retrain

**Higher than Average Error**:
- Term-end predictions worse than daily average
- May need specialized term-end models
- **Action**: Focus on term-boundary predictions

**Lower than Average Error**:
- Better accuracy at term ends (unusual)
- May indicate overfitting to milestones
- Validate model generalization

## Related Metrics

* **Absolute Error**: Error for all predictions (sketch)
* **Trailing Twelve Months Error**: Cumulative error over 12 months
* **MAE**: Average error across all predictions (built-in)
* **MAPE**: Percentage error across all predictions
* **Forecast Error**: Signed error for all predictions

## When to Use End of Term Error

**Use end-of-term error when**:
- Business decisions tied to specific milestones
- Reporting accuracy matters at term boundaries
- Budget/target accuracy critical at period end
- Need to track KPI achievement accuracy
- Term-end predictions have higher stakes

**Use continuous metrics (MAE, RMSE) when**:
- All predictions equally important
- No special significance to term boundaries
- Real-time accuracy matters
- Operational decisions independent of calendar periods
