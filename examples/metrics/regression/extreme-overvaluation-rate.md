# Extreme Overvaluation Rate

## Overview

**Extreme Overvaluation Rate** tracks the proportion of predictions that significantly exceed actual values by more than a specified threshold percentage. This metric is essential for identifying systematic optimistic bias in regression models, helping teams detect when models consistently overestimate values in ways that can lead to poor business decisions.

**Key Insights:**
- Identifies when models are dangerously optimistic
- Quantifies the frequency of extreme overestimation errors
- Helps detect systematic bias patterns over time
- Enables threshold-based alerting for risk management

**When to Use:**
- Loan amount prediction (overestimating repayment capacity leads to defaults)
- Demand forecasting (overestimating demand causes excess inventory and waste)
- Pricing models (overestimating willingness to pay results in lost sales)
- Revenue forecasting (overestimation causes budget shortfalls)
- Any scenario where overestimation has asymmetric cost (higher than underestimation)

***

## Step 1: Write the SQL

This SQL computes the proportion of predictions that exceed actual values by more than the specified threshold percentage.

```sql
WITH
  valid_predictions AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_col}}::float AS prediction,
      {{ground_truth_col}}::float AS actual
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
      AND {{prediction_col}} IS NOT NULL
      AND {{ground_truth_col}} IS NOT NULL
      AND {{ground_truth_col}} != 0  -- Exclude zero actuals to avoid division by zero
  ),
  overvaluation_flags AS (
    SELECT
      ts,
      CASE
        WHEN ABS(actual) > 0.0001
         AND (prediction - actual) / ABS(actual) > {{threshold}} THEN 1.0
        ELSE 0.0
      END AS is_extreme_overvaluation
    FROM valid_predictions
  )
SELECT
  ts,
  AVG(is_extreme_overvaluation)::float AS extreme_overvaluation_rate,
  SUM(is_extreme_overvaluation)::int AS extreme_overvaluation_count,
  COUNT(*)::int AS total_predictions
FROM overvaluation_flags
GROUP BY ts
ORDER BY ts;
```

**What this query returns:**

* `ts` — timestamp bucket (1 day)
* `extreme_overvaluation_rate` — proportion of extreme overvaluations (float, 0.0 to 1.0)
* `extreme_overvaluation_count` — count of extreme overvaluations (integer)
* `total_predictions` — total number of predictions in the time bucket (integer)

**SQL Logic:**

1. **valid_predictions CTE**: Filters out NULL values and zero actuals to ensure valid percentage calculations
2. **overvaluation_flags CTE**: Flags each prediction as extreme overvaluation or not using:
   - **Precision safeguard**: `ABS(actual) > 0.0001` prevents division issues with very small values
   - **Formula**: `(prediction - actual) / ABS(actual) > threshold` computes percentage overvaluation
   - **Float flags**: Returns `1.0` (overvaluation) or `0.0` (not overvaluation) for proper type handling
3. **Final aggregation**: Computes the rate, count, and total per day with explicit type casting:
   - `AVG()::float` ensures rate is returned as floating-point decimal (0.0 to 1.0)
   - `SUM()::int` returns integer count of overvaluations
   - `COUNT()::int` returns integer total of predictions

***

## Step 2: Fill Basic Information

When creating the custom metric in the Arthur UI:

1. **Name**:
   `Extreme Overvaluation Rate`

2. **Description** (optional but recommended):
   `Proportion of predictions that exceed actual values by more than a specified threshold percentage. Helps identify systematic optimistic bias and extreme overestimation errors in regression models.`

***

## Step 3: Configure the Aggregate Arguments

You will set up five aggregate arguments to parameterize the SQL.

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
7. **Tag Hints:** `prediction`
8. **Allowed Column Types:** `int, float`

### Argument 3 — Ground Truth Column

