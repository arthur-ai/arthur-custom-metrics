## Overview

The **Curve-Based Discrimination** bucket measures how well your model’s scores separate positive from negative outcomes across the full score range, using classic evaluation curves.

This bucket is implemented for **binary classification**. Multiclass models can be evaluated via one-vs-rest or macro-averaged strategies by defining separate metrics per class.

It uses:

* Receiver Operating Characteristic (**ROC**) and **AUC-ROC**
* **Gini** coefficient
* **KS** (Kolmogorov–Smirnov) statistic and score

## Metrics

All metrics are derived from (`fpr`, `tpr`) pairs computed across a grid of thresholds on the positive-class score.

**auc_roc**  
Area under the ROC curve, approximated via the trapezoidal rule:

For adjacent ROC points `(fpr_i, tpr_i)` and `(fpr_{i+1}, tpr_{i+1})`:

```text
ΔAUC_i = (fpr_{i+1} − fpr_i) × (tpr_{i+1} + tpr_i) / 2
auc_roc = Σ_i ΔAUC_i
```

**gini_coefficient**  (optional)
Linear transform of AUC commonly used in risk/scoring domains:

```text
gini_coefficient = 2 × auc_roc − 1
```

**ks_statistic**  
Maximum separation between the cumulative distributions of scores for positives vs negatives:

```text
ks_statistic = max_threshold | CDF_positive(score ≥ t) − CDF_negative(score ≥ t) |
```

**ks_score**  
The **threshold value** `t*` at which `ks_statistic` is attained. This is often used as a candidate operating point.

## Data Requirements

* `{{label_col}}` – binary ground truth (0 for negative, 1 for positive)
* `{{score_col}}` – probability or score for the positive class (continuous)
* `{{timestamp_col}}` – event timestamp

## Base Metric SQL — ROC Components

```sql
WITH base AS (
    SELECT
        {{timestamp_col}} AS event_ts,
        {{label_col}}    AS label,
        {{score_col}}    AS score
    FROM {{dataset}}
),
grid AS (
    SELECT generate_series(0.0, 1.0, 0.01) AS threshold
),
scored AS (
    SELECT
        time_bucket(INTERVAL '5 minutes', event_ts) AS ts,
        g.threshold,
        label,
        score,
        CASE WHEN score >= g.threshold THEN 1 ELSE 0 END AS pred_pos
    FROM base
    CROSS JOIN grid g
)
SELECT
    ts     																											AS ts,
    threshold																										AS threshold,
    SUM(CASE WHEN label = 1 THEN 1 ELSE 0 END)                  AS actual_pos,
    SUM(CASE WHEN label = 0 THEN 1 ELSE 0 END)                  AS actual_neg,
    SUM(CASE WHEN pred_pos = 1 AND label = 1 THEN 1 ELSE 0 END) AS tp,
    SUM(CASE WHEN pred_pos = 1 AND label = 0 THEN 1 ELSE 0 END) AS fp
FROM scored
GROUP BY ts, threshold
ORDER BY ts, threshold;
```

You can materialize this as `{{bucket_5_curve_metrics_daily}}`.

## Computing AUC-ROC, Gini, and KS

### AUC-ROC (Binary Only)

```sql
WITH roc_points AS (
    SELECT
        day,
        threshold,
        tpr,
        fpr,
        LAG(fpr) OVER (PARTITION BY day ORDER BY fpr) AS prev_fpr,
        LAG(tpr) OVER (PARTITION BY day ORDER BY fpr) AS prev_tpr
    FROM {{bucket_5_curve_metrics_daily}}
)
SELECT
    day,
    SUM(
        COALESCE((fpr - prev_fpr) * (tpr + prev_tpr) / 2.0, 0.0)
    ) AS auc_roc
FROM roc_points
GROUP BY day;
```

### Gini Coefficient

```sql
SELECT
    day,
    auc_roc,
    2 * auc_roc - 1 AS gini_coefficient
FROM {{bucket_5_auc_metrics}};
```

### KS Statistic and Score

```sql
WITH roc_points AS (
    SELECT
        day,
        threshold,
        tpr,
        fpr
    FROM {{bucket_5_curve_metrics_daily}}
),
cum AS (
    SELECT
        day,
        threshold,
        SUM(tpr) OVER (PARTITION BY day ORDER BY threshold DESC) AS cum_tpr,
        SUM(fpr) OVER (PARTITION BY day ORDER BY threshold DESC) AS cum_fpr
    FROM roc_points
)
SELECT
    day,
    MAX(ABS(cum_tpr - cum_fpr)) AS ks_statistic,
    FIRST_VALUE(threshold) OVER (
        PARTITION BY day
        ORDER BY ABS(cum_tpr - cum_fpr) DESC
    ) AS ks_score
FROM cum
GROUP BY day;
```

