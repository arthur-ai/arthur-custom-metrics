# Plot 1: AUPRC Over Time

## Metrics Used

* `auprc`
* `average_precision`

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
        WHEN metric_name = 'auprc' THEN 'AUPRC (Trapezoidal)'
        WHEN metric_name = 'average_precision' THEN 'Average Precision'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'auprc',
    'average_precision'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot tracks both **AUPRC** (trapezoidal rule) and **Average Precision** (step-function) over time, providing two views of precision-recall performance.

## How to interpret it

* Values close to **1.0** mean the model achieves high precision at all recall levels — strong positive-class detection with few false positives.
* Values near the **prevalence rate** (proportion of positives) indicate performance no better than random.
* Sustained **drops** signal degrading ability to reliably identify positives, even if AUC-ROC appears stable.
* The two variants typically agree closely; large divergence may indicate noisy or sparse data in a time bucket.
