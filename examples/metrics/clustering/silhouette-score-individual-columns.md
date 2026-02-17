## Overview

The **Silhouette Score (Individual Columns)** measures clustering quality by evaluating how similar each data point is to its own cluster compared to the nearest neighboring cluster.

This is a variant of the standard Silhouette Score metric designed for datasets where **features are stored as separate float columns** rather than a single array column.

It produces:

* **silhouette_score** — Overall average silhouette coefficient per time bucket
* **cluster_silhouette** — Per-cluster average silhouette (dimension: cluster name)

For the array-based version, see [silhouette-score.md](silhouette-score.md).

## Metrics

For each data point `i` assigned to cluster `C_i`:

**a(i)** — mean intra-cluster distance:

```text
a(i) = AVG(distance(i, j))  for all j in C_i where j ≠ i
```

**b(i)** — mean nearest-cluster distance:

```text
b(i) = MIN over all clusters C ≠ C_i [ AVG(distance(i, j)) for j in C ]
```

**silhouette(i)** — per-point silhouette coefficient:

```text
silhouette(i) = (b(i) − a(i)) / max(a(i), b(i))
```

**Euclidean distance** between points computed as:

```text
distance(i, j) = SQRT(Σ (feature_k[i] - feature_k[j])²)
```

## Data Requirements

* `{{timestamp_col}}` – event timestamp
* `{{row_id_col}}` – unique identifier for each data point
* `{{cluster_col}}` – cluster assignment (categorical: string or integer label)
* `{{feature_a}}` through `{{feature_e}}` – individual float feature columns
* `{{dataset}}` – dataset containing the inferences

**Configuring features**: This metric uses 5 feature columns by default. Adapt to your needs:

* **Fewer than 5 features**: Set unused feature arguments to a constant like `0::float` to disable them, or modify the SQL to remove unused `POWER()` terms.
* **More than 5 features**: Add additional feature column arguments and extend the distance formula with more `POWER(feature_x_a - feature_x_b, 2)` terms.

## Base Metric SQL

This SQL computes the Silhouette Score using a self-join to form all point pairs, Euclidean distance via explicit column references, and the standard a(i)/b(i) formulation.

> **Performance warning**: This query has **O(n²)** complexity per time bucket due to the self-join across all point pairs. For large datasets, use daily or wider time buckets and consider sampling (e.g., add `AND random() < 0.1` in the base CTE) to limit the number of points per bucket.

