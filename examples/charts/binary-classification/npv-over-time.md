# Plot 1: NPV Over Time

## Metrics Used

* `npv`
* `specificity`

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
        WHEN metric_name = 'npv'         THEN 'Negative Predictive Value'
        WHEN metric_name = 'specificity' THEN 'Specificity (TNR)'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'npv',
    'specificity'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot tracks both **Negative Predictive Value** and **Specificity** over time, providing a complete view of the model's negative-class behavior.

## How to interpret it

* **NPV dropping** means more actual positives are leaking into the negative bucket — the model is missing true positives.
* **Specificity dropping** means the model is incorrectly flagging more true negatives as positive — increased false alarm rate.
* When both drop simultaneously, the model is degrading broadly on negative-class handling.
* NPV is particularly sensitive to **prevalence**: when positives are rare, NPV can appear high even with poor recall. Always pair with recall for a complete picture.
