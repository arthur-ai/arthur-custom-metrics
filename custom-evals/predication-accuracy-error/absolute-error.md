## Overview

The **Absolute Error** metric measures the absolute difference between a predicted value and the actual value for each individual record in regression models. Unlike Mean Absolute Error (MAE), which is an average, Absolute Error captures the per-record error magnitude.

This metric is useful for:

* Tracking the distribution of prediction errors over time
* Understanding individual prediction accuracy, not just averages
* Monitoring error patterns and outliers
* Computing quantiles, percentiles, and other distribution statistics
* Identifying records with high error magnitudes

**Important:** This metric requires **raw dataset data** (individual predictions and actual values), not pre-aggregated metrics. You cannot compute per-record absolute error from already-aggregated data.

The metric stores absolute error values as a **sketch** (probabilistic distribution summary), allowing you to query quantiles, min, max, and distribution statistics while maintaining efficient storage.

***

## Metrics

**absolute_error**  
The absolute difference between predicted and actual values for each record:

```text
absolute_error = |predicted_value - actual_value|
```

This is computed per record and stored as a sketch distribution, allowing you to query:
* Individual error values (via sketch functions)
* Quantiles (median, 95th percentile, etc.)
* Min/max absolute errors
* Distribution histograms

***

## Data Requirements

Your dataset must include:

* `{{timestamp_col}}` – event or prediction timestamp
* `{{prediction_col}}` – predicted value (continuous numeric)
* `{{actual_col}}` – ground truth/actual value (continuous numeric)

Both prediction and actual columns must be continuous numeric values (float or integer types).

***

## Base Metric SQL

This SQL computes absolute error per record and stores it as a sketch distribution. For sketch metrics, Arthur handles time bucketing automatically, so we output per-record absolute error values:

```sql
SELECT
    {{timestamp_col}} AS ts,
    ABS({{prediction_col}} - {{actual_col}}) AS absolute_error
FROM {{dataset}}
WHERE {{prediction_col}} IS NOT NULL
  AND {{actual_col}} IS NOT NULL;
```

**What this query does:**

* `ABS({{prediction_col}} - {{actual_col}})` computes the absolute difference for each individual record
* Outputs per-record absolute error values (not aggregated)
* Arthur automatically buckets these into 5-minute intervals when storing as a sketch metric
* Filters out NULL values in prediction or actual columns

**Note:** This requires access to the **raw dataset** with individual prediction and actual values. You cannot compute this from pre-aggregated metrics.

***

## Step 1: Fill Basic Information

When creating the custom metric in the Arthur UI:

1. **Name**:  
   `Absolute Error`

2. **Description**:  
   `The absolute difference between a predicted value and the actual value for each record. Stored as a sketch distribution to enable quantile and distribution queries.`

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

This links the metric definition to whichever **Arthur dataset** (inference or batch) you want to compute absolute error on.

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

### Reported Metric 1 — Absolute Error (Sketch)

1. **Metric Name:** `absolute_error`
2. **Description:** `Absolute error (|predicted - actual|) for each record, stored as a sketch distribution.`
3. **Value Column:** `absolute_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Sketch`

This tells Arthur to store the absolute error values as a sketch distribution. Sketch metrics allow you to query quantiles, min, max, and distribution statistics while maintaining efficient storage.

***

## Plots (Daily Aggregated)

> Preview Data
>
> for startDate use 2026-01-02T00:00:00.000Z
> for endDate use 2026-02-01T23:59:59.999Z
>
> **Note:** Ensure your date range overlaps with your actual data. Your data spans from 2026-01-02 to 2026-02-01. If the dashboard date range doesn't overlap with this, the query will return no results.

### Plot 1 — Absolute Error Distribution Over Time

This plot shows the actual absolute error values over time by displaying multiple quantiles (min, p25, median, p75, p95, max) aggregated to daily buckets. This reveals the full distribution of error values, not just the median.