1. **Parameter Key:** `ground_truth_col`
2. **Friendly Name:** `Ground_Truth_Col`
3. **Description:** `Column parameter: ground_truth_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `ground_truth`
8. **Allowed Column Types:** `int, float`

### Argument 4 — Threshold

1. **Parameter Key:** `threshold`
2. **Friendly Name:** `Threshold`
3. **Description:** `Threshold for extreme overvaluation (e.g., 0.20 for 20%, 0.50 for 50%)`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Float`
6. **Default Value:** `0.20` (20%)

### Argument 5 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

***

## Step 4: Configure Reported Metrics

This metric reports three values for comprehensive monitoring.

### Metric 1 — Extreme Overvaluation Rate

1. **Metric Name:** `extreme_overvaluation_rate`
2. **Description:** `Proportion of predictions that exceed actual values by more than the threshold percentage`
3. **Value Column:** `extreme_overvaluation_rate`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 2 — Extreme Overvaluation Count

1. **Metric Name:** `extreme_overvaluation_count`
2. **Description:** `Number of predictions that exceed actual values by more than the threshold percentage`
3. **Value Column:** `extreme_overvaluation_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 3 — Total Predictions

1. **Metric Name:** `total_predictions`
2. **Description:** `Total number of predictions evaluated`
3. **Value Column:** `total_predictions`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

***

## Step 5: Dashboard Chart SQL

This query reads from the **metrics_numeric_latest_version** table, which stores pre-computed metric values from the base SQL query. The chart visualizes the stored metrics over time rather than re-computing them.

**Metrics Table Schema:**
The `metrics_numeric_latest_version` table contains:
- `model_id` (uuid) - Model identifier
- `project_id` (uuid) - Project identifier
- `workspace_id` (uuid) - Workspace identifier
- `organization_id` (uuid) - Organization identifier
- `metric_name` (varchar) - Name of the metric (from Step 4)
- `timestamp` (timestamptz) - Time bucket timestamp
- `metric_version` (integer) - Version of the metric definition
- `value` (double precision) - Computed metric value
- `dimensions` (jsonb) - Optional dimension data

**Chart SQL Query:**

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,

    metric_name,

    CASE
        WHEN metric_name = 'extreme_overvaluation_rate' THEN 'Overvaluation Rate'
        WHEN metric_name = 'extreme_overvaluation_count' THEN 'Overvaluation Count'
        WHEN metric_name = 'total_predictions' THEN 'Total Predictions'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'extreme_overvaluation_rate',
    'extreme_overvaluation_count',
    'total_predictions'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**Query Explanation:**
- **`time_bucket_gapfill()`** - Creates continuous time series with no gaps, filling missing time buckets
- **`{{dateStart}}` and `{{dateEnd}}`** - Template variables for configurable time range
- **`[[AND ...]]`** - Optional filter syntax in Arthur Platform
- **`metric_name IN (...)`** - Filters to only the metrics defined in Step 4
- **`COALESCE(AVG(value), 0)`** - Handles missing values gracefully by defaulting to 0
- **CASE statement** - Provides user-friendly display names for metrics

**Chart Configuration:**
- **Chart Type:** Line chart with dual y-axes
- **Primary Y-axis:** `extreme_overvaluation_rate` (multiply by 100 for percentage display: 0.05 → 5%)
- **Secondary Y-axis:** `extreme_overvaluation_count` (raw count)
- **X-axis:** `time_bucket_1d` (daily time buckets)
- **Time Range:** Configurable via `{{dateStart}}` and `{{dateEnd}}` parameters

**What this shows:**
- Trend of extreme overvaluation rate over time
- Volume of extreme overvaluation cases
- Correlation between rate and prediction volume
- Time periods with elevated risk
- Historical patterns and seasonality

***

## Interpreting the Metric

### Value Ranges

**Threshold = 20% (0.20)**:
- **Excellent (< 1%)**: Very few extreme overvaluations, model is well-calibrated
- **Good (1-5%)**: Acceptable level, occasional extreme errors
- **Warning (5-10%)**: Elevated overvaluation rate, investigate patterns
- **Critical (> 10%)**: Significant systematic overestimation, requires immediate attention

**Threshold = 50% (0.50)**:
- **Excellent (< 0.5%)**: Rare catastrophic overestimations
- **Good (0.5-2%)**: Occasional severe errors
- **Warning (2-5%)**: Frequent severe overestimations
- **Critical (> 5%)**: Pervasive severe overestimation issues

### Trends to Watch

**Increasing rate over time:**
- Model drift or data distribution shift
- Systematic bias emerging in recent predictions
- May indicate need for model retraining

**Sudden spikes:**
- Data quality issues (outliers, errors in input features)
- System changes or integration problems
- Specific segments or conditions causing extreme errors

**Consistently high rate:**
- Fundamental model calibration issue
- Wrong features or insufficient training data
- Model architecture not suited for the problem

### When to Investigate

1. **Rate exceeds 5%** (with 20% threshold) - Review recent predictions and look for patterns
2. **Rate doubles week-over-week** - Check for data or system changes
3. **Count increases while total predictions stays constant** - Model performance degrading
4. **Specific time periods show spikes** - Investigate seasonal or temporal factors

***

## Use Cases

### Loan Amount Prediction
**Problem**: Overestimating loan amounts leads to defaults and credit losses.

**Setup**:
- Prediction: `predicted_loan_amount`
- Ground truth: `actual_loan_amount`
- Threshold: 0.30 (30%) - loans approved 30% above what borrower could repay

**Action**: When rate > 5%, review lending criteria and add safety margins to predictions.

### Demand Forecasting
**Problem**: Overestimating demand causes excess inventory, spoilage, and write-offs.

**Setup**:
- Prediction: `predicted_demand`
- Ground truth: `actual_sales`
- Threshold: 0.50 (50%) - predictions 50% above actual sales

**Action**: When rate > 3%, adjust ordering quantities and review forecast model.

### Real Estate Pricing
**Problem**: Overestimating property values leads to unsold inventory and price reductions.

**Setup**:
- Prediction: `predicted_price`
- Ground truth: `actual_sale_price`
- Threshold: 0.20 (20%) - predicted 20% above sale price

**Action**: When rate > 8%, review pricing strategy and adjust model calibration.

### Revenue Forecasting
**Problem**: Overestimating revenue causes budget shortfalls and missed targets.

**Setup**:
- Prediction: `predicted_revenue`
- Ground truth: `actual_revenue`
- Threshold: 0.25 (25%) - predicted 25% above actual

**Action**: When rate > 10%, revise financial plans and investigate forecast assumptions.

***

## Debugging & Verification

If the metric returns empty or unexpected values, use these queries to diagnose the issue:

### 1. Check if base data exists

```sql
SELECT COUNT(*) as total_rows,
       COUNT({{timestamp_col}}) as non_null_timestamps,
       COUNT({{prediction_col}}) as non_null_predictions,
       COUNT({{ground_truth_col}}) as non_null_actuals,
       COUNT(CASE WHEN {{ground_truth_col}} != 0 THEN 1 END) as non_zero_actuals
