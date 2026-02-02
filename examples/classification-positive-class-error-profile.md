

## Overview

The **Positive-Class Error Profile** bucket describes how your classifier makes mistakes on the _positive_ class across the score distribution. It focuses on:

* Where false positives and false negatives concentrate
* How error behavior changes as scores increase
* How much “bad” volume you get when you target a given positive-class segment

This bucket is most natural for **binary classification** but can be applied to **multiclass** by defining a _one-vs-rest_ positive class (e.g., “fraud” vs “not fraud”).

## Metrics

All metrics are defined in terms of the confusion-matrix counts within a segment (e.g., score bin, time bucket):

* `TP` – true positives
* `FP` – false positives
* `FN` – false negatives
* `TN` – true negatives  
  `Total = TP + FP + FN + TN`

**adjusted_false_positive_rate**  
False positive rate on _negative_ cases (optionally smoothed to avoid divide-by-zero):

```text
adjusted_false_positive_rate = FP / (FP + TN)
```

**bad_case_rate**  
Fraction of all cases that are **classified as bad** (prediction = 0):

```text
bad_case_rate = (FN + TN) / (TP + FP + FN + TN)
```

**false_positive_ratio**  
Share of predicted positive cases that are actually negative (how “dirty” your positive bucket is):

```text
false_positive_ratio = FP / (TP + FP)
```

**total_false_positive_rate**  
Fraction of _all_ cases that are false positives:

```text
total_false_positive_rate = FP / (TP + FP + FN + TN)
```

**overprediction_rate**  
Rate at which the model **over-predicts positives** relative to the negative population (conceptually FPR):

```text
overprediction_rate = FP / (FP + TN)
```

**underprediction_rate**  
Rate at which the model **under-predicts positives** (missed positives) relative to actual positives (FNR):

```text
underprediction_rate = FN / (TP + FN)
```

**valid_detection_rate**  
Overall fraction of correctly classified cases (global accuracy):

```text
valid_detection_rate = (TP + TN) / (TP + FP + FN + TN)
```

## Data Requirements

Your dataset must include:

* `{{label_col}}` – ground truth label (0/1 for binary; specific class for multiclass one-vs-rest)
* `{{score_col}}` – predicted probability or score for the positive class
* `{{timestamp_col}}` – event or prediction timestamp
* Optional: `{{weight_col}}` – sample weight (if used)

## Base Metric SQL (Per-Score-Bin Confusion Matrix)

This SQL computes confusion-matrix counts and derived rates per score bin and 5-minute time bucket using a default threshold of 0.5. You can change the threshold if your application uses a different operating point.

```sql
WITH scored AS (
    SELECT
        {{timestamp_col}} AS event_ts,
        {{label_col}}    AS label,
        {{score_col}}    AS score
    FROM {{dataset}}
),
binned AS (
    SELECT
        time_bucket(INTERVAL '5 minutes', event_ts) AS ts,
        width_bucket(score, 0.0, 1.0, 10) AS score_bin,
        label,
        score,
        CASE WHEN score >= 0.5 THEN 1 ELSE 0 END AS pred_label
    FROM scored
)
SELECT
    ts,
    score_bin,
    COUNT(*) AS total,
    SUM(CASE WHEN label = 1 THEN 1 ELSE 0 END) AS positives,
    SUM(CASE WHEN label = 0 THEN 1 ELSE 0 END) AS negatives,

    -- Confusion matrix
    SUM(CASE WHEN pred_label = 1 AND label = 1 THEN 1 ELSE 0 END) AS tp,
    SUM(CASE WHEN pred_label = 1 AND label = 0 THEN 1 ELSE 0 END) AS fp,
    SUM(CASE WHEN pred_label = 0 AND label = 1 THEN 1 ELSE 0 END) AS fn,
    SUM(CASE WHEN pred_label = 0 AND label = 0 THEN 1 ELSE 0 END) AS tn,

    -- Derived rates
    (SUM(CASE WHEN pred_label = 1 AND label = 0 THEN 1 ELSE 0 END))::double precision
        / NULLIF(SUM(CASE WHEN label = 0 THEN 1 ELSE 0 END), 0)      AS adjusted_false_positive_rate,
    (SUM(CASE WHEN pred_label = 0 THEN 1 ELSE 0 END))::double precision
        / NULLIF(COUNT(*), 0)                                       AS bad_case_rate,
    (SUM(CASE WHEN pred_label = 1 AND label = 0 THEN 1 ELSE 0 END))::double precision
        / NULLIF(SUM(CASE WHEN pred_label = 1 THEN 1 ELSE 0 END), 0) AS false_positive_ratio,
    (SUM(CASE WHEN pred_label = 1 AND label = 0 THEN 1 ELSE 0 END))::double precision
        / NULLIF(COUNT(*), 0)                                       AS total_false_positive_rate,
    (SUM(CASE WHEN pred_label = 1 AND label = 0 THEN 1 ELSE 0 END))::double precision
        / NULLIF(SUM(CASE WHEN label = 0 THEN 1 ELSE 0 END), 0)      AS overprediction_rate,
    (SUM(CASE WHEN pred_label = 0 AND label = 1 THEN 1 ELSE 0 END))::double precision
        / NULLIF(SUM(CASE WHEN label = 1 THEN 1 ELSE 0 END), 0)      AS underprediction_rate,
    (SUM(CASE WHEN pred_label = label THEN 1 ELSE 0 END))::double precision
        / NULLIF(COUNT(*), 0)                                       AS valid_detection_rate
FROM binned
GROUP BY ts, score_bin
ORDER BY ts, score_bin;
```

