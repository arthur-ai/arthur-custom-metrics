Arthur supports implementing **Population Stability Index (PSI)** as custom metrics in two main ways:

1. **PSI vs Fixed Reference Dataset** — compare your live data to a _fixed_ baseline (e.g., training data).
2. **PSI vs 30-Day Rolling Baseline** — compare each time bucket to a _recent_ window of past data.

Both variants measure how much a feature’s distribution has shifted using PSI:

PSI is defined as:

PSI = Σ_b (cur_b − ref_b) · ln(cur_b / ref_b)

Where, for each bin b:

* ref_b = proportion of the **reference** distribution in that bin
* cur_b = proportion of the **current** distribution in that bin

***

## PSI vs Fixed Reference Dataset (Numeric Feature)

### Overview

This custom metric computes **PSI per 5-minute bucket** for a numeric feature by comparing:

* **Reference**: a fixed dataset (e.g., training or holdout)
* **Current**: your live / inference dataset in Arthur

It:

* Uses the **reference dataset** to define **min/max and bin boundaries**
* Computes **reference bin proportions** once
* Computes **current bin proportions per 5-minute bucket**
* Aggregates to **PSI per bucket**

This is ideal when you want a **stable baseline** for regulatory/compliance or long-term drift monitoring.

***

### Step 1: Write the SQL

This SQL assumes:

* `{{reference_dataset}}` — baseline dataset/table (e.g., training)
* `{{dataset}}` — current/live dataset
* `{{timestamp_col}}` — timestamp column on the _current_ dataset
* `{{feature_col}}` — numeric feature to monitor
* `{{num_bins}}` — number of bins (e.g., 10 or 20)

```sql
SELECT
  bucket,
  SUM((p_cur - p_ref) * LN(p_cur / p_ref)) AS psi_against_reference
FROM
  (
    ----------------------------------------------------------------------------
    -- 0) Compute ref_min and ref_max ONCE and reuse them everywhere
    ----------------------------------------------------------------------------
    SELECT
      bucket,
      bin_id,
      -- sanitized proportions
      GREATEST(p_cur_raw, 1e-6) AS p_cur,
      GREATEST(p_ref_raw, 1e-6) AS p_ref
    FROM
      (
        ----------------------------------------------------------------------------
        -- Join reference + current distributions
        ----------------------------------------------------------------------------
        SELECT
          c.bucket,
          c.bin_id,
          COALESCE(c.p_cur, 0) AS p_cur_raw,
          COALESCE(r.p_ref, 0) AS p_ref_raw
        FROM
          (
            ----------------------------------------------------------------------------
            -- Current distribution (per 5-minute bucket)
            ----------------------------------------------------------------------------
            SELECT
              bucket,
              bin_id,
              cur_count / NULLIF(
                SUM(cur_count) OVER (
                  PARTITION BY
                    bucket
                ),
                0
              ) AS p_cur
            FROM
              (
                SELECT
                  time_bucket (INTERVAL '5 minutes', d.{{timestamp_col}}) AS bucket,
                  CASE
                    WHEN ref_max = ref_min THEN 1
                    ELSE LEAST(
                      {{num_bins}},
                      GREATEST(
                        1,
                        CAST(
                          FLOOR(
                            ({{feature_col}} - ref_min) / NULLIF(ref_max - ref_min, 0) * {{num_bins}}
                          ) AS INTEGER
                        ) + 1
                      )
                    )
                  END AS bin_id,
                  COUNT(*)::float AS cur_count
                FROM
                  {{dataset}} AS d,
                  (
                    SELECT
                      MIN({{feature_col}})::float AS ref_min,
                      MAX({{feature_col}})::float AS ref_max
                    FROM
                      {{reference_dataset}}
                  ) AS rs
                GROUP BY
                  bucket,
                  bin_id,
                  ref_min,
                  ref_max
              ) cur_raw
          ) c
          LEFT JOIN (
            ----------------------------------------------------------------------------
            -- Reference distribution (global)
            ----------------------------------------------------------------------------
            SELECT
              bin_id,
              ref_count / NULLIF(SUM(ref_count) OVER (), 0) AS p_ref
            FROM
              (
                SELECT
                  CASE
                    WHEN ref_max = ref_min THEN 1
                    ELSE LEAST(
                      {{num_bins}},
                      GREATEST(
                        1,
                        CAST(
                          FLOOR(
                            ({{feature_col}} - ref_min) / NULLIF(ref_max - ref_min, 0) * {{num_bins}}
                          ) AS INTEGER
                        ) + 1
                      )
                    )
                  END AS bin_id,
                  COUNT(*)::float AS ref_count
                FROM
                  {{reference_dataset}} r,
                  (
                    SELECT
                      MIN({{feature_col}})::float AS ref_min,
                      MAX({{feature_col}})::float AS ref_max
                    FROM
                      {{reference_dataset}}
                  ) AS rs
                GROUP BY
                  bin_id,
                  ref_min,
                  ref_max
              ) ref_bins
          ) r USING (bin_id)
      ) psi_terms
  ) psi_final
GROUP BY
  bucket
ORDER BY
  bucket;
```