FROM {{dataset}}
WHERE {{timestamp_col}} >= NOW() - INTERVAL '30 days';
```

**Expected**: All counts should be greater than 0, especially `non_zero_actuals`.

### 2. Verify threshold and value ranges

```sql
SELECT
  AVG({{prediction_col}}::float) as avg_prediction,
  AVG({{ground_truth_col}}::float) as avg_actual,
  MIN({{ground_truth_col}}::float) as min_actual,
  MAX({{ground_truth_col}}::float) as max_actual,
  AVG(({{prediction_col}}::float - {{ground_truth_col}}::float) / ABS({{ground_truth_col}}::float)) as avg_relative_error
FROM {{dataset}}
WHERE {{timestamp_col}} IS NOT NULL
  AND {{prediction_col}} IS NOT NULL
  AND {{ground_truth_col}} IS NOT NULL
  AND {{ground_truth_col}} != 0
  AND {{timestamp_col}} >= NOW() - INTERVAL '30 days';
```

**Expected**: `avg_relative_error` should give you an idea of typical overvaluation. If threshold is 0.20 and avg_relative_error is 0.05, you'd expect low extreme_overvaluation_rate.

### 3. Test with sample data

Manually test the formula with known values:

```sql
SELECT
  100.0 as actual,
  150.0 as prediction,
  0.20 as threshold,
  (150.0 - 100.0) / ABS(100.0) as relative_error,
  (150.0 - 100.0) / ABS(100.0) > 0.20 as is_overvaluation,
  CASE
    WHEN ABS(100.0) > 0.0001 AND (150.0 - 100.0) / ABS(100.0) > 0.20 THEN 1.0
    ELSE 0.0
  END as flag_value;
