# Inference Volume by Image Quality Band

## Metrics Used

* `inference_count` — segmented by `image_quality_band`

## Axes

* **X axis:** Date (`time_bucket_1d`)
* **Y axis:** Inference Count (`inference_count`)
* **Series:** Image Quality Band (`image_quality_band`)

## SQL Query

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,
    dimensions ->> 'image_quality_band' AS image_quality_band,
    COALESCE(SUM(value), 0) AS inference_count

FROM metrics_numeric_latest_version
WHERE metric_name = 'inference_count'
  AND dimensions ->> 'image_quality_band' IS NOT NULL
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, image_quality_band
ORDER BY time_bucket_1d, image_quality_band;
```

## What this shows

Daily inference volume broken down by image quality band (`high`, `medium`, `low`). Shows whether the mix of image quality coming into the system is shifting over time — a leading indicator for accuracy degradation before it appears in extraction metrics.

## How to interpret it

* **Low-band share growing**: more poor-quality images are being submitted, which typically precedes drops in OCR confidence and field match rates within a few days.
* **High-band share growing**: improving upstream image capture; field accuracy improvements may follow.
* **All bands dropping uniformly**: volume decline regardless of quality — likely an upstream pipeline or ingestion issue, not a quality issue.
* Cross-reference with `image_quality_score` and `ocr_confidence` trends to confirm whether quality-mix shifts are affecting extraction outcomes.