**What this query is doing**

1. `ref_stats` — compute `ref_min` and `ref_max` from the reference dataset to define bin edges.
2. `ref_bins` / `ref_dist` — compute reference bin counts and convert to proportions `p_ref`.
3. `cur_bins` / `cur_dist` — compute current bin counts per 5-minute bucket and convert to `p_cur`.
4. `psi_terms` / `psi_sanitized` — join the two distributions and enforce a small epsilon to avoid `log(0)` and division by zero.
5. Final `SELECT` — aggregates PSI per `bucket` as `psi_against_reference`.

***

### Step 2: Fill Basic Information

In the Arthur UI, for this custom metric:

1. **Name:**  
   `PSI_<feature_name>_vs_reference`  
   (e.g., `PSI_income_vs_training_reference`)

2. **Description:**  
   `Population Stability Index for {{feature_col}} comparing the current dataset against {{reference_dataset}} as a fixed baseline.`

***

### Step 3: Configure the Aggregate Arguments

You’ll define the following aggregate arguments.

#### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Timestamp column on the current dataset used for 5-minute bucketing.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `Dataset (dataset)`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types (optional):** `timestamp`

***

#### Argument 2 — Feature Column

1. **Parameter Key:** `feature_col`
2. **Friendly Name:** `Feature Column`
3. **Description:** `Numeric feature column to compute PSI for.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `Dataset (dataset)`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `float`, `int`

***

#### Argument 3 — Current Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Current Dataset`
3. **Description:** `Current (live/log) dataset to compute PSI on.`
4. **Parameter Type:** `Dataset`

***

#### Argument 4 — Reference Dataset

1. **Parameter Key:** `reference_dataset`
2. **Friendly Name:** `Reference Dataset`
3. **Description:** `Fixed baseline dataset (e.g., training or holdout) used as the PSI reference.`
4. **Parameter Type:** `Dataset`

***

#### Argument 5 — Number of Bins

1. **Parameter Key:** `num_bins`
2. **Friendly Name:** `Number of Bins`
3. **Description:** `Number of equal-width bins between the reference min and max.`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Integer`

Typical values: `10` or `20`.

***

### Step 4: Configure the Reported Metrics

#### Reported Metric 1 — PSI Against Reference

1. **Metric Name:** `PSI (vs Reference)`
2. **Description:** `Population Stability Index for {{feature_col}} per 5-minute bucket, against the fixed reference dataset.`
3. **Value Column:** `psi_against_reference`
4. **Timestamp Column:** `bucket`
5. **Metric Kind:** `Numeric`

***

### Interpreting PSI vs Fixed Reference

Common rules of thumb:

* **PSI \< 0.1**
  * Little to no shift. Distribution is stable vs training.
* **0.1 ≤ PSI \< 0.25**
  * Moderate shift. Monitor closely; may indicate emerging drift.
* **PSI ≥ 0.25**
  * Significant shift. Often used as a trigger for review/retraining.

Because the reference dataset is **fixed**, this metric is ideal for:

* Regulatory/Model Risk Management reporting
* Comparing production behavior to the **original model design population**
* Long-horizon stability analysis

***

## Optional: Categorical PSI vs Reference

For categorical features, you can use categories as “bins” instead of numeric ranges. The logic is the same; only the bin definition changes.

**High-level SQL pattern (categorical):**

```sql
WITH ref_dist AS (
  SELECT
    {{feature_col}} AS category,
    COUNT(*)::float AS ref_count
  FROM {{reference_dataset}}
  GROUP BY category
),

