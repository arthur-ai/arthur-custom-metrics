## Overview

The **Rank Association Profile** bucket measures how well your model’s scores **rank-order** examples relative to their outcomes or business value. It focuses on **correlation between scores and targets**, rather than only on thresholded classification.

This is especially useful when:

* You primarily care about **ordering** (e.g., who to review first, which lead to call)
* Decisions are based on **top-K** segments rather than a single threshold
* Targets may be continuous (e.g., revenue, loss amount) even if the model is classification-based

## Metrics

Let `score` be the model’s prediction (probability/score) and `target` be the outcome (binary or continuous).

**spearman_rho**  
Spearman rank correlation between `score` and `target`, computed per time bucket:

1. Rank scores → `rank_score`
2. Rank targets → `rank_target`
3. Compute Pearson correlation between the ranks:

```text
spearman_rho = corr(rank_score, rank_target)
```

**kendall_tau**  
Kendall’s τ rank correlation between `score` and `target`, representing concordant vs discordant pairs:

```text
kendall_tau = (number_concordant_pairs − number_discordant_pairs) / total_pairs
```

In practice, Kendall τ is computed via a built-in function where available (e.g., `corr_kendall`) or approximated via sampling.

## Data Requirements

* `{{score_col}}` – model score or probability
* `{{target_col}}` – outcome (binary label, continuous value, or ordinal target)
* `{{timestamp_col}}` – event time

Optionally, include subgroup or model version columns for segmented profiles.

## Base Metric SQL

This SQL computes Spearman rank correlation and Kendall's tau between two variables (x and y). These metrics measure how well the rankings of the two variables align.

```sql
WITH base AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    {{timestamp_col}}                                   AS ts,
    {{x_col}}::float                                    AS x,
    {{y_col}}::float                                    AS y
  FROM
    {{dataset}}
  WHERE
    {{x_col}} IS NOT NULL
    AND {{y_col}} IS NOT NULL
),

-- Ranks per bucket for Spearman
ranked AS (
  SELECT
    bucket,
    RANK() OVER (PARTITION BY bucket ORDER BY x)::float AS rx,
    RANK() OVER (PARTITION BY bucket ORDER BY y)::float AS ry
  FROM
    base
),

spearman AS (
  SELECT
    bucket,
    COUNT(*)::float        AS n,
    AVG(rx)                AS mean_rx,
    AVG(ry)                AS mean_ry,
    AVG(rx * ry)           AS mean_rxry,
    AVG(rx * rx)           AS mean_rx2,
    AVG(ry * ry)           AS mean_ry2
  FROM
    ranked
  GROUP BY
    bucket
),

-- Row numbers per bucket for Kendall pairs
numbered AS (
  SELECT
    bucket,
    x,
    y,
    ROW_NUMBER() OVER (
      PARTITION BY bucket
      ORDER BY ts, x, y
    ) AS row_id
  FROM
    base
),

-- Pairwise concordant/discordant counts for Kendall's tau
kendall_counts AS (
  SELECT
    b1.bucket,
    SUM(
      CASE
        WHEN (b1.x < b2.x AND b1.y < b2.y)
          OR (b1.x > b2.x AND b1.y > b2.y)
        THEN 1 ELSE 0
      END
    )::float AS c,   -- concordant pairs
    SUM(
      CASE
        WHEN (b1.x < b2.x AND b1.y > b2.y)
          OR (b1.x > b2.x AND b1.y < b2.y)
        THEN 1 ELSE 0
      END
    )::float AS d    -- discordant pairs
  FROM
    numbered b1
    JOIN numbered b2
      ON b1.bucket = b2.bucket
     AND b1.row_id < b2.row_id
  GROUP BY
    b1.bucket
)

SELECT
  s.bucket AS bucket,

  -- Spearman Rank Correlation Coefficient (Spearman's rho)
  CASE
    WHEN s.n < 2 THEN 0
    ELSE
      CASE
        WHEN ( (s.mean_rx2 - s.mean_rx * s.mean_rx)
             * (s.mean_ry2 - s.mean_ry * s.mean_ry) ) <= 0
        THEN 0
        ELSE
          (s.mean_rxry - s.mean_rx * s.mean_ry)
          / sqrt(
              (s.mean_rx2 - s.mean_rx * s.mean_rx)
            * (s.mean_ry2 - s.mean_ry * s.mean_ry)
            )
      END
  END AS spearman_rank_correlation_coefficient,
  CASE
    WHEN s.n < 2 THEN 0
    ELSE
      CASE
        WHEN ( (s.mean_rx2 - s.mean_rx * s.mean_rx)
             * (s.mean_ry2 - s.mean_ry * s.mean_ry) ) <= 0
        THEN 0
        ELSE
          (s.mean_rxry - s.mean_rx * s.mean_ry)
          / sqrt(
              (s.mean_rx2 - s.mean_rx * s.mean_rx)
            * (s.mean_ry2 - s.mean_ry * s.mean_ry)
            )
      END
  END AS spearman_rho,

  -- Kendall Rank Correlation Coefficient (Kendall's tau)
  CASE
    WHEN k.c IS NULL OR k.d IS NULL OR (k.c + k.d) = 0 THEN 0
    ELSE (k.c - k.d) / (k.c + k.d)
  END AS kendall_rank_correlation_coefficient,
  CASE
    WHEN k.c IS NULL OR k.d IS NULL OR (k.c + k.d) = 0 THEN 0
    ELSE (k.c - k.d) / (k.c + k.d)
  END AS kendall_tau

FROM
  spearman s
  LEFT JOIN kendall_counts k
    ON s.bucket = k.bucket
ORDER BY
  s.bucket;
```

**What this query returns**

* `bucket` — timestamp bucket (1 day)
* `spearman_rank_correlation_coefficient` — Spearman's rho (rank correlation)
* `spearman_rho` — Alias for Spearman's rho
* `kendall_rank_correlation_coefficient` — Kendall's tau (pairwise rank correlation)
* `kendall_tau` — Alias for Kendall's tau

## Plots

See the [charts](../charts/binary-classification/) folder for visualization examples:

* [Plot 1: Spearman Over Time](../charts/binary-classification/spearman-over-time.md)
* [Plot 2: Kendall Tau Over Time](../charts/binary-classification/kendall-tau-over-time.md)
* [Plot 3: Spearman + Kendall Combined](../charts/binary-classification/spearman-kendall-combined.md)

## Use Cases

* Lead scoring and sales prioritization
* Collections and recovery models
* Any pipeline where analysts work the top-ranked items first
* Evaluating whether a new model actually improves ranking quality
