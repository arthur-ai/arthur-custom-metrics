## Overview

The **Negative Predictive Value** (NPV) metric measures the proportion of negative predictions that are actually negative. It is the negative-class counterpart to **Precision** (Positive Predictive Value).

While Precision answers "of everything I flagged, how much is real?", NPV answers "of everything I let through, how much is truly safe?"

This is critical in domains where **missing a positive is costly** — if NPV is low, too many actual positives are slipping through the negative bucket undetected.

This metric is implemented for **binary classification**. Multiclass models can be evaluated via one-vs-rest strategies by defining separate metrics per class.

It produces:

* **npv** — Negative Predictive Value: TN / (TN + FN)
* **specificity** — True Negative Rate: TN / (TN + FP), a natural companion that measures how well the model identifies negatives overall

## Metrics

All metrics are computed from the confusion matrix at a user-supplied decision threshold.

**npv**
Proportion of negative predictions that are truly negative:

```text
npv = TN / (TN + FN)
```

* High NPV means when the model says "negative", it is usually right.
* Low NPV means many actual positives are being misclassified as negative (leakage).

**specificity**
Proportion of actual negatives that are correctly identified (True Negative Rate):

```text
specificity = TN / (TN + FP)
```

* High specificity means the model rarely flags a true negative as positive.
* Included as a natural companion — both metrics focus on the model's negative-class behavior.

## Data Requirements

* `{{ground_truth}}` – binary ground truth (0 for negative, 1 for positive)
* `{{prediction}}` – probability or score for the positive class (continuous)
* `{{threshold}}` – literal: decision threshold (e.g., 0.5). Scores >= threshold are classified as positive.
* `{{timestamp_col}}` – event timestamp

## Base Metric SQL

This SQL computes the confusion matrix at a fixed threshold, then derives NPV and Specificity per time bucket.

```sql
WITH counts AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    SUM(CASE WHEN {{ground_truth}} = 1 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END)::float AS tp,
    SUM(CASE WHEN {{ground_truth}} = 0 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END)::float AS fp,
    SUM(CASE WHEN {{ground_truth}} = 0 AND {{prediction}} <  {{threshold}} THEN 1 ELSE 0 END)::float AS tn,
    SUM(CASE WHEN {{ground_truth}} = 1 AND {{prediction}} <  {{threshold}} THEN 1 ELSE 0 END)::float AS fn
  FROM
    {{dataset}}
  GROUP BY
    1
)

SELECT
  bucket AS bucket,

  -- Negative Predictive Value: TN / (TN + FN)
  CASE
    WHEN (tn + fn) > 0 THEN tn / (tn + fn)
    ELSE NULL
  END AS npv,

  -- Specificity (True Negative Rate): TN / (TN + FP)
  CASE
    WHEN (tn + fp) > 0 THEN tn / (tn + fp)
    ELSE NULL
  END AS specificity

FROM
  counts
ORDER BY
  bucket;
```

**What this query returns**

* `bucket` — timestamp bucket (1 day)
* `npv` — Negative Predictive Value
* `specificity` — True Negative Rate (Specificity)

## Plots

See the [charts](../../charts/binary-classification/) folder for visualization examples:

* [Plot 1: NPV Over Time](../../charts/binary-classification/npv-over-time.md)
* [Plot 2: NPV vs Precision](../../charts/binary-classification/npv-vs-precision.md)

---

### Plot 1 — NPV Over Time

Uses:

* `npv`
* `specificity`

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
        WHEN metric_name = 'npv'         THEN 'Negative Predictive Value'
        WHEN metric_name = 'specificity' THEN 'Specificity (TNR)'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'npv',
    'specificity'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**
This plot tracks both NPV and Specificity over time, providing a complete view of the model's negative-class behavior.

**How to interpret it**

* **NPV dropping** means more actual positives are leaking into the negative bucket — the model is missing more true positives.
* **Specificity dropping** means the model is incorrectly flagging more true negatives as positive — increased false alarm rate.
* When both drop simultaneously, the model is degrading broadly on negative-class handling.
* NPV is particularly sensitive to **prevalence**: when positives are rare, NPV can appear high even with poor recall. Always pair with recall for a complete picture.

***

### Plot 2 — NPV vs Precision

Uses:

* `npv`
* `precision` (from the Detection & Acceptance Profile metric)

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
        WHEN metric_name = 'npv'       THEN 'NPV (Negative Predictive Value)'
        WHEN metric_name = 'precision' THEN 'Precision (PPV)'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'npv',
    'precision'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**
This plot overlays NPV and Precision (PPV) to show the predictive quality of both decision buckets — "how trustworthy are the positives?" vs "how trustworthy are the negatives?"

**How to interpret it**

* **Both high**: The model's predictions are reliable in both directions.
* **Precision high, NPV low**: The model is conservative — what it flags is usually right, but it misses many positives (they leak into the negative bucket).
* **Precision low, NPV high**: The model is aggressive — it catches most positives but also flags many negatives incorrectly.
* This trade-off view helps calibrate the decision threshold for the right balance.

## Interpretation Guide

| NPV Range  | Interpretation |
|------------|----------------|
| 0.95 – 1.0 | Excellent — very few positives leak through as negatives |
| 0.90 – 0.95 | Good — acceptable for most applications |
| 0.80 – 0.90 | Moderate — meaningful leakage, investigate FN patterns |
| < 0.80     | Poor — significant positive leakage, threshold or model adjustment needed |

**Important**: NPV is heavily influenced by **prevalence** (the proportion of positives). When positives are rare (e.g., 1% fraud rate), NPV can be > 0.99 even with a mediocre model simply because most samples are truly negative. Always interpret NPV alongside Recall to get the full picture.

## Relationship to Other Metrics

| This Metric | Counterpart | Relationship |
|-------------|-------------|--------------|
| **NPV** = TN / (TN + FN) | **Precision (PPV)** = TP / (TP + FP) | NPV is for the negative bucket; Precision is for the positive bucket |
| **Specificity** = TN / (TN + FP) | **Recall (Sensitivity)** = TP / (TP + FN) | Specificity is "recall for negatives"; Recall is "recall for positives" |

## Use Cases

* **Medical screening** — when a patient tests negative, how confident are we that they are truly disease-free?
* **Fraud detection** — of transactions allowed through (not flagged), what fraction are truly legitimate?
* **Credit decisioning** — of applications approved (predicted non-default), how many will actually repay?
* **Content moderation** — of content allowed to publish (not flagged), how much is truly safe?
* **Manufacturing QA** — of items passed by the inspection model, how many are truly defect-free?

## Binary vs Multiclass

* **Binary:** use the natural positive class and its probability as `prediction`.
* **Multiclass:** for each class `c` of interest:
  * Define ground truth as 1 when the true label is `c`, else 0.
  * Use the model's predicted probability for class `c` as `prediction`.
  * Compute NPV per class for a one-vs-rest evaluation.
