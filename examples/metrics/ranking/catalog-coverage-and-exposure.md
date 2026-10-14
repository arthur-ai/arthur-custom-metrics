# Catalog Coverage and Exposure

## Overview

The **Catalog Coverage and Exposure** bucket measures **what a recommendation or ads engine actually shows**, independent of whether users engage. Rankers optimized purely for clicks tend to collapse onto a small set of popular items (popularity bias), which hurts long-tail sellers and advertisers, shrinks the data available to learn about new items, and makes feeds feel repetitive. This metric makes that collapse visible before it shows up in business metrics.

It produces, per time bucket:

* **catalog_coverage** — share of the catalog that received at least one impression
* **top_n_exposure_share** — share of all impressions that went to the N most-served items
* **exposure_gini** — Gini coefficient of impressions across the catalog (0 = perfectly even, 1 = everything on one item)
* **effective_catalog_size** — exponential of the Shannon entropy of exposure; the number of equally-exposed items that would produce the same concentration
* **items_served** and **impression_count** — raw volumes

It works on impression-level data (one row per item shown) and only needs an item identifier.

## Metrics

Let `x_i` be the number of impressions for item `i` in the bucket, `n` the number of items served, `N` the catalog size, and `T = Σ x_i`.

**catalog_coverage** = `n / N`

**top_n_exposure_share** = `(Σ of the N largest x_i) / T`

**exposure_gini** — computed over the whole catalog, so unserved items count as zero exposure:

```text
sort x ascending over all N items (unserved items first, as zeros)
G = 2 · Σ_{i=1..N} i · x_(i) / (N · T) − (N + 1) / N
```

**effective_catalog_size**

```text
p_i = x_i / T
H   = − Σ p_i · ln(p_i)
effective_catalog_size = exp(H)
```

## Data Requirements

* `{{timestamp_col}}` — timestamp of the impression
* `{{item_id_col}}` — identifier of the item shown
* `{{catalog_size}}` — total number of items available to the ranker (literal). Set to `0` to auto-detect as the number of distinct items seen anywhere in the dataset.
* `{{top_n}}` — number of top items for the exposure-share metric (literal)
* `{{dataset}}` — impression-level dataset

## Base Metric SQL

This SQL counts impressions per item per bucket, then derives coverage, top-N share, Gini and effective catalog size.

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{item_id_col}}::text                             AS item_id
    FROM
      {{dataset}}
    WHERE
      {{timestamp_col}} IS NOT NULL
      AND {{item_id_col}} IS NOT NULL
  ),

  -- Catalog size: the configured literal, or (when 0) the number of distinct
  -- items seen anywhere in the dataset
  catalog AS (
    SELECT
      CASE
        WHEN {{catalog_size}} > 0 THEN {{catalog_size}}::float
        ELSE COUNT(DISTINCT item_id)::float
      END AS catalog_size
    FROM
      base
  ),

  -- Impressions per item per bucket
  item_counts AS (
    SELECT
      ts,
      item_id,
      COUNT(*)::float AS impressions
    FROM
      base
    GROUP BY
      ts,
      item_id
  ),

  -- Rank items by exposure within each bucket
  ranked AS (
    SELECT
      ts,
      item_id,
      impressions,
      ROW_NUMBER() OVER (PARTITION BY ts ORDER BY impressions DESC, item_id) AS popularity_rank,
      ROW_NUMBER() OVER (PARTITION BY ts ORDER BY impressions ASC,  item_id) AS ascending_rank,
      SUM(impressions) OVER (PARTITION BY ts)                                AS total_impressions,
      COUNT(*)        OVER (PARTITION BY ts)                                 AS items_served
    FROM
      item_counts
  ),

  per_bucket AS (
    SELECT
      r.ts,
      MAX(r.items_served)::float     AS items_served,
      MAX(r.total_impressions)       AS total_impressions,
      MAX(c.catalog_size)            AS catalog_size,
      SUM(CASE WHEN r.popularity_rank <= {{top_n}} THEN r.impressions ELSE 0 END) AS top_n_impressions,
      -- Gini over the full catalog. Unserved items have zero exposure and
      -- occupy the lowest ranks, so a served item's rank in the ascending
      -- order of the whole catalog is (catalog_size - items_served + ascending_rank).
      --   G = 2 * SUM(rank_i * x_i) / (N * SUM(x)) - (N + 1) / N
      (2.0 * SUM((c.catalog_size - r.items_served + r.ascending_rank) * r.impressions))
        / NULLIF(MAX(c.catalog_size) * MAX(r.total_impressions), 0)
        - (MAX(c.catalog_size) + 1.0) / NULLIF(MAX(c.catalog_size), 0)         AS exposure_gini,
      -- Shannon entropy of the exposure distribution over served items
      -SUM((r.impressions / r.total_impressions) * LN(r.impressions / r.total_impressions)) AS exposure_entropy
    FROM
      ranked r
      CROSS JOIN catalog c
    GROUP BY
      r.ts
  )

SELECT
  ts,
  items_served / NULLIF(catalog_size, 0)         AS catalog_coverage,
  top_n_impressions / NULLIF(total_impressions, 0) AS top_n_exposure_share,
  exposure_gini                                  AS exposure_gini,
  EXP(exposure_entropy)                          AS effective_catalog_size,
  items_served                                   AS items_served,
  total_impressions                              AS impression_count
FROM
  per_bucket
ORDER BY
  ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `catalog_coverage` — items served / catalog size (0 to 1)
