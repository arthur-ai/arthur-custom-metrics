# Plot 1: Spearman Over Time

## Metrics Used

* `spearman_rho`

## SQL Query

```sql
SELECT
  time_bucket_gapfill(
    '1 day',
    timestamp,
    '{{dateStart}}'::timestamptz,
    '{{dateEnd}}'::timestamptz
  ) AS time_bucket_1d,

  'spearman_rho' AS metric_name,
  'Spearman Rank Correlation' AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name = 'spearman_rho'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

## What this shows

This plot tracks how strongly **score rankings** align with **target rankings** over time.

## How to interpret it

* Higher `spearman_rho` means that as scores increase, targets generally increase too (good ordering).
* Drops in Spearman often show that the model's ranking power is weakening, even if thresholded metrics (like accuracy) look stable.
* Particularly useful in prioritization use cases (e.g., lead scoring, collections).
