# Plot 1: AUC Relative Decrease Over Time

## Metrics Used

* `auc_relative_decrease`

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
        WHEN metric_name = 'auc_relative_decrease' THEN 'AUC Relative Decrease (%)'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'auc_relative_decrease'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot tracks the **percentage decrease** in AUC-ROC from the baseline over time. The zero line represents parity with the baseline model.

## How to interpret it

* Values **at or near 0%** mean the model is performing in line with the baseline.
* **Positive values** indicate degradation — the higher the value, the more AUC has dropped relative to the baseline.
* **Negative values** indicate the model is outperforming the baseline.
* Sustained upward trends suggest progressive model decay and may warrant retraining or investigation.
* Ideal for **guardrail alerts** (e.g., "alert if relative decrease exceeds 5%").
