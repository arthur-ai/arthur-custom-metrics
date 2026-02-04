# Plot 3: Combined Disparity View

## Metrics Used

* `rate_difference`
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
        WHEN metric_name = 'rate_difference'              THEN 'Rate Difference'
        WHEN metric_name = 'relative_bad_rate_difference' THEN 'Relative Bad Rate Difference'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'rate_difference',
    'relative_bad_rate_difference'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot combines **absolute acceptance-rate disparity** with **relative error-rate disparity** for each subgroup.

## How to interpret it

* Subgroups with **high rate_difference and high relative_bad_rate_difference** are "double cluster" risk: they are treated differently _and_ experience more errors.
* Subgroups with low acceptance disparity but high bad-rate disparity might be getting similar volumes, but with very different quality of decisions.
* This combined view is a strong candidate for a "fairness overview" chart for auditors and risk teams.
