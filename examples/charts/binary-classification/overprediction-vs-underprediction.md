# Plot 2: Overprediction vs Underprediction

## Metrics Used

* `overprediction_rate`
* `underprediction_rate`

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
        WHEN metric_name = 'overprediction_rate' THEN 'Overprediction Rate'
        WHEN metric_name = 'underprediction_rate' THEN 'Underprediction Rate'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'overprediction_rate',
    'underprediction_rate'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot compares how often the model **over-predicts positives** (FPs) vs **under-predicts positives** (FNs) over time.

## How to interpret it

* If **overprediction_rate >> underprediction_rate**, the model is aggressively calling positives, likely impacting cost/capacity.
* If **underprediction_rate >> overprediction_rate**, the model is missing many true positives, impacting risk detection.
* Ideally, the ratio between the two aligns with business preferences: in some risk domains, you prefer more FPs; in others, you strongly penalize FNs.