* `top_n_exposure_share` — impressions on the top N items / all impressions (0 to 1)
* `exposure_gini` — Gini coefficient of exposure over the catalog (0 to 1)
* `effective_catalog_size` — exp(entropy) of the exposure distribution (1 to items served)
* `items_served` — distinct items with at least one impression
* `impression_count` — total impressions in the bucket

## Aggregate Arguments

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Timestamp of the impression.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Item ID Column

1. **Parameter Key:** `item_id_col`
2. **Friendly Name:** `Item ID Column`
3. **Description:** `Identifier of the item, product, creative, or ad that was shown.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `categorical`
8. **Allowed Column Types:** `str, uuid, int`

### Argument 3 — Catalog Size

1. **Parameter Key:** `catalog_size`
2. **Friendly Name:** `Catalog Size`
3. **Description:** `Total number of items the ranker could serve. Use 0 to auto-detect from the distinct items present in the dataset.`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Integer`
6. **Default Value:** `0`

### Argument 4 — Top N

1. **Parameter Key:** `top_n`
2. **Friendly Name:** `Top N Items`
3. **Description:** `Number of most-served items whose combined impression share is reported.`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Integer`
6. **Default Value:** `50`

### Argument 5 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Impression-level dataset (one row per item shown).`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Catalog Coverage

1. **Metric Name:** `catalog_coverage`
2. **Description:** `Share of the catalog that received at least one impression in the bucket`
3. **Value Column:** `catalog_coverage`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 2 — Top-N Exposure Share

1. **Metric Name:** `top_n_exposure_share`
2. **Description:** `Share of impressions going to the N most-served items`
3. **Value Column:** `top_n_exposure_share`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 3 — Exposure Gini

1. **Metric Name:** `exposure_gini`
2. **Description:** `Gini coefficient of impressions across the catalog (0 = even, 1 = concentrated)`
3. **Value Column:** `exposure_gini`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 4 — Effective Catalog Size

1. **Metric Name:** `effective_catalog_size`
2. **Description:** `Number of equally-exposed items equivalent to the observed exposure distribution (exp of entropy)`
3. **Value Column:** `effective_catalog_size`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 5 — Items Served

1. **Metric Name:** `items_served`
2. **Description:** `Distinct items shown at least once in the bucket`
3. **Value Column:** `items_served`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 6 — Impression Count

1. **Metric Name:** `exposure_impression_count`
2. **Description:** `Total impressions in the bucket`
3. **Value Column:** `impression_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

## Plots

See the [charts](../../charts/ranking/) folder for visualization examples:

* [Catalog Coverage Over Time](../../charts/ranking/catalog-coverage-over-time.md)
* [Exposure Concentration Over Time](../../charts/ranking/exposure-concentration-over-time.md)

## Interpreting the Metric

### Value ranges

* **catalog_coverage** depends on traffic volume: a small catalog with heavy traffic reaches 1.0 daily; a large catalog never will. Establish a baseline, then alert on relative drops (for example 20% below the trailing average).
* **top_n_exposure_share** — the "head" share. If the top 50 of 2,000 items take 50% of impressions, half of all exposure goes to 2.5% of the catalog. Values above ~0.7 usually mean the long tail is effectively invisible.
* **exposure_gini** — above 0.8 is common for popularity-driven feeds; rising values mean concentration is getting worse. Because it is computed over the whole catalog, a low coverage day raises Gini even if served items are evenly exposed.
* **effective_catalog_size** is the most intuitive single number: "we are really only recommending ~300 items." Compare it to `items_served` — a large gap means many items get token exposure.

### Trends to watch

* **Coverage falls, top-N share rises, effective size falls together** — classic feedback-loop collapse: the ranker learns from its own popular picks. Usually traced to a retraining on recent logs, a stronger popularity prior, or a candidate generator change.
* **Coverage falls, impression_count falls** — just lower traffic; coverage is volume-dependent. Normalize by looking at effective_catalog_size or Gini, which are less sensitive to volume.
* **Step change at a deployment** — compare the new model's effective catalog size against the old before and after ramp
* **Gradual coverage rise with flat Gini** — new items entering the catalog are being served but only lightly; healthy exploration

### Caveats

* `catalog_size` should reflect what the ranker was **eligible** to serve. If you pass the full catalog but half of it is out of stock, coverage will look structurally low. Auto-detect (`0`) sidesteps this but can only count items that were served at least once in the dataset window.
* Daily buckets with low traffic will under-count coverage; use weekly buckets for small surfaces.

## Use Cases

* **Marketplace fairness** — ensure long-tail sellers and new listings receive exposure
* **Ads inventory health** — detect when a handful of advertisers or creatives dominate delivery, which also concentrates revenue risk
* **Cold-start monitoring** — confirm new catalog items are entering the slate (coverage and items_served rise after ingestion)
* **Feedback-loop detection** — a steady decline in effective catalog size after each retrain is the signature of a popularity feedback loop
* **Exploration budgets** — verify that an exploration policy is actually widening exposure, not just adding noise

## Relationship to Other Metrics

* **Label Coverage Ratio** and **Multi-Label Class Count** give per-label prevalence as a dimensioned series; this metric summarizes exposure concentration across thousands of items where a per-item dimension would be impractical
* **Slate Diversity** measures variety **within** a request; this metric measures variety **across** requests
* **Top-K Ranking Quality** tells you whether users engaged with what was shown; trade-offs between engagement and coverage are expected and should be explicit
