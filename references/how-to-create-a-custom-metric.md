# How to Create a Custom Metric

## Overview

Arthur **Custom Metrics** let you define model- or business-specific metrics using SQL. Custom metrics are evaluated during metrics calculation jobs and appear alongside Arthur's built-in metrics in dashboards, plots, comparisons, and alerts.

Custom metrics are:

* **Reusable** across multiple models and projects
* **Versioned**, so you can evolve metric logic while preserving historical results
* **Queryable**, just like any other Arthur metric

Each custom metric produces time-series data with the format:

`(Model ID, Metric Name, Timestamp, Value, Dimensions)`

For more on how these fields are stored and queried, see the
**[Metrics & Querying Overview](overview-metrics-and-querying.md) .**

Arthur also supports **custom metric versioning**. When you create a new version of a custom metric, existing models will continue to use the previous version until you explicitly update their metric configuration. This gives you a precise audit trail of which query and aggregation logic produced any historical time series.

Custom metrics are built around four core components:

1. **SQL Query** – How the metric is computed from your data
2. **Description** – Human-readable explanation of what the metric means
3. **Reported Metrics** – Numeric outputs from your SQL query
4. **Aggregate Arguments** – Templated parameters that make the metric reusable across datasets and models

Once defined, custom metrics fit into the broader Arthur metrics ecosystem:

```text
Datasets (ML & GenAI)
    ↓
[SQL Query] → Reported Metrics
    ↓
[Metrics Engine & Aggregations]
    ↓
Dashboards • Alerts • Metrics Query UI
```

Custom metrics are **model-agnostic**: they can capture metrics for binary/multiclass classification, regression, GenAI/LLM, decisioning systems, and business KPIs.

***

## Quickstart Guide

In this quickstart, we'll walk through configuring a custom metric that counts records in a category (a simple "category count" metric). This illustrates all four building blocks:

* SQL query
* Aggregate arguments
* Reported metrics
* Model metric configuration

### Step 1: Write the SQL

Start by defining the SQL query that computes your metric. In this example, we'll count records for a given categorical value over daily buckets:

```sql
SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
    '{{categorical_value_literal}}' AS categorical_value,
    COUNT(*) AS count
FROM {{dataset}}
WHERE {{categorical_column}} = '{{categorical_value_literal}}'
  AND {{timestamp_col}} IS NOT NULL
GROUP BY ts, categorical_value
ORDER BY ts;
```

**Callouts:**

1. **Templated variables**
   Any generic argument is written using `{{variable_name}}` syntax. These are the **aggregate arguments** that users configure when adding the metric to a model (e.g., which dataset, which timestamp column, which categorical value).

2. **Dimension columns**
   We include `categorical_value` in both the `SELECT` and `GROUP BY` clauses. This value will later be used as a **dimension** in the output time series (so you can tell _which_ category the count belongs to).

3. **Time bucketing**
   We use the `time_bucket` function to aggregate counts. Common bucket sizes: `5 minutes`, `1 hour`, `1 day`. Daily buckets are typical for longer-term trend analysis.

4. **NULL handling**
   Always filter `WHERE {{timestamp_col}} IS NOT NULL` to avoid including records with missing timestamps.

***

### Step 2: Configure the Aggregate Arguments

In the Custom Metric UI, configure an aggregate argument for each templated variable in your SQL query (everything inside `{{}}`).

You will typically define:

* A **dataset argument** for `{{dataset}}`
* A **timestamp column argument** for `{{timestamp_col}}`
* One or more **column arguments** for fields like `{{categorical_column}}`
* Optional **literal arguments** for values like `{{categorical_value_literal}}`

These arguments make your metric **reusable** across different models and datasets.

> 🛈 The timestamp and dataset arguments are used by every custom metric. They identify:
>
> * Which dataset to query
> * Which column contains record timestamps

Clear names, types, and descriptions help other users know how to configure your metric correctly.

<Image align="center" alt="Aggregate arguments configuration in the UI" border={false} src="https://files.readme.io/6712b29b198b4773be38325a59800b8b5eecf85d7d172829b0e56587f137335d-Screenshot_2025-12-05_at_12.44.25.png" />

***

### Step 3: Configure the Reported Metrics

