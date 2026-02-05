## Overview

The **Core Accuracy at PPE 10% Threshold** metric measures the proportion of predictions that fall within a 10% error threshold of the actual value. This is a regression accuracy metric that evaluates how many predictions are "close enough" to the ground truth, where "close enough" is defined as within 10% of the actual value.

This metric is useful for:

* Tracking the proportion of predictions that meet a business-defined accuracy threshold
* Understanding model performance in terms of acceptable error rates
* Monitoring how many predictions are within acceptable bounds over time
* Comparing model versions on a threshold-based accuracy measure
* Providing an interpretable metric for regression models (e.g., "80% of predictions are within 10% of actual")

**Important:** This metric requires **regression models** with continuous numeric predictions and actual values. It calculates the percentage prediction error (PPE) for each prediction and counts how many fall within the 10% threshold.

The metric stores accuracy values as a **numeric** metric, aggregated into 5-minute time buckets.

***

## Metrics

**core_accuracy_at_ppe_10_threshold**  
The proportion of predictions within 10% of the actual value:

```text
PPE = |predicted_value - actual_value| / actual_value
core_accuracy_at_ppe_10_threshold = count(PPE <= 0.10) / total_count
```

Where:
* `PPE` = Percentage Prediction Error (absolute percentage difference)
* A prediction is considered "accurate" if its PPE is ≤ 0.10 (10%)
* The metric is the proportion of accurate predictions among all predictions

This is computed per time bucket and stored as a numeric metric, allowing you to:
* Track accuracy over time
* Query accuracy values for specific time ranges
* Compare accuracy across different dimensions

***

## Data Requirements

Your dataset must include:

* `{{timestamp_col}}` – event or prediction timestamp
* `{{prediction_col}}` – predicted value (continuous numeric)
* `{{actual_col}}` – ground truth/actual value (continuous numeric)

Both prediction and actual columns must be continuous numeric values (float or integer types). The actual value must be non-zero to avoid division by zero when calculating percentage error.

***

## Base Metric SQL

This SQL computes accuracy at PPE 10% threshold per 5-minute time bucket by calculating the percentage prediction error for each record and counting how many fall within the 10% threshold:

```sql
SELECT
    time_bucket(INTERVAL '5 minutes', {{timestamp_col}}) AS ts,
    COUNT(*) AS total_predictions,
    SUM(
        CASE 
            WHEN {{actual_col}} != 0 
                 AND ABS({{prediction_col}} - {{actual_col}}) / ABS({{actual_col}}) <= 0.10 
            THEN 1 
            ELSE 0 
        END
    ) AS accurate_predictions,
    CASE 
        WHEN COUNT(*) > 0 
        THEN (
            SUM(
                CASE 
                    WHEN {{actual_col}} != 0 
                         AND ABS({{prediction_col}} - {{actual_col}}) / ABS({{actual_col}}) <= 0.10 
                    THEN 1 
                    ELSE 0 
                END
            )
        )::double precision / COUNT(*)
        ELSE 0.0
    END AS core_accuracy_at_ppe_10_threshold
FROM {{dataset}}
WHERE {{prediction_col}} IS NOT NULL
  AND {{actual_col}} IS NOT NULL
GROUP BY ts
ORDER BY ts;
```

**What this query does:**

* `time_bucket(INTERVAL '5 minutes', {{timestamp_col}})` aggregates records into 5-minute time buckets
* `COUNT(*)` counts total predictions in each bucket
* `ABS({{prediction_col}} - {{actual_col}}) / ABS({{actual_col}})` calculates the percentage prediction error (PPE) for each record
* `SUM(CASE WHEN PPE <= 0.10 THEN 1 ELSE 0 END)` counts predictions within the 10% threshold
* `core_accuracy_at_ppe_10_threshold` divides accurate predictions by total predictions, with divide-by-zero protection
* Filters out NULL values in prediction or actual columns
* Handles division by zero by checking `{{actual_col}} != 0` before calculating PPE

**Note:** This requires access to the **raw dataset** with individual prediction and actual values.

***

## Step 1: Fill Basic Information

When creating the custom metric in the Arthur UI:

1. **Name**:  
   `Core Accuracy at PPE 10% Threshold`

2. **Description**:  
   `The proportion of predictions that fall within 10% of the actual value. This metric calculates the percentage prediction error (PPE) for each prediction and counts how many are within the 10% threshold.`

3. **Model Problem Type**:  
   `regression` (optional, but recommended to help users discover this metric)

