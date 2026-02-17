## Overview

The **Data Completeness Percentage** metric measures what proportion of data records contain all required fields (i.e., no NULLs in the specified columns). It is a foundational **data quality** metric for any ML or analytics pipeline.

Low completeness means the model is making predictions on partial data — a leading indicator of silent failures, degraded accuracy, and unreliable outputs.

This metric is **model-type agnostic** — it applies to any dataset (classification, regression, clustering, GenAI, decisioning, etc.).

It produces:

* **completeness_pct** — percentage of rows where all required columns are non-NULL (0–100)
* **incomplete_row_count** — absolute count of incomplete rows per time bucket (for volume-based alerting)

## Metrics

**completeness_pct**
Percentage of records with all required fields present:

```text
completeness_pct = (COUNT(complete_rows) / COUNT(all_rows)) × 100
```

A row is "complete" when every configured required column is non-NULL.

**incomplete_row_count**
Absolute count of rows missing at least one required field:

```text
incomplete_row_count = COUNT(all_rows) − COUNT(complete_rows)
```

Useful for volume-based alerts (e.g., "alert if more than 50 incomplete rows per day").

## Data Requirements

* `{{timestamp_col}}` – event timestamp
* `{{required_col_1}}` through `{{required_col_5}}` – the columns to check for completeness
* `{{dataset}}` – dataset containing the inferences

**Configuring the required columns**: This metric checks 5 columns by default. Adapt to your needs:

* **Fewer than 5 columns to check**: Set unused column arguments to `{{timestamp_col}}` (which is always non-NULL for valid rows), effectively disabling those checks.
* **More than 5 columns to check**: Duplicate the metric and add additional `AND {{required_col_N}} IS NOT NULL` conditions to the SQL.

## Base Metric SQL

This SQL counts rows where all required columns are non-NULL, then computes the completeness percentage per time bucket.

```sql
WITH base AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    CASE
      WHEN {{required_col_1}} IS NOT NULL
       AND {{required_col_2}} IS NOT NULL
       AND {{required_col_3}} IS NOT NULL
       AND {{required_col_4}} IS NOT NULL
       AND {{required_col_5}} IS NOT NULL
      THEN 1
      ELSE 0
    END AS is_complete
  FROM
    {{dataset}}
  WHERE
    {{timestamp_col}} IS NOT NULL
)

SELECT
  bucket AS bucket,
  (SUM(is_complete)::float / NULLIF(COUNT(*)::float, 0)) * 100.0 AS completeness_pct,
  (COUNT(*) - SUM(is_complete))::float AS incomplete_row_count
FROM
  base
GROUP BY
  bucket
ORDER BY
  bucket;
```

**What this query returns**

* `bucket` — timestamp bucket (1 day)
* `completeness_pct` — percentage of complete rows (0–100)
* `incomplete_row_count` — number of rows with at least one NULL in the required columns

## Aggregate Arguments

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Timestamp column for time bucketing`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Required Column 1

1. **Parameter Key:** `required_col_1`
2. **Friendly Name:** `Required Column 1`
3. **Description:** `First column to check for NULL values. Map to your most critical required field (e.g., prediction column).`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `prediction`

### Argument 3 — Required Column 2

1. **Parameter Key:** `required_col_2`
2. **Friendly Name:** `Required Column 2`
3. **Description:** `Second column to check for NULL values (e.g., ground truth column). Set to timestamp column if unused.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `ground_truth`

### Argument 4 — Required Column 3

1. **Parameter Key:** `required_col_3`
2. **Friendly Name:** `Required Column 3`
3. **Description:** `Third column to check for NULL values (e.g., key feature column). Set to timestamp column if unused.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`

### Argument 5 — Required Column 4

1. **Parameter Key:** `required_col_4`
2. **Friendly Name:** `Required Column 4`
3. **Description:** `Fourth column to check for NULL values. Set to timestamp column if unused.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`

### Argument 6 — Required Column 5

1. **Parameter Key:** `required_col_5`
2. **Friendly Name:** `Required Column 5`
3. **Description:** `Fifth column to check for NULL values. Set to timestamp column if unused.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`

### Argument 7 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Completeness Percentage

