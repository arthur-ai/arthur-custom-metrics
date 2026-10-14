# Chart: Slate Diversity Over Time

## Metrics Used

From **Slate Diversity**:
* `intra_list_diversity` — share of item pairs in a slate with different categories
* `normalized_category_entropy` — normalized entropy of the slate's category mix
* `single_category_slate_ratio` — share of slates with a single category

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
    WHEN metric_name = 'intra_list_diversity'         THEN 'Intra-List Diversity'
    WHEN metric_name = 'normalized_category_entropy'  THEN 'Category Entropy (normalized)'
    WHEN metric_name = 'single_category_slate_ratio'  THEN 'Single-Category Slates'
    ELSE metric_name
  END AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN ('intra_list_diversity', 'normalized_category_entropy', 'single_category_slate_ratio')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

How mixed each day's slates are. The two diversity measures should sit near a stable baseline; the single-category ratio should sit near zero.

## How to interpret it

* **Diversity drops after a retrain** — the ranker is stacking categories; check whether engagement actually improved before accepting it
* **Single-category ratio spikes** — a category boost, campaign override, or candidate filter bug produced monotone slates
* **Diversity rises with a drop in ranking metrics** — a diversity re-ranker may be over-correcting
* **Entropy and intra-list diversity diverge** — entropy is more sensitive to one dominant category, intra-list diversity to many small clusters; both together point to the shape of the problem

**Visualization tip**: line chart; overlay `avg_slate_size` from the same metric if slates can be truncated, since smaller slates mechanically change pair counts.
