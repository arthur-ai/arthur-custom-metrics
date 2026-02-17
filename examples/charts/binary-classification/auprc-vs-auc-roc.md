# Plot 2: AUPRC vs AUC-ROC Comparison

## Metrics Used

* `auprc`
* `auc_roc` (from the Curve-Based Discrimination metric)

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
        WHEN metric_name = 'auprc'   THEN 'AUPRC'
        WHEN metric_name = 'auc_roc' THEN 'AUC ROC'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'auprc',
    'auc_roc'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot overlays **AUPRC** and **AUC-ROC** on the same time axis, highlighting cases where one metric tells a different story than the other.

## How to interpret it

* **AUC-ROC high, AUPRC low**: The model ranks well overall but struggles with the positive class — common in highly imbalanced datasets where high true-negative count inflates AUC-ROC.
* **Both declining together**: Broad model degradation affecting all aspects of discrimination.
* **AUPRC declining, AUC-ROC stable**: The model is losing precision at high-recall operating points — the most actionable signal for imbalanced problems.
* This comparison is essential for **imbalanced classification** (fraud, rare disease, anomaly detection) where AUC-ROC alone can be misleading.
