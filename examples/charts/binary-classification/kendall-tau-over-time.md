# Plot 2: Kendall Tau Over Time

## Metrics Used

* `kendall_tau`

## SQL Query

```sql
SELECT
  time_bucket_gapfill(
    '1 day',
    timestamp,
    '{{dateStart}}'::timestamptz,
    '{{dateEnd}}'::timestamptz
  ) AS time_bucket_1d,

  'kendall_tau' AS metric_name,
  'Kendall Tau' AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name = 'kendall_tau'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

## What this shows

This plot shows Kendall's τ, which measures **pairwise agreement** in ranking between scores and targets.

## How to interpret it

* Unlike Spearman, Kendall focuses on how many pairs are ordered correctly vs incorrectly.
* It can be more robust to outliers, so divergences between Spearman and Kendall might highlight unusual target distributions.
* If your DB doesn't provide Kendall natively, you can still reserve this plot for offline-computed metrics.