Next, configure the **reported metrics** that Arthur will store from your query.

For our category count example, we'll define:

* **Value column**: `count`
* **Metric name**: a descriptive name for the time series (e.g. `category_count`)
* **Timestamp column**: `ts`
* **Dimension columns**: `categorical_value`

Each reported metric tells Arthur how to interpret a single time series in the output:

* Which column is the metric **value**
* Which column is the **timestamp**
* Which columns become **dimensions** in the `dimensions` field

Arthur uses this metadata to store and serve time series for use in dashboards, alerts, and queries.

<Image align="center" alt="Reported metrics configuration in the UI" border={false} src="https://files.readme.io/25a125a1b67ee34451a8bfc2515f89aece64b9f0cc1e2802620f642782c83624-Screenshot_2025-12-05_at_12.48.58.png" />

<Callout icon="🔍" theme="default">
  You can query reported metric values directly using the Metrics Query UI. This is especially helpful for validating your SQL output and inspecting bucket-level values. See **[Metrics & Querying Overview](https://docs.arthur.ai/docs/metrics-querying-overview-1#/) .**
</Callout>

***

### Step 4: Add the Metric to Your Model Metric Configuration

Finally, add your custom metric to a model:

1. Go to your **model's metric configuration**
2. Select the custom metric you created
3. Fill in the aggregate arguments:
   * Dataset
   * Timestamp column
   * Column arguments
   * Literal thresholds, if applicable

On the next metrics calculation job, your new metric (e.g. `category_count`) will run and populate time series for that model. You can then:

* Plot it in dashboards
* Query it with SQL via the Metrics Querying interface
* Use it in alert rules

<Image align="center" alt="Configuring a custom metric for a model" border={false} src="https://files.readme.io/8877aab08f9855cb087300ac189508df5d4d2a343804ab1268cadabbde30acbf-Screenshot_2025-12-05_at_12.51.27.png" />

***

## Advanced Patterns

The following patterns cover more sophisticated metric designs commonly used in production ML monitoring.

### Pattern 1: Multi-Dimensional Metrics

Multi-dimensional metrics use multiple dimension columns to create rich time series. This is useful for pairwise analysis like label co-occurrence or feature interactions.

**Example: Label Co-occurrence Matrix**

Tracks which label pairs appear together in multi-label classification:

```sql
WITH
  pred_exploded AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{row_id_col}}::text AS row_id,
      unnest({{predicted_labels_col}}) AS label
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
      AND {{predicted_labels_col}} IS NOT NULL
  ),
  pred_pairs AS (
    SELECT
      ts,
      row_id,
      LEAST(p1.label, p2.label) AS label_1,
      GREATEST(p1.label, p2.label) AS label_2
    FROM pred_exploded p1
    JOIN pred_exploded p2
      ON p1.row_id = p2.row_id
      AND p1.ts = p2.ts
    WHERE p1.label < p2.label
  )
SELECT
  ts,
  label_1,
  label_2,
  COUNT(DISTINCT row_id)::float AS cooccurrence_count
FROM pred_pairs
GROUP BY ts, label_1, label_2
ORDER BY ts, label_1, label_2;
```

**Reported Metric Configuration:**
- Value column: `cooccurrence_count`
- Timestamp column: `ts`
- **Dimension columns**: `label_1`, `label_2` (multiple dimensions)
- Metric kind: `Numeric`

### Pattern 2: Array Operations with CROSS JOIN LATERAL

When working with array columns (common in multi-label classification), use `CROSS JOIN LATERAL` with `unnest()` to explode arrays while preserving context.

**Example: Label Coverage Ratio**

Calculates what proportion of inferences contain each label:

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{row_id_col}}::text AS row_id,
      {{pred_labels_col}} AS pred_labels
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
  ),
  n_by_bucket AS (
    SELECT
      ts,
      COUNT(DISTINCT row_id)::float AS n
    FROM base
    GROUP BY ts
  ),
  exploded AS (
    SELECT
      ts,
      row_id,
      lbl AS series
    FROM base
    CROSS JOIN LATERAL (
      SELECT DISTINCT
        unnest(COALESCE(pred_labels, ARRAY[]::TEXT[])) AS lbl
    ) u
    WHERE lbl IS NOT NULL AND lbl <> ''
  ),
  label_counts AS (
    SELECT
      ts,
      series,
      COUNT(DISTINCT row_id)::float AS label_n
    FROM exploded
    GROUP BY ts, series
  )
