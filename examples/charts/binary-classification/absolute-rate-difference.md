# Plot 1: Absolute Rate Difference

## Metrics Used

* `rate_difference`

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
        WHEN metric_name = 'rate_difference' THEN 'Rate Difference'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'rate_difference'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot highlights how far each subgroup's **acceptance rate** deviates from the global average on an absolute scale.

## How to interpret it

* Larger `rate_difference` values mean greater disparity in how frequently groups are accepted.
* If specific subgroups consistently show higher or lower acceptance, that may indicate potential bias or misalignment with policy.
* You can set alert thresholds (e.g., "> 5 percentage points difference") to flag fairness concerns.
