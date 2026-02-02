# Plot 3: Detection vs Acceptance Trade-Off

## Metrics Used

* `true_positive_rate`
* `correct_acceptance_rate`

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
        WHEN metric_name = 'true_positive_rate'      THEN 'True Positive Rate (Recall)'
        WHEN metric_name = 'correct_acceptance_rate' THEN 'Correct Acceptance Rate'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'true_positive_rate',
    'correct_acceptance_rate'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot is a **trade-off curve** between **recall** (`true_positive_rate`) and **how much correctly-accepted positive volume you get** (`correct_acceptance_rate`) as you move the threshold.

## How to interpret it

* Moving along the curve corresponds to adjusting the threshold.
* Regions where **small increases in acceptance yield big gains in recall** are often attractive operating points.
* If the curve is very flat, the model may lack discriminative power in the relevant region, and you may need feature or model improvements rather than threshold tweaks.