***

## Step 2: Configure the Aggregate Arguments

You will set up three aggregate arguments to parameterize the SQL.

### Argument 1 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

This links the metric definition to whichever **Arthur dataset** (inference or batch) you want to compute accuracy on.

***

### Argument 2 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Column containing the timestamp for time bucketing.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag hints (optional):** `primary_timestamp`
8. **Allowed Column Types (optional):** `timestamp`

This tells Arthur which timestamp column to use for the `time_bucket` function.

***

### Argument 3 — Prediction Column

1. **Parameter Key:** `prediction_col`
2. **Friendly Name:** `Prediction Column`
3. **Description:** `Column containing the model's predicted values (continuous numeric).`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag hints (optional):** `prediction`
8. **Allowed Column Types (optional):** `float`, `numeric`, `integer`

This should point to your model's **prediction column** (continuous numeric values).

***

### Argument 4 — Actual Column

1. **Parameter Key:** `actual_col`
2. **Friendly Name:** `Actual Column`
3. **Description:** `Column containing the ground truth/actual values (continuous numeric).`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag hints (optional):** `ground_truth`, `label`
8. **Allowed Column Types (optional):** `float`, `numeric`, `integer`

This should point to your **ground truth/actual value column** (continuous numeric values).

***

## Step 3: Configure the Reported Metrics

### Reported Metric 1 — Core Accuracy at PPE 10% Threshold (Numeric)

1. **Metric Name:** `core_accuracy_at_ppe_10_threshold`
2. **Description:** `The proportion of predictions that fall within 10% of the actual value (percentage prediction error <= 0.10).`
3. **Value Column:** `core_accuracy_at_ppe_10_threshold`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

This tells Arthur to store the accuracy values as a numeric metric. Numeric metrics allow you to query values over time and aggregate them into larger time windows.

***

## Plots (Daily Aggregated)

> Preview Data
>
> for startDate use 2026-01-02T00:00:00.000Z
> for endDate use 2026-02-01T23:59:59.999Z
>
> **Note:** Ensure your date range overlaps with your actual data. Your data spans from 2026-01-02 to 2026-02-01. If the dashboard date range doesn't overlap with this, the query will return no results.

### Plot 1 — Core Accuracy at PPE 10% Threshold Over Time

This plot shows accuracy values over time aggregated to daily buckets. This reveals how the proportion of predictions within the 10% threshold changes over time and helps identify performance degradation or improvement.

