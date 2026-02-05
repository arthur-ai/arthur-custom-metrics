## Overview

The **Accuracy** metric measures the proportion of correct predictions (true positives and true negatives) among all predictions. It is a fundamental classification metric that provides an overall measure of model performance.

This metric is useful for:

* Tracking overall model correctness over time
* Understanding the proportion of predictions that match ground truth
* Monitoring model performance degradation
* Comparing model versions
* Providing a simple, interpretable performance metric

**Important:** This metric requires **classification models** with binary or multiclass labels. It compares predicted labels to actual labels to determine correctness.

The metric stores accuracy values as a **numeric** metric, aggregated into 5-minute time buckets.

***

## Metrics

**accuracy**  
The proportion of correct predictions among all predictions:

```text
accuracy = (TP + TN) / (TP + FP + FN + TN)
```

Where:
* `TP` = True Positives (correctly predicted positive cases)
* `TN` = True Negatives (correctly predicted negative cases)
* `FP` = False Positives (incorrectly predicted as positive)
* `FN` = False Negatives (incorrectly predicted as negative)

This is computed per time bucket and stored as a numeric metric, allowing you to:
* Track accuracy over time
* Query accuracy values for specific time ranges
* Compare accuracy across different dimensions

***

## Data Requirements

Your dataset must include:

* `{{timestamp_col}}` – event or prediction timestamp
* `{{prediction_col}}` – predicted label (binary: 0/1, or multiclass: class names/IDs)
* `{{actual_col}}` – ground truth/actual label (binary: 0/1, or multiclass: class names/IDs)

