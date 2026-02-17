# Plot 2: Current AUC vs Baseline

## Metrics Used

* `current_auc`

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
        WHEN metric_name = 'current_auc' THEN 'Current AUC'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'current_auc'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot shows the **raw AUC-ROC** per time bucket. Overlay a horizontal reference line at the baseline AUC value to visually compare current performance against the target.

## How to interpret it

* When `current_auc` hovers near the baseline, the model is performing as expected.
* Drops below the baseline line indicate periods of degraded discrimination.
* Spikes above may reflect favorable data shifts or seasonal patterns — investigate whether they represent genuine improvement.
* Pair with the **AUC Relative Decrease** plot to see both the absolute and proportional view of drift.
