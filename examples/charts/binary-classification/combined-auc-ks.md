# Plot 3: Combined AUC + KS

## Metrics Used

* `auc_roc`
* `ks_statistic`
* `ks_score`

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
        WHEN metric_name = 'auc_roc'      THEN 'ROC AUC'
        WHEN metric_name = 'ks_statistic' THEN 'KS Statistic'
        WHEN metric_name = 'ks_score'     THEN 'KS Score'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'auc_roc',
    'ks_statistic',
    'ks_score'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot overlays **global ranking quality** (AUC) with **maximum local separation** (KS) on the same time axis.

## How to interpret it

* When AUC and KS move together, the model's ranking power is consistently changing.
* Divergence (e.g., AUC flat, KS moving) suggests that certain score regions become more/less separative even though global ranking is unchanged.
* This is an excellent high-level monitoring view for risk committees and model governance reviews.