Both prediction and actual columns must be categorical values (binary or multiclass labels). The values must match exactly for accuracy calculation (e.g., if actual is 1 and prediction is 1, it's correct).

***

## Base Metric SQL

This SQL computes accuracy per 5-minute time bucket by counting correct predictions (where prediction equals actual) and dividing by total predictions:

```sql
SELECT
    time_bucket(INTERVAL '5 minutes', {{timestamp_col}}) AS ts,
    COUNT(*) AS total_predictions,
    SUM(CASE WHEN {{prediction_col}} = {{actual_col}} THEN 1 ELSE 0 END) AS correct_predictions,
    CASE 
        WHEN COUNT(*) > 0 
        THEN (SUM(CASE WHEN {{prediction_col}} = {{actual_col}} THEN 1 ELSE 0 END))::double precision / COUNT(*)
        ELSE 0.0
    END AS accuracy
FROM {{dataset}}
WHERE {{prediction_col}} IS NOT NULL
  AND {{actual_col}} IS NOT NULL
GROUP BY ts
ORDER BY ts;
```

**What this query does:**

* `time_bucket(INTERVAL '5 minutes', {{timestamp_col}})` aggregates records into 5-minute time buckets
* `COUNT(*)` counts total predictions in each bucket
* `SUM(CASE WHEN {{prediction_col}} = {{actual_col}} THEN 1 ELSE 0 END)` counts correct predictions (where prediction matches actual)
* `accuracy` divides correct predictions by total predictions, with divide-by-zero protection
* Filters out NULL values in prediction or actual columns

**Note:** This requires access to the **raw dataset** with individual prediction and actual label values.

***

## Step 1: Fill Basic Information

When creating the custom metric in the Arthur UI:

1. **Name**:  
   `Accuracy`

2. **Description**:  
   `The proportion of correct predictions (true positives and true negatives) among all predictions.`

3. **Model Problem Type**:  
   `binary_classification`, `multiclass_classification` (optional, but recommended to help users discover this metric)

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
3. **Description:** `Column containing the model's predicted labels (binary or multiclass).`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag hints (optional):** `prediction`
8. **Allowed Column Types (optional):** `int`, `str`, `categorical`

This should point to your model's **prediction column** (binary: 0/1, or multiclass: class names/IDs).

***

### Argument 4 — Actual Column

1. **Parameter Key:** `actual_col`
2. **Friendly Name:** `Actual Column`
3. **Description:** `Column containing the ground truth/actual labels (binary or multiclass).`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag hints (optional):** `ground_truth`, `label`
8. **Allowed Column Types (optional):** `int`, `str`, `categorical`

This should point to your **ground truth/actual label column** (binary: 0/1, or multiclass: class names/IDs).

***

## Step 3: Configure the Reported Metrics

### Reported Metric 1 — Accuracy (Numeric)

1. **Metric Name:** `accuracy`
2. **Description:** `The proportion of correct predictions (true positives and true negatives) among all predictions.`
3. **Value Column:** `accuracy`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

This tells Arthur to store the accuracy values as a numeric metric. Numeric metrics allow you to query values over time and aggregate them into larger time windows.

***

## Plots (Daily Aggregated)

> Preview Data
>
> for startDate use 2025-11-03T00:00:00.000Z
> for endDate use 2026-02-01T23:59:59.999Z
>
> **Note:** Ensure your date range overlaps with your actual data. Your data spans from 2025-11-03 to 2026-02-01. If the dashboard date range doesn't overlap with this, the query will return no results.

### Plot 1 — Accuracy Over Time

This plot shows accuracy values over time aggregated to daily buckets. This reveals how model accuracy changes over time and helps identify performance degradation or improvement.

```sql
SELECT 
    time_bucket_gapfill(
        INTERVAL '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,
    COALESCE(AVG(value), 0.0) AS accuracy
FROM metrics_numeric_latest_version
WHERE metric_name = 'accuracy'
    [[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

**Troubleshooting:** If this query returns no data:
1. **Check date range:** Ensure `{{dateStart}}` and `{{dateEnd}}` overlap with your actual data range. Your data exists from 2025-11-03 to 2026-02-01. Try removing the date filter temporarily to test: remove the line `[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]`
2. Verify the custom metric `accuracy` has been created and configured for your model
3. Ensure a metrics calculation job has run successfully
4. Confirm the metric name matches exactly: `accuracy`

**What this shows**  
This plot displays accuracy values over time, showing:

* **Accuracy trends** - Whether accuracy is improving, degrading, or stable
* **Performance stability** - How consistent the model's accuracy is over time
* **Anomalies** - Sudden drops or spikes in accuracy that may indicate data quality issues or model problems

**How to interpret it**

* **High accuracy (close to 1.0)** indicates the model is making mostly correct predictions
* **Low accuracy (close to 0.0)** indicates the model is making mostly incorrect predictions
* **Stable accuracy** suggests consistent model performance
* **Declining accuracy** may indicate model degradation, data drift, or changing conditions
* **Spikes or drops** often correspond to data quality issues, model updates, or edge cases
* **Accuracy of 0.5** for binary classification suggests random performance (no better than chance)

***

### Plot 2 — Accuracy with Confidence Intervals

This plot shows accuracy over time with confidence intervals, providing a more nuanced view of model performance by accounting for sample size variability.

```sql
WITH daily_accuracy AS (
    SELECT 
        time_bucket(INTERVAL '1 day', timestamp) AS bucket,
        AVG(value) AS avg_accuracy,
        COUNT(*) AS sample_count,
        STDDEV(value) AS stddev_accuracy
    FROM metrics_numeric_latest_version
    WHERE metric_name = 'accuracy'
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
    COALESCE(avg_accuracy, 0.0) AS accuracy,
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
    SUM(CASE WHEN {{prediction_col}} = {{actual_col}} THEN 1 ELSE 0 END) AS correct_predictions,
    CASE 
        WHEN COUNT(*) > 0 
        THEN (SUM(CASE WHEN {{prediction_col}} = {{actual_col}} THEN 1 ELSE 0 END))::double precision / COUNT(*)
        ELSE 0.0
    END AS accuracy
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
    AVG(value) AS accuracy
FROM metrics_numeric_latest_version
WHERE metric_name = 'accuracy'
    [[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
GROUP BY bucket, region
ORDER BY bucket, region;
```

***

### Alternative 2: Multiclass Accuracy

For multiclass classification, the same SQL works as long as the prediction and actual columns contain matching class values:

```sql
SELECT
    time_bucket(INTERVAL '5 minutes', {{timestamp_col}}) AS ts,
    COUNT(*) AS total_predictions,
    SUM(CASE WHEN {{prediction_col}} = {{actual_col}} THEN 1 ELSE 0 END) AS correct_predictions,
    CASE 
        WHEN COUNT(*) > 0 
        THEN (SUM(CASE WHEN {{prediction_col}} = {{actual_col}} THEN 1 ELSE 0 END))::double precision / COUNT(*)
        ELSE 0.0
    END AS accuracy
FROM {{dataset}}
WHERE {{prediction_col}} IS NOT NULL
  AND {{actual_col}} IS NOT NULL
GROUP BY ts
ORDER BY ts;
```

This works for any number of classes as long as the prediction and actual values match exactly (e.g., "class_A" = "class_A" is correct, "class_A" = "class_B" is incorrect).

***

## Model Compatibility

### Compatible Datasets

This metric is compatible with **classification models** (binary or multiclass) that have categorical prediction and ground truth labels.

#### Card Fraud Dataset

**Location:** `/data/card-fraud/`

**Compatibility:** ✅ **Fully Compatible**

**Relevant Columns:**
* `timestamp` - Timestamp column for time bucketing (ISO 8601 string format)
* `fraud_pred` - Binary prediction column (0=legitimate, 1=fraud)
* `is_fraud` - Binary ground truth column (0=legitimate, 1=fraud)

**Configuration:**
* `timestamp_col`: `timestamp`
* `prediction_col`: `fraud_pred`
* `actual_col`: `is_fraud`

**Dataset Description:**  
This dataset simulates a credit card fraud detection system where a model predicts whether transactions are fraudulent. Both predicted and actual values are binary (0/1), making it ideal for accuracy computation.

**Additional Features:**
* Geographic regions (`region`) - can be used for dimension-based accuracy analysis
* Customer segments (`customer_segment`) - can be used for dimension-based accuracy analysis
* Transaction channels (`channel`) - can be used for dimension-based accuracy analysis
* Fraud probability scores (`fraud_score`) - continuous 0-1 probability (not used for accuracy, but available for other metrics)

#### Credit Card Application Dataset

**Location:** `/data/cc-application/`

**Compatibility:** ✅ **Fully Compatible**

**Relevant Columns:**
* `timestamp` - Timestamp column for time bucketing (timestamp with UTC timezone)
* `predicted_label` - Binary prediction column (0=Rejected, 1=Approved)
* `actual_label` - Binary ground truth column (0=Rejected, 1=Approved)

**Configuration:**
* `timestamp_col`: `timestamp`
* `prediction_col`: `predicted_label`
* `actual_col`: `actual_label`

**Dataset Description:**  
This dataset simulates a credit card application approval system where a model predicts whether applications should be approved or rejected. Both predicted and actual values are binary (0/1), making it ideal for accuracy computation.

**Additional Features:**
* Geographic regions (`region`) - can be used for dimension-based accuracy analysis
* Predicted probabilities (`predicted_probability`) - continuous 0-1 probability (not used for accuracy, but available for other metrics)
* Credit risk features (credit score, income, age, etc.)

#### Incompatible Datasets

**Loan Amount Prediction Dataset** (`/data/loan-amount-prediction/`)
* ❌ **Not Compatible** - This dataset contains continuous numeric predictions (`predicted_loan_amount`) and actual values (`actual_loan_amount`), not categorical labels suitable for accuracy. This is a regression dataset, not a classification dataset.

***

## Use Cases

* **Fraud detection** - Track how accurately the model identifies fraudulent transactions
* **Credit approval** - Monitor accuracy of approval/rejection decisions
* **Spam detection** - Measure accuracy of spam vs. legitimate email classification
* **Medical diagnosis** - Track accuracy of disease detection or diagnosis
* **Image classification** - Monitor accuracy of image classification models
* **Sentiment analysis** - Track accuracy of positive/negative sentiment classification
* **Any binary or multiclass classification model** - Monitor overall correctness for any classification task

***

## Interpreting Accuracy

* **Higher values (closer to 1.0)** indicate better model performance
* **Lower values (closer to 0.0)** indicate worse model performance
* **Perfect accuracy (1.0)** means all predictions are correct (rare in practice)
* **Random performance (0.5 for binary classification)** means the model performs no better than chance
* **Worse than random (<0.5 for binary classification)** indicates the model is systematically making incorrect predictions

**Key Considerations:**

* **Class imbalance** - Accuracy can be misleading when classes are imbalanced. For example, if 95% of transactions are legitimate, a model that always predicts "legitimate" will have 95% accuracy but will miss all fraud cases.
* **Cost asymmetry** - Accuracy treats all errors equally, but in practice, false positives and false negatives may have very different costs (e.g., missing fraud vs. blocking legitimate transactions).
* **Complementary metrics** - Consider using accuracy alongside precision, recall, F1 score, and confusion matrix metrics to get a complete picture of model performance.

**Best Practices:**

* Use accuracy as a high-level performance indicator, but don't rely on it alone
* For imbalanced datasets, consider precision, recall, and F1 score
* Monitor accuracy trends over time to detect model degradation
* Segment accuracy by dimensions (region, customer segment, etc.) to identify performance disparities
* Compare accuracy across model versions to evaluate improvements
* Set accuracy thresholds for alerting when performance drops below acceptable levels

**Data Requirements:**
* ✅ **Requires raw dataset data** with individual `prediction_col` and `actual_col` values
* ✅ **Works with inference datasets** - as long as they contain both prediction and actual label columns
* ✅ **Works with binary and multiclass classification** - as long as prediction and actual values match exactly
