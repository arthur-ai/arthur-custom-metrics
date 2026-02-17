# Plot 2: Incomplete Rows Over Time

## Metrics Used

* `incomplete_row_count`

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
        WHEN metric_name = 'incomplete_row_count' THEN 'Incomplete Rows'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(SUM(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'incomplete_row_count'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot tracks the **absolute count of incomplete records** per day — rows where at least one required column is NULL.

## How to interpret it

* Useful when completeness percentage stays high but volume matters — 1% of 1M rows is still 10K incomplete records.
* **Spikes** reveal specific days with data quality issues, making root-cause investigation easier.
* Pair with completeness percentage: if both metrics change proportionally, total volume may simply be growing. If count spikes while percentage is stable, volume increased.
