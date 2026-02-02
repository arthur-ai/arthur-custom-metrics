# Plot 4: KS-Only Variant (optional)

## Metrics Used

* `ks_statistic`

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

## What this shows

A lightweight KS-only time series focusing on **separation strength**.

## How to interpret it

* Useful when you want a single scalar to monitor drift in discrimination.
* Can be wired into simple guardrails (e.g., "alert if KS falls below 0.25").
