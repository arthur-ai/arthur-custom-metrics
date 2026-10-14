# Chart: Calibration Ratio Over Time

## Metrics Used

From **Calibration Profile**:
* `calibration_ratio` — Σ predicted probability / Σ observed positives
* `avg_predicted_probability` — mean predicted probability
* `observed_positive_rate` — observed positive rate

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
    WHEN metric_name = 'calibration_ratio'         THEN 'Calibration Ratio'
    WHEN metric_name = 'avg_predicted_probability' THEN 'Avg Predicted'
    WHEN metric_name = 'observed_positive_rate'    THEN 'Observed Rate'
    ELSE metric_name
  END AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN ('calibration_ratio', 'avg_predicted_probability', 'observed_positive_rate')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

The calibration ratio with a reference line at 1.0, plus the two rates that make it up. When the predicted and observed lines diverge, the ratio moves away from 1.

## How to interpret it

* **Ratio within 0.95–1.05** — aggregate calibration is healthy; bids and expected-value estimates can be trusted
* **Ratio steps above 1 at a deployment while observed rate is flat** — the new model's scores are inflated; it will over-bid or over-forecast until recalibrated
* **Observed rate drops while predicted is flat** — the environment changed (seasonality, traffic mix) and the model is stale; ratio rises
* **Ratio spikes in the most recent days only** — delayed labels; conversions have not matured yet. Wait, or exclude immature buckets.
* **Ratio slowly trends down** — under-prediction growing; in ads this means losing auctions you should have won

**Visualization tip**: plot the ratio on its own axis with a horizontal line at 1.0 and a shaded tolerance band (e.g. ±5%); plot the two rates on a secondary axis.
