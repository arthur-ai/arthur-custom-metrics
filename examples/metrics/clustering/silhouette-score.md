## Overview

The **Silhouette Score** measures clustering quality by evaluating how similar each data point is to its own cluster compared to the nearest neighboring cluster. It produces a coefficient in [-1, 1] where:

* **+1** — points are well matched to their own cluster and poorly matched to others (ideal)
* **0** — points sit on or near the boundary between clusters
* **-1** — points are likely assigned to the wrong cluster

This metric is **model-type agnostic** — it applies to any system that produces cluster assignments (k-means, DBSCAN, hierarchical clustering, LLM-based categorization, business rule segmentation, etc.).

This version expects **features as a float array column**. For datasets with features stored as separate columns, see [silhouette-score-individual-columns.md](silhouette-score-individual-columns.md).

It produces:

* **silhouette_score** — Overall average silhouette coefficient per time bucket
* **cluster_silhouette** — Per-cluster average silhouette (dimension: cluster name)

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

Special cases:
* If point `i` is the only member of its cluster (singleton), `silhouette(i) = 0`
* If only one cluster exists in the bucket, `silhouette(i) = 0`

**silhouette_score** — overall average:

```text
silhouette_score = AVG(silhouette(i))  over all points i in the bucket
```

**cluster_silhouette** — per-cluster average:

```text
cluster_silhouette(C) = AVG(silhouette(i))  for all i in cluster C
```

## Data Requirements

* `{{timestamp_col}}` – event timestamp
* `{{row_id_col}}` – unique identifier for each data point
* `{{cluster_col}}` – cluster assignment (categorical: string or integer label)
* `{{features_col}}` – feature vector as a float array (e.g., `ARRAY[0.5, 1.2, 3.7]`)
* `{{dataset}}` – dataset containing the inferences

**Note on feature columns**: If your features are stored as separate float columns rather than an array, combine them in your dataset configuration using `ARRAY[col1, col2, col3]` as the column expression, or pre-compute the array in a view.

## Base Metric SQL

This SQL computes the Silhouette Score using a self-join to form all point pairs, Euclidean distance via array index iteration, and the standard a(i)/b(i) formulation.

> **Performance warning**: This query has **O(n²)** complexity per time bucket due to the self-join across all point pairs. For large datasets, use daily or wider time buckets and consider sampling (e.g., add `AND random() < 0.1` in the base CTE) to limit the number of points per bucket.

```sql
WITH base AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    {{row_id_col}}::text AS row_id,
    {{cluster_col}}::text AS cluster_id,
    {{features_col}} AS features
  FROM
    {{dataset}}
  WHERE
    {{timestamp_col}} IS NOT NULL
    AND {{cluster_col}} IS NOT NULL
    AND {{features_col}} IS NOT NULL
),

-- Self-join: all distinct point pairs within the same bucket
point_pairs AS (
  SELECT
    a.bucket,
    a.row_id    AS id_a,
    a.cluster_id AS cluster_a,
    a.features  AS features_a,
    b.row_id    AS id_b,
    b.cluster_id AS cluster_b,
    b.features  AS features_b
  FROM
    base a
    JOIN base b
      ON a.bucket = b.bucket
      AND a.row_id <> b.row_id
),

-- Euclidean distance for each pair via array index iteration
pair_distances AS (
  SELECT
    pp.bucket,
    pp.id_a,
    pp.cluster_a,
    pp.id_b,
    pp.cluster_b,
    SQRT(SUM(POWER(pp.features_a[i] - pp.features_b[i], 2))) AS distance
  FROM
    point_pairs pp,
    generate_series(1, array_length(pp.features_a, 1)) AS i
  GROUP BY
    pp.bucket, pp.id_a, pp.cluster_a, pp.id_b, pp.cluster_b
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

### Argument 4 — Feature Vector Column

1. **Parameter Key:** `features_col`
2. **Friendly Name:** `Feature Vector Column`
3. **Description:** `Float array column containing the feature vector (e.g., ARRAY[f1, f2, f3]). All arrays must have the same length.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`

### Argument 5 — Dataset

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

See the [charts](../../charts/clustering/) folder for visualization examples:

* [Plot 1: Silhouette Score Over Time](../../charts/clustering/silhouette-score-over-time.md)
* [Plot 2: Per-Cluster Silhouette Over Time](../../charts/clustering/cluster-silhouette-over-time.md)

---

### Plot 1 — Silhouette Score Over Time

Uses:

* `silhouette_score`

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
        WHEN metric_name = 'silhouette_score' THEN 'Silhouette Score'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'silhouette_score'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**
This plot tracks overall clustering quality over time as a single scalar value.

**How to interpret it**

* **Stable near +1**: Clusters are well-separated and cohesive — clustering is working well.
* **Declining toward 0**: Cluster boundaries are becoming ambiguous — data distribution may be drifting or the number of clusters may no longer be appropriate.
* **Negative values**: Points are frequently closer to other clusters than their own — clustering is actively wrong.
* Sudden drops may indicate data distribution shifts, new subpopulations, or feature drift.

***

### Plot 2 — Per-Cluster Silhouette Over Time

Uses:

* `cluster_silhouette`

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,

    metric_name,

    dimension->>'series' AS cluster_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name = 'cluster_silhouette'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name, cluster_name
ORDER BY time_bucket_1d, cluster_name;
```

**What this shows**
This plot breaks down silhouette by cluster, revealing which clusters are well-formed and which are problematic.

**How to interpret it**

* Clusters with consistently **high silhouette** are well-defined and stable.
* Clusters with **low or negative silhouette** are poorly separated — their members may belong to neighboring clusters.
* If one cluster's silhouette drops while others remain stable, investigate that specific cluster for data shifts or concept drift.
* Large variance between clusters suggests the clustering model fits some segments of the data much better than others.

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
-- Sample ~10% of points per bucket
WHERE random() < 0.1
```

Alternatively, use wider time buckets (weekly instead of daily) to reduce the number of distinct points per bucket.

## Use Cases

* **Clustering model monitoring** — detect when cluster quality degrades over time due to data drift
* **Optimal k selection** — compare silhouette scores across different numbers of clusters
* **Feature quality assessment** — low silhouette may indicate the feature space doesn't support the desired clustering
* **Customer segmentation** — monitor whether market segments remain distinct or are converging
* **Anomaly detection pipelines** — validate that normal/anomalous clusters remain well-separated
* **LLM categorization** — evaluate quality of categories assigned by language models
