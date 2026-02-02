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

## Base Metric SQL

This SQL computes subgroup rate comparison metrics by comparing two groups (Group A and Group B). It calculates rate differences in acceptance rates and relative differences in bad rates.

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

**What this query returns**

* `bucket` — timestamp bucket (1 day)
* `rate_difference` — Absolute difference in acceptance/approval rates between groups
* `relative_bad_rate_difference` — Relative difference in bad rates normalized by reference group

## Plots

See the [charts](../charts/binary-classification/) folder for visualization examples:

* [Plot 1: Absolute Rate Difference](../charts/binary-classification/absolute-rate-difference.md)
* [Plot 2: Relative Bad Rate Difference](../charts/binary-classification/relative-bad-rate-difference.md)
* [Plot 3: Combined Disparity View](../charts/binary-classification/combined-disparity-view.md)