SELECT
  c.ts AS ts,
  c.series AS series,
  (c.label_n / NULLIF(n.n, 0)) AS coverage_ratio
FROM label_counts c
JOIN n_by_bucket n ON n.ts = c.ts
ORDER BY c.ts, c.series;
```

**Key techniques:**
- `COALESCE(pred_labels, ARRAY[]::TEXT[])` - Handle NULL arrays
- `CROSS JOIN LATERAL` - Explode arrays with row context
- `NULLIF(n.n, 0)` - Prevent division by zero

### Pattern 3: Confusion Matrix Components

Calculate TP, FP, FN for each label by comparing predicted and ground truth arrays:

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
      {{row_id_col}}::text AS row_id,
      {{predicted_labels_col}} AS pred_labels,
      {{ground_truth_labels_col}} AS gt_labels
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
  ),
  pred_exploded AS (
    SELECT
      bucket, row_id, label, 1 AS predicted
    FROM base
    CROSS JOIN LATERAL (
      SELECT DISTINCT unnest(pred_labels) AS label
    ) p
    WHERE label IS NOT NULL AND label <> ''
  ),
  gt_exploded AS (
    SELECT
      bucket, row_id, label, 1 AS actual
    FROM base
    CROSS JOIN LATERAL (
      SELECT DISTINCT unnest(gt_labels) AS label
    ) g
    WHERE label IS NOT NULL AND label <> ''
  ),
  joined AS (
    SELECT
      COALESCE(p.bucket, g.bucket) AS bucket,
      COALESCE(p.label, g.label) AS label,
      COALESCE(predicted, 0) AS predicted,
      COALESCE(actual, 0) AS actual
    FROM pred_exploded p
    FULL OUTER JOIN gt_exploded g
      ON p.row_id = g.row_id AND p.label = g.label
  )
SELECT
  bucket AS ts,
  label AS series,
  SUM(CASE WHEN predicted = 1 AND actual = 1 THEN 1 ELSE 0 END)::float AS tp,
  SUM(CASE WHEN predicted = 1 AND actual = 0 THEN 1 ELSE 0 END)::float AS fp,
  SUM(CASE WHEN predicted = 0 AND actual = 1 THEN 1 ELSE 0 END)::float AS fn
FROM joined
GROUP BY ts, series
ORDER BY ts, series;
```

**Output**: Three metrics (tp, fp, fn) with same dimension (series)

### Pattern 4: Derived Metrics from Confusion Matrix

Calculate precision, recall, and F1 from confusion matrix components:

```sql
-- (Use confusion matrix query as CTE, then calculate ratios)
WITH confusion AS (
  -- Previous confusion matrix query here
)
SELECT
  ts,
  series,
  tp / NULLIF(tp + fp, 0) AS precision,
  tp / NULLIF(tp + fn, 0) AS recall,
  (2.0 * tp) / NULLIF(2.0 * tp + fp + fn, 0) AS f1_score
FROM confusion
ORDER BY ts, series;
```

**Multiple reported metrics** from single query:
1. Metric name: `precision`, Value column: `precision`
2. Metric name: `recall`, Value column: `recall`
3. Metric name: `f1_score`, Value column: `f1_score`

### Pattern 5: Set Comparison (Jaccard Similarity)

Compare predicted and ground truth label sets using set operations:

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{row_id_col}}::text AS row_id,
      COALESCE({{predicted_labels_col}}, ARRAY[]::TEXT[]) AS pred_set,
      COALESCE({{ground_truth_labels_col}}, ARRAY[]::TEXT[]) AS gt_set
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
  ),
  jaccard_per_row AS (
    SELECT
      ts,
      row_id,
      CARDINALITY(
        ARRAY(
          SELECT unnest(pred_set)
          INTERSECT
          SELECT unnest(gt_set)
        )
      )::float AS intersection_size,
      CARDINALITY(
        ARRAY(
          SELECT DISTINCT unnest(pred_set || gt_set)
        )
      )::float AS union_size
    FROM base
  )