```

**Expected output**:
- `relative_error` = 0.50 (50% overvaluation)
- `is_overvaluation` = true
- `flag_value` = 1.0

### 4. Check metric output directly

Run the full metric SQL manually with your parameters replaced (replace `{{dataset}}`, `{{threshold}}`, etc.) and verify it returns data.

### Common Issues

- **All zeros**: Threshold too high, or predictions are well-calibrated
- **Empty results**: Check if time range in query matches data availability
- **NULL values**: Ensure all three columns (timestamp, prediction, actual) are present and non-NULL
- **Wrong threshold format**: Use decimal (0.20), not percentage (20)
- **Very small actual values**: The safeguard `ABS(actual) > 0.0001` will exclude these

***

## Dataset Compatibility

This metric is compatible with regression model datasets that include continuous predictions and ground truth values.

### Compatible Datasets from `/data` folder:

#### 1. regression-loan-amount-prediction
**Required Columns:**
- `timestamp` (timestamp) → `timestamp_col`
- `predicted_amount` (float) → `prediction_col`
- `actual_amount` (float) → `ground_truth_col`

**Example Configuration:**
- Threshold: `0.30` (30% overestimation)
- Use case: Identify loans where model significantly overestimated repayment capacity

#### 2. regression-housing-price-prediction
**Required Columns:**
- `timestamp` (timestamp) → `timestamp_col`
- `predicted_house_value` (float) → `prediction_col`
- `actual_house_value` (float) → `ground_truth_col`

**Example Configuration:**
- Threshold: `0.05` (5% overestimation) - **Recommended for this dataset**
- Alternative: `0.10` (10% overestimation) for more extreme cases only
- Note: This model is well-calibrated with typical errors of 2-10%, so a 20% threshold will detect almost no cases
- Use case: Track cases where model overestimated property values

### Data Requirements

**Essential:**
- Timestamp column for time-series aggregation
- Continuous prediction values (int or float)
- Continuous ground truth values (int or float)
- Non-zero ground truth values (zeros filtered in query)

**Optional but Recommended:**
- Segmentation columns (region, product_type, etc.) for drill-down analysis
- Feature columns for root cause analysis of extreme errors

### Notes

- Ground truth values of zero are excluded to prevent division by zero
- Very small actual values (|actual| ≤ 0.0001) are excluded to prevent precision issues
- Negative values are supported (uses absolute value of actual in formula)
- Works with any continuous regression problem
- Threshold should be chosen based on business tolerance for overestimation
- Pair with **Extreme Undervaluation Rate** for complete bias analysis
- Uses explicit float casting (1.0/0.0) in CASE statements for proper type handling

### Choosing the Right Threshold

**Before setting a threshold, analyze your model's error distribution:**

Run this query to understand your model's typical errors:
```sql
SELECT
    MAX((prediction - actual) / ABS(actual)) * 100 as max_overvaluation_pct,
    PERCENTILE_CONT(0.95) WITHIN GROUP (
        ORDER BY (prediction - actual) / ABS(actual)
    ) * 100 as p95_overvaluation_pct,
    AVG((prediction - actual) / ABS(actual)) * 100 as avg_error_pct
FROM your_dataset
WHERE actual != 0;
```

**Threshold guidelines:**
- **Well-calibrated models** (errors typically < 10%): Use threshold 0.05-0.10
- **Moderately accurate models** (errors 10-30%): Use threshold 0.15-0.25
- **Less accurate models** (errors > 30%): Use threshold 0.30-0.50
- Set threshold slightly above your 95th percentile error to flag true outliers
