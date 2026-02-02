# Plot 2: Relative Bad Rate Difference

## Metrics Used

* `relative_bad_rate_difference`

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
        WHEN metric_name = 'relative_bad_rate_difference' THEN 'Relative Bad Rate Difference'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'relative_bad_rate_difference'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot measures how much **higher or lower each subgroup's error rate is relative to the global error rate**, on a relative scale.

## How to interpret it

* A value of `0.4` means "this subgroup's bad rate is 40% higher than the global average."
* Large positive values highlight groups bearing a disproportionate error burden.
* This is especially useful in fairness/compliance reviews where _relative_ harm matters more than absolute percentage points.
