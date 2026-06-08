# Processing Time by Document Type

## Metrics Used

* `numeric_sum` (column: `processing_time_ms`) — segmented by `document_type`

## Axes

* **X axis:** Date (`time_bucket_1d`)
* **Y axis:** Processing Time (`avg_processing_time_ms` / `p95_processing_time_ms`, ms)
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
    COALESCE(AVG(value), 0) AS avg_processing_time_ms,
    COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value), 0) AS p95_processing_time_ms

FROM metrics_numeric_latest_version
WHERE metric_name = 'numeric_sum'
  AND dimensions ->> 'column_name' = 'processing_time_ms'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, document_type
ORDER BY time_bucket_1d, document_type;
```

## What this shows

Average and 95th-percentile processing latency per day by document type. Both aggregates are computed directly from the raw per-inference values, giving a central-tendency view (avg) and a tail-latency view (p95) segmented by `driver_license` vs `passport`.

## How to interpret it

* A **widening gap** between p95 and average indicates increasing latency variance — a small fraction of inferences are taking much longer, which can signal hard or unusual inputs.
* A **rising average without a rising p95** suggests broad, uniform slowdowns rather than isolated edge cases.
* Sudden spikes in **p95 only** often correlate with low-quality or complex images that require more processing cycles.
* Monitor both lines against SLA thresholds — the p95 line is the more conservative and appropriate target for latency SLAs.
