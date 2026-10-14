# Slate Diversity

## Overview

The **Slate Diversity** bucket measures how varied the items **within a single recommendation slate or ad slot set** are, using a categorical attribute such as product category, genre, advertiser, or content type. Feeds that show ten near-identical items may score well on click metrics in the short term while frustrating users and starving other categories of exposure. Ads engines likewise need to cap how many slots a single advertiser or vertical occupies.

It produces, per time bucket:

* **avg_slate_size** — mean number of items per request (also a logging-health check)
* **avg_distinct_categories** — mean number of distinct categories per slate
* **intra_list_diversity** — share of item pairs within a slate that belong to different categories (1 = every item a different category, 0 = all the same)
* **normalized_category_entropy** — Shannon entropy of the category mix divided by its maximum for that slate size (0 to 1)
* **single_category_slate_ratio** — share of slates where every item has the same category
* **request_count** — number of slates

## Metrics

For one slate of `n` items with category counts `c_1 … c_m` (so `Σ c_j = n`):

**intra_list_diversity**

```text
same_category_pairs = Σ_j c_j · (c_j − 1) / 2
total_pairs         = n · (n − 1) / 2
intra_list_diversity = 1 − same_category_pairs / total_pairs        (defined for n ≥ 2)
```

This is `1 − intra-list similarity` with a categorical (exact-match) similarity kernel.

**normalized_category_entropy**

```text
p_j = c_j / n
H   = − Σ_j p_j · ln(p_j)
normalized_category_entropy = H / ln(n)                              (defined for n ≥ 2)
```

**single_category_slate_ratio** — fraction of slates with `m = 1`

Per-slate values are averaged within the time bucket. Slates with a single item are excluded from the two pair-based metrics (they have no pairs) but still count toward slate size and the single-category ratio.

## Data Requirements

* `{{timestamp_col}}` — timestamp of the request
* `{{request_id_col}}` — identifier grouping the rows of one slate
* `{{item_category_col}}` — categorical attribute of each item (category, genre, advertiser, vertical)
* `{{dataset}}` — impression-level dataset (one row per item shown)

## Base Metric SQL

This SQL counts items per category within each slate, derives pairwise diversity and entropy per slate, then averages per time bucket.

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{request_id_col}}::text                          AS request_id,
      {{item_category_col}}::text                       AS category
    FROM
      {{dataset}}
    WHERE
      {{timestamp_col}} IS NOT NULL
      AND {{request_id_col}} IS NOT NULL
      AND {{item_category_col}} IS NOT NULL
  ),

  -- Items per category within each slate, plus the slate size
  category_counts AS (
    SELECT
      ts,
      request_id,
      category,
      COUNT(*)::float                                         AS c,
      SUM(COUNT(*)) OVER (PARTITION BY ts, request_id)::float AS n
    FROM
      base
    GROUP BY
      ts,
      request_id,
      category
  ),

  per_request AS (
    SELECT
      ts,
      request_id,
      MAX(n)                                  AS slate_size,
      COUNT(*)::float                         AS distinct_categories,
      -- Pairs of items in the slate that share a category
      SUM(c * (c - 1)) / 2.0                  AS same_category_pairs,
      -- All item pairs in the slate
      MAX(n) * (MAX(n) - 1) / 2.0             AS total_pairs,
      -- Shannon entropy of the category mix
      -SUM((c / n) * LN(c / n))               AS category_entropy
    FROM
      category_counts
    GROUP BY
      ts,
      request_id
  ),

  scored AS (
    SELECT
      ts,
      request_id,
      slate_size,
      distinct_categories,
      -- Share of item pairs that differ in category (1 = fully diverse)
      CASE WHEN total_pairs > 0
           THEN 1.0 - same_category_pairs / total_pairs END       AS intra_list_diversity,
      -- Entropy normalized by its maximum for this slate size, ln(slate_size)
      CASE WHEN slate_size > 1
           THEN category_entropy / LN(slate_size) END              AS normalized_category_entropy,
      CASE WHEN distinct_categories = 1 THEN 1 ELSE 0 END          AS single_category
    FROM
      per_request
  )

SELECT
  ts,
  AVG(slate_size)::float                   AS avg_slate_size,
  AVG(distinct_categories)::float          AS avg_distinct_categories,
  AVG(intra_list_diversity)::float         AS intra_list_diversity,
  AVG(normalized_category_entropy)::float  AS normalized_category_entropy,
  AVG(single_category)::float              AS single_category_slate_ratio,
  COUNT(*)::float                          AS request_count
FROM
  scored
GROUP BY
  ts
ORDER BY
  ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `avg_slate_size` — mean items per request
