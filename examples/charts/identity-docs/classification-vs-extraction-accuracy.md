# Classification Accuracy vs Field Accuracy

## Metrics Used

* `classification_accuracy_rate_metric`
* `numeric_sum` (column: `field_accuracy`)

## Axes

* **X axis:** Date (`time_bucket_1d`)
* **Y axis:** Accuracy Rate (`metric_value`, 0–1)
* **Series:** Metric (`friendly_name`)

## SQL Query

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,
    CASE
        WHEN metric_name = 'classification_accuracy_rate_metric' THEN 'Classification Accuracy'
        WHEN dimensions ->> 'column_name' = 'field_accuracy'    THEN 'Field Accuracy'
    END AS friendly_name,
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE (
    metric_name = 'classification_accuracy_rate_metric'
    OR (metric_name = 'numeric_sum' AND dimensions ->> 'column_name' = 'field_accuracy')
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, friendly_name
ORDER BY time_bucket_1d, friendly_name;
```

## What this shows

Side-by-side trend of the two top-level accuracy signals: whether the model correctly classified the document type vs the average fraction of fields it extracted correctly per inference. These measure different failure modes — classification is about document type recognition, field accuracy is about per-field extraction quality.

## How to interpret it

* **Classification high, field accuracy low**: The model identifies the document correctly but struggles to read specific fields (e.g., poor OCR on expiry dates).
* **Field accuracy high, classification low**: Fields are extracted correctly but the model sometimes misidentifies which document type it's processing.
* **Both dropping together**: Systemic issue — likely image quality degradation or a model regression.
* Field accuracy is a continuous 0–1 score per inference; classification accuracy is binary. Both are averaged daily, so they are directly comparable on the same chart.
