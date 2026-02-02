# Plot 1: Recall Variants Over Time

## Metrics Used

* `capture_rate`
* `correct_detection_rate`
* `true_detection_rate`
* `true_positive_rate`

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
        WHEN metric_name = 'true_detection_rate'	   THEN 'True Detection Rate'
        WHEN metric_name = 'capture_rate'						 THEN 'Capture Rate'
		WHEN metric_name = 'true_positive_rate'			 THEN 'True Positive Rate'
        WHEN metric_name = 'correct_acceptance_rate' THEN 'Correct Acceptance Rate'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'true_detection_rate',
	  'capture_rate',
  	'true_positive_rate',
		'correct_acceptance_rate'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

For each day and threshold, this plot shows how **volume**, **accuracy**, **precision**, and **recall** move together. It lets you see how different operating points behave over time.

## How to interpret it

* Use vertical slices (fixed `day`) to compare thresholds and choose an operating point.
* Use horizontal slices (fixed `threshold`) to see whether recall or precision is drifting.
* If `capture_rate` is stable but `true_detection_rate` drops, the model is accepting the same volume but with worse quality (precision regression).