ref_norm AS (
  SELECT
    category,
    ref_count / NULLIF(SUM(ref_count) OVER (), 0) AS p_ref
  FROM ref_dist
),

cur_dist AS (
  SELECT
    time_bucket(INTERVAL '5 minutes', {{timestamp_col}}) AS bucket,
    {{feature_col}} AS category,
    COUNT(*)::float AS cur_count
  FROM {{dataset}}
  GROUP BY bucket, category
),

cur_norm AS (
  SELECT
    bucket,
    category,
    cur_count / NULLIF(SUM(cur_count) OVER (PARTITION BY bucket), 0) AS p_cur
  FROM cur_dist
),

psi_terms AS (
  SELECT
    c.bucket,
    COALESCE(c.p_cur, 0.0) AS p_cur_raw,
    COALESCE(r.p_ref, 0.0) AS p_ref_raw
  FROM cur_norm AS c
  LEFT JOIN ref_norm AS r USING (category)
),

psi_sanitized AS (
  SELECT
    bucket,
    GREATEST(p_cur_raw, 1e-6) AS p_cur,
    GREATEST(p_ref_raw, 1e-6) AS p_ref
  FROM psi_terms
)

SELECT
  bucket,
  SUM( (p_cur - p_ref) * LN(p_cur / p_ref) ) AS psi_against_reference
FROM psi_sanitized
GROUP BY bucket
ORDER BY bucket;
```

The **arguments** and **reported metric** configuration are analogous to the numeric case, but `feature_col` must be a categorical type (e.g., string).

***

## PSI vs 30-Day Rolling Baseline

### Overview

The **rolling PSI** variant compares each 5-minute bucket to a **recent 30-day window** instead of a fixed dataset.

For each bucket `b`:

* **Reference** = all rows from `{{dataset}}` with `timestamp` in `[b - 30 days, b)`
* **Current** = rows in bucket `b` itself

This:

* Highlights **short-term changes** in feature distribution
* Adapts to evolving populations
* Is useful for day-to-day operational monitoring

> Note: This is more complex to compute than the fixed-reference version and may be more expensive for very large datasets. Treat this SQL as a **pattern** that you can adapt and optimize.

***

### Step 1: Write the SQL (Numeric Feature, Rolling 30-Day Baseline)

Below is a conceptual SQL pattern for 5-minute buckets and a 30-day reference window:

```sql
WITH base AS (
  SELECT
    {{timestamp_col}} AS event_ts,
    {{feature_col}}   AS feature_value
  FROM {{dataset}}
),

-- Distinct 5-minute buckets present in the data
buckets AS (
  SELECT DISTINCT time_bucket(INTERVAL '5 minutes', event_ts) AS bucket
  FROM base
),

-- Optional: global min/max to define stable bins (instead of per-window min/max)
global_stats AS (
  SELECT
    MIN(feature_value)::float AS global_min,
    MAX(feature_value)::float AS global_max
  FROM base
),

-- Current distribution per bucket
cur_bins AS (
  SELECT
    b.bucket,
    WIDTH_BUCKET(bc.feature_value, gs.global_min, gs.global_max, {{num_bins}}) AS bin_id,
    COUNT(*)::float AS cur_count
  FROM buckets b
  JOIN base bc
    ON bc.event_ts >= b.bucket
   AND bc.event_ts <  b.bucket + INTERVAL '5 minutes'
  CROSS JOIN global_stats AS gs
  GROUP BY b.bucket, bin_id
),

