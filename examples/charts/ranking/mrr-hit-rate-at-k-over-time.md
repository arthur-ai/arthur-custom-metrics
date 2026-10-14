# Chart: MRR and Hit Rate@K Over Time

## Metrics Used

From **Top-K Ranking Quality**:
* `mrr_at_k` — Mean Reciprocal Rank of the first relevant item
* `hit_rate_at_k` — share of evaluable requests with a relevant item in the top K

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
    WHEN metric_name = 'mrr_at_k'      THEN 'MRR@K'
    WHEN metric_name = 'hit_rate_at_k' THEN 'Hit Rate@K'
    ELSE metric_name
  END AS friendly_name,

  COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN ('mrr_at_k', 'hit_rate_at_k')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

Hit Rate@K answers "did the user find something in the first K items"; MRR@K answers "how far down was it". MRR is always at or below Hit Rate, and the gap between them is the average depth of the first relevant item.

## How to interpret it

* **Hit Rate flat, MRR falling** — the right item is still in the top K but drifting lower. A subtle ranker regression that click-through rate alone would miss.
* **Both falling together** — relevant items are leaving the top K entirely
* **MRR near Hit Rate** — the first relevant item is nearly always at position 1 (typical for strong search ranking)
* **MRR around half of Hit Rate** — the first relevant item averages position 2; acceptable for feeds, poor for search

**Visualization tip**: line chart with both series on the same 0–1 axis; shade the area between them to visualize depth-to-first-hit.
