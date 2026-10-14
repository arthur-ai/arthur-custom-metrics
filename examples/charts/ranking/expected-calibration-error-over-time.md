# Chart: Expected Calibration Error Over Time

## Metrics Used

From **Calibration Profile**:
* `expected_calibration_error` — volume-weighted mean |predicted − observed| across score bins
* `max_calibration_error` — worst single bin

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
    WHEN metric_name = 'expected_calibration_error' THEN 'ECE'
    WHEN metric_name = 'max_calibration_error'      THEN 'MCE'
    ELSE metric_name
  END AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN ('expected_calibration_error', 'max_calibration_error')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

ECE is the headline calibration quality number (lower is better). MCE is the worst bin and is much noisier because it is usually driven by a sparse high-score bin.

## How to interpret it

* **ECE below ~0.01** — excellent; **0.01–0.03** — acceptable for most ad systems; **above 0.05** — investigate with the reliability diagram
* **ECE rises while the calibration ratio stays near 1** — offsetting errors: over-predicting in some bins, under-predicting in others. Needs per-bin recalibration, not a global multiplier.
* **MCE jumps with flat ECE** — a thin bin went wrong; check `reliability_bin_share` before acting
* **ECE steps up at a deployment** — the new model's probability scale differs; recalibrate before full ramp

**Visualization tip**: line chart; consider plotting MCE with a lighter color or dashed line so the noisier series does not dominate.
