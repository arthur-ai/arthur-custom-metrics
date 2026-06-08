# Custom Metrics — SQL Authoring Guide

A detailed reference for writing, configuring, and troubleshooting custom metric SQL in Arthur. Read this when you're ready to write a metric from scratch, adapt an existing one, or understand why a metric is returning unexpected values.

For the high-level overview and UI walkthrough, return to [§4 of the Onboarding Guide](./user-onboarding-guide.md#4-creating-custom-metrics).

---

## Table of Contents

1. [How Custom Metrics Work](#1-how-custom-metrics-work)
2. [Step 1 — Write the SQL](#2-step-1--write-the-sql)
3. [Step 2 — Basic Information](#3-step-2--basic-information)
4. [Step 3 — Configure Aggregate Arguments](#4-step-3--configure-aggregate-arguments)
5. [Step 4 — Configure Reported Metrics](#5-step-4--configure-reported-metrics)
6. [Step 5 — Attach to a Model](#6-step-5--attach-to-a-model)
7. [Advanced Patterns](#7-advanced-patterns)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. How Custom Metrics Work

Each custom metric is a SQL query that runs against your raw inference data on a schedule. Arthur substitutes `{{template_variables}}` with the dataset, column names, and literal values you configure per model, then stores the query output as named time series.

```
Raw inference data (your S3 / Snowflake / etc.)
    ↓
[Custom SQL with {{template_variables}}]
    ↓
Reported Metrics (time series per output column)
    ↓
metrics_numeric_latest_version  ←  dashboards, alerts, queries
```

A single SQL query can produce multiple reported metrics. A single metric definition can be attached to multiple models with different column mappings each time.

---

## 2. Step 1 — Write the SQL

### Minimum viable structure

Every custom metric query must:

1. Use `time_bucket()` to group results into time windows
2. Reference the dataset via `{{dataset}}`
3. Filter `WHERE {{timestamp_col}} IS NOT NULL`
4. Output all columns referenced in your Reported Metrics configuration

```sql
SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
    COUNT(*)::int AS row_count
FROM {{dataset}}
WHERE {{timestamp_col}} IS NOT NULL
GROUP BY ts
ORDER BY ts;
```

### Time bucket sizing

| Interval | Use When |
|----------|----------|
| `'5 minutes'` | High-frequency data, real-time dashboards |
| `'1 hour'` | Moderate volume, intraday trends |
| `'1 day'` | Most production metrics — good balance of granularity and performance |
| `'1 week'` | Long-term trend analysis, low-volume models |

Daily buckets are the standard recommendation for production models.

### Template variable syntax

Every `{{variable_name}}` in the SQL must have a matching Aggregate Argument (see §4). Arthur substitutes these at execution time:

| Variable type | Example in SQL | Resolves to |
|--------------|----------------|-------------|
| Dataset | `FROM {{dataset}}` | The table backing the chosen dataset |
| Column | `{{timestamp_col}}` | A column name (e.g., `timestamp`) |
| Literal | `{{threshold}}` | A scalar value (e.g., `0.10`) |

### NULL handling

Always handle NULLs explicitly — unhandled NULLs silently drop rows or cause errors:

```sql
-- Filter NULL timestamps (required in every query)
WHERE {{timestamp_col}} IS NOT NULL

-- Default NULL arrays to empty
COALESCE({{array_column}}, ARRAY[]::TEXT[])

-- Prevent division by zero
value_a / NULLIF(value_b, 0)

-- Handle NULLs in array length
COALESCE(array_length({{array_col}}, 1), 0)::float
```

### Type casting

Cast output columns explicitly to ensure correct storage:

```sql
COUNT(*)::int           -- integer counts
AVG(value)::float       -- rates, averages
SUM(value)::float       -- running totals
value::text             -- dimension strings
```

### Using CTEs for readability

For any query with more than one logical step, use CTEs:

```sql
WITH
  -- Step 1: filter and bucket
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_col}}::float AS prediction,
      {{ground_truth_col}}::float AS actual
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
      AND {{prediction_col}} IS NOT NULL
      AND {{ground_truth_col}} IS NOT NULL
  ),
  -- Step 2: flag each row
  flags AS (
    SELECT
      ts,
      CASE
        WHEN ABS((prediction - actual) / NULLIF(actual, 0)) <= {{threshold}}
        THEN 1.0 ELSE 0.0
      END AS is_accurate
    FROM base
  )
-- Step 3: aggregate
SELECT
  ts,
  AVG(is_accurate)::float AS accuracy_rate,
  COUNT(*)::int            AS total_predictions
FROM flags
GROUP BY ts
ORDER BY ts;
```

CTEs make it easier to debug each step independently by running just that CTE in the SQL workspace.

---

## 3. Step 2 — Basic Information

| Field | Guidance |
|-------|----------|
| **Name** | Human-readable label shown in the UI. Does not need to match the metric name in the time series output. |
| **Description** | Explain what the metric measures and how to interpret it. Include the normal range and what a bad value looks like. |
| **Model Problem Type** | Optionally restrict the metric to `binary_classification`, `regression`, `multiclass_classification`, or `genai`. Arthur uses this to suggest the metric when users configure models of that type. |

### Versioning

When you edit a custom metric and save, Arthur creates a new version. Models remain pinned to the previous version until you explicitly update their metric configuration. This means you always have a clear audit trail of which SQL produced which historical values.

---

## 4. Step 3 — Configure Aggregate Arguments

Add one argument for every `{{variable}}` in your SQL. Arthur renders these as form fields when a user attaches the metric to a model.

### Dataset argument (required for every metric)

| Field | Value |
|-------|-------|
| Parameter Key | `dataset` (must match your `FROM {{dataset}}` variable) |
| Parameter Type | **Dataset** |
| Friendly Name | e.g., `Inference Dataset` |
| Description | e.g., `Dataset containing model predictions and ground truth` |

### Timestamp column argument (required for every metric)

| Field | Value |
|-------|-------|
| Parameter Key | `timestamp_col` |
| Parameter Type | **Column** |
| Source Dataset Parameter Key | `dataset` |
| Allowed Column Types | `timestamp` |
| Tag Hint | `primary_timestamp` |

### Column arguments (one per data column referenced)

| Field | Guidance |
|-------|----------|
| Parameter Key | Must match the `{{variable_name}}` in your SQL |
| Parameter Type | **Column** |
| Source Dataset Parameter Key | `dataset` |
| Allowed Column Types | Use `int, float` for numeric; `str` for categorical; leave blank and set "Allow Any Column Type" to Yes for array columns |
| Tag Hints | `prediction`, `ground_truth`, `categorical`, `continuous` — guides users to the right column |

### Literal arguments (for thresholds and fixed values)

| Field | Guidance |
|-------|----------|
| Parameter Key | Must match the `{{variable_name}}` in your SQL |
| Parameter Type | **Literal** |
| Data Type | `Float`, `Integer`, or `String` |
| Default Value | Set a sensible default (e.g., `0.10` for a 10% accuracy threshold) |

**Common literal use cases:**

- Classification threshold (e.g., `0.5`)
- Accuracy tolerance (e.g., `0.10` for 10%)
- Category name to filter on
- Lookback window size

---

## 5. Step 4 — Configure Reported Metrics

A single SQL query can produce multiple reported metrics — one per output column. Each reported metric becomes an independent time series in Arthur's metrics store.

| Field | Description |
|-------|-------------|
| **Metric Name** | The `metric_name` value stored in the metrics table. This is what you filter on in dashboard SQL and alert queries. Use `snake_case`. |
| **Description** | Description specific to this particular output column. |
| **Value Column** | The column from your SQL query that contains the metric value (e.g., `accuracy_rate`). |
| **Timestamp Column** | The time bucket column from your SQL (e.g., `ts`). |
| **Metric Kind** | `Numeric` for scalar floats/integers; `Sketch` for distribution summaries (histograms, percentiles). Most metrics are `Numeric`. |
| **Dimension Columns** | Optional columns whose values become key-value pairs in the `dimensions` JSONB field. Used for filtering or grouping in dashboard queries. |

### Multiple outputs from one query

If your SQL outputs `accuracy_rate`, `accurate_count`, and `total_count`, add three reported metrics — one for each column, all pointing to the same `ts` timestamp column.

### Dimension column guidance

Dimensions let you slice a single metric by a categorical value (e.g., `region`, `label`, `model_version`).

- **Keep cardinality low**: 10–100 unique values is fine; thousands of values will cause storage bloat.
- **Include in GROUP BY**: Dimension columns must appear in the `GROUP BY` clause of your SQL.
- **Multiple dimensions multiply**: Two dimension columns with 10 values each produce up to 100 time series (10 × 10). Be deliberate.

To filter by dimension in a dashboard query:

```sql
WHERE metric_name = 'accuracy_rate'
  AND dimensions->>'region' = 'northeast'
```

---

## 6. Step 5 — Attach to a Model

After saving the metric definition at the workspace level:

1. Navigate to your model's **Metric Configuration** (Model Management → Metric Configuration).
2. Click **+ Add Custom Metric** and select the definition you created.
3. Fill in each aggregate argument:
   - **Dataset**: select the dataset associated with this model
   - **Column arguments**: map each argument to the correct column in that dataset
   - **Literal arguments**: enter the threshold or value (or accept the default)
4. Click **Save**.

The metric will run on the next scheduled metrics calculation job. To run it immediately, use **Refresh Data Now** from the model overview page.

---

## 7. Advanced Patterns

### Pattern: Multi-dimensional output

Use multiple `GROUP BY` columns to produce metrics broken out by category:

```sql
SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
    {{segment_col}}::text AS segment,
    AVG({{score_col}})::float AS avg_score
FROM {{dataset}}
WHERE {{timestamp_col}} IS NOT NULL
GROUP BY ts, segment
ORDER BY ts, segment;
```

Configure `segment` as a dimension column in the Reported Metric. Dashboard queries can then filter to a specific segment or plot all segments as separate lines.

### Pattern: Confusion matrix components

Calculate TP, FP, FN per time bucket for binary classification:

```sql
SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
    SUM(CASE WHEN pred = 1 AND actual = 1 THEN 1 ELSE 0 END)::float AS tp,
    SUM(CASE WHEN pred = 1 AND actual = 0 THEN 1 ELSE 0 END)::float AS fp,
    SUM(CASE WHEN pred = 0 AND actual = 1 THEN 1 ELSE 0 END)::float AS fn
FROM (
    SELECT
        {{timestamp_col}},
        CASE WHEN {{score_col}}::float >= {{threshold}} THEN 1 ELSE 0 END AS pred,
        {{ground_truth_col}}::int AS actual
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
) classified
GROUP BY ts
ORDER BY ts;
```

Register `tp`, `fp`, and `fn` as three separate reported metrics from this one query. Add a fourth metric for F1 by extending the SELECT:

```sql
(2.0 * tp) / NULLIF(2.0 * tp + fp + fn, 0) AS f1_score
```

### Pattern: Array column operations (multi-label classification)

Use `CROSS JOIN LATERAL` with `unnest()` to explode array columns:

```sql
WITH base AS (
    SELECT
        time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
        {{row_id_col}}::text AS row_id,
        COALESCE({{pred_labels_col}}, ARRAY[]::TEXT[]) AS pred_labels
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
),
exploded AS (
    SELECT
        ts,
        row_id,
        lbl
    FROM base
    CROSS JOIN LATERAL (
        SELECT DISTINCT unnest(pred_labels) AS lbl
    ) u
    WHERE lbl IS NOT NULL AND lbl <> ''
)
SELECT
    ts,
    lbl AS label,
    COUNT(DISTINCT row_id)::float AS label_count
FROM exploded
GROUP BY ts, label
ORDER BY ts, label;
```

Set `label` as a dimension column so each label appears as a separate line in dashboard charts.

### Pattern: Jaccard similarity (set comparison)

Compare predicted and ground truth label sets per inference, then average over a time bucket:

```sql
WITH base AS (
    SELECT
        time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
        COALESCE({{pred_labels_col}}, ARRAY[]::TEXT[]) AS pred_set,
        COALESCE({{gt_labels_col}},   ARRAY[]::TEXT[]) AS gt_set
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
),
jaccard AS (
    SELECT
        ts,
        CARDINALITY(
            ARRAY(SELECT unnest(pred_set) INTERSECT SELECT unnest(gt_set))
        )::float AS intersection_size,
        CARDINALITY(
            ARRAY(SELECT DISTINCT unnest(pred_set || gt_set))
        )::float AS union_size
    FROM base
)
SELECT
    ts,
    AVG(
        CASE WHEN union_size = 0 THEN 1.0
             ELSE intersection_size / union_size
        END
    )::float AS jaccard_similarity
FROM jaccard
GROUP BY ts
ORDER BY ts;
```

### Pattern: Derived rates (precision, recall, F1)

Calculate rates at query time from stored count metrics rather than recomputing from raw data:

```sql
WITH confusion AS (
    -- ... confusion matrix CTE from above
)
SELECT
    ts,
    tp / NULLIF(tp + fp, 0) AS precision,
    tp / NULLIF(tp + fn, 0) AS recall,
    (2.0 * tp) / NULLIF(2.0 * tp + fp + fn, 0) AS f1_score
FROM confusion
ORDER BY ts;
```

Register `precision`, `recall`, and `f1_score` as separate reported metrics — all from one query.

---

## 8. Troubleshooting

### No values appearing

1. Verify the SQL returns rows by running it in the Metrics Query UI with literal values substituted.
2. Check that the timestamp range in the query overlaps with data in the dataset.
3. Confirm the aggregate argument values are filled in on the model (not left blank).
4. Check for NULL values in required columns with:

```sql
SELECT
    COUNT(*) AS total,
    COUNT({{timestamp_col}}) AS non_null_timestamps,
    COUNT({{prediction_col}}) AS non_null_predictions
FROM {{dataset}};
```

### Unexpected or wrong values

- Run each CTE in isolation in the SQL workspace to verify intermediate results.
- Check dimension columns for unexpected cardinality or NULL values.
- Verify type casts — a column stored as `str` that contains numbers needs an explicit `::float` cast.
- Confirm `NULLIF` is preventing division by zero where expected.

### Metric values differ from manual calculation

The most common cause is excluded rows. Check whether NULLs, zero actuals, or values outside the time range are being filtered out:

```sql
SELECT
    COUNT(*) FILTER (WHERE {{ground_truth_col}} IS NULL) AS null_actuals,
    COUNT(*) FILTER (WHERE {{ground_truth_col}} = 0)     AS zero_actuals,
    MIN({{timestamp_col}}) AS earliest,
    MAX({{timestamp_col}}) AS latest
FROM {{dataset}};
```

### Performance issues

- Add a timestamp filter early in the query: `WHERE {{timestamp_col}} BETWEEN ... AND ...`
- Avoid `SELECT DISTINCT` on large sets — use `GROUP BY` instead where possible.
- Use larger time buckets (hourly or daily) for high-volume datasets.
- Run `EXPLAIN` on the query to check for sequential scans.

### Array operation errors

- Ensure array columns are proper PostgreSQL array types, not JSON strings.
- Use `COALESCE(col, ARRAY[]::TEXT[])` to handle NULL arrays before `unnest()`.
- Cast arrays explicitly: `col::TEXT[]`
- Filter empty strings after unnesting: `WHERE lbl IS NOT NULL AND lbl <> ''`

---

## See Also

- [Onboarding Guide §4 — Custom Metrics Overview](./user-onboarding-guide.md#4-creating-custom-metrics)
- [Pre-built metric examples](../examples/metrics/) — production-ready SQL for all model types
- [Configuration options reference](../references/configuration-options.md) — valid column types, tag hints, and data types
- [Metrics & Querying Overview](../references/overview-metrics-and-querying.md) — how metrics are stored and queried
- [How to Create a Custom Metric](../references/how-to-create-a-custom-metric.md) — official platform reference
