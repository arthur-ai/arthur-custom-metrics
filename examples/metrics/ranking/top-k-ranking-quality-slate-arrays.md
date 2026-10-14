# Top-K Ranking Quality (Slate Arrays)

## Overview

This is the **array-layout variant** of [Top-K Ranking Quality](top-k-ranking-quality.md). It computes the same position-aware ranking metrics — **NDCG@K, MAP@K, MRR@K, Precision@K, Recall@K, Hit Rate@K** — for datasets that log **one row per request** with:

* an **ordered array** of recommended item IDs (array index = position), and
* an **array of engaged item IDs** (clicked, added to cart, purchased, watched…)

This layout is common when a recommender service logs the whole slate it returned, and the engagement set is joined on later from an events pipeline. Relevance is **binary** in this variant: an item is relevant if it appears in the engaged array.

Use the impression-level version instead if your dataset has one row per (request, position) or you need graded relevance.

## Metrics

For each request, let `recommended_items = [i_1, i_2, …, i_n]` (position = array index) and `engaged_items` be a set `E`.

```text
rel_p    = 1 if i_p ∈ E else 0
DCG@K    = Σ_{p=1..K} rel_p / log2(p + 1)
IDCG@K   = Σ_{p=1..min(K, |E|)} 1 / log2(p + 1)
NDCG@K   = DCG@K / IDCG@K
AP@K     = ( Σ_{p=1..K, rel_p = 1} precision@p ) / min(K, |E|)
RR@K     = 1 / (first p with rel_p = 1)   if that p <= K, else 0
Prec@K   = Σ_{p=1..K} rel_p / K
Recall@K = Σ_{p=1..K} rel_p / |E|
Hit@K    = 1 if Σ_{p=1..K} rel_p > 0 else 0
```

Note that `|E|` counts **all** engaged items, including ones that were never recommended. Those are misses and correctly lower Recall@K and NDCG@K. Requests with an empty engaged set are **not evaluable** and are excluded from the six ranking metrics; their share is reported via `evaluable_request_ratio`.

## Data Requirements

* `{{timestamp_col}}` — timestamp of the request
* `{{request_id_col}}` — unique request identifier
* `{{recommended_items_col}}` — ordered array (`TEXT[]` / list of strings) of recommended item IDs
* `{{engaged_items_col}}` — array of engaged item IDs (may be empty or NULL)
* `{{k}}` — cutoff depth (literal)
* `{{dataset}}` — dataset with one row per request

## Base Metric SQL

This SQL explodes the ordered recommendation array to recover positions, flags each position as relevant if the item is in the engaged array, and aggregates the ranking metrics per time bucket.

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{request_id_col}}::text                          AS request_id,
      COALESCE({{recommended_items_col}}, ARRAY[]::TEXT[]) AS recommended_items,
      COALESCE({{engaged_items_col}}, ARRAY[]::TEXT[])     AS engaged_items
    FROM
      {{dataset}}
    WHERE
      {{timestamp_col}} IS NOT NULL
      AND {{request_id_col}} IS NOT NULL
  ),

  -- Explode the ordered recommendation list; array index = position
  recommended AS (
    SELECT
      ts,
      request_id,
      unnest(recommended_items)::text              AS item_id,
      generate_subscripts(recommended_items, 1)    AS position
    FROM
      base
  ),

  -- Distinct set of engaged items per request (clicks, purchases, etc.)
  engaged AS (
    SELECT DISTINCT
      ts,
      request_id,
      unnest(engaged_items)::text AS item_id
    FROM
      base
  ),

  -- Flag each recommended item as relevant if it was engaged with
  ranked AS (
    SELECT
      r.ts,
      r.request_id,
      r.position,
      CASE WHEN e.item_id IS NOT NULL THEN 1 ELSE 0 END AS is_rel,
      SUM(CASE WHEN e.item_id IS NOT NULL THEN 1 ELSE 0 END) OVER (
        PARTITION BY r.ts, r.request_id
        ORDER BY r.position
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
      ) AS cum_rel
    FROM
      recommended r
      LEFT JOIN engaged e
        ON e.ts = r.ts
       AND e.request_id = r.request_id
       AND e.item_id = r.item_id
  ),

  -- Number of engaged items per request (recall denominator and IDCG basis).
  -- Items engaged but never recommended still count: they are misses.
  engaged_counts AS (
    SELECT
      ts,
      request_id,
      COUNT(*)::float AS rel_total
    FROM
      engaged
    WHERE
      item_id IS NOT NULL
      AND item_id <> ''
    GROUP BY
      ts,
      request_id
  ),

  -- IDCG@K for binary gain: sum of 1/log2(i+1) for i = 1..min(K, rel_total)
  ideal AS (
    SELECT
      ts,
      request_id,
      SUM(CASE WHEN ideal_rank <= {{k}}
               THEN 1.0 / (LN(ideal_rank + 1) / LN(2)) ELSE 0 END) AS idcg_k
    FROM (
      SELECT
        ts,
        request_id,
        ROW_NUMBER() OVER (PARTITION BY ts, request_id ORDER BY item_id) AS ideal_rank
      FROM
        engaged
      WHERE
        item_id IS NOT NULL
        AND item_id <> ''
    ) e
    GROUP BY
      ts,
      request_id
  ),

  per_request AS (
    SELECT
      b.ts,
      b.request_id,
      COALESCE(SUM(CASE WHEN r.position <= {{k}}
                        THEN r.is_rel / (LN(r.position + 1) / LN(2)) ELSE 0 END), 0) AS dcg_k,
      COALESCE(MAX(i.idcg_k), 0)                                                   AS idcg_k,
      COALESCE(SUM(CASE WHEN r.position <= {{k}} THEN r.is_rel ELSE 0 END), 0)::float AS rel_in_k,
      COALESCE(MAX(c.rel_total), 0)                                                AS rel_total,
      MIN(CASE WHEN r.is_rel = 1 THEN r.position END)                              AS first_rel_position,
      COALESCE(SUM(CASE WHEN r.position <= {{k}} AND r.is_rel = 1
                        THEN r.cum_rel::float / r.position ELSE 0 END), 0)         AS ap_numerator
    FROM
      base b
      LEFT JOIN ranked r
        ON r.ts = b.ts AND r.request_id = b.request_id
      LEFT JOIN ideal i
        ON i.ts = b.ts AND i.request_id = b.request_id
      LEFT JOIN engaged_counts c
        ON c.ts = b.ts AND c.request_id = b.request_id
    GROUP BY
      b.ts,
      b.request_id
  ),

  scored AS (
    SELECT
      ts,
      request_id,
      CASE WHEN rel_total > 0 THEN 1 ELSE 0 END                 AS evaluable,
      dcg_k / NULLIF(idcg_k, 0)                                 AS ndcg,
      ap_numerator / NULLIF(LEAST({{k}}, rel_total), 0)         AS ap,
      CASE WHEN first_rel_position <= {{k}}
           THEN 1.0 / first_rel_position ELSE 0 END             AS reciprocal_rank,
      rel_in_k / {{k}}                                          AS precision_k,
      rel_in_k / NULLIF(rel_total, 0)                           AS recall_k,
      CASE WHEN rel_in_k > 0 THEN 1 ELSE 0 END                  AS hit
    FROM
      per_request
  )

