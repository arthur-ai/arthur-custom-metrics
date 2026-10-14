# Top-K Ranking Quality

## Overview

The **Top-K Ranking Quality** bucket measures whether a recommendation, search, or ad-ranking engine places the items users actually engage with near the **top of each slate**. It is the position-aware counterpart to the classification and rank-correlation metrics: instead of asking "did we score this item correctly?", it asks "within this request, were the relevant items ranked where users would see them?"

It computes the standard information-retrieval family per time bucket:

* **NDCG@K** — Normalized Discounted Cumulative Gain; rewards relevant items in higher positions, supports graded relevance
* **MAP@K** — Mean Average Precision; rewards relevant items appearing early and densely
* **MRR@K** — Mean Reciprocal Rank; how far down the first relevant item appears
* **Precision@K** — share of the top K slots filled with relevant items
* **Recall@K** — share of a request's relevant items that made it into the top K
* **Hit Rate@K** — share of requests with at least one relevant item in the top K

This is especially useful when:

* Your dataset logs **one row per (request, position)** — the native format for impression logs, search result logs, and ad auctions
* Engagement is sparse (most impressions get nothing) and you want to isolate **ordering quality** from engagement volume
* You want to compare rankers or surfaces by how well they front-load relevance, not just by overall click-through rate

## Metrics

Let a **request** be one ranked slate identified by `{{request_id_col}}`, with items at 1-indexed `{{position_col}}` and a non-negative `{{relevance_col}}` value per item (a click flag, a graded label such as 0 / 1 / 2 for none / click / purchase, or a business value such as revenue). An item is **relevant** when its relevance value is greater than 0; the relevance value itself is used as the **gain** for DCG.

**ndcg_at_k**

```text
DCG@K  = Σ_{p=1..K} gain_p / log2(p + 1)
IDCG@K = DCG@K of the same slate sorted by gain descending
NDCG@K = DCG@K / IDCG@K
```

**map_at_k**

```text
AP@K = ( Σ_{p=1..K, item p relevant} precision@p ) / min(K, number of relevant items in the slate)
```

**mrr_at_k**

```text
RR@K = 1 / (position of the first relevant item)   if that position <= K, else 0
```

**precision_at_k** = (relevant items in positions 1..K) / K

**recall_at_k** = (relevant items in positions 1..K) / (relevant items anywhere in the logged slate)

**hit_rate_at_k** = 1 if any relevant item is in positions 1..K, else 0

Each per-request value is averaged within the time bucket. **Only evaluable requests** — those with at least one relevant item somewhere in the logged slate — contribute to the six ranking metrics, because ordering quality is undefined when nothing was relevant. The share of evaluable requests is reported separately as `evaluable_request_ratio` so you can see engagement volume alongside ranking quality.

## Data Requirements

* `{{timestamp_col}}` — timestamp of the request (every row in a slate should share it)
* `{{request_id_col}}` — identifier that groups the rows of one slate
* `{{position_col}}` — 1-indexed rank of the item within the slate
* `{{relevance_col}}` — click flag, graded relevance, or value; `> 0` means relevant
* `{{k}}` — cutoff depth (literal, e.g. `5` or `10`)
* `{{dataset}}` — dataset containing one row per impression

If your dataset instead logs **one row per request** with an ordered array of recommended items and an array of engaged items, use [Top-K Ranking Quality (Slate Arrays)](top-k-ranking-quality-slate-arrays.md).

## Base Metric SQL

