# Extreme Undervaluation Rate

## Overview

**Extreme Undervaluation Rate** tracks the proportion of predictions that fall significantly below actual values by more than a specified threshold percentage. This metric is essential for identifying systematic pessimistic bias in regression models, helping teams detect when models consistently underestimate values in ways that lead to missed opportunities and overly conservative decisions.

**Key Insights:**
- Identifies when models are dangerously pessimistic
- Quantifies the frequency of extreme underestimation errors
- Helps detect systematic conservative bias patterns over time
- Enables threshold-based alerting for opportunity cost management

**When to Use:**
- Pricing models (underestimating willingness to pay leaves money on the table)
- Demand forecasting (underestimating demand causes stockouts and lost sales)
- Credit scoring (underestimating creditworthiness excludes viable customers)
- Revenue forecasting (underestimation causes missed growth opportunities)
- Any scenario where underestimation has asymmetric cost (higher than overestimation)

***

## Step 1: Write the SQL

This SQL computes the proportion of predictions that fall below actual values by more than the specified threshold percentage.

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
  undervaluation_flags AS (
    SELECT
      ts,
      CASE
        WHEN ABS(actual) > 0.0001
         AND (actual - prediction) / ABS(actual) > {{threshold}} THEN 1.0
        ELSE 0.0
      END AS is_extreme_undervaluation
    FROM valid_predictions
  )
SELECT
  ts,
  AVG(is_extreme_undervaluation)::float AS extreme_undervaluation_rate,
  SUM(is_extreme_undervaluation)::int AS extreme_undervaluation_count,
  COUNT(*)::int AS total_predictions
FROM undervaluation_flags
GROUP BY ts
ORDER BY ts;
```

**What this query returns:**

* `ts` — timestamp bucket (1 day)
* `extreme_undervaluation_rate` — proportion of extreme undervaluations (float, 0.0 to 1.0)
* `extreme_undervaluation_count` — count of extreme undervaluations (integer)
* `total_predictions` — total number of predictions in the time bucket (integer)

**SQL Logic:**

1. **valid_predictions CTE**: Filters out NULL values and zero actuals to ensure valid percentage calculations
2. **undervaluation_flags CTE**: Flags each prediction as extreme undervaluation or not using:
   - **Precision safeguard**: `ABS(actual) > 0.0001` prevents division issues with very small values
   - **Formula**: `(actual - prediction) / ABS(actual) > threshold` computes percentage undervaluation
   - **Float flags**: Returns `1.0` (undervaluation) or `0.0` (not undervaluation) for proper type handling
3. **Final aggregation**: Computes the rate, count, and total per day with explicit type casting:
   - `AVG()::float` ensures rate is returned as floating-point decimal (0.0 to 1.0)
   - `SUM()::int` returns integer count of undervaluations
   - `COUNT()::int` returns integer total of predictions

***

## Step 2: Fill Basic Information

When creating the custom metric in the Arthur UI:

1. **Name**:
   `Extreme Undervaluation Rate`

2. **Description** (optional but recommended):
   `Proportion of predictions that fall below actual values by more than a specified threshold percentage. Helps identify systematic pessimistic bias and extreme underestimation errors in regression models.`

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
3. **Description:** `Threshold for extreme undervaluation (e.g., 0.20 for 20%, 0.50 for 50%)`
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

### Metric 1 — Extreme Undervaluation Rate

1. **Metric Name:** `extreme_undervaluation_rate`
2. **Description:** `Proportion of predictions that fall below actual values by more than the threshold percentage`
3. **Value Column:** `extreme_undervaluation_rate`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 2 — Extreme Undervaluation Count

1. **Metric Name:** `extreme_undervaluation_count`
2. **Description:** `Number of predictions that fall below actual values by more than the threshold percentage`
3. **Value Column:** `extreme_undervaluation_count`
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
        WHEN metric_name = 'extreme_undervaluation_rate' THEN 'Undervaluation Rate'
        WHEN metric_name = 'extreme_undervaluation_count' THEN 'Undervaluation Count'
        WHEN metric_name = 'total_predictions' THEN 'Total Predictions'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'extreme_undervaluation_rate',
    'extreme_undervaluation_count',
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
- **Primary Y-axis:** `extreme_undervaluation_rate` (multiply by 100 for percentage display: 0.05 → 5%)
- **Secondary Y-axis:** `extreme_undervaluation_count` (raw count)
- **X-axis:** `time_bucket_1d` (daily time buckets)
- **Time Range:** Configurable via `{{dateStart}}` and `{{dateEnd}}` parameters

**What this shows:**
- Trend of extreme undervaluation rate over time
- Volume of extreme undervaluation cases
- Correlation between rate and prediction volume
- Time periods with elevated missed opportunity risk
- Historical patterns and seasonality

***

## Interpreting the Metric

### Value Ranges

**Threshold = 20% (0.20)**:
- **Excellent (< 1%)**: Very few extreme undervaluations, model is well-calibrated
- **Good (1-5%)**: Acceptable level, occasional extreme errors
- **Warning (5-10%)**: Elevated undervaluation rate, investigate patterns
- **Critical (> 10%)**: Significant systematic underestimation, requires immediate attention

**Threshold = 50% (0.50)**:
- **Excellent (< 0.5%)**: Rare catastrophic underestimations
- **Good (0.5-2%)**: Occasional severe errors
- **Warning (2-5%)**: Frequent severe underestimations
- **Critical (> 5%)**: Pervasive severe underestimation issues

### Trends to Watch

**Increasing rate over time:**
- Model drift or data distribution shift
- Systematic conservative bias emerging in recent predictions
- May indicate need for model retraining or recalibration

**Sudden spikes:**
- Data quality issues (outliers, errors in input features)
- System changes or integration problems
- Specific segments or conditions causing extreme errors

**Consistently high rate:**
- Fundamental model calibration issue
- Wrong features or insufficient training data
- Model architecture overly conservative for the problem

### When to Investigate

1. **Rate exceeds 5%** (with 20% threshold) - Review recent predictions and look for patterns
2. **Rate doubles week-over-week** - Check for data or system changes
3. **Count increases while total predictions stays constant** - Model performance degrading
4. **Specific time periods show spikes** - Investigate seasonal or temporal factors

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
  AVG(({{ground_truth_col}}::float - {{prediction_col}}::float) / ABS({{ground_truth_col}}::float)) as avg_undervaluation
FROM {{dataset}}
WHERE {{timestamp_col}} IS NOT NULL
  AND {{prediction_col}} IS NOT NULL
  AND {{ground_truth_col}} IS NOT NULL
  AND {{ground_truth_col}} != 0
  AND {{timestamp_col}} >= NOW() - INTERVAL '30 days';
```