SELECT
  ts,
  AVG(
    CASE
      WHEN union_size = 0 THEN 1.0
      ELSE intersection_size / union_size
    END
  ) AS jaccard_similarity
FROM jaccard_per_row
GROUP BY ts
ORDER BY ts;
```

**Key techniques:**
- `ARRAY(...INTERSECT...)` - Set intersection
- `pred_set || gt_set` - Array concatenation for union
- `CARDINALITY()` - Array length
- Per-row calculation then aggregation

### Pattern 6: Array Comparison (Exact Match)

Check if two arrays are exactly equal:

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{row_id_col}}::text AS row_id,
      {{predicted_labels_col}} AS pred_labels,
      {{ground_truth_labels_col}} AS gt_labels
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
  ),
  normalized AS (
    SELECT
      ts,
      row_id,
      ARRAY(
        SELECT DISTINCT unnest(COALESCE(pred_labels, ARRAY[]::TEXT[]))
        ORDER BY 1
      ) AS pred_set,
      ARRAY(
        SELECT DISTINCT unnest(COALESCE(gt_labels, ARRAY[]::TEXT[]))
        ORDER BY 1
      ) AS gt_set
    FROM base
  )
SELECT
  ts,
  AVG(
    CASE WHEN pred_set = gt_set THEN 1.0 ELSE 0.0 END
  ) AS exact_match_ratio
FROM normalized
GROUP BY ts
ORDER BY ts;
```

**Important**: Sort and deduplicate arrays before comparison to ensure order-independent equality.

### Pattern 7: Auto-Detect Label Catalog

Calculate metrics normalized by total unique labels seen in data:

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{row_id_col}}::text AS row_id,
      {{pred_labels_col}} AS pred_labels
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
  ),
  total_label_catalog AS (
    SELECT COUNT(DISTINCT label)::float AS total_labels
    FROM base
    CROSS JOIN LATERAL (
      SELECT unnest(COALESCE(pred_labels, ARRAY[]::TEXT[])) AS label
    ) u
    WHERE label IS NOT NULL AND label <> ''
  ),
  per_row AS (
    SELECT
      ts,
      row_id,
      COALESCE(array_length(pred_labels, 1), 0)::float AS label_count
    FROM base
  ),
  avg_per_bucket AS (
    SELECT ts, AVG(label_count) AS avg_labels
    FROM per_row
    GROUP BY ts
  )
SELECT
  a.ts AS ts,
  a.avg_labels / NULLIF(c.total_labels, 0) AS label_density
