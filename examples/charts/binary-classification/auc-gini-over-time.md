# Plot 1: AUC + Gini Over Time

## Metrics Used

* `auc_roc`
* `gini_coefficient`

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
        WHEN metric_name = 'auc_roc' THEN 'AUC ROC'
        WHEN metric_name = 'gini_coefficient'     THEN 'Gini Coefficient'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'auc_roc',
    'gini_coefficient'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot tracks both **AUC** and its corresponding **Gini** coefficient over time, providing two familiar views of discrimination strength.

## How to interpret it

* Sustained **drops in auc_roc** or **gini_coefficient** usually indicate that the model's ability to separate positives from negatives has degraded.
* If AUC remains stable while business KPIs worsen, the issue may be threshold selection or data mix, not raw score discrimination.
* Gini is often the metric business stakeholders and regulators expect in credit/risk settings, so having both on one chart helps bridge ML and business views.