**Expected**: `avg_undervaluation` > 0 indicates predictions are generally lower than actuals. If threshold is 0.20 and avg_undervaluation is 0.05, you'd expect low extreme_undervaluation_rate.

### 3. Test with sample data

Manually test the formula with known values:

```sql
SELECT
  100.0 as actual,
  70.0 as prediction,
  0.20 as threshold,
  (100.0 - 70.0) / ABS(100.0) as undervaluation,
  (100.0 - 70.0) / ABS(100.0) > 0.20 as is_undervaluation,
  CASE
    WHEN ABS(100.0) > 0.0001 AND (100.0 - 70.0) / ABS(100.0) > 0.20 THEN 1.0
    ELSE 0.0
  END as flag_value;
```

**Expected output**:
- `undervaluation` = 0.30 (30% undervaluation)
- `is_undervaluation` = true
- `flag_value` = 1.0

### 4. Check how many predictions fall below threshold

```sql
SELECT
    COUNT(*) as total_predictions,
    COUNT(CASE
        WHEN ({{ground_truth_col}}::float - {{prediction_col}}::float) / ABS({{ground_truth_col}}::float) > {{threshold}}
        THEN 1
    END) as predictions_below_threshold,
    COUNT(CASE
        WHEN ({{ground_truth_col}}::float - {{prediction_col}}::float) / ABS({{ground_truth_col}}::float) > {{threshold}}
        THEN 1
    END)::float / NULLIF(COUNT(*), 0) as rate
FROM {{dataset}}
WHERE {{timestamp_col}} IS NOT NULL
  AND {{prediction_col}} IS NOT NULL
  AND {{ground_truth_col}} IS NOT NULL
  AND {{ground_truth_col}} != 0
  AND ABS({{ground_truth_col}}::float) > 0.0001;
```

