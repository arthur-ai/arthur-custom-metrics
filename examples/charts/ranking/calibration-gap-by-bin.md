# Chart: Calibration Gap by Score Bin Over Time

## Metrics Used

From **Reliability Diagram Bins**:
* `reliability_calibration_gap` — predicted rate minus observed rate per score bin (dimension: `score_bin`)

## SQL Query

```sql
SELECT
  time_bucket_gapfill(
    '1 day',
    timestamp,
    '{{dateStart}}'::timestamptz,
    '{{dateEnd}}'::timestamptz
  ) AS time_bucket_1d,

  dimensions->>'score_bin' AS score_bin,

  AVG(value) AS calibration_gap

FROM metrics_numeric_latest_version
WHERE metric_name = 'reliability_calibration_gap'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, score_bin
ORDER BY time_bucket_1d, score_bin;
```

## What this shows

A heatmap (or one line per bin) of how far each score range is from calibrated over time. Positive values are over-prediction, negative are under-prediction, zero is calibrated.

## How to interpret it

* **A whole column turns positive on one day** — all bins shifted at once; a global score inflation (deployment or feature change). A single bid multiplier would correct it.
* **Only the top rows turn positive** — over-confidence concentrated in high scores; needs per-bin recalibration
* **Alternating signs across bins** — compressed or S-shaped probabilities; the aggregate calibration ratio may look fine while ECE rises
* **Noisy top rows** — sparse bins; filter to bins with meaningful `reliability_bin_share` or widen the time bucket

**Visualization tip**: heatmap with a diverging color scale centered at 0, bins on the y-axis, time on the x-axis.
