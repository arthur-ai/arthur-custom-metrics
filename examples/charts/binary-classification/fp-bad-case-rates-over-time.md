# Plot 1: FP & Bad Case Rates Over Time

## Metrics Used

* `adjusted_false_positive_rate`
* `false_positive_ratio`
* `total_false_positive_rate`
* `bad_case_rate`

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
        WHEN metric_name = 'adjusted_false_positive_rate' THEN 'Adjusted False Positive Rate'
        WHEN metric_name = 'false_positive_ratio'         THEN 'False Positive Ratio'
        WHEN metric_name = 'total_false_positive_rate'    THEN 'Total False Positive Rate'
        WHEN metric_name = 'bad_case_rate'                THEN 'Bad Case Rate'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'adjusted_false_positive_rate',
    'false_positive_ratio',
    'total_false_positive_rate',
    'bad_case_rate'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot trends multiple notions of "false positives" and "bad outcomes" over time. It lets you see whether the model is:

* Flagging too many negatives as positives (`adjusted_false_positive_rate` / `total_false_positive_rate`)
* Putting too many negatives into the positive bucket (`false_positive_ratio`)
* Over-classifying cases as bad overall (`bad_case_rate`)

## How to interpret it

* **Spikes** in any FP-related line often correspond to data issues, model regressions, or policy changes.
* A **rising bad_case_rate** without business explanation may mean the model is over-declining / over-rejecting.
* If FP rates increase while business KPIs worsen, this is a strong signal that thresholds or retraining should be reviewed.
