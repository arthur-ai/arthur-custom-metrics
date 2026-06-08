# Image Quality Score by Document Type

## Metrics Used

* `numeric_sum` (column: `image_quality_score`) — segmented by `document_type`

## Axes

* **X axis:** Date (`time_bucket_1d`)
* **Y axis:** Image Quality Score (`metric_value`, 0–1)
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
  AND dimensions ->> 'column_name' = 'image_quality_score'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, document_type
ORDER BY time_bucket_1d, document_type;
```

## What this shows

Average image quality score per day by document type. Unlike OCR confidence (which reflects how well the model read the text), image quality score reflects the raw quality of the submitted image before extraction — blur, lighting, resolution.

## How to interpret it

* **Quality score stable, OCR confidence dropping**: the images are fine but the model is struggling — possible model regression.
* **Quality score dropping, OCR confidence dropping**: upstream image capture issue (e.g., camera settings change, new mobile app version).
* **Quality score dropping, field match rates stable**: the model may be robust enough to handle lower-quality images — useful to know before making pipeline changes.