FROM avg_per_bucket a
CROSS JOIN total_label_catalog c
ORDER BY ts;
```

**Use case**: Label density shows what portion of available labels are used on average.

***

## More Details

The sections below describe each part of a custom metric in more depth.

***

### Basic Information

Each custom metric starts with some basic configuration:

1. **Name**
   A user-friendly label shown in the UI. This does _not_ have to match the `metric_name` in the time series output.

2. **Description**
   A human-readable explanation of what the metric measures and how to interpret it.

3. **Model Problem Type**
   Optionally, specify which model types the metric applies to (e.g. `binary_classification`, `multiclass_classification`, `regression`, `genai`). Arthur can use this to suggest relevant metrics when users configure models.

4. **Versioning**
   When you edit a custom metric, Arthur creates a new version. Existing models remain pinned to the old version until you update their configuration. This ensures you can always tell which query & aggregation logic produced historical values.

***

### Reported Metrics

A single custom metric can output **one or many** reported metrics from the same SQL query. This is useful when the same query naturally produces multiple related measurements (e.g., true positives and false positives, or counts for multiple categories).

Each **reported metric** corresponds to one time series in Arthur's metrics storage and includes:

1. **Metric name**
   The name used in the metrics tables (the `metric_name` field). This is what you'll filter on when querying metrics in dashboards or the Metrics Query UI.

2. **Description**
   A description specific to that particular metric (e.g. "Count of records where prediction = 1").

3. **Value column**
   The column in your SQL query that contains the metric's value (e.g. `count`, `error_rate`).

4. **Timestamp column**
   The column that contains the time bucket for the metric (e.g. `ts` from `time_bucket(...)`).

5. **Metric kind**

   * `Numeric` – a floating point value
   * `Sketch` – a sketch-encoded distribution (used for histograms, latency distributions, etc.)

   For more on numeric vs sketch metrics, see the **[Types of Metrics](https://docs.arthur.ai/docs/metrics-querying-overview-1#/) section of Metrics & Querying Overview**.

6. **Dimension columns**
   One or more columns from your SQL query that should become dimensions in the output time series (e.g. `categorical_value`, `label_1`, `label_2`). These must be in the `GROUP BY` clause and should have **manageable cardinality** to avoid explosion in the metrics store.

   **Best practices for dimensions:**
   - Limit to low-cardinality columns (10-100 unique values)
   - For high cardinality (1000s of values), consider filtering to top N
   - Multiple dimensions create cartesian product (label_1 × label_2 = N² combinations)
   - Always include dimensions in GROUP BY clause

***

### Aggregate Arguments

**Aggregate arguments** are templated parameters that make your custom metric configurable and reusable across multiple datasets and models. Anywhere you write `{{variable_name}}` in your SQL, you'll define an argument with that name.

Arthur supports three kinds of aggregate arguments:

#### Dataset Arguments

These indicate **which dataset** the query runs against.

* Parameter key (e.g. `dataset`)
* Friendly name
* Description
* Parameter type: `Dataset`

Your `FROM` clause should use the templated variable:

```sql
FROM {{dataset}}
```

Arthur will automatically provide a dataset argument in the UI; you specify how it should be described and used.

<Image align="center" alt="Dataset argument configuration" border={false} src="https://files.readme.io/a5c472a093239e8c29b3a12a754217f4b6146e46d89c52ff0ea0e16cfcc064a6-Screenshot_2025-12-05_at_12.52.28.png" />

***

#### Literal Arguments

Literal arguments represent **scalar values** you want users to configure, such as thresholds or category values.

Typical use cases:

* Thresholds for pass/fail
* Category names or IDs
* Numeric cutoffs for risk scores

Configuration fields include:

* Parameter key (e.g. `score_threshold`)
* Friendly name
* Description
* Parameter type: `Literal`
* Data type (e.g. numeric, string, boolean, timestamp)

Example usage in SQL:

```sql
CASE WHEN {{score_threshold}} IS NOT NULL
     AND score > {{score_threshold}}
     THEN 1 ELSE 0 END AS above_threshold
```

<Image align="center" alt="Literal argument configuration" border={false} src="https://files.readme.io/3d88525885b5b386aaa00f4bbe1f07502927da6b8f47fc502b23414fdfe083a3-Screenshot_2025-12-05_at_12.52.41.png" />

***

#### Column Arguments

Column arguments represent **column names** that the user selects from the dataset. They allow you to reuse the same metric logic for different columns.

Configuration fields include:

* Parameter key (e.g. `timestamp_col`, `feature_column`)
* Friendly name
* Description
* Parameter type: `Column`
* Source dataset parameter key (usually `dataset`)
* Allowed column types (e.g. `timestamp`, `numeric`, `categorical`)
* **Allow any column type**: Set to `Yes` for array columns or when column type varies
* Tag hints (e.g. `primary_timestamp`, `prediction`, `ground_truth`) to guide users

Example usage:

```sql
SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
    COUNT(*) AS count
FROM {{dataset}}
WHERE {{timestamp_col}} IS NOT NULL
GROUP BY ts;
```

By constraining allowed types and using tags, you help users pick the right column and avoid misconfiguration.

**Common tag hints:**
- `primary_timestamp` - Main timestamp column
- `prediction` - Model prediction column
- `ground_truth` - Ground truth/label column
- `prediction_score` - Confidence/probability scores

<Image align="center" alt="Column argument configuration" border={false} src="https://files.readme.io/1d8a616cd5f29ded1fd7acc6edf513981e2182119ade9c49011bf95f004dbf44-Screenshot_2025-12-05_at_12.54.00.png" />

***

### SQL Query Best Practices

Your SQL query is written in **DuckDBSQL**, which is very close to PostgreSQL with a few differences. See the DuckDB documentation for detailed syntax and function references.

#### Requirements

* Must be valid DuckDBSQL
* Must use `{{argument_name}}` syntax for all templated values
* Must output all columns referenced in your **reported metrics** configuration
* Must produce time series data:
  * **Numeric metrics**: use `time_bucket` to aggregate
  * **Sketch metrics**: may output per-record values; Arthur handles bucketing

#### Time Bucketing Guidelines

Choose bucket size based on data volume and use case:

```sql
-- 5 minutes (Arthur default, high granularity)
time_bucket(INTERVAL '5 minutes', {{timestamp_col}})

