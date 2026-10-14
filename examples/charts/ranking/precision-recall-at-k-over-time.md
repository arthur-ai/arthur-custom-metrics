# Chart: Precision and Recall@K Over Time

## Metrics Used

From **Top-K Ranking Quality**:
* `precision_at_k` — share of top-K slots filled with relevant items
* `recall_at_k` — share of each request's relevant items that made the top K
* `evaluable_request_ratio` — share of requests with any relevant item

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
    WHEN metric_name = 'precision_at_k'          THEN 'Precision@K'
    WHEN metric_name = 'recall_at_k'             THEN 'Recall@K'
    WHEN metric_name = 'evaluable_request_ratio' THEN 'Requests with engagement'
    ELSE metric_name
  END AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN ('precision_at_k', 'recall_at_k', 'evaluable_request_ratio')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

Three lines: Precision@K (bounded by how many items a user engages with per slate, so typically low), Recall@K (how much of the engaged set sits in the top K, typically high), and the share of requests that had any engagement at all.

## How to interpret it

* **Recall@K falls, engagement share flat** — relevant items are increasingly ranked below K. An ordering problem.
* **Engagement share falls, Recall@K flat** — users engage less, but when they do, the ranking is fine. A retrieval, content, or traffic-mix problem rather than an ordering one.
* **Precision@K rises with engagement share** — users are engaging with more items per slate; the ranking metrics will look better without the model changing
* **Precision@K ceiling** — with one engaged item per slate, Precision@10 cannot exceed 0.1. Do not alert on absolute Precision@K; alert on relative change.

**Visualization tip**: put Precision@K on a secondary axis, or plot it separately, since its scale is much smaller than Recall@K.
