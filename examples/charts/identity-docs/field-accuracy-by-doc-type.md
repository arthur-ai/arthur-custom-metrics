# Field Accuracy by Document Type

## Metrics Used

* `numeric_sum` (column: `field_accuracy`) — segmented by `document_type`

## Axes

* **X axis:** Date (`time_bucket_1d`)
* **Y axis:** Field Accuracy (`metric_value`, 0–1)
* **Series:** Document Type (`document_type`)

## SQL Query

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,
    dimensions ->> 'document_type' AS document_type,
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name = 'numeric_sum'
  AND dimensions ->> 'column_name' = 'field_accuracy'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, document_type
ORDER BY time_bucket_1d, document_type;
```

## What this shows

Displays the average fraction of fields correctly extracted per inference over time, separately for driver licenses and passports, enabling direct comparison of extraction quality between the two document types.

## How to interpret it

* A value of **1.0** means every inference that day had all fields extracted correctly; values below 1.0 reflect partial extraction errors on some inferences.
* A **persistent gap** between driver license and passport lines indicates the model is structurally better or worse at one document type.
* A **gradual decline** in either line can signal model drift or a shift in image quality before the hard extraction pass rate threshold is breached.
* Cross-reference with `image_quality_score` to determine whether accuracy changes track with input quality changes.
