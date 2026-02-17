# Plot 1: Silhouette Score Over Time

## Metrics Used

* `silhouette_score`

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

## What this shows

This plot tracks **overall clustering quality** over time as a single scalar in [-1, 1].

## How to interpret it

* **Stable near +1**: Clusters are well-separated and cohesive — clustering is working well.
* **Declining toward 0**: Cluster boundaries are becoming ambiguous — data distribution may be drifting or the number of clusters may no longer be appropriate.
* **Negative values**: Points are frequently closer to other clusters than their own — clustering is actively wrong.
* Sudden drops may indicate data distribution shifts, new subpopulations, or feature drift.
* Set alerts at a meaningful threshold (e.g., "alert if silhouette drops below 0.3") to catch degradation early.