1. **Metric Name:** `completeness_pct`
2. **Description:** `Percentage of rows where all required columns are non-NULL (0–100)`
3. **Value Column:** `completeness_pct`
4. **Timestamp Column:** `bucket`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** _(none)_

### Metric 2 — Incomplete Row Count

1. **Metric Name:** `incomplete_row_count`
2. **Description:** `Count of rows with at least one NULL in the required columns`
3. **Value Column:** `incomplete_row_count`
4. **Timestamp Column:** `bucket`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** _(none)_

## Plots

See the [charts](../../charts/data-quality/) folder for visualization examples:

* [Plot 1: Completeness Percentage Over Time](../../charts/data-quality/completeness-pct-over-time.md)
* [Plot 2: Incomplete Rows Over Time](../../charts/data-quality/incomplete-rows-over-time.md)

---

### Plot 1 — Completeness Percentage Over Time

Uses:

* `completeness_pct`

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
        WHEN metric_name = 'completeness_pct' THEN 'Data Completeness (%)'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'completeness_pct'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**
This plot tracks the percentage of complete data records over time.

**How to interpret it**

* **100%** means every record has all required fields populated — ideal state.
* **Gradual decline** suggests an upstream data pipeline is progressively losing fields (e.g., a source table schema change, ETL failures, or new data sources without all fields).
* **Sudden drop** indicates an acute issue — a broken pipeline, provider outage, or schema migration that introduced NULLs.
* Set a **floor alert** (e.g., "alert if completeness drops below 95%") as an early warning for data pipeline issues.

***

### Plot 2 — Incomplete Rows Over Time

Uses:

* `incomplete_row_count`

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
        WHEN metric_name = 'incomplete_row_count' THEN 'Incomplete Rows'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(SUM(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'incomplete_row_count'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**What this shows**
This plot tracks the absolute count of incomplete records per day.

**How to interpret it**

* Useful when completeness percentage stays high but volume matters — 1% of 1M rows is still 10K incomplete records.
* Spikes reveal specific days with data quality issues, making root-cause investigation easier.
* Pair with completeness percentage: if both rise together, it may be normal growth with proportional gaps. If count rises while percentage is stable, total volume is increasing.

## Interpretation Guide

| Completeness | Interpretation |
|-------------|----------------|
| 99% – 100%  | Excellent — data pipeline is healthy |
| 95% – 99%   | Good — minor gaps, typically acceptable |
| 90% – 95%   | Warning — investigate which fields are missing and why |
| 80% – 90%   | Poor — significant data gaps, model predictions may be unreliable |
| < 80%       | Critical — data pipeline is substantially broken |

## Use Cases

* **Data pipeline monitoring** — detect upstream failures, schema changes, or ETL issues before they impact model performance
* **Model input validation** — ensure prediction requests contain all features the model expects
* **Ground truth tracking** — monitor whether labels/outcomes are arriving on schedule (ground truth columns often lag)
* **SLA compliance** — prove data completeness meets contractual or regulatory requirements
* **Root cause analysis** — when model performance drops, check completeness first to rule out missing input data
* **Onboarding validation** — verify new data sources provide all required fields before enabling model scoring

## Extending This Metric

**Per-column NULL rates**: To identify which specific column is causing incompleteness, create a variant that reports NULL rate per column:

```sql
SELECT
  time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
  'col_1' AS series,
  (COUNT(*) - COUNT({{required_col_1}}))::float / NULLIF(COUNT(*)::float, 0) * 100.0 AS null_rate_pct
FROM {{dataset}}
WHERE {{timestamp_col}} IS NOT NULL
GROUP BY bucket

UNION ALL

SELECT
  time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
  'col_2' AS series,
  (COUNT(*) - COUNT({{required_col_2}}))::float / NULLIF(COUNT(*)::float, 0) * 100.0 AS null_rate_pct
FROM {{dataset}}
WHERE {{timestamp_col}} IS NOT NULL
GROUP BY bucket

-- ... repeat for each column
ORDER BY bucket, series;
```

This gives a `null_rate_pct` metric with dimension `series` (column name), making it easy to pinpoint which field is causing drops in overall completeness.