-- 1 hour (moderate granularity)
time_bucket(INTERVAL '1 hour', {{timestamp_col}})

-- 1 day (common for trend analysis)
time_bucket(INTERVAL '1 day', {{timestamp_col}})

-- 1 week (low granularity, long-term trends)
time_bucket(INTERVAL '1 week', {{timestamp_col}})
```

**Recommendation**: Use daily buckets for most production metrics. Provides good balance of granularity and query performance.

#### NULL Handling Patterns

Always handle NULL values explicitly:

```sql
-- Filter NULL timestamps
WHERE {{timestamp_col}} IS NOT NULL

-- Default NULL arrays to empty
COALESCE({{array_column}}, ARRAY[]::TEXT[])

-- Prevent division by zero
column_a / NULLIF(column_b, 0)

-- Handle NULL in aggregations
COALESCE(array_length({{array_col}}, 1), 0)::float
```

#### Query Structure Best Practices

Use CTEs (Common Table Expressions) for readability:

```sql
WITH
  -- Step 1: Time bucket and filter
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{row_id_col}}::text AS row_id,
      {{feature_col}} AS feature
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
  ),
  -- Step 2: Compute intermediate values
  intermediate AS (
    SELECT
      ts,
      feature,
      COUNT(*) AS count
    FROM base
    GROUP BY ts, feature
  )
-- Step 3: Final aggregation
SELECT
  ts,
  feature AS dimension,
  count AS value
FROM intermediate
ORDER BY ts, dimension;
```

**Benefits:**
- Easier to debug (query each CTE separately)
- More maintainable
- Self-documenting logic flow

#### Performance Optimization

For large datasets:

1. **Add early filters** in WHERE clause
2. **Use appropriate data types** (::text, ::float cast)
3. **Limit DISTINCT operations** (expensive on large sets)
4. **Consider indexes** on timestamp columns
5. **Test on sample data** before full deployment

***

### Configuring a Custom Aggregation for Your Model

After you've created a custom metric in the workspace:

1. Go to your model's **metric configuration**
2. Add the custom metric to the model
3. Provide values for each aggregate argument:
   * Dataset
   * Timestamp column
   * Feature or label columns
   * Any literal thresholds or category values

Arthur will substitute the configured values into your SQL by replacing `{{variable_name}}` with the chosen dataset, column names, or literals at execution time. The metric will then be computed in subsequent metrics calculation jobs and appear alongside all other metrics for that model.

***

## Complete Example – Multi-Label F1 Score

Here's a complete, production-ready example that calculates precision, recall, and F1 score per label for multi-label classification:

**SQL query:**

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
      {{row_id_col}}::text AS row_id,
      {{predicted_labels_col}} AS pred_labels,
      {{ground_truth_labels_col}} AS gt_labels
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
  ),
  pred_exploded AS (
    SELECT
      bucket, row_id, label, 1 AS predicted
    FROM base
    CROSS JOIN LATERAL (
      SELECT DISTINCT unnest(pred_labels) AS label
    ) p
    WHERE label IS NOT NULL AND label <> ''
  ),
  gt_exploded AS (
    SELECT
      bucket, row_id, label, 1 AS actual
    FROM base
    CROSS JOIN LATERAL (
      SELECT DISTINCT unnest(gt_labels) AS label
    ) g
    WHERE label IS NOT NULL AND label <> ''
  ),
  joined AS (
    SELECT
      COALESCE(p.bucket, g.bucket) AS bucket,
      COALESCE(p.label, g.label) AS label,
      COALESCE(predicted, 0) AS predicted,
      COALESCE(actual, 0) AS actual
    FROM pred_exploded p
    FULL OUTER JOIN gt_exploded g
      ON p.row_id = g.row_id AND p.label = g.label
  ),
  confusion AS (
    SELECT
      bucket AS ts,
      label AS series,
      SUM(CASE WHEN predicted = 1 AND actual = 1 THEN 1 ELSE 0 END)::float AS tp,
      SUM(CASE WHEN predicted = 1 AND actual = 0 THEN 1 ELSE 0 END)::float AS fp,
      SUM(CASE WHEN predicted = 0 AND actual = 1 THEN 1 ELSE 0 END)::float AS fn
    FROM joined
    GROUP BY ts, series
  )
SELECT
  ts,
  series,
  tp / NULLIF(tp + fp, 0) AS precision,
  tp / NULLIF(tp + fn, 0) AS recall,
  (2.0 * tp) / NULLIF(2.0 * tp + fp + fn, 0) AS f1_score
FROM confusion
ORDER BY ts, series;
```

