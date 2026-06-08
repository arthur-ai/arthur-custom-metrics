# Classification Accuracy by Document Type

## Metrics Used

* `classification_accuracy_rate_metric` — segmented by `document_type`

## Axes

* **X axis:** Date (`time_bucket_1d`)
* **Y axis:** Accuracy Rate (`metric_value`, 0–1)
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
WHERE metric_name = 'classification_accuracy_rate_metric'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, document_type
ORDER BY time_bucket_1d, document_type;
```

## What this shows

Tracks how often the model's classification prediction (`validation_pred`) matches the ground truth (`extraction_valid`) over time, broken out by `driver_license` vs `passport`. A single series per document type — one line for each.

## How to interpret it

* A **sustained drop** in one document type but not the other suggests the model is degrading on that specific doc class (e.g., new passport formats not in training data).
* Both lines dropping simultaneously indicates a systemic issue — data pipeline, OCR quality, or model regression.
* Target: both lines ≥ 0.90. Alert if either drops below 0.85 for 2+ consecutive days.
