## Overview

The **AUC Relative Decrease** metric measures how much a model's discrimination power (AUC-ROC) has degraded relative to a reference or baseline value.

This is a **model-monitoring** metric: it takes a known-good AUC (e.g., from validation at deployment time) and quantifies drift as a percentage, making it easy to set alerts and governance thresholds.

It is implemented for **binary classification**. Multiclass models can be evaluated via one-vs-rest strategies by defining separate metrics per class.

It produces:

* **auc_relative_decrease** — Percentage decrease in AUC from the baseline (positive = degradation, negative = improvement)
* **current_auc** — The AUC-ROC for the current time bucket (for context alongside the relative change)

## Metrics

**auc_relative_decrease**
Percentage change in AUC-ROC relative to a user-supplied baseline:

```text
auc_relative_decrease = ((baseline_auc − current_auc) / baseline_auc) × 100
```

* **Positive** values indicate degradation (current AUC is below baseline)
* **Negative** values indicate improvement (current AUC exceeds baseline)
* **Zero** means the model matches the baseline exactly

**current_auc**
The AUC-ROC computed for the current time bucket, identical to the `auc_roc` metric from Curve-Based Discrimination. Included so the raw score is visible alongside the relative change.

## Data Requirements

* `{{label_col}}` – binary ground truth (0 for negative, 1 for positive)
* `{{score_col}}` – probability or score for the positive class (continuous)
* `{{timestamp_col}}` – event timestamp
* `{{baseline_auc}}` – literal: the reference AUC-ROC value to compare against (e.g., 0.85)

## Base Metric SQL

This SQL computes the current AUC-ROC per time bucket (using the standard ROC curve approach), then calculates the percentage decrease from a user-supplied baseline.

```sql
WITH scored AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    {{ground_truth}} AS label,
    {{score_col}}     AS score
  FROM
    {{dataset}}
),

-- Total positives / negatives per bucket
bucket_totals AS (
  SELECT
    bucket,
    SUM(CASE WHEN label = 1 THEN 1 ELSE 0 END)::float AS num_pos,
    SUM(CASE WHEN label = 0 THEN 1 ELSE 0 END)::float AS num_neg
  FROM
    scored
  GROUP BY
    bucket
),

-- Cumulative TP / FP as we sweep thresholds from high score to low score
roc_raw AS (
  SELECT
    s.bucket,
    s.score,
    SUM(CASE WHEN s.label = 1 THEN 1 ELSE 0 END)
      OVER (
        PARTITION BY s.bucket
        ORDER BY s.score DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
      )::float AS cum_pos,
    SUM(CASE WHEN s.label = 0 THEN 1 ELSE 0 END)
      OVER (
        PARTITION BY s.bucket
        ORDER BY s.score DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
      )::float AS cum_neg
  FROM
    scored s
),

-- Turn cumulative counts into TPR/FPR points
roc_points AS (
  SELECT DISTINCT
    r.bucket,
    r.score AS threshold,
    CASE WHEN bt.num_pos > 0 THEN r.cum_pos / bt.num_pos ELSE 0 END AS tpr,
    CASE WHEN bt.num_neg > 0 THEN r.cum_neg / bt.num_neg ELSE 0 END AS fpr
  FROM
    roc_raw r
    JOIN bucket_totals bt USING (bucket)
),

-- Add (0,0) and (1,1) endpoints for a closed ROC curve
roc_with_endpoints AS (
  SELECT
    bt.bucket,
    0.0::float AS fpr,
    0.0::float AS tpr
  FROM
    bucket_totals bt

  UNION ALL

  SELECT
    bucket,
    fpr,
    tpr
  FROM
    roc_points

  UNION ALL

  SELECT
    bt.bucket,
    1.0::float AS fpr,
    1.0::float AS tpr
  FROM
    bucket_totals bt
),

-- Order ROC points and keep previous point for trapezoids
roc_ordered AS (
  SELECT
    bucket,
    fpr,
    tpr,
    LAG(fpr) OVER (PARTITION BY bucket ORDER BY fpr, tpr) AS prev_fpr,
    LAG(tpr) OVER (PARTITION BY bucket ORDER BY fpr, tpr) AS prev_tpr
  FROM
    roc_with_endpoints
),

-- AUC via trapezoidal rule
auc_per_bucket AS (
  SELECT
    bucket,
    COALESCE(
      SUM(
        CASE
          WHEN prev_fpr IS NULL THEN 0
          ELSE (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0
        END
      ),
      0
    ) AS current_auc
  FROM
    roc_ordered
  GROUP BY
    bucket
)

SELECT
  bucket                                                                    AS bucket,
  current_auc                                                               AS current_auc,
  (({{baseline_auc}} - current_auc) / NULLIF({{baseline_auc}}, 0)) * 100.0 AS auc_relative_decrease
FROM
  auc_per_bucket
ORDER BY
  bucket;
```