## Plots

### Plot 1— AUC + Gini Over Time

Uses:

* `auc_roc`
* `gini_coefficient`

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
        WHEN metric_name = 'auc_roc' THEN 'AUC ROC'
        WHEN metric_name = 'gini_coefficient'     THEN 'Gini Coefficient'
        ELSE metric_name
    END AS friendly_name,
    
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'auc_roc',
    'gini_coefficient'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**  
This plot tracks both **AUC** and its corresponding **Gini** coefficient over time, providing two familiar views of discrimination strength.

**How to interpret it**

* Sustained **drops in auc_roc** or **gini_coefficient** usually indicate that the model’s ability to separate positives from negatives has degraded.
* If AUC remains stable while business KPIs worsen, the issue may be threshold selection or data mix, not raw score discrimination.
* Gini is often the metric business stakeholders and regulators expect in credit/risk settings, so having both on one chart helps bridge ML and business views.

***

### Plot 2 — KS Statistic Over Time

Uses:

* `ks_statistic`
* `ks_score`

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
        WHEN metric_name = 'ks_statistic' THEN 'KS Statistic'
        WHEN metric_name = 'ks_score'     THEN 'KS Score'
        ELSE metric_name
    END AS friendly_name,
    
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'ks_statistic',
    'ks_score'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**  
This plot tracks the **maximum separation** between positive and negative score distributions (`ks_statistic`) and where that separation occurs in score space (`ks_score`).

**How to interpret it**

* Higher `ks_statistic` values indicate stronger separation; many credit models target KS in a specific band (e.g., 0.3–0.5).
* Changes in `ks_score` tell you **where** in the score range the separation is happening—if it drifts, your best cut-off point may be moving.
* If KS drops while AUC is flat, the problem may be in specific parts of the distribution (e.g., tail behavior) rather than global ranking.

***

### Plot 3— Combined AUC + KS

Uses:

* `auc_roc`
* `ks_statistic`
* `ks_score`

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
        WHEN metric_name = 'auc_roc'      THEN 'ROC AUC'
        WHEN metric_name = 'ks_statistic' THEN 'KS Statistic'
        WHEN metric_name = 'ks_score'     THEN 'KS Score'
        ELSE metric_name
    END AS friendly_name,
    
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'auc_roc',
    'ks_statistic',
    'ks_score'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;

```

**What this shows**  
This plot overlays **global ranking quality** (AUC) with **maximum local separation** (KS) on the same time axis.

**How to interpret it**

* When AUC and KS move together, the model’s ranking power is consistently changing.
* Divergence (e.g., AUC flat, KS moving) suggests that certain score regions become more/less separative even though global ranking is unchanged.
* This is an excellent high-level monitoring view for risk committees and model governance reviews.

***

### Plot 4 — KS-Only Variant (optional)

Uses:

* `ks_statistic`

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
        WHEN metric_name = 'ks_statistic' THEN 'KS Statistic'
        ELSE metric_name
    END AS friendly_name,
    
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'ks_statistic',
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;

```

**What this shows**  
A lightweight KS-only time series focusing on **separation strength**.

**How to interpret it**

* Useful when you want a single scalar to monitor drift in discrimination.
* Can be wired into simple guardrails (e.g., “alert if KS falls below 0.25”).



### Alternative SQL

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
  -- (0,0) per bucket
  SELECT
    bt.bucket,
    0.0::float AS fpr,
    0.0::float AS tpr
  FROM
    bucket_totals bt

  UNION ALL

  -- All ROC points
  SELECT
    bucket,
    fpr,
    tpr
  FROM
    roc_points

  UNION ALL

  -- (1,1) per bucket
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

-- Area Under the Curve (AUC) via trapezoidal rule
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
    ) AS area_under_curve  -- AUC: ability to distinguish between classes
  FROM
    roc_ordered
  GROUP BY
    bucket
),

-- Kolmogorov-Smirnov Statistic: max |TPR - FPR|
ks_per_bucket AS (
  SELECT
    bucket,
    MAX(ABS(tpr - fpr)) AS kolmogorov_smirnov_statistic
  FROM
    roc_with_endpoints
  GROUP BY
    bucket
)

SELECT
  a.bucket                                   AS bucket,
  a.area_under_curve                         AS auc_roc,
  k.kolmogorov_smirnov_statistic             AS ks_statistic,
  k.kolmogorov_smirnov_statistic             AS ks_score
FROM
  auc_per_bucket a
  JOIN ks_per_bucket k USING (bucket)
ORDER BY
  a.bucket;

```