cur_dist AS (
  SELECT
    bucket,
    bin_id,
    cur_count / NULLIF(SUM(cur_count) OVER (PARTITION BY bucket), 0) AS p_cur
  FROM cur_bins
),

-- Reference distribution: last 30 days before each bucket
ref_bins AS (
  SELECT
    b.bucket,
    WIDTH_BUCKET(br.feature_value, gs.global_min, gs.global_max, {{num_bins}}) AS bin_id,
    COUNT(*)::float AS ref_count
  FROM buckets b
  JOIN base br
    ON br.event_ts >= b.bucket - INTERVAL '30 days'
   AND br.event_ts <  b.bucket
  CROSS JOIN global_stats AS gs
  GROUP BY b.bucket, bin_id
),

ref_dist AS (
  SELECT
    bucket,
    bin_id,
    ref_count / NULLIF(SUM(ref_count) OVER (PARTITION BY bucket), 0) AS p_ref
  FROM ref_bins
),

psi_terms AS (
  SELECT
    c.bucket,
    c.bin_id,
    COALESCE(c.p_cur, 0.0) AS p_cur_raw,
    COALESCE(r.p_ref, 0.0) AS p_ref_raw
  FROM cur_dist AS c
  LEFT JOIN ref_dist AS r
    ON c.bucket = r.bucket
   AND c.bin_id = r.bin_id
),

psi_sanitized AS (
  SELECT
    bucket,
    bin_id,
    GREATEST(p_cur_raw, 1e-6) AS p_cur,
    GREATEST(p_ref_raw, 1e-6) AS p_ref
  FROM psi_terms
)

SELECT
  bucket,
  SUM( (p_cur - p_ref) * LN(p_cur / p_ref) ) AS psi_vs_30d_baseline
