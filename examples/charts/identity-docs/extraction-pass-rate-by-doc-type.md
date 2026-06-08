# Extraction Pass Rate by Document Type

## Metrics Used

* `numeric_sum` (column: `field_accuracy`) — fraction where value = 1.0, segmented by `document_type`

## Axes

* **X axis:** Date (`time_bucket_1d`)
* **Y axis:** Pass Rate (`extraction_pass_rate`, 0–1)
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
    COALESCE(AVG(CASE WHEN value = 1.0 THEN 1.0 ELSE 0.0 END), 0) AS extraction_pass_rate

FROM metrics_numeric_latest_version
WHERE metric_name = 'numeric_sum'
  AND dimensions ->> 'column_name' = 'field_accuracy'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, document_type
ORDER BY time_bucket_1d, document_type;
```

## What this shows

Tracks the share of inferences where all extracted attributes were correct (i.e., `field_accuracy = 1.0`), split by `driver_license` vs `passport`. This is the hard pass/fail rollup — an inference either got every field right or it didn't.

## How to interpret it

* A **low pass rate** means most inferences get at least one field wrong, even if average field accuracy looks reasonable. A model with 0.9 average field accuracy can still have a sub-0.5 pass rate if errors are spread across different fields per inference.
* Compare this chart against the per-field match rate charts to identify which specific fields are pulling down the rollup.
* Driver license and passport extract different field sets, so separate lines prevent one document type masking the other.
