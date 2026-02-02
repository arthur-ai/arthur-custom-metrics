## Overview

The **Subgroup Rate Comparison** bucket evaluates how key classification metrics differ across **segments or subgroups** (e.g., region, channel, demographic buckets). It is primarily used for **fairness**, **bias**, and **performance parity** analysis.

It helps answer:

* “Is my acceptance rate much higher for one group than another?”
* “Does recall degrade for certain segments?”
* “Are error rates uneven across subgroups?”

## Metrics

Let `bad_rate` be the misclassification rate in a subgroup:

```text
bad_rate_subgroup = (FP + FN) / (TP + FP + FN + TN)
```

Let `rate_subgroup` be some primary rate of interest (acceptance, recall, FPR, etc.), and `rate_reference` / `bad_rate_reference` be the corresponding rate for a reference group (e.g., global population or a designated baseline subgroup).

**rate_difference**  
Absolute difference between a subgroup’s rate and the reference rate:

```text
rate_difference = | rate_subgroup − rate_reference |
```

**relative_bad_rate_difference**  
Relative difference in bad rate between a subgroup and the reference:

```text
relative_bad_rate_difference = (bad_rate_subgroup − bad_rate_reference) / bad_rate_reference
```

> Often expressed as a percentage in UI (e.g., “Subgroup A has 40% higher bad rate than reference group”).

## Data Requirements

* `{{label_col}}` – ground truth label
* `{{pred_label_col}}` – predicted label (or thresholded score)
* `{{subgroup_col}}` – subgroup identifier (e.g., channel, geography, age band)
* `{{timestamp_col}}` – event time

Subgroups should have **reasonable sample sizes**; very rare groups will yield noisy metrics.

## Base Metric SQL — Per-Subgroup Confusion Matrix

```sql
WITH base AS (
    SELECT
        {{timestamp_col}} AS event_ts,
        {{label_col}}     AS label,
        {{pred_label_col}} AS pred_label,
        {{subgroup_col}}  AS subgroup
    FROM {{dataset}}
),
agg AS (
    SELECT
        time_bucket(INTERVAL '5 minutes', event_ts) AS ts,
        subgroup,
        COUNT(*)                                                   AS total,
        SUM(CASE WHEN pred_label = 1 AND label = 1 THEN 1 ELSE 0 END) AS tp,
        SUM(CASE WHEN pred_label = 1 AND label = 0 THEN 1 ELSE 0 END) AS fp,
        SUM(CASE WHEN pred_label = 0 AND label = 1 THEN 1 ELSE 0 END) AS fn,
        SUM(CASE WHEN pred_label = 0 AND label = 0 THEN 1 ELSE 0 END) AS tn
    FROM base
    GROUP BY ts, subgroup
)
SELECT
    ts,
    subgroup,
    total,
    tp,
    fp,
    fn,
    tn,
    (tp + fp)::double precision / NULLIF(total, 0) AS acceptance_rate,
    (fp + fn)::double precision / NULLIF(total, 0) AS bad_rate
FROM agg;
```

You can store `acceptance_rate` and `bad_rate` as reported metrics, then compute disparity metrics in downstream queries.

## Plots

> Preview Data
>
> for startDate use 2025-11-26T17:54:05.425Z
> for endDate use 2025-12-10T17:54:05.425Z

### Plot 1 — Absolute Rate Difference

Uses:

* `rate_difference`

Example to compute acceptance rate differences vs global:

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
        WHEN metric_name = 'rate_difference' THEN 'Rate Difference'
        ELSE metric_name
    END AS friendly_name,
    
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'rate_difference'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**  
This plot highlights how far each subgroup’s **acceptance rate** deviates from the global average on an absolute scale.

**How to interpret it**

* Larger `rate_difference` values mean greater disparity in how frequently groups are accepted.
* If specific subgroups consistently show higher or lower acceptance, that may indicate potential bias or misalignment with policy.
* You can set alert thresholds (e.g., “> 5 percentage points difference”) to flag fairness concerns.

***

### Plot 2 — Relative Bad Rate Difference

Uses:

