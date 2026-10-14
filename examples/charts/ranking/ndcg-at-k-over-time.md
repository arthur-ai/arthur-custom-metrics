# Chart: NDCG@K Over Time

## Metrics Used

From **Top-K Ranking Quality**:
* `ndcg_at_k` — Normalized Discounted Cumulative Gain at K
* `map_at_k` — Mean Average Precision at K

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
    WHEN metric_name = 'ndcg_at_k' THEN 'NDCG@K'
    WHEN metric_name = 'map_at_k'  THEN 'MAP@K'
    ELSE metric_name
  END AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN ('ndcg_at_k', 'map_at_k')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

Two lines on a 0–1 scale: how well each day's slates placed the items users engaged with near the top. NDCG@K rewards relevant items in high positions with a logarithmic discount; MAP@K rewards relevant items appearing early and densely. They usually move together.

## How to interpret it

* **Flat lines at the baseline** — the ranker is stable; absolute level depends on K and engagement sparsity, so judge movement, not the number
* **Both lines step down at a date** — almost always a model deployment or a change in how `position` is logged; check `model_version`
* **Gradual decline over weeks** — relevance drift; users' interests moved and the ranker has not been retrained
* **NDCG falls while MAP is flat** — the top position specifically is getting worse (NDCG weights position 1 most)
* **Spiky daily values** — low request volume; overlay `ranking_request_count` or switch to weekly buckets

**Visualization tip**: line chart; add a horizontal reference line at the trailing 28-day mean and alert on a relative drop (for example 10%).