This SQL computes NDCG@K, MAP@K, MRR@K, Precision@K, Recall@K and Hit Rate@K per time bucket from impression-level rows.

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{request_id_col}}::text                          AS request_id,
      {{position_col}}::int                             AS position,
      GREATEST(COALESCE({{relevance_col}}::float, 0), 0) AS gain
    FROM
      {{dataset}}
    WHERE
      {{timestamp_col}} IS NOT NULL
      AND {{request_id_col}} IS NOT NULL
      AND {{position_col}} IS NOT NULL
      AND {{position_col}} >= 1
  ),

  -- Per impression: binary relevance flag, running count of relevant items
  -- down the slate (for AP@K), and the item's rank in the ideal ordering
  -- of the same slate (for IDCG@K)
  ranked AS (
    SELECT
      ts,
      request_id,
      position,
      gain,
      CASE WHEN gain > 0 THEN 1 ELSE 0 END AS is_rel,
      SUM(CASE WHEN gain > 0 THEN 1 ELSE 0 END) OVER (
        PARTITION BY ts, request_id
        ORDER BY position
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
      ) AS cum_rel,
      ROW_NUMBER() OVER (
        PARTITION BY ts, request_id
        ORDER BY gain DESC, position
      ) AS ideal_rank
    FROM
      base
  ),

  -- Per request: DCG@K from logged positions, IDCG@K from the ideal ordering,
  -- relevant counts, first relevant position, and the AP@K numerator
  per_request AS (
    SELECT
      ts,
      request_id,
      SUM(CASE WHEN position <= {{k}}
               THEN gain / (LN(position + 1) / LN(2)) ELSE 0 END)   AS dcg_k,
      SUM(CASE WHEN ideal_rank <= {{k}}
               THEN gain / (LN(ideal_rank + 1) / LN(2)) ELSE 0 END) AS idcg_k,
      SUM(CASE WHEN position <= {{k}} THEN is_rel ELSE 0 END)::float AS rel_in_k,
      SUM(is_rel)::float                                              AS rel_total,
      MIN(CASE WHEN is_rel = 1 THEN position END)                     AS first_rel_position,
      SUM(CASE WHEN position <= {{k}} AND is_rel = 1
               THEN cum_rel::float / position ELSE 0 END)             AS ap_numerator
    FROM
      ranked
    GROUP BY
      ts,
      request_id
  ),

  -- Per request scores. A request is "evaluable" when at least one logged
  -- item in the slate was relevant; ranking quality is undefined otherwise.
  scored AS (
    SELECT
      ts,
      request_id,
      CASE WHEN rel_total > 0 THEN 1 ELSE 0 END                               AS evaluable,
      dcg_k / NULLIF(idcg_k, 0)                                               AS ndcg,
      ap_numerator / NULLIF(LEAST({{k}}, rel_total), 0)                       AS ap,
      CASE WHEN first_rel_position <= {{k}}
           THEN 1.0 / first_rel_position ELSE 0 END                           AS reciprocal_rank,
      rel_in_k / {{k}}                                                        AS precision_k,
      rel_in_k / NULLIF(rel_total, 0)                                         AS recall_k,
      CASE WHEN rel_in_k > 0 THEN 1 ELSE 0 END                                AS hit
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
* `ndcg_at_k` — mean NDCG@K over evaluable requests (0 to 1)
* `map_at_k` — mean Average Precision@K over evaluable requests (0 to 1)
* `mrr_at_k` — mean Reciprocal Rank@K over evaluable requests (0 to 1)
* `precision_at_k` — mean Precision@K over evaluable requests (0 to 1)
* `recall_at_k` — mean Recall@K over evaluable requests (0 to 1)
* `hit_rate_at_k` — share of evaluable requests with a relevant item in the top K (0 to 1)
* `evaluable_request_ratio` — share of all requests that had at least one relevant item (0 to 1)
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
3. **Description:** `Identifier shared by every row of one ranked slate (request, session, query, or auction ID).`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `str, uuid, int`

### Argument 3 — Position Column

1. **Parameter Key:** `position_col`
2. **Friendly Name:** `Position Column`
3. **Description:** `1-indexed rank of the item within its slate.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `int`

### Argument 4 — Relevance Column

1. **Parameter Key:** `relevance_col`
2. **Friendly Name:** `Relevance Column`
3. **Description:** `Engagement signal per impression: click flag (0/1), graded relevance (0/1/2...), or value. Values greater than 0 count as relevant and are used as the NDCG gain.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `ground_truth`
8. **Allowed Column Types:** `int, float, bool`

### Argument 5 — K (Cutoff Depth)

1. **Parameter Key:** `k`
2. **Friendly Name:** `K`
3. **Description:** `Number of top positions to evaluate (e.g. 5 for a carousel, 10 for a feed page).`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Integer`
6. **Default Value:** `10`

### Argument 6 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Impression-level dataset with one row per (request, position).`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — NDCG@K

1. **Metric Name:** `ndcg_at_k`
2. **Description:** `Normalized Discounted Cumulative Gain at K, averaged over requests with at least one relevant item`
3. **Value Column:** `ndcg_at_k`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 2 — MAP@K

1. **Metric Name:** `map_at_k`
2. **Description:** `Mean Average Precision at K over evaluable requests`
3. **Value Column:** `map_at_k`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 3 — MRR@K

1. **Metric Name:** `mrr_at_k`
2. **Description:** `Mean Reciprocal Rank of the first relevant item within the top K`
3. **Value Column:** `mrr_at_k`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 4 — Precision@K

1. **Metric Name:** `precision_at_k`
2. **Description:** `Share of the top K positions occupied by relevant items`
3. **Value Column:** `precision_at_k`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 5 — Recall@K

1. **Metric Name:** `recall_at_k`
2. **Description:** `Share of each request's relevant items that appear in the top K`
3. **Value Column:** `recall_at_k`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 6 — Hit Rate@K

1. **Metric Name:** `hit_rate_at_k`
2. **Description:** `Share of evaluable requests with at least one relevant item in the top K`
3. **Value Column:** `hit_rate_at_k`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 7 — Evaluable Request Ratio

1. **Metric Name:** `evaluable_request_ratio`
2. **Description:** `Share of requests with at least one relevant item anywhere in the slate (engagement volume)`
3. **Value Column:** `evaluable_request_ratio`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 8 — Request Count

1. **Metric Name:** `ranking_request_count`
2. **Description:** `Number of ranked requests in the bucket`
3. **Value Column:** `request_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

## Plots

See the [charts](../../charts/ranking/) folder for visualization examples:

* [NDCG@K Over Time](../../charts/ranking/ndcg-at-k-over-time.md)
* [Precision and Recall@K Over Time](../../charts/ranking/precision-recall-at-k-over-time.md)
* [MRR and Hit Rate@K Over Time](../../charts/ranking/mrr-hit-rate-at-k-over-time.md)

## Interpreting the Metric

### Value ranges

All six ranking metrics lie in **[0, 1]**, higher is better. Absolute levels depend heavily on how sparse engagement is and on K, so **compare against your own baseline** rather than a universal threshold.

* **NDCG@K**
  * Near 1.0: relevant items sit at the very top in the ideal order
  * Mid-range (0.3–0.7): typical for feeds where the engaged item is often a few slots down
  * Near 0: relevant items exist in the slate but are ranked below K

* **MRR@K**
  * 1.0 means the first relevant item is always at position 1; 0.5 means position 2 on average
  * Most sensitive of the group to "the right item is there but one slot too low"

* **Precision@K vs Recall@K**
  * Precision@K is bounded by engagement density: if users engage with one item per slate, Precision@10 cannot exceed 0.1
  * Recall@K near 1 with low Precision@K is normal for sparse feedback; watch for **Recall@K falling** while Precision@K is flat

* **Hit Rate@K** — the simplest business read: "how often did the user find something in the first K items"

### Trends to watch

* **NDCG and MRR fall together, Hit Rate flat** — the right items are still in the slate but being pushed down; typical after a ranker regression or a change in business-rule boosting
* **Recall@K falls, evaluable ratio flat** — relevant items are increasingly ranked below K; check candidate ordering and slate truncation
* **evaluable_request_ratio falls** — engagement itself is dropping; this is a volume or retrieval problem, not an ordering problem, and ranking metrics may look artificially stable
* **Sudden step changes** — usually coincide with a model deployment, a change in the position layout (e.g. a new carousel size), or a logging change in how `position` is recorded

### Caveats

* Metrics are computed from **logged slates only**: items that were never shown cannot be relevant. Recall@K is therefore relative to the engaged items that were displayed, not to all items the user might have liked.
* Implicit feedback is **position-biased**: items at the top get clicked more because they are seen more. Flat or rising NDCG does not rule out a worse model; pair with the [Calibration Profile](calibration-profile.md) and A/B tests.
* Choose K to match the surface: the number of items visible without scrolling, or the number of ad slots.

## Use Cases

* **Home feed and product recommendations** — track NDCG@K and Hit Rate@K per surface; alert when a deployment lowers them
* **Search ranking** — MRR@K on clicked results is the standard health signal for "did the first result satisfy the query"
* **Ad ranking** — use `clicked` for engagement quality or `revenue` as the relevance value to measure whether high-value ads are ranked first
* **Email and push campaigns** — Precision@K for small slates (K = 3–5) where every slot is expensive
* **Ranker A/B comparisons** — run the same metric with a `model_version` filter on two datasets, or add a dimension column

### Segmenting by placement, device, or model version

To report the metrics per segment, add a column argument such as `{{segment_col}}` to the `base` CTE, carry it through every `GROUP BY`, and declare it as a **dimension column** in the Reported Metrics configuration. Keep the segment cardinality low (tens of values, not thousands).

## Relationship to Other Metrics

* **Rank Association Profile** (Spearman, Kendall) measures global score-to-outcome correlation across all rows; Top-K Ranking Quality measures per-request ordering at the top of each slate, which is what users experience
* **AUC / Gini** evaluate the score as a classifier over all impressions and ignore request grouping and position
* **Calibration Profile** checks whether the scores are honest probabilities; a ranker can have excellent NDCG and poor calibration (or vice versa)
* **Catalog Coverage and Exposure** and **Slate Diversity** capture what the ranker shows; this metric captures whether what it shows is what users wanted