You can register any or all of these derived columns as **reported metrics**.

## Plots (Daily Aggregated)

> Preview Data
>
> for startDate use 2025-11-26T17:54:05.425Z
> for endDate use 2025-12-10T17:54:05.425Z

### Plot 1 — FP & Bad Case Rates Over Time

Uses:

* `adjusted_false_positive_rate`
* `false_positive_ratio`
* `total_false_positive_rate`
* `bad_case_rate`

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
        WHEN metric_name = 'adjusted_false_positive_rate' THEN 'Adjusted False Positive Rate'
        WHEN metric_name = 'false_positive_ratio'         THEN 'False Positive Ratio'
        WHEN metric_name = 'total_false_positive_rate'    THEN 'Total False Positive Rate'
        WHEN metric_name = 'bad_case_rate'                THEN 'Bad Case Rate'
        ELSE metric_name
    END AS friendly_name,
    
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'adjusted_false_positive_rate',
    'false_positive_ratio',
    'total_false_positive_rate',
    'bad_case_rate'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;

```

**What this shows**  
This plot trends multiple notions of “false positives” and “bad outcomes” over time. It lets you see whether the model is:

* Flagging too many negatives as positives (`adjusted_false_positive_rate` / `total_false_positive_rate`)
* Putting too many negatives into the positive bucket (`false_positive_ratio`)
* Over-classifying cases as bad overall (`bad_case_rate`)

**How to interpret it**

* **Spikes** in any FP-related line often correspond to data issues, model regressions, or policy changes.
* A **rising bad_case_rate** without business explanation may mean the model is over-declining / over-rejecting.
* If FP rates increase while business KPIs worsen, this is a strong signal that thresholds or retraining should be reviewed.

***

### Plot 2 — Overprediction vs Underprediction

Uses:

* `overprediction_rate`
* `underprediction_rate`

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
        WHEN metric_name = 'overprediction_rate' THEN 'Overprediction Rate'
        WHEN metric_name = 'underprediction_rate' THEN 'Underprediction Rate'
        ELSE metric_name
    END AS friendly_name,
    
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'overprediction_rate',
    'underprediction_rate'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;

```

**What this shows**  
This plot compares how often the model **over-predicts positives** (FPs) vs **under-predicts positives** (FNs) over time.

**How to interpret it**

* If **overprediction_rate >> underprediction_rate**, the model is aggressively calling positives, likely impacting cost/capacity.
* If **underprediction_rate >> overprediction_rate**, the model is missing many true positives, impacting risk detection.
* Ideally, the ratio between the two aligns with business preferences: in some risk domains, you prefer more FPs; in others, you strongly penalize FNs.

