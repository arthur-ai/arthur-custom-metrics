# Chart: Exposure Concentration Over Time

## Metrics Used

From **Catalog Coverage and Exposure**:
* `top_n_exposure_share` — share of impressions on the N most-served items
* `exposure_gini` — Gini coefficient of impressions across the catalog

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
    WHEN metric_name = 'top_n_exposure_share' THEN 'Top-N Exposure Share'
    WHEN metric_name = 'exposure_gini'        THEN 'Exposure Gini'
    ELSE metric_name
  END AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN ('top_n_exposure_share', 'exposure_gini')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

Two concentration measures on a 0–1 scale. Top-N share is the intuitive "head" share (how much traffic goes to the N biggest items); Gini summarizes inequality across the whole catalog, counting unserved items as zero.

## How to interpret it

* **Both rising** — exposure is concentrating; long-tail items and advertisers are losing delivery
* **Top-N share rising, Gini flat** — the head is growing at the expense of the middle, while the tail was already unserved
* **Gini rising, Top-N share flat** — the tail is thinning out (coverage dropping) without the head changing
* **Step change at a deployment** — compare against the reference dataset or the previous model version; decide whether the engagement gain justifies the concentration

**Visualization tip**: line chart; mark deployments and campaign launches as vertical annotations, since both commonly cause concentration spikes.
