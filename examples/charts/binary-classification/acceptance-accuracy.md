# Plot 2: Acceptance + Accuracy

## Metrics Used

* `correct_acceptance_rate`
* `valid_detection_rate`

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
        WHEN metric_name = 'valid_detection_rate'      THEN 'Valid Detection Rate'
        WHEN metric_name = 'correct_acceptance_rate' THEN 'Correct Acceptance Rate'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'valid_detection_rate',
    'correct_acceptance_rate'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

This plot focuses on **how many cases are correctly picked up as positive** (correct_acceptance_rate) vs **how often the model is right overall** (valid_detection_rate).

## How to interpret it

* Points with **high valid_detection_rate but low correct_acceptance_rate** mean the model is accurate but conservative—good at saying "no," not at finding positives.
* Points with **high correct_acceptance_rate but modest valid_detection_rate** indicate the model is catching many positives but also making more mistakes elsewhere.
* This is a good "business-friendly" view when explaining model performance to non-ML stakeholders.
