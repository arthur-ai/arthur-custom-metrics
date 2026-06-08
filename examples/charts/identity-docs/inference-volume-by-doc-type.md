# Inference Volume by Document Type

## Metrics Used

* `inference_count` — segmented by `document_type`

## Axes

* **X axis:** Date (`time_bucket_1d`)
* **Y axis:** Inference Count (`metric_value`)
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
    COALESCE(SUM(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name = 'inference_count'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, document_type
ORDER BY time_bucket_1d, document_type;
```

## What this shows

Daily count of inferences processed, split by `driver_license` vs `passport`. Useful as a context layer when reading accuracy charts — accuracy swings on low-volume days carry less weight.

## How to interpret it

* **Sudden volume spike**: could mean a batch job or backfill was processed; accuracy metrics on that day may not be representative.
* **Volume drop to zero**: data pipeline outage or upstream integration failure.
* **Passport share increasing**: the model may begin to see a different mix than it was trained on, which can affect per-type accuracy benchmarks.
