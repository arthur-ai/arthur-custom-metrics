# OCR Confidence by Document Type

## Metrics Used

* `numeric_sum` (column: `ocr_confidence`) — segmented by `document_type`

## Axes

* **X axis:** Date (`time_bucket_1d`)
* **Y axis:** OCR Confidence (`metric_value`, 0–1)
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
  AND dimensions ->> 'column_name' = 'ocr_confidence'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, document_type
ORDER BY time_bucket_1d, document_type;
```

## What this shows

Average OCR confidence score per day, split by document type. OCR confidence is an upstream signal — drops here often precede drops in field match rates by a short lag, making this useful for early detection.

## How to interpret it

* **OCR confidence dropping before field match rates drop**: the model is reading text less confidently, which will manifest as extraction errors soon.
* **Persistent gap between driver_license and passport**: one document type may consistently have lower image quality submissions (e.g., photos taken in low light vs scans).
* Alert threshold: sustained average below 0.75 warrants investigation of the ingestion pipeline.
