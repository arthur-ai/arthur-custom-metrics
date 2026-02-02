# Plot 2: KS Statistic Over Time

## Metrics Used

* `ks_statistic`
* `ks_score`

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

## What this shows

This plot tracks the **maximum separation** between positive and negative score distributions (`ks_statistic`) and where that separation occurs in score space (`ks_score`).

## How to interpret it

* Higher `ks_statistic` values indicate stronger separation; many credit models target KS in a specific band (e.g., 0.3–0.5).
* Changes in `ks_score` tell you **where** in the score range the separation is happening—if it drifts, your best cut-off point may be moving.
* If KS drops while AUC is flat, the problem may be in specific parts of the distribution (e.g., tail behavior) rather than global ranking.
