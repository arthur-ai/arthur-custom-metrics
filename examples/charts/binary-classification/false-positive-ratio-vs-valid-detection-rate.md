# Plot 3: False Positive Ratio vs Valid Detection Rate

## Metrics Used

* `false_positive_ratio`
* `valid_detection_rate`

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
        WHEN metric_name = 'false_positive_ratio' THEN 'False Positive Ratio'
        WHEN metric_name = 'valid_detection_rate' THEN 'Valid Detection Rate'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'false_positive_ratio',
    'valid_detection_rate'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot contrasts **how dirty the positive bucket is** (`false_positive_ratio`) with **overall correctness** (`valid_detection_rate`).

## How to interpret it

* Days where `false_positive_ratio` is high but `valid_detection_rate` remains flat may mean errors are mostly concentrated in positives rather than negatives.
* If both degrade together, the model is likely struggling broadly (not just in the positive segment).
* You can use this to explain to stakeholders _why_ precision dropped: because the model is trading global accuracy for more aggressive positive predictions.