* `avg_distinct_categories` — mean distinct categories per request
* `intra_list_diversity` — mean share of differing-category item pairs (0 to 1)
* `normalized_category_entropy` — mean normalized entropy of the category mix (0 to 1)
* `single_category_slate_ratio` — share of single-category slates (0 to 1)
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
3. **Description:** `Identifier shared by every row of one slate.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `str, uuid, int`

### Argument 3 — Item Category Column

1. **Parameter Key:** `item_category_col`
2. **Friendly Name:** `Item Category Column`
3. **Description:** `Categorical attribute of the item used to judge diversity (category, genre, advertiser, content type).`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `categorical`
8. **Allowed Column Types:** `str, int`

### Argument 4 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Impression-level dataset (one row per item shown).`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Average Slate Size

1. **Metric Name:** `avg_slate_size`
2. **Description:** `Mean number of items served per request`
3. **Value Column:** `avg_slate_size`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 2 — Average Distinct Categories

1. **Metric Name:** `avg_distinct_categories`
2. **Description:** `Mean number of distinct categories per slate`
3. **Value Column:** `avg_distinct_categories`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 3 — Intra-List Diversity

1. **Metric Name:** `intra_list_diversity`
2. **Description:** `Mean share of item pairs within a slate that have different categories (1 = fully diverse)`
3. **Value Column:** `intra_list_diversity`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 4 — Normalized Category Entropy

1. **Metric Name:** `normalized_category_entropy`
2. **Description:** `Mean Shannon entropy of the slate's category mix, normalized to [0, 1]`
3. **Value Column:** `normalized_category_entropy`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 5 — Single-Category Slate Ratio

1. **Metric Name:** `single_category_slate_ratio`
2. **Description:** `Share of slates where every item belongs to the same category`
3. **Value Column:** `single_category_slate_ratio`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 6 — Request Count

1. **Metric Name:** `diversity_request_count`
2. **Description:** `Number of slates evaluated in the bucket`
3. **Value Column:** `request_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

## Plots

See the [charts](../../charts/ranking/) folder for visualization examples:

* [Slate Diversity Over Time](../../charts/ranking/slate-diversity-over-time.md)

## Interpreting the Metric

### Value ranges

* **intra_list_diversity** — for a 10-item slate drawn from 12 categories, random assignment gives roughly 0.9; values well below your baseline mean the ranker is stacking a category. 0.5 means half of all item pairs share a category.
* **normalized_category_entropy** — 1.0 only when every item has a unique category; with fewer categories than slots the ceiling is lower, so compare against the baseline rather than 1.0.
* **single_category_slate_ratio** — should be near 0 for general feeds. A non-zero value is a direct count of "monotone" slates and makes a good alert.
* **avg_slate_size** — should match the configured slot count; a drop means slates are being truncated (filtering, inventory shortfall, timeouts) and a rise means a layout change.

### Trends to watch

* **Diversity falls, Top-K ranking metrics rise** — the ranker is exploiting a category the user likes; may be fine short-term but watch for long-term engagement and coverage effects
* **Diversity falls after a retrain with no engagement gain** — a popularity or category feedback loop; consider a diversity re-ranker or a per-category cap
* **single_category_slate_ratio spikes** — usually a business rule or campaign override (e.g. a seasonal category boost) or a bug in candidate filtering
* **avg_slate_size drops** — a logging or serving issue; investigate before interpreting the other metrics, since smaller slates mechanically change pair counts

### Caveats

* The metric is only as meaningful as the attribute: a coarse category (3 values) will always look low-diversity; a fine one (thousands of values) will look uniformly high. Pick the attribute users perceive.
* Diversity is not a goal in itself. A search results page for a specific query **should** be low-diversity. Apply this metric to discovery surfaces, and segment by placement if one dataset covers several.

## Use Cases

* **Home feed and discovery surfaces** — keep slates mixed across categories to avoid filter bubbles and fatigue
* **Ads delivery** — enforce and monitor advertiser or vertical caps per slot set
* **Streaming and media** — genre diversity per row or carousel
* **Marketplace listings** — avoid showing ten variants of the same product in a "you may also like" shelf
* **Post-deployment checks** — confirm a new ranker did not reduce diversity as a side effect of optimizing clicks

## Relationship to Other Metrics

* **Catalog Coverage and Exposure** measures variety across all requests (are we serving the whole catalog?); Slate Diversity measures variety within one request (is each slate mixed?)
* **Label Co-occurrence Matrix** shows which labels appear together across inferences and is the natural next step when you want to know *which* categories are being stacked
* **Top-K Ranking Quality** captures the engagement side of the diversity/relevance trade-off