**What this query returns**

* `bucket` — timestamp bucket (1 day)
* `current_auc` — AUC-ROC for this time bucket
* `auc_relative_decrease` — percentage decrease from the baseline AUC

## Plots

See the [charts](../../charts/binary-classification/) folder for visualization examples:

* [Plot 1: AUC Relative Decrease Over Time](../../charts/binary-classification/auc-relative-decrease-over-time.md)
* [Plot 2: Current AUC vs Baseline](../../charts/binary-classification/current-auc-vs-baseline.md)

---

### Plot 1 — AUC Relative Decrease Over Time

Uses:

* `auc_relative_decrease`

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
        WHEN metric_name = 'auc_relative_decrease' THEN 'AUC Relative Decrease (%)'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'auc_relative_decrease'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**
This plot tracks the percentage decrease in AUC from the baseline over time, with zero representing parity with the baseline.

**How to interpret it**

* Values **at or near 0%** mean the model is performing in line with the baseline.
* **Positive values** indicate degradation — the higher the value, the more the model has drifted from the baseline. A value of 10% means the model's AUC is 10% lower than the baseline.
* **Negative values** indicate improvement over the baseline.
* Sustained upward trends suggest progressive model decay and may warrant retraining or investigation.
* This is ideal for **guardrail alerts** (e.g., "alert if AUC relative decrease exceeds 5%").

***

### Plot 2 — Current AUC vs Baseline

Uses:

* `current_auc`

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
        WHEN metric_name = 'current_auc' THEN 'Current AUC'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'current_auc'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**
This plot shows the raw AUC-ROC per time bucket, providing context for the relative decrease. Overlay a horizontal reference line at the baseline AUC value to visually compare.

**How to interpret it**

* When `current_auc` hovers near the baseline, the model is performing as expected.
* Drops below the baseline line indicate periods of degraded discrimination.
* Spikes above the baseline may reflect favorable data shifts or seasonal patterns — investigate whether they are genuine improvements.
* Pair with the relative decrease plot to see both the absolute and proportional view of drift.

## Interpretation Guide

| Relative Decrease | Interpretation |
|-------------------|----------------|
| < 0%             | Model has improved over the baseline |
| 0% – 2%          | Negligible change — within normal variation |
| 2% – 5%          | Minor degradation — monitor closely |
| 5% – 10%         | Significant degradation — investigate root cause |
| > 10%            | Severe degradation — consider retraining or rollback |

**Note**: These thresholds are guidelines. The right alert levels depend on your domain, risk tolerance, and the consequences of model failure.

## Use Cases

* **Model governance** — quantify model decay against a validated baseline for audit and compliance
* **Drift alerting** — set percentage-based thresholds (e.g., "alert if AUC drops more than 5% from baseline") rather than absolute AUC thresholds that depend on the problem difficulty
* **Champion-challenger comparison** — set the champion model's AUC as the baseline and monitor how the production model compares over time
* **Retraining triggers** — use sustained relative decrease as an objective signal to trigger model retraining pipelines
* **Regulatory reporting** — demonstrate ongoing model performance relative to the validated benchmark in credit, insurance, and healthcare settings

## Binary vs Multiclass

* **Binary:** use the natural positive class and its probability as `score`.
* **Multiclass:** for each class `c` of interest:
  * Define `label = 1` when the ground truth is `c`, else 0.
  * Use the model's predicted probability for class `c` as `score`.
  * Set a per-class baseline AUC and compute relative decrease independently.
