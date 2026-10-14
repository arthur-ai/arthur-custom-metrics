# Chart: Catalog Coverage Over Time

## Metrics Used

From **Catalog Coverage and Exposure**:
* `catalog_coverage` — share of the catalog served at least once
* `effective_catalog_size` — exp(entropy) of the exposure distribution
* `items_served` — distinct items served

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
    WHEN metric_name = 'catalog_coverage'       THEN 'Catalog Coverage'
    WHEN metric_name = 'effective_catalog_size' THEN 'Effective Catalog Size'
    WHEN metric_name = 'items_served'           THEN 'Items Served'
    ELSE metric_name
  END AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN ('catalog_coverage', 'effective_catalog_size', 'items_served')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

How much of the catalog the ranker actually uses each day. Coverage is a ratio (0–1); items served and effective catalog size are item counts. The gap between items served and effective catalog size shows how many items get only token exposure.

## How to interpret it

* **Coverage and effective size fall together after a retrain** — popularity feedback loop; the model is learning from its own popular picks
* **Coverage falls but effective size is flat** — fewer long-tail items get any exposure, but the core set is unchanged; often a candidate-generator or eligibility change
* **Items served rises, effective size flat** — new items are entering the slate lightly; healthy cold-start behavior
* **Coverage tracks traffic volume** — expected; normalize by looking at effective catalog size or Gini when volume changes

**Visualization tip**: coverage on a 0–1 axis; items served and effective catalog size on a secondary count axis.