**Basic information:**

* Name: "Multi-Label Precision, Recall, and F1 Score"
* Model Problem Type: `multiclass_classification`
* Description: "Calculates precision, recall, and F1 score for each label separately in multi-label classification"

**Aggregate arguments:**

1. Dataset argument (`dataset`)
2. Timestamp column argument (`timestamp_col`)
   * Allowed type: `timestamp`
   * Tag hint: `primary_timestamp`
3. Row ID column argument (`row_id_col`)
   * Allowed types: `str`, `uuid`, `int`
4. Predicted labels column argument (`predicted_labels_col`)
   * Allow any column type: `Yes`
   * Tag hint: `prediction`
5. Ground truth labels column argument (`ground_truth_labels_col`)
   * Allow any column type: `Yes`
   * Tag hint: `ground_truth`

**Reported metric configuration:**

1. Metric name: `precision`
   * Value column: `precision`
   * Timestamp column: `ts`
   * Dimension columns: `series`
   * Metric kind: `Numeric`

2. Metric name: `recall`
   * Value column: `recall`
   * Timestamp column: `ts`
   * Dimension columns: `series`
   * Metric kind: `Numeric`

3. Metric name: `f1_score`
   * Value column: `f1_score`
   * Timestamp column: `ts`
   * Dimension columns: `series`
   * Metric kind: `Numeric`

Once configured for a model, you can:

* Plot precision, recall, and F1 for each label over time
* Compare performance across labels
* Set alerts on F1 thresholds per label
* Query via the Metrics Query UI

***

## Troubleshooting

**No values appearing for a custom metric**

* Verify the SQL query runs and returns rows in the SQL workspace
* Check that value/timestamp columns match your reported metric configuration
* Confirm aggregate arguments are filled in correctly for the model
* Ensure timestamp filtering includes data in your date range
* Check for NULL values in required columns

**Metric configuration errors**

* Ensure all `{{variables}}` used in SQL are defined as aggregate arguments
* Confirm column arguments point to columns of compatible types
* Verify array columns have "Allow any column type" set to Yes
* Check that dimension columns are in both SELECT and GROUP BY

**Unexpected values or trends**

* Query the metric directly in the Metrics Query UI to inspect bucket-level values
* Check dimension columns for cardinality issues or unexpected groupings
* Validate NULL handling with COALESCE and NULLIF
* Test SQL on sample data to verify logic

**Performance issues**

* Add timestamp filters: `WHERE {{timestamp_col}} BETWEEN ... AND ...`
* Limit data scanned with additional WHERE clauses
* Consider larger bucket sizes (hourly instead of 5-minute)
* Check for expensive operations like DISTINCT on large sets
* Review query plan with EXPLAIN

**Array operation errors**

* Ensure array columns are proper PostgreSQL array types
* Use `COALESCE(array_col, ARRAY[]::TEXT[])` for NULL arrays
* Cast arrays explicitly: `array_col::TEXT[]`
* Filter empty strings: `WHERE label <> ''`

***

## Additional Resources

For more examples and patterns, see:

* **[examples/binary-classification](../examples/binary-classification/)** - 7 production metrics
* **[examples/multi-classification](../examples/multi-classification/)** - 10 production metrics including advanced array operations
* **[Metrics & Querying Overview](overview-metrics-and-querying.md)** - Query patterns and aggregation techniques
* **[Arthur Custom Metrics Repository](https://github.com/anthropics/arthur-custom-metrics)** - Complete documentation and chart specifications