**Expected**: If predictions_below_threshold = 0, then the rate will be 0 (meaning no undervaluations, not a bug).

### Common Issues

- **All zeros**: Threshold too high, or predictions are well-calibrated / actually overvaluing
- **Empty results**: Check if time range in query matches data availability
- **NULL values**: Ensure all three columns (timestamp, prediction, actual) are present and non-NULL
- **Wrong threshold format**: Use decimal (0.20), not percentage (20)
- **Very small actual values**: The safeguard `ABS(actual) > 0.0001` will exclude these
- **Model overvalues instead**: If predictions are consistently above actuals, undervaluation rate will be 0

***

## Use Cases

### Pricing Models
**Problem**: Underestimating customer willingness to pay leaves revenue on the table.

**Setup**:
- Prediction: `predicted_price`
- Ground truth: `actual_sale_price`
- Threshold: 0.20 (20%) - prices set 20% below what customers actually paid

**Action**: When rate > 5%, review pricing strategy and increase price recommendations.

### Demand Forecasting
**Problem**: Underestimating demand causes stockouts, lost sales, and customer dissatisfaction.

**Setup**:
- Prediction: `predicted_demand`
- Ground truth: `actual_demand`
- Threshold: 0.30 (30%) - forecast 30% below actual demand

**Action**: When rate > 3%, increase safety stock levels and adjust forecast model.

### Credit Scoring
**Problem**: Underestimating creditworthiness excludes viable customers and reduces revenue.

**Setup**:
- Prediction: `predicted_default_probability`
- Ground truth: `actual_default_probability`
- Threshold: 0.50 (50%) - significantly overestimating default risk

**Action**: When rate > 8%, review credit approval thresholds and recalibrate risk model.

### Real Estate Valuation
**Problem**: Underestimating property values leads to underpricing and lost equity.

**Setup**:
- Prediction: `predicted_valuation`
- Ground truth: `actual_appraisal`
- Threshold: 0.15 (15%) - valuations 15% below appraisal

**Action**: When rate > 10%, adjust valuation model to capture true market value.

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
- Threshold: `0.30` (30% underestimation)
- Use case: Identify loans where model significantly underestimated borrowing capacity

#### 2. regression-housing-price-prediction
**Required Columns:**
- `timestamp` (timestamp) → `timestamp_col`
- `predicted_house_value` (float) → `prediction_col`
- `actual_house_value` (float) → `ground_truth_col`

**Example Configuration:**
- Threshold: `0.05` (5% underestimation) - **Recommended for this dataset**
- Alternative: `0.10` (10% underestimation) for more extreme cases only
- Note: This model is well-calibrated with typical errors of 2-10%, so a 20% threshold will detect almost no cases
- Use case: Track cases where model underestimated property values

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
- Threshold should be chosen based on business tolerance for underestimation
- Pair with **Extreme Overvaluation Rate** for complete bias analysis
- Uses explicit float casting (1.0/0.0) in CASE statements for proper type handling

### Choosing the Right Threshold

**Before setting a threshold, analyze your model's error distribution:**

Run this query to understand your model's typical errors:
```sql
SELECT
    MIN((actual - prediction) / ABS(actual)) * 100 as max_undervaluation_pct,
    PERCENTILE_CONT(0.05) WITHIN GROUP (
        ORDER BY (prediction - actual) / ABS(actual)
    ) * 100 as p5_undervaluation_pct,
    AVG((actual - prediction) / ABS(actual)) * 100 as avg_undervaluation_pct
FROM your_dataset
WHERE actual != 0
  AND (actual - prediction) > 0;  -- Only look at undervaluations
```

**Threshold guidelines:**
- **Well-calibrated models** (errors typically < 10%): Use threshold 0.05-0.10
- **Moderately accurate models** (errors 10-30%): Use threshold 0.15-0.25
- **Less accurate models** (errors > 30%): Use threshold 0.30-0.50
- Set threshold slightly above your 5th percentile error to flag true outliers
- For the housing dataset, use 0.05-0.10 based on observed error distribution
