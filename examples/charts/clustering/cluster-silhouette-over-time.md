# Plot 2: Per-Cluster Silhouette Over Time

## Metrics Used

* `cluster_silhouette`

## SQL Query

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

## What this shows

This plot breaks down silhouette by **individual cluster**, revealing which clusters are well-formed and which are problematic.

## How to interpret it

* Clusters with consistently **high silhouette** (> 0.5) are well-defined and stable.
* Clusters with **low or negative silhouette** are poorly separated — their members may belong to neighboring clusters.
* If one cluster's silhouette drops while others remain stable, investigate that specific cluster for data drift or concept changes.
* Large variance between clusters suggests the model fits some segments much better than others — consider splitting poorly-performing clusters or merging overlapping ones.