FROM psi_sanitized
GROUP BY bucket
ORDER BY bucket;
```

**What this query is doing**

1. `buckets` — identifies all 5-minute buckets present in the data.
2. `global_stats` — computes global min/max to define bin edges (keeps bins stable).
3. `cur_bins` / `cur_dist` — compute per-bucket proportions `p_cur`.
4. `ref_bins` / `ref_dist` — for each bucket, compute the distribution over the **preceding 30 days** as `p_ref`.
5. `psi_terms` / `psi_sanitized` — join `p_cur` and `p_ref` per bucket/bin with epsilons.
6. Final `SELECT` — returns `psi_vs_30d_baseline` per 5-minute bucket.

***

### Step 2: Basic Information

In Arthur:

1. **Name:**  
   `PSI_<feature_name>_vs_30d_baseline`

2. **Description:**  
   `Population Stability Index for {{feature_col}} comparing each 5-minute bucket to the preceding 30 days on the same dataset.`

***

### Step 3: Aggregate Arguments

Most arguments are shared with the fixed-reference version:

* `timestamp_col` — timestamp column
* `feature_col` — numeric feature
* `dataset` — current dataset
* `num_bins` — number of bins (Literal, Integer)

You **don’t** need a `reference_dataset` here because the reference is derived from the same dataset.

***

### Step 4: Reported Metrics

1. **Metric Name:** `PSI (vs 30-Day Baseline)`
2. **Description:** `Population Stability Index per 5-minute bucket comparing to a rolling 30-day reference window.`
3. **Value Column:** `psi_vs_30d_baseline`
4. **Timestamp Column:** `bucket`
5. **Metric Kind:** `Numeric`

***

### Interpreting PSI vs 30-Day Baseline

Interpretation thresholds (0.1 / 0.25) are similar, but now:

* The **reference is moving** with time (last 30 days).
* Large PSI spikes indicate **short-term distribution changes** relative to recent behavior.

This variant is ideal when:

* The overall population evolves over time (seasonality, product changes).
* You care about **operational anomalies** (“something weird happened this week”) rather than deviation from old training data.

***

## Choosing Between the Two

You can (and often should) have **both** metrics in Arthur:

* **`PSI_<feature>_vs_reference`**
  * Fixed baseline (e.g., training).
  * Great for long-term stability and regulatory reporting.

* **`PSI_<feature>_vs_30d_baseline`**
  * Rolling baseline (last 30 days).
  * Great for day-to-day operational monitoring and alerting.

Used together, they let you answer both:

* “How far have we drifted from where we trained?”
* “How weird is today compared to what we’ve recently seen?”

> Preview Data
>
> for startDate use 2025-11-26T17:54:05.425Z
> for endDate use 2025-12-10T17:54:05.425Z

### Alternative SQL

```sql
WITH
  ref_range AS (
    -- Global min/max of the feature, used for binning both reference and current
    SELECT
      MIN({{feature_col}})::float AS ref_min,
      MAX({{feature_col}})::float AS ref_max
    FROM
      {{reference_dataset}}
  ),
  -- Reference distribution (global)
  ref_bins AS (
    SELECT
      CASE
        WHEN rr.ref_max = rr.ref_min THEN 1
        ELSE LEAST(
          {{num_bins}},
          GREATEST(
            1,
            CAST(
              FLOOR(
                ({{feature_col}} - rr.ref_min) / NULLIF(rr.ref_max - rr.ref_min, 0) * {{num_bins}}
              ) AS integer
            ) + 1
          )
        )
      END AS bin_id,
      COUNT(*)::float AS ref_count
    FROM
      {{reference_dataset}} r
      CROSS JOIN ref_range rr
    GROUP BY
      bin_id
  ),
  ref_totals AS (
    SELECT
      SUM(ref_count) AS total_ref_count
    FROM
      ref_bins
  ),
  ref_dist AS (
    SELECT
      rb.bin_id,
      rb.ref_count / NULLIF(rt.total_ref_count, 0) AS p_ref_raw
    FROM
      ref_bins rb
      CROSS JOIN ref_totals rt
  ),
  -- Current distribution per 1 day bucket
  cur_bins AS (
    SELECT
      time_bucket (INTERVAL '1 day', d.{{timestamp_col}}) AS bucket,
      CASE
        WHEN rr.ref_max = rr.ref_min THEN 1
        ELSE LEAST(
          {{num_bins}},
          GREATEST(
            1,
            CAST(
              FLOOR(
                ({{feature_col}} - rr.ref_min) / NULLIF(rr.ref_max - rr.ref_min, 0) * {{num_bins}}
              ) AS integer
            ) + 1
          )
        )
      END AS bin_id,
      COUNT(*)::float AS cur_count
    FROM
      {{dataset}} d
      CROSS JOIN ref_range rr
    GROUP BY
      bucket,
      bin_id
  ),
  cur_totals AS (
    SELECT
      bucket,
      SUM(cur_count) AS total_cur_count
    FROM
      cur_bins
    GROUP BY
      bucket
  ),
  cur_dist AS (
    SELECT
      cb.bucket,
      cb.bin_id,
      cb.cur_count / NULLIF(ct.total_cur_count, 0) AS p_cur_raw
    FROM
      cur_bins cb
      JOIN cur_totals ct ON cb.bucket = ct.bucket
  ),
  -- Join current + reference, apply smoothing
  psi_input AS (
    SELECT
      c.bucket,
      c.bin_id,
      GREATEST(COALESCE(c.p_cur_raw, 0), 1e-6) AS p_cur,
      GREATEST(COALESCE(r.p_ref_raw, 0), 1e-6) AS p_ref
    FROM
      cur_dist c
      LEFT JOIN ref_dist r ON c.bin_id = r.bin_id
  ),
  psi_terms AS (
    SELECT
      bucket,
      (p_cur - p_ref) * LN(p_cur / p_ref) AS term
    FROM
      psi_input
  )
SELECT
  bucket AS bucket,
  SUM(term) AS psi_against_reference
FROM
  psi_terms
GROUP BY
  bucket
ORDER BY
  bucket;
```
