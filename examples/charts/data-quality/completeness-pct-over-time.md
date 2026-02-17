# Plot 1: Completeness Percentage Over Time

## Metrics Used

* `completeness_pct`

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
        WHEN metric_name = 'completeness_pct' THEN 'Data Completeness (%)'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'completeness_pct'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot tracks the **percentage of complete data records** over time, where "complete" means all required columns are non-NULL.

## How to interpret it

* **100%** means every record has all required fields populated — ideal state.
* **Gradual decline** suggests an upstream data pipeline is progressively losing fields (e.g., schema changes, ETL failures, new sources without all fields).
* **Sudden drop** indicates an acute issue — a broken pipeline, provider outage, or schema migration that introduced NULLs.
* Set a **floor alert** (e.g., "alert if completeness drops below 95%") as an early warning for data pipeline issues.
