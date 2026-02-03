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

## Base Metric SQL — Spearman and Kendall per Day

```sql
WITH
  base_data AS (
    SELECT
      time_bucket (INTERVAL '5 minutes', {{timestamp_col}}) AS bucket,
      {{x_col}}::float AS x,
      {{y_col}}::float AS y
    FROM
      {{dataset}}
    WHERE
      {{x_col}} IS NOT NULL
      AND {{y_col}} IS NOT NULL
  ),
  -- Spearman: Pearson correlation on ranks
  spearman_stats AS (
    SELECT
      r.bucket AS bucket,
      COUNT(*)::float AS n,
      AVG(r.rx) AS mean_rx,
      AVG(r.ry) AS mean_ry,
      AVG(r.rx * r.ry) AS mean_rxry,
      AVG(r.rx * r.rx) AS mean_rx2,
      AVG(r.ry * r.ry) AS mean_ry2
    FROM
      (
        SELECT
          bucket AS bucket,
          RANK() OVER (
            PARTITION BY
              bucket
            ORDER BY
              x
          )::float AS rx,
          RANK() OVER (
            PARTITION BY
              bucket
            ORDER BY
              y
          )::float AS ry
        FROM
          base_data
      ) AS r
    GROUP BY
      r.bucket
  ),
  -- Kendall: pairwise concordant / discordant counts
  kendall_pairs AS (
    SELECT
      b1.bucket AS bucket,
      CASE
        WHEN (
          b1.x < b2.x
          AND b1.y < b2.y
        )
        OR (
          b1.x > b2.x
          AND b1.y > b2.y
        ) THEN 1
        ELSE 0
      END AS concordant,
      CASE
        WHEN (
          b1.x < b2.x
          AND b1.y > b2.y
        )
        OR (
          b1.x > b2.x
          AND b1.y < b2.y
        ) THEN 1
        ELSE 0
      END AS discordant
    FROM
      (
        SELECT
          bucket,
          x,
          y,
          ROW_NUMBER() OVER (
            PARTITION BY
              bucket
            ORDER BY
              {{timestamp_col}},
              x,
              y
          ) AS row_id
        FROM
          base_data
      ) AS b1
      JOIN (
        SELECT
          bucket,
          x,
          y,
          ROW_NUMBER() OVER (
            PARTITION BY
              bucket
            ORDER BY
              {{timestamp_col}},
              x,
              y
          ) AS row_id
        FROM
          base_data
      ) AS b2 ON b1.bucket = b2.bucket
      AND b1.row_id < b2.row_id
  ),
  kendall_stats AS (
    SELECT
      bucket AS bucket,
      SUM(concordant)::float AS c,
      SUM(discordant)::float AS d
    FROM
      kendall_pairs
    GROUP BY
      bucket
  )
SELECT
  s.bucket AS bucket,
  -- Spearman's rho (never NULL)
  CASE
    WHEN s.n < 2 THEN 0
    ELSE COALESCE(
      (s.mean_rxry - s.mean_rx * s.mean_ry) / NULLIF(
        sqrt(
          (s.mean_rx2 - s.mean_rx * s.mean_rx) * (s.mean_ry2 - s.mean_ry * s.mean_ry)
        ),
        0
      ),
      0
    )
  END AS spearman_rho,
  -- Kendall's tau (never NULL)
  CASE
    WHEN COALESCE(k.c + k.d, 0) = 0 THEN 0
    ELSE COALESCE((k.c - k.d) / NULLIF(k.c + k.d, 0), 0)
  END AS kendall_tau
FROM
  spearman_stats AS s
  LEFT JOIN kendall_stats AS k ON s.bucket = k.bucket
ORDER BY
  s.bucket;
```

If your SQL engine does not support Kendall τ directly, you can compute it offline or via a custom function and then load it into Arthur as a time series metric.

## Plots

> Preview Data
>
> for startDate use 2025-11-26T17:54:05.425Z
> for endDate use 2025-12-10T17:54:05.425Z

### Plot 1 — Spearman Over Time

Uses:

* `spearman_rho`

```sql
SELECT
  time_bucket_gapfill(
    '1 day',
    timestamp,
    '{{dateStart}}'::timestamptz,
    '{{dateEnd}}'::timestamptz
  ) AS time_bucket_1d,

  'spearman_rho' AS metric_name,
  'Spearman Rank Correlation' AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name = 'spearman_rho'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

**What this shows**  
This plot tracks how strongly **score rankings** align with **target rankings** over time.

**How to interpret it**

* Higher `spearman_rho` means that as scores increase, targets generally increase too (good ordering).
* Drops in Spearman often show that the model’s ranking power is weakening, even if thresholded metrics (like accuracy) look stable.
* Particularly useful in prioritization use cases (e.g., lead scoring, collections).

***

### Plot 2 — Kendall Tau Over Time

Uses:

* `kendall_tau`

```sql
SELECT
  time_bucket_gapfill(
    '1 day',
    timestamp,
    '{{dateStart}}'::timestamptz,
    '{{dateEnd}}'::timestamptz
  ) AS time_bucket_1d,

  'kendall_tau' AS metric_name,
  'Kendall Tau' AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name = 'kendall_tau'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;

```

**What this shows**  
This plot shows Kendall’s τ, which measures **pairwise agreement** in ranking between scores and targets.

**How to interpret it**

* Unlike Spearman, Kendall focuses on how many pairs are ordered correctly vs incorrectly.
* It can be more robust to outliers, so divergences between Spearman and Kendall might highlight unusual target distributions.
* If your DB doesn’t provide Kendall natively, you can still reserve this plot for offline-computed metrics.

***

### Plot 3 — Spearman + Kendall Combined

Uses:

* `spearman_rho`
* `kendall_tau`

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
        WHEN metric_name = 'spearman_rho'      THEN 'Spearman Rank Correlation'
        WHEN metric_name = 'kendall_tau'     THEN 'Kendall Tau'
        ELSE metric_name
    END AS friendly_name,


  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'kendall_tau',
    'spearman_rho'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;

```

**What this shows**  
This combined plot overlays both **Spearman** and **Kendall** rank correlations.

**How to interpret it**

* When both move together, you have a consistent picture of ranking quality.
* If they diverge—e.g., Spearman stable but Kendall falling—it may indicate that ranking issues are concentrated in specific regions or pairs.
* This is a powerful diagnostic for evaluating whether a new model actually improves **ordering**, not just threshold metrics.

## Use Cases

* Lead scoring and sales prioritization
* Collections and recovery models
* Any pipeline where analysts work the top-ranked items first
* Evaluating whether a new model actually improves ranking quality

### Alternative SQL

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
