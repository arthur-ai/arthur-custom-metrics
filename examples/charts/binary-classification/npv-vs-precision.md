# Plot 2: NPV vs Precision

## Metrics Used

* `npv`
* `precision` (from the Detection & Acceptance Profile metric)

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
        WHEN metric_name = 'npv'       THEN 'NPV (Negative Predictive Value)'
        WHEN metric_name = 'precision' THEN 'Precision (PPV)'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'npv',
    'precision'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot overlays **NPV** and **Precision (PPV)** to show predictive quality of both decision buckets — "how trustworthy are the negatives?" vs "how trustworthy are the positives?"

## How to interpret it

* **Both high**: The model's predictions are reliable in both directions.
* **Precision high, NPV low**: The model is conservative — what it flags is usually right, but it misses many positives (they leak into the negative bucket).
* **Precision low, NPV high**: The model is aggressive — it catches most positives but also flags many negatives incorrectly.
* This trade-off view helps calibrate the decision threshold for the right balance.