***

### Plot 3 — False Positive Ratio vs Valid Detection Rate

Uses:

* `false_positive_ratio`
* `valid_detection_rate`

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
        WHEN metric_name = 'false_positive_ratio' THEN 'False Positive Ratio'
        WHEN metric_name = 'valid_detection_rate' THEN 'Valid Detection Rate'
        ELSE metric_name
    END AS friendly_name,
    
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'false_positive_ratio',
    'valid_detection_rate'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;

```

**What this shows**  
This plot contrasts **how dirty the positive bucket is** (`false_positive_ratio`) with **overall correctness** (`valid_detection_rate`).

**How to interpret it**

* Days where `false_positive_ratio` is high but `valid_detection_rate` remains flat may mean errors are mostly concentrated in positives rather than negatives.
* If both degrade together, the model is likely struggling broadly (not just in the positive segment).
* You can use this to explain to stakeholders _why_ precision dropped: because the model is trading global accuracy for more aggressive positive predictions.

## Binary vs Multiclass

* **Binary:** use `label ∈ {0,1}` and `score` as the probability `p(y=1 | x)`.
* **Multiclass:** choose a `{{positive_class_value}}` and convert to one-vs-rest:

  ```sql
  CASE WHEN {{label_col}} = '{{positive_class_value}}' THEN 1 ELSE 0 END AS label
  ```

  Use the probability for that class as `score`. Repeat the metric for each class of interest.

## Use Cases

* Risk scoring (fraud, credit, abuse detection)
* Triage models where analysts work the top-scoring cases
* Any binary decisioning system with high cost asymmetry between FP and FN



## Alternative SQL example

```sql
WITH counts AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    SUM(CASE WHEN {{ground_truth}} = 1 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END) AS tp,
    SUM(CASE WHEN {{ground_truth}} = 0 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END) AS fp,
    SUM(CASE WHEN {{ground_truth}} = 0 AND {{prediction}} <  {{threshold}} THEN 1 ELSE 0 END) AS tn,
    SUM(CASE WHEN {{ground_truth}} = 1 AND {{prediction}} <  {{threshold}} THEN 1 ELSE 0 END) AS fn
  FROM {{dataset}}
  GROUP BY 1
),
prepared AS (
  SELECT
    bucket,
    tp::float AS tp,
    fp::float AS fp,
    tn::float AS tn,
    fn::float AS fn,
    (tp + fp + tn + fn)::float AS total,
    (tp + fp)::float          AS predicted_pos,
    (tp + fn)::float          AS actual_pos,
    (fp + tn)::float          AS negatives
  FROM counts
)
SELECT
  bucket AS bucket,

  -- Adjusted False Positive Rate: FP / negatives
  CASE WHEN negatives > 0 THEN fp / negatives ELSE 0 END
    AS adjusted_false_positive_rate,

  -- Bad Case Rate: actual "bad" cases / total
  CASE WHEN total > 0 THEN (tp + fn) / total ELSE 0 END
    AS bad_case_rate,

  -- False Positive Ratio: FP / total
  CASE WHEN total > 0 THEN fp / total ELSE 0 END
    AS false_positive_ratio,

  -- Valid Detection Rate: (TP + TN) / total
  CASE WHEN total > 0 THEN (tp + tn) / total ELSE 0 END
    AS valid_detection_rate,

  -- Overprediction: (predicted_pos - actual_pos) / total, floored at 0
  CASE WHEN total > 0 THEN GREATEST((predicted_pos - actual_pos) / total, 0)
       ELSE 0 END
    AS overprediction_rate,

  -- Underprediction: (actual_pos - predicted_pos) / total, floored at 0
  CASE WHEN total > 0 THEN GREATEST((actual_pos - predicted_pos) / total, 0)
       ELSE 0 END
    AS underprediction_rate,

  -- Total False Positive Rate: global FP / global total
  CASE WHEN SUM(total) OVER () > 0
       THEN SUM(fp) OVER () / SUM(total) OVER ()
       ELSE 0 END
    AS total_false_positive_rate

FROM prepared
ORDER BY bucket;
```