```sql
SELECT 
    time_bucket(INTERVAL '1 day', timestamp) AS time_bucket_1d,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.0) AS min_absolute_error,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.25) AS p25_absolute_error,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.5) AS median_absolute_error,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.75) AS p75_absolute_error,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.95) AS p95_absolute_error,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 1.0) AS max_absolute_error
FROM metrics_sketch_latest_version
WHERE metric_name = 'absolute_error'
    [[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

**Troubleshooting:** If this query returns no data:
1. **Check date range:** Ensure `{{dateStart}}` and `{{dateEnd}}` overlap with your actual data range. Your data exists from 2026-01-02 to 2026-02-01. Try removing the date filter temporarily to test: remove the line `[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]`
2. Verify the custom metric `absolute_error` has been created and configured for your model
3. Ensure a metrics calculation job has run successfully
4. Confirm the metric name matches exactly: `absolute_error`

**What this shows**  
This plot displays the actual distribution of absolute error values over time, showing:

* **Min/Max** - The actual minimum and maximum error values in each time bucket
* **25th/75th Percentiles** - The interquartile range showing where 50% of errors fall
* **Median** - The middle value of the error distribution
* **95th Percentile** - The value below which 95% of errors fall (identifies worst-case scenarios)

**How to interpret it**

* **Widening gap between min and max** indicates increasing variability in prediction accuracy
* **Rising p95 or max values** show that worst-case errors are getting worse, even if median stays stable
* **Narrowing distribution** (min, p25, median, p75, p95 all close together) suggests more consistent predictions
* **Spikes in max/p95** often correspond to data quality issues, edge cases, or model failures on specific records
* **Increasing trend across all quantiles** indicates overall model degradation
* **Stable distribution** suggests consistent model performance across all error magnitudes

***

### Plot 2 — Absolute Error Distribution Histogram

This plot shows the distribution of absolute error values as a histogram, allowing you to see how errors are distributed across different ranges.

```sql
WITH merged AS (
    SELECT 
        kll_float_sketch_get_pmf(
            kll_float_sketch_merge(value),
            ARRAY[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        ) AS pmf,
        kll_float_sketch_get_n(kll_float_sketch_merge(value)) AS total_count
    FROM metrics_sketch_latest_version
    WHERE metric_name = 'absolute_error'
        [[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
)
SELECT 
    ROUND(((ordinality - 1) / 10.0), 1)::VARCHAR AS error_range,
    val * merged.total_count AS record_count
FROM merged,
     unnest(merged.pmf) WITH ordinality AS val
ORDER BY ordinality;
```

**Note:** The PMF (probability mass function) approach above uses normalized percentiles (0.0-1.0). For actual error value ranges, you'll need to scale based on your error range. Alternatively, you can query specific quantiles:

```sql
SELECT 
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.0) AS p0,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.25) AS p25,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.5) AS p50,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.75) AS p75,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.95) AS p95,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 1.0) AS p100
FROM metrics_sketch_latest_version
WHERE metric_name = 'absolute_error'
    [[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']];
```

**What this shows**  
This plot helps you understand:

* The distribution shape of absolute errors
* Whether errors are concentrated in certain ranges
* Presence of outliers or long tails
* Overall error distribution characteristics

**How to interpret it**

* **Concentrated distribution** suggests consistent error magnitudes
* **Wide distribution** indicates high variability in prediction accuracy
* **Long tail** suggests some records have very high errors (outliers)
* Use this to identify error patterns and set appropriate thresholds

***

## Alternative SQL Examples

### Alternative 1: With Dimension Support

If you want to track absolute error by dimension (e.g., region, segment), you can add dimension columns:

```sql
SELECT
    {{timestamp_col}} AS ts,
    {{dimension_col}} AS dimension_value,
    ABS({{prediction_col}} - {{actual_col}}) AS absolute_error
FROM {{dataset}}
WHERE {{prediction_col}} IS NOT NULL
  AND {{actual_col}} IS NOT NULL;
```

Then configure `dimension_value` as a dimension column in your reported metric to enable segmentation in dashboards. This allows you to query absolute error distributions separately for each dimension value (e.g., by region).

**Querying by dimension:**
```sql
SELECT 
    time_bucket(INTERVAL '1 day', timestamp) AS bucket,
    dimensions ->> 'dimension_value' AS region,
    kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.5) AS median_absolute_error
FROM metrics_sketch_latest_version
WHERE metric_name = 'absolute_error'
    [[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
GROUP BY bucket, region
ORDER BY bucket, region;
```

***

## Model Compatibility

### Compatible Datasets

This metric is compatible with **regression models** that have continuous numeric predictions and ground truth values.

#### Loan Amount Prediction Dataset

**Location:** `/data/loan-amount-prediction/`

**Compatibility:** ✅ **Fully Compatible**

**Relevant Columns:**
* `timestamp` - Timestamp column for time bucketing
* `predicted_loan_amount` - Continuous numeric prediction column (float64, range: $5,000-$500,000)
* `actual_loan_amount` - Continuous numeric ground truth column (float64, range: $5,000-$500,000)

**Configuration:**
* `timestamp_col`: `timestamp`
* `prediction_col`: `predicted_loan_amount`
* `actual_col`: `actual_loan_amount`

**Dataset Description:**  
This dataset simulates a loan amount prediction system where a model predicts the approved loan amount based on applicant features. Both predicted and actual loan amounts are continuous numeric values, making it ideal for absolute error computation.

**Additional Features:**
* Geographic regions (`region`) - can be used for dimension-based error analysis
* Loan application features (credit score, income, age, etc.)
* Date partitioning for efficient querying

#### Incompatible Datasets

**Credit Card Application Dataset** (`/data/cc-application/`)
* ❌ **Not Compatible** - This dataset contains binary classification labels (`actual_label`, `predicted_label`) and probabilities, not continuous numeric predictions suitable for absolute error.

**Card Fraud Dataset** (`/data/card-fraud/`)
* ❌ **Not Compatible** - This dataset contains binary classification labels (`is_fraud`, `fraud_pred`) and scores, not continuous numeric predictions suitable for absolute error.

***

## Use Cases

* **Loan amount prediction** - Track how accurately the model predicts approved loan amounts
* **Price prediction** - Monitor prediction accuracy for pricing models
* **Demand forecasting** - Measure error in demand prediction models
* **Revenue prediction** - Track accuracy of revenue forecasting models
* **Any regression model** - Monitor prediction accuracy for any continuous numeric prediction task

***

## Interpreting Absolute Error

* **Lower values** indicate better prediction accuracy for individual records
* **Higher values** indicate larger prediction errors for individual records
* **Zero** means perfect prediction for that record (rare in practice)
* **Scale-dependent** - The magnitude of absolute error depends on the scale of your target variable (e.g., errors in thousands for loan amounts vs. errors in dollars for prices)

**Key Differences from Mean Absolute Error:**
* **Absolute Error** = per-record error values (stored as sketch distribution)
* **Mean Absolute Error (MAE)** = average of absolute errors (single aggregated value)
* With Absolute Error, you can query quantiles, distributions, and individual error patterns
* With MAE, you only get the average, losing information about error distribution

**Best Practices:**
* Use sketch queries to understand error distributions, not just averages
* Query quantiles (median, 95th percentile) to understand typical vs. worst-case errors
* Compare absolute error values relative to the scale of your predictions
* Monitor trends over time using median or other quantiles
* Segment by dimensions (region, customer segment, etc.) to identify where errors are highest
* Use the distribution histogram to identify error patterns and outliers

**Data Requirements:**
* ⚠️ **You need raw dataset data** with individual `prediction_col` and `actual_col` values
* ❌ **Cannot compute from aggregated metrics** - you cannot derive per-record absolute error from pre-aggregated data
* ✅ **Works with inference datasets** - as long as they contain both prediction and actual value columns