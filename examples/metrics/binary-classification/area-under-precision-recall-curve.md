## Overview

The **Area Under Precision-Recall Curve** (AUPRC) measures how well your model balances precision and recall across all possible decision thresholds on the positive-class score.

Unlike AUC-ROC, which can appear optimistic on imbalanced datasets, AUPRC focuses solely on the positive class and is especially informative when positives are rare (e.g., fraud, disease, default).

This metric is implemented for **binary classification**. Multiclass models can be evaluated via one-vs-rest strategies by defining separate metrics per class.

It produces:

* **auprc** — Area under the precision-recall curve (trapezoidal rule)
* **average_precision** — Step-function approximation (equivalent to sklearn's `average_precision_score`)

## Metrics

All metrics are derived from (`recall`, `precision`) pairs computed across the full range of score thresholds.

**auprc**
Area under the precision-recall curve, approximated via the trapezoidal rule:

For adjacent PR points `(recall_i, precision_i)` and `(recall_{i+1}, precision_{i+1})`:

```text
ΔAUPRC_i = (recall_{i+1} − recall_i) × (precision_{i+1} + precision_i) / 2
auprc = Σ_i ΔAUPRC_i
```

**average_precision**
Step-function approximation that weights each precision value by the change in recall:

```text
average_precision = Σ_n (recall_n − recall_{n−1}) × precision_n
```

This matches the computation in sklearn's `average_precision_score` and is often used interchangeably with AUPRC.

## Data Requirements

* `{{label_col}}` – binary ground truth (0 for negative, 1 for positive)
* `{{score_col}}` – probability or score for the positive class (continuous)
* `{{timestamp_col}}` – event timestamp

## Base Metric SQL

This SQL computes AUPRC and Average Precision for binary classification. It builds a precision-recall curve by sweeping thresholds from high to low, computing precision and recall at each point, then derives the area metrics.

```sql
WITH scored AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    {{ground_truth}} AS label,
    {{score_col}}     AS score
  FROM
    {{dataset}}
),

-- Total positives per bucket
bucket_totals AS (
  SELECT
    bucket,
    SUM(CASE WHEN label = 1 THEN 1 ELSE 0 END)::float AS num_pos
  FROM
    scored
  GROUP BY
    bucket
),

-- Cumulative TP and total predicted-positive as we sweep thresholds high → low
pr_raw AS (
  SELECT
    s.bucket,
    s.score,
    SUM(CASE WHEN s.label = 1 THEN 1 ELSE 0 END)
      OVER (
        PARTITION BY s.bucket
        ORDER BY s.score DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
      )::float AS cum_tp,
    COUNT(*)
      OVER (
        PARTITION BY s.bucket
        ORDER BY s.score DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
      )::float AS cum_predicted
  FROM
    scored s
),

-- Turn cumulative counts into precision/recall points
pr_points AS (
  SELECT DISTINCT
    r.bucket,
    r.score AS threshold,
    CASE WHEN r.cum_predicted > 0 THEN r.cum_tp / r.cum_predicted ELSE 1 END AS precision,
    CASE WHEN bt.num_pos > 0 THEN r.cum_tp / bt.num_pos ELSE 0 END AS recall
  FROM
    pr_raw r
    JOIN bucket_totals bt USING (bucket)
),

-- Add (recall=0, precision=1) starting endpoint
pr_with_endpoints AS (
  SELECT
    bt.bucket,
    0.0::float AS recall,
    1.0::float AS precision
  FROM
    bucket_totals bt

  UNION ALL

  SELECT
    bucket,
    recall,
    precision
  FROM
    pr_points
),

-- Order by recall and keep previous point for trapezoids
pr_ordered AS (
  SELECT
    bucket,
    recall,
    precision,
    LAG(recall) OVER (PARTITION BY bucket ORDER BY recall, precision DESC) AS prev_recall,
    LAG(precision) OVER (PARTITION BY bucket ORDER BY recall, precision DESC) AS prev_precision
  FROM
    pr_with_endpoints
),

-- AUPRC via trapezoidal rule
auprc_per_bucket AS (
  SELECT
    bucket,
    COALESCE(
      SUM(
        CASE
          WHEN prev_recall IS NULL THEN 0
          ELSE (recall - prev_recall) * (precision + prev_precision) / 2.0
        END
      ),
      0
    ) AS auprc
  FROM
    pr_ordered
  GROUP BY
    bucket
),

-- Average Precision via step-function: Σ (R_n − R_{n−1}) × P_n
ap_ordered AS (
  SELECT
    bucket,
    recall,
    precision,
    LAG(recall, 1, 0.0) OVER (PARTITION BY bucket ORDER BY recall, precision DESC) AS prev_recall
  FROM
    pr_with_endpoints
),

ap_per_bucket AS (
  SELECT
    bucket,
    COALESCE(
      SUM((recall - prev_recall) * precision),
      0
    ) AS average_precision
  FROM
    ap_ordered
  GROUP BY
    bucket
)

SELECT
  a.bucket            AS bucket,
  a.auprc             AS auprc,
  p.average_precision AS average_precision
FROM
  auprc_per_bucket a
  JOIN ap_per_bucket p USING (bucket)
ORDER BY
  a.bucket;
```

**What this query returns**

* `bucket` — timestamp bucket (1 day)
* `auprc` — Area under the precision-recall curve (trapezoidal)
* `average_precision` — Step-function approximation of AUPRC

## Plots

See the [charts](../../charts/binary-classification/) folder for visualization examples:

* [Plot 1: AUPRC Over Time](../../charts/binary-classification/auprc-over-time.md)
* [Plot 2: AUPRC vs AUC-ROC Comparison](../../charts/binary-classification/auprc-vs-auc-roc.md)

---

### Plot 1 — AUPRC Over Time

Uses:

* `auprc`
* `average_precision`

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
        WHEN metric_name = 'auprc' THEN 'AUPRC (Trapezoidal)'
        WHEN metric_name = 'average_precision' THEN 'Average Precision'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'auprc',
    'average_precision'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**
This plot tracks both AUPRC variants over time, letting you monitor how well the model identifies positives without generating excessive false positives.

**How to interpret it**

* Values close to **1.0** indicate the model achieves high precision at all recall levels — strong positive-class detection.
* Values near the **prevalence rate** (proportion of positives in the data) indicate performance no better than random.
* A sustained **drop** in AUPRC signals that the model's ability to reliably identify positives is degrading, even if AUC-ROC looks stable.
* The two variants (trapezoidal vs step-function) typically agree closely; large divergence may indicate noisy or sparse data in a bucket.

***

### Plot 2 — AUPRC vs AUC-ROC Comparison

Uses:

* `auprc`
* `auc_roc` (from the Curve-Based Discrimination metric)

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
        WHEN metric_name = 'auprc'   THEN 'AUPRC'
        WHEN metric_name = 'auc_roc' THEN 'AUC ROC'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'auprc',
    'auc_roc'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**
This plot overlays AUPRC and AUC-ROC on the same time axis, highlighting cases where one metric tells a different story than the other.

**How to interpret it**

* **AUC-ROC high, AUPRC low**: The model ranks well overall but struggles with the positive class specifically — common in highly imbalanced datasets where high TN count inflates AUC-ROC.
* **Both declining together**: Broad model degradation affecting all aspects of discrimination.
* **AUPRC declining, AUC-ROC stable**: The model is losing precision at high-recall operating points. This is the most actionable signal for imbalanced problems.
* This comparison is essential for **imbalanced classification** (fraud, rare disease, anomaly detection) where AUC-ROC alone can be misleading.

## Interpretation Guide

| AUPRC Range | Interpretation |
|-------------|----------------|
| 0.9 – 1.0  | Excellent — near-perfect precision across all recall levels |
| 0.7 – 0.9  | Good — strong positive-class identification |
| 0.5 – 0.7  | Moderate — useful but with meaningful precision-recall trade-off |
| < 0.5      | Weak — may be near-random depending on class prevalence |

**Important**: Unlike AUC-ROC where 0.5 is random, AUPRC's random baseline equals the **prevalence** of the positive class. A model predicting fraud (1% prevalence) has a random-baseline AUPRC of ~0.01, so even AUPRC = 0.3 can be a strong result.

## Use Cases

* **Imbalanced classification** — fraud detection, rare disease diagnosis, anomaly detection where positives are < 5% of data
* **Threshold selection** — understanding how precision degrades as you increase recall
* **Model comparison** — AUPRC provides a fairer comparison than AUC-ROC when classes are imbalanced
* **Regulatory reporting** — demonstrating model effectiveness on the minority class in credit, healthcare, and insurance

## Binary vs Multiclass

* **Binary:** use the natural positive class and its probability as `score`.
* **Multiclass:** for each class `c` of interest:
  * Define `label = 1` when the ground truth is `c`, else 0.
  * Use the model's predicted probability for class `c` as `score`.
  * Compute AUPRC per class for a one-vs-rest evaluation.