* `relative_bad_rate_difference`

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
        WHEN metric_name = 'relative_bad_rate_difference' THEN 'Relative Bad Rate Difference'
        ELSE metric_name
    END AS friendly_name,
    
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'relative_bad_rate_difference'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**  
This plot measures how much **higher or lower each subgroup’s error rate is relative to the global error rate**, on a relative scale.

**How to interpret it**

* A value of `0.4` means “this subgroup’s bad rate is 40% higher than the global average.”
* Large positive values highlight groups bearing a disproportionate error burden.
* This is especially useful in fairness/compliance reviews where _relative_ harm matters more than absolute percentage points.

***

### Plot 3 — Combined Disparity View

Uses:

* `rate_difference`
* `relative_bad_rate_difference`

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
        WHEN metric_name = 'rate_difference'              THEN 'Rate Difference'
        WHEN metric_name = 'relative_bad_rate_difference' THEN 'Relative Bad Rate Difference'
        ELSE metric_name
    END AS friendly_name,
    
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'rate_difference',
    'relative_bad_rate_difference'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**  
This plot combines **absolute acceptance-rate disparity** with **relative error-rate disparity** for each subgroup.

**How to interpret it**

* Subgroups with **high rate_difference and high relative_bad_rate_difference** are “double cluster” risk: they are treated differently _and_ experience more errors.
* Subgroups with low acceptance disparity but high bad-rate disparity might be getting similar volumes, but with very different quality of decisions.
* This combined view is a strong candidate for a “fairness overview” chart for auditors and risk teams.



### Alternative SQL

```sql
WITH base AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    {{group_col}} AS group_val,

    -- Predicted label (e.g., approval / selection)
    CASE
      WHEN {{score_col}} >= {{threshold}} THEN 1
      ELSE 0
    END AS pred_label,

    -- "Bad" outcome from actual ground truth (e.g., default, event)
    CASE
      WHEN {{ground_truth}} = 1 THEN 1
      ELSE 0
    END AS bad_label
  FROM
    {{dataset}}
),

counts AS (
  SELECT
    bucket,

    -- Group A (protected / comparison group)
    SUM(CASE WHEN group_val = '{{group_a}}' THEN 1 ELSE 0 END)::float AS n_a,
    SUM(CASE WHEN group_val = '{{group_a}}' AND pred_label = 1 THEN 1 ELSE 0 END)::float AS approved_a,
    SUM(CASE WHEN group_val = '{{group_a}}' AND bad_label  = 1 THEN 1 ELSE 0 END)::float AS bad_a,

    -- Group B (reference group)
    SUM(CASE WHEN group_val = '{{group_b}}' THEN 1 ELSE 0 END)::float AS n_b,
    SUM(CASE WHEN group_val = '{{group_b}}' AND pred_label = 1 THEN 1 ELSE 0 END)::float AS approved_b,
    SUM(CASE WHEN group_val = '{{group_b}}' AND bad_label  = 1 THEN 1 ELSE 0 END)::float AS bad_b
  FROM
    base
  GROUP BY
    1
),

rates AS (
  SELECT
    bucket,

    -- Approval / selection rates (for Rate Difference)
    CASE WHEN n_a > 0 THEN approved_a / n_a ELSE 0 END AS rate_a,
    CASE WHEN n_b > 0 THEN approved_b / n_b ELSE 0 END AS rate_b,

    -- Bad rates (for Relative Bad Rate Difference)
    CASE WHEN n_a > 0 THEN bad_a / n_a ELSE 0 END AS bad_rate_a,
    CASE WHEN n_b > 0 THEN bad_b / n_b ELSE 0 END AS bad_rate_b
  FROM
    counts
)

SELECT
  bucket AS bucket,

  -- Rate Difference: difference between approval/selection rates
  -- (signed, so positive => Group A has higher rate than Group B)
  rate_a - rate_b AS rate_difference,

  -- Relative Bad Rate Difference:
  -- difference in bad rates, normalized by reference group's bad rate (Group B)
  CASE
    WHEN bad_rate_b <> 0 THEN (bad_rate_a - bad_rate_b) / bad_rate_b
    ELSE 0
  END AS relative_bad_rate_difference

FROM
  rates
ORDER BY
  bucket;

```