```sql
WITH base AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    {{row_id_col}}::text AS row_id,
    {{cluster_col}}::text AS cluster_id,
    {{feature_a}}::float AS feature_a,
    {{feature_b}}::float AS feature_b
    -- {{feature_c}}::float AS feature_c,
    -- {{feature_d}}::float AS feature_d,
    -- {{feature_e}}::float AS feature_e
  FROM
    {{dataset}}
  WHERE
    {{timestamp_col}} IS NOT NULL
    AND {{cluster_col}} IS NOT NULL
),

-- Self-join: all distinct point pairs within the same bucket
point_pairs AS (
  SELECT
    a.bucket,
    a.row_id     AS id_a,
    a.cluster_id AS cluster_a,
    a.feature_a  AS feature_a_a,
    a.feature_b  AS feature_b_a,
    -- a.feature_c  AS feature_c_a,
    -- a.feature_d  AS feature_d_a,
    -- a.feature_e  AS feature_e_a,
    b.row_id     AS id_b,
    b.cluster_id AS cluster_b,
    b.feature_a  AS feature_a_b,
    b.feature_b  AS feature_b_b
    -- b.feature_c  AS feature_c_b,
    -- b.feature_d  AS feature_d_b,
    -- b.feature_e  AS feature_e_b
  FROM
    base a
    JOIN base b
      ON a.bucket = b.bucket
      AND a.row_id <> b.row_id
),

-- Euclidean distance for each pair via explicit column arithmetic
pair_distances AS (
  SELECT
    pp.bucket,
    pp.id_a,
    pp.cluster_a,
    pp.id_b,
    pp.cluster_b,
    SQRT(
      POWER(pp.feature_a_a - pp.feature_a_b, 2) +
      POWER(pp.feature_b_a - pp.feature_b_b, 2)
      -- + POWER(pp.feature_c_a - pp.feature_c_b, 2)
      -- + POWER(pp.feature_d_a - pp.feature_d_b, 2)
      -- + POWER(pp.feature_e_a - pp.feature_e_b, 2)
    ) AS distance
  FROM
    point_pairs pp
),

-- a(i): mean distance to other points in the SAME cluster
intra_cluster AS (
  SELECT
    bucket,
    id_a AS row_id,
    cluster_a AS cluster_id,
    AVG(distance) AS a_i
  FROM
    pair_distances
  WHERE
    cluster_a = cluster_b
  GROUP BY
    bucket, id_a, cluster_a
),

-- Mean distance from each point to every OTHER cluster
inter_cluster_avg AS (
  SELECT
    bucket,
    id_a AS row_id,
    cluster_a AS cluster_id,
    cluster_b AS other_cluster,
    AVG(distance) AS avg_dist
  FROM
    pair_distances
  WHERE
    cluster_a <> cluster_b
  GROUP BY
    bucket, id_a, cluster_a, cluster_b
),

-- b(i): nearest-cluster distance (min of per-cluster averages)
inter_cluster AS (
  SELECT
    bucket,
    row_id,
    cluster_id,
    MIN(avg_dist) AS b_i
  FROM
    inter_cluster_avg
  GROUP BY
    bucket, row_id, cluster_id
),

-- Per-point silhouette coefficient
silhouette_per_point AS (
  SELECT
    base.bucket,
    base.row_id,
    base.cluster_id,
    CASE
      WHEN a.a_i IS NULL OR b.b_i IS NULL THEN 0.0
      WHEN GREATEST(a.a_i, b.b_i) = 0     THEN 0.0
      ELSE (b.b_i - a.a_i) / GREATEST(a.a_i, b.b_i)
    END AS silhouette_i
  FROM
    base
    LEFT JOIN intra_cluster a
      ON base.bucket = a.bucket AND base.row_id = a.row_id
    LEFT JOIN inter_cluster b
      ON base.bucket = b.bucket AND base.row_id = b.row_id
),

-- Per-cluster average
per_cluster AS (
  SELECT
    bucket,
    cluster_id AS series,
    AVG(silhouette_i) AS cluster_silhouette
  FROM
    silhouette_per_point
  GROUP BY
    bucket, cluster_id
),

-- Overall average (weighted by point count, not cluster count)
overall AS (
  SELECT
    bucket,
    AVG(silhouette_i) AS silhouette_score
  FROM
    silhouette_per_point
  GROUP BY
    bucket
)

SELECT
  pc.bucket              AS bucket,
  pc.series              AS series,
  pc.cluster_silhouette  AS cluster_silhouette,
  o.silhouette_score     AS silhouette_score
FROM
  per_cluster pc
  JOIN overall o ON pc.bucket = o.bucket
ORDER BY
  pc.bucket, pc.series;
```

**What this query returns**

* `bucket` — timestamp bucket (1 day)
* `series` — cluster identifier (dimension)
* `cluster_silhouette` — average silhouette for this specific cluster
* `silhouette_score` — overall average silhouette across all points in the bucket

## Aggregate Arguments

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Timestamp column for time bucketing`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Row ID Column

1. **Parameter Key:** `row_id_col`
2. **Friendly Name:** `Row ID Column`
3. **Description:** `Unique identifier for each data point`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `str`, `uuid`, `int`

### Argument 3 — Cluster Assignment Column

1. **Parameter Key:** `cluster_col`
2. **Friendly Name:** `Cluster Assignment Column`
3. **Description:** `Categorical column containing the cluster label for each data point`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `str`, `int`

### Argument 4 — Feature Column A

1. **Parameter Key:** `feature_a`
2. **Friendly Name:** `Feature Column A`
3. **Description:** `Feature A column (must be numeric)`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `float`, `int`

### Argument 5 — Feature Column B

1. **Parameter Key:** `feature_b`
2. **Friendly Name:** `Feature Column B`
3. **Description:** `Feature B column (must be numeric). Set to 0::float if unused.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `float`, `int`

