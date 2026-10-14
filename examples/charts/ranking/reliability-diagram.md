# Chart: Reliability Diagram

## Metrics Used

From **Reliability Diagram Bins**:
* `reliability_predicted_rate` — mean predicted probability per score bin (dimension: `score_bin`)
* `reliability_observed_rate` — observed positive rate per score bin (dimension: `score_bin`)
* `reliability_bin_share` — share of predictions per score bin (dimension: `score_bin`)

## SQL Query

```sql
SELECT
  dimensions->>'score_bin' AS score_bin,

  AVG(CASE WHEN metric_name = 'reliability_predicted_rate' THEN value END) AS predicted_rate,
  AVG(CASE WHEN metric_name = 'reliability_observed_rate'  THEN value END) AS observed_rate,
  AVG(CASE WHEN metric_name = 'reliability_bin_share'      THEN value END) AS bin_share

FROM metrics_numeric_latest_version
WHERE metric_name IN ('reliability_predicted_rate', 'reliability_observed_rate', 'reliability_bin_share')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY score_bin
ORDER BY score_bin;
```

## What this shows

One point per score bin: predicted rate on the x-axis, observed rate on the y-axis, averaged over the selected time range. A perfectly calibrated model lies on the diagonal `y = x`. Bin share gives each point its weight.

## How to interpret it

* **Points on the diagonal** — calibrated in that score range
* **Points below the diagonal at high scores** — over-confidence; the model's best candidates happen less often than claimed. In ads these are over-bid.
* **Points above the diagonal at low scores** — under-confidence in the tail; often from negative down-sampling without re-weighting
* **S-curve** — probabilities compressed toward the mean; a monotone recalibration (Platt or isotonic) fixes it
* **Large gaps only in bins with tiny share** — statistical noise; weight your judgement by `bin_share`

**Visualization tip**: scatter or line chart of `observed_rate` vs `predicted_rate` with a `y = x` reference line; size the markers by `bin_share`. Compare two date ranges side by side to see how a deployment changed the curve.