SELECT
  ts,
  AVG(CASE WHEN evaluable = 1 THEN ndcg END)::float             AS ndcg_at_k,
  AVG(CASE WHEN evaluable = 1 THEN ap END)::float               AS map_at_k,
  AVG(CASE WHEN evaluable = 1 THEN reciprocal_rank END)::float  AS mrr_at_k,
  AVG(CASE WHEN evaluable = 1 THEN precision_k END)::float      AS precision_at_k,
  AVG(CASE WHEN evaluable = 1 THEN recall_k END)::float         AS recall_at_k,
  AVG(CASE WHEN evaluable = 1 THEN hit END)::float              AS hit_rate_at_k,
  AVG(evaluable)::float                                         AS evaluable_request_ratio,
  COUNT(*)::float                                               AS request_count
FROM
  scored
GROUP BY
  ts
ORDER BY
  ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `ndcg_at_k`, `map_at_k`, `mrr_at_k`, `precision_at_k`, `recall_at_k`, `hit_rate_at_k` — ranking metrics averaged over evaluable requests (0 to 1)
* `evaluable_request_ratio` — share of requests with a non-empty engaged set (0 to 1)
* `request_count` — number of requests in the bucket

## Aggregate Arguments

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Timestamp of the ranked request.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Request ID Column

1. **Parameter Key:** `request_id_col`
2. **Friendly Name:** `Request ID Column`
3. **Description:** `Unique identifier of the request (one row per request).`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `str, uuid, int`

### Argument 3 — Recommended Items Column

1. **Parameter Key:** `recommended_items_col`
2. **Friendly Name:** `Recommended Items Column`
3. **Description:** `Ordered array of recommended item IDs; array index is the position.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `prediction`

### Argument 4 — Engaged Items Column

1. **Parameter Key:** `engaged_items_col`
2. **Friendly Name:** `Engaged Items Column`
3. **Description:** `Array of item IDs the user engaged with (clicked, purchased, etc.). Empty or NULL when there was no engagement.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `ground_truth`

### Argument 5 — K (Cutoff Depth)

1. **Parameter Key:** `k`
2. **Friendly Name:** `K`
3. **Description:** `Number of top positions to evaluate.`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Integer`
6. **Default Value:** `10`

### Argument 6 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Request-level dataset with array columns for recommended and engaged items.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

Configure the same eight reported metrics as [Top-K Ranking Quality](top-k-ranking-quality.md#reported-metrics): `ndcg_at_k`, `map_at_k`, `mrr_at_k`, `precision_at_k`, `recall_at_k`, `hit_rate_at_k`, `evaluable_request_ratio`, and `ranking_request_count` (value column `request_count`), all with timestamp column `ts` and metric kind `Numeric`.

If you run both variants on different datasets of the same model, give the metric names a suffix (for example `ndcg_at_k_slate`) so the time series stay distinct.

## Plots

The charts in [`/examples/charts/ranking/`](../../charts/ranking/) work unchanged as long as the reported metric names match.

## Interpreting the Metric

See [Top-K Ranking Quality — Interpreting the Metric](top-k-ranking-quality.md#interpreting-the-metric). Two additional points apply to the array layout:

* **Engaged items outside the slate** lower Recall@K and NDCG@K even though the ranker never had the chance to show them. If your engagement pipeline attributes purchases from other surfaces to the request, Recall@K will be structurally low; consider filtering the engaged array to items in the slate upstream, or treat the level as a baseline and watch the trend.
* **Duplicate item IDs** in `engaged_items` are de-duplicated; duplicates in `recommended_items` keep their first (highest) position for relevance purposes, since the join matches every occurrence.

## Use Cases

* Recommender services that log the full returned slate as one record
* Session-based recommenders where the engaged set is assembled from a clickstream after the fact
* Offline replay of a ranking policy where you store `(request, recommended_list, held-out positives)` per row
* Validating that an impression-level pipeline and a slate-level pipeline agree: on the `ranking-recsys-ads` test dataset the two variants produce identical values when the engaged array is built from `clicked = 1`
