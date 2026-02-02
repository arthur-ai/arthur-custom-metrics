# Plot 3: Spearman + Kendall Combined

## Metrics Used

* `spearman_rho`
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

	metric_name,
	CASE
        WHEN metric_name = 'spearman_rho'      THEN 'Spearman Rank Correlation'
        WHEN metric_name = 'kendall_tau'     THEN 'Kendall Tau'
        ELSE metric_name
    END AS friendly_name,


  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'kendall_tau',
    'spearman_rho'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

## What this shows

This combined plot overlays both **Spearman** and **Kendall** rank correlations.

## How to interpret it

* When both move together, you have a consistent picture of ranking quality.
* If they diverge—e.g., Spearman stable but Kendall falling—it may indicate that ranking issues are concentrated in specific regions or pairs.
* This is a powerful diagnostic for evaluating whether a new model actually improves **ordering**, not just threshold metrics.