### Argument 6 — Feature Column C

1. **Parameter Key:** `feature_c`
2. **Friendly Name:** `Feature Column C`
3. **Description:** `Feature C column (must be numeric). Set to 0::float if unused.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `float`, `int`

### Argument 7 — Feature Column D

1. **Parameter Key:** `feature_d`
2. **Friendly Name:** `Feature Column D`
3. **Description:** `Feature D column (must be numeric). Set to 0::float if unused.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `float`, `int`

### Argument 8 — Feature Column E

1. **Parameter Key:** `feature_e`
2. **Friendly Name:** `Feature Column E`
3. **Description:** `Feature E column (must be numeric). Set to 0::float if unused.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `float`, `int`

### Argument 9 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Silhouette Score (Overall)

1. **Metric Name:** `silhouette_score`
2. **Description:** `Overall average silhouette coefficient across all points in the time bucket`
3. **Value Column:** `silhouette_score`
4. **Timestamp Column:** `bucket`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** _(none)_

### Metric 2 — Cluster Silhouette (Per-Cluster)

1. **Metric Name:** `cluster_silhouette`
2. **Description:** `Average silhouette coefficient for each cluster`
3. **Value Column:** `cluster_silhouette`
4. **Timestamp Column:** `bucket`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `series`

## Plots

Uses the same charts as the array-based version:

* [Plot 1: Silhouette Score Over Time](../../charts/clustering/silhouette-score-over-time.md)
* [Plot 2: Per-Cluster Silhouette Over Time](../../charts/clustering/cluster-silhouette-over-time.md)

## Interpretation Guide

| Silhouette Range | Interpretation |
|-----------------|----------------|
| 0.71 – 1.00    | Strong structure — clusters are well-separated and cohesive |
| 0.51 – 0.70    | Reasonable structure — clusters are meaningful but with some overlap |
| 0.26 – 0.50    | Weak structure — clusters are overlapping, consider adjusting k or features |
| ≤ 0.25         | No substantial structure — clustering may not be appropriate for this data |

## Performance Considerations

This metric has **O(n²)** complexity per time bucket because it computes pairwise distances between all points.

| Points per bucket | Pairs computed | Recommendation |
|-------------------|---------------|----------------|
| < 500             | ~125K         | Runs efficiently |
| 500 – 2,000       | ~2M           | Acceptable, may take a few seconds |
| 2,000 – 10,000    | ~50M          | Consider sampling |
| > 10,000          | > 50M         | Requires sampling |

**Sampling strategy**: Add a filter in the base CTE to randomly sample points:

```sql
WHERE random() < 0.1
```

Alternatively, use wider time buckets (weekly instead of daily) to reduce the number of distinct points per bucket.

## Comparison with Array-Based Version

| Aspect | Individual Columns (this metric) | Array-Based |
|--------|----------------------------------|-------------|
| **Data structure** | Separate float columns | Single array column |
| **Configuration** | Map 5 column arguments | Map 1 array column or use `ARRAY[col1, col2, ...]` |
| **SQL complexity** | Explicit column arithmetic | Array iteration with `generate_series` |
| **Flexibility** | Fixed number of features (need to edit SQL to change) | Any number of features |
| **Use when** | Features are already in separate columns | Features are in an array, or you want flexibility |

## Use Cases

* **Clustering model monitoring** — detect when cluster quality degrades over time due to data drift
* **Optimal k selection** — compare silhouette scores across different numbers of clusters
* **Feature quality assessment** — low silhouette may indicate the feature space doesn't support the desired clustering
* **Customer segmentation** — monitor whether market segments remain distinct or are converging
* **Anomaly detection pipelines** — validate that normal/anomalous clusters remain well-separated
* **LLM categorization** — evaluate quality of categories assigned by language models