```sql
SELECT 
    time_bucket_gapfill(
        INTERVAL '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,
    COALESCE(AVG(value), 0.0) AS core_accuracy_at_ppe_10_threshold
FROM metrics_numeric_latest_version
WHERE metric_name = 'core_accuracy_at_ppe_10_threshold'
    [[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

**Troubleshooting:** If this query returns no data:
1. **Check date range:** Ensure `{{dateStart}}` and `{{dateEnd}}` overlap with your actual data range. Your data exists from 2026-01-02 to 2026-02-01. Try removing the date filter temporarily to test: remove the line `[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]`
2. Verify the custom metric `core_accuracy_at_ppe_10_threshold` has been created and configured for your model
3. Ensure a metrics calculation job has run successfully
4. Confirm the metric name matches exactly: `core_accuracy_at_ppe_10_threshold`

**What this shows**  
This plot displays accuracy values over time, showing:

* **Accuracy trends** - Whether the proportion of predictions within 10% threshold is improving, degrading, or stable
* **Performance stability** - How consistent the model's accuracy is over time
* **Anomalies** - Sudden drops or spikes in accuracy that may indicate data quality issues or model problems

**How to interpret it**

* **High accuracy (close to 1.0)** indicates most predictions are within 10% of actual values
* **Low accuracy (close to 0.0)** indicates few predictions are within the 10% threshold
* **Stable accuracy** suggests consistent model performance
* **Declining accuracy** may indicate model degradation, data drift, or changing conditions
* **Spikes or drops** often correspond to data quality issues, model updates, or edge cases
* **Accuracy of 0.5** means half of predictions are within 10% of actual values

***

### Plot 2 — Core Accuracy with Confidence Intervals

This plot shows accuracy over time with confidence intervals, providing a more nuanced view of model performance by accounting for sample size variability.

```sql
WITH daily_accuracy AS (
    SELECT 
        time_bucket(INTERVAL '1 day', timestamp) AS bucket,
        AVG(value) AS avg_accuracy,
        COUNT(*) AS sample_count,
        STDDEV(value) AS stddev_accuracy
    FROM metrics_numeric_latest_version
    WHERE metric_name = 'core_accuracy_at_ppe_10_threshold'
        [[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
    GROUP BY bucket
)
SELECT 
    time_bucket_gapfill(
        INTERVAL '1 day',
        bucket,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,
    COALESCE(avg_accuracy, 0.0) AS core_accuracy_at_ppe_10_threshold,
    COALESCE(avg_accuracy - 1.96 * (stddev_accuracy / SQRT(sample_count)), 0.0) AS lower_bound,
    COALESCE(avg_accuracy + 1.96 * (stddev_accuracy / SQRT(sample_count)), 1.0) AS upper_bound
FROM daily_accuracy
ORDER BY time_bucket_1d;
```

**What this shows**  
This plot helps you understand:

* **Accuracy variability** - How much accuracy varies within each day
* **Statistical significance** - Whether changes in accuracy are meaningful or within normal variation
* **Confidence in estimates** - Wider intervals indicate less confidence due to smaller sample sizes

**How to interpret it**

* **Narrow confidence intervals** indicate stable, well-estimated accuracy
* **Wide confidence intervals** suggest high variability or small sample sizes
* **Overlapping intervals** between time periods suggest changes may not be statistically significant
* **Non-overlapping intervals** suggest meaningful changes in accuracy

***

## Alternative SQL Examples

### Alternative 1: With Dimension Support

If you want to track accuracy by dimension (e.g., region, customer segment), you can add dimension columns:

```sql
SELECT
    time_bucket(INTERVAL '5 minutes', {{timestamp_col}}) AS ts,
    {{dimension_col}} AS dimension_value,
    COUNT(*) AS total_predictions,
    SUM(
        CASE 
            WHEN {{actual_col}} != 0 
                 AND ABS({{prediction_col}} - {{actual_col}}) / ABS({{actual_col}}) <= 0.10 
            THEN 1 
            ELSE 0 
        END
    ) AS accurate_predictions,
    CASE 
        WHEN COUNT(*) > 0 
        THEN (
            SUM(
                CASE 
                    WHEN {{actual_col}} != 0 
                         AND ABS({{prediction_col}} - {{actual_col}}) / ABS({{actual_col}}) <= 0.10 
                    THEN 1 
                    ELSE 0 
                END
            )
        )::double precision / COUNT(*)
        ELSE 0.0
    END AS core_accuracy_at_ppe_10_threshold
FROM {{dataset}}
WHERE {{prediction_col}} IS NOT NULL
  AND {{actual_col}} IS NOT NULL
GROUP BY ts, dimension_value
ORDER BY ts, dimension_value;
```

Then configure `dimension_value` as a dimension column in your reported metric to enable segmentation in dashboards. This allows you to query accuracy separately for each dimension value (e.g., by region).

**Querying by dimension:**
```sql
SELECT 
    time_bucket(INTERVAL '1 day', timestamp) AS bucket,
    dimensions ->> 'dimension_value' AS region,
    AVG(value) AS core_accuracy_at_ppe_10_threshold
FROM metrics_numeric_latest_version
WHERE metric_name = 'core_accuracy_at_ppe_10_threshold'
    [[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
GROUP BY bucket, region
ORDER BY bucket, region;
```

***

### Alternative 2: Configurable Threshold

If you want to make the threshold configurable (not hardcoded to 10%), you can add a literal argument:

```sql
SELECT
    time_bucket(INTERVAL '5 minutes', {{timestamp_col}}) AS ts,
    COUNT(*) AS total_predictions,
    SUM(
        CASE 
            WHEN {{actual_col}} != 0 
                 AND ABS({{prediction_col}} - {{actual_col}}) / ABS({{actual_col}}) <= {{threshold}}
            THEN 1 
            ELSE 0 
        END
    ) AS accurate_predictions,
    CASE 
        WHEN COUNT(*) > 0 
        THEN (
            SUM(
                CASE 
                    WHEN {{actual_col}} != 0 
                         AND ABS({{prediction_col}} - {{actual_col}}) / ABS({{actual_col}}) <= {{threshold}}
                    THEN 1 
                    ELSE 0 
                END
            )
        )::double precision / COUNT(*)
        ELSE 0.0
    END AS core_accuracy_at_ppe_threshold
FROM {{dataset}}
WHERE {{prediction_col}} IS NOT NULL
  AND {{actual_col}} IS NOT NULL
GROUP BY ts
ORDER BY ts;
```

Then add a literal argument:
* **Parameter Key:** `threshold`
* **Friendly Name:** `Error Threshold`
* **Description:** `Percentage error threshold (e.g., 0.10 for 10%, 0.05 for 5%)`
* **Parameter Type:** `Literal`
* **Data Type:** `Float`

For the standard 10% threshold metric, use `0.10` as the default value.

***

## Model Compatibility

### Compatible Datasets

This metric is compatible with **regression models** that have continuous numeric predictions and ground truth values.

#### Loan Amount Prediction Dataset

**Location:** `/data/loan-amount-prediction/`

**Compatibility:** ✅ **Fully Compatible**

**Relevant Columns:**
* `timestamp` - Timestamp column for time bucketing (timestamp with UTC timezone)
* `predicted_loan_amount` - Continuous numeric prediction column (float64, range: $5,000-$500,000)
* `actual_loan_amount` - Continuous numeric ground truth column (float64, range: $5,000-$500,000)

**Configuration:**
* `timestamp_col`: `timestamp`
* `prediction_col`: `predicted_loan_amount`
* `actual_col`: `actual_loan_amount`

**Dataset Description:**  
This dataset simulates a loan amount prediction system where a model predicts the approved loan amount based on applicant features. Both predicted and actual loan amounts are continuous numeric values, making it ideal for computing percentage prediction error and accuracy at PPE threshold.

**Additional Features:**
* Geographic regions (`region`) - can be used for dimension-based accuracy analysis
* Loan application features (credit score, income, age, etc.)
* Date partitioning for efficient querying

#### Incompatible Datasets

**Credit Card Application Dataset** (`/data/cc-application/`)
* ❌ **Not Compatible** - This dataset contains binary classification labels (`actual_label`, `predicted_label`) and probabilities, not continuous numeric predictions suitable for percentage prediction error calculation.

**Card Fraud Dataset** (`/data/card-fraud/`)
* ❌ **Not Compatible** - This dataset contains binary classification labels (`is_fraud`, `fraud_pred`) and scores, not continuous numeric predictions suitable for percentage prediction error calculation.

***

## Use Cases

* **Loan amount prediction** - Track what proportion of predicted loan amounts are within 10% of actual approved amounts
* **Price prediction** - Monitor how many price predictions are within acceptable error bounds
* **Demand forecasting** - Measure the proportion of demand predictions that are close enough to actual demand
* **Revenue prediction** - Track accuracy of revenue forecasting models using threshold-based metrics
* **Inventory management** - Evaluate how many inventory predictions fall within acceptable error ranges
* **Any regression model** - Monitor threshold-based accuracy for any continuous numeric prediction task where business requirements define acceptable error bounds

***

## Interpreting Core Accuracy at PPE 10% Threshold

* **Higher values (closer to 1.0)** indicate better model performance - more predictions are within the 10% threshold
* **Lower values (closer to 0.0)** indicate worse model performance - fewer predictions are within the acceptable range
* **Perfect accuracy (1.0)** means all predictions are within 10% of actual values (rare in practice)
* **Accuracy of 0.5** means half of predictions are within 10% of actual values
* **Accuracy of 0.0** means no predictions are within the 10% threshold

**Key Considerations:**

* **Scale-dependent** - The 10% threshold is relative to the actual value, so it adapts to different scales automatically
* **Zero values** - Predictions where actual value is zero are excluded from accuracy calculation (division by zero protection)
* **Business context** - The 10% threshold should align with business requirements for acceptable prediction error
* **Complementary metrics** - Consider using this alongside Mean Absolute Error, Mean Absolute Percentage Error, and other regression metrics to get a complete picture of model performance

**Best Practices:**

* Use this metric to track threshold-based accuracy over time
* Compare accuracy across model versions to evaluate improvements
* Segment accuracy by dimensions (region, customer segment, etc.) to identify performance disparities
* Set accuracy thresholds for alerting when performance drops below acceptable levels
* Consider using configurable thresholds if different use cases require different error tolerances
* Monitor trends to detect model degradation or improvement

**Data Requirements:**
* ✅ **Requires raw dataset data** with individual `prediction_col` and `actual_col` values
* ✅ **Works with inference datasets** - as long as they contain both prediction and actual value columns
* ✅ **Works with regression models** - requires continuous numeric predictions and actual values
* ⚠️ **Actual values must be non-zero** - predictions with zero actual values are excluded from accuracy calculation
