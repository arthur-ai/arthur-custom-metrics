# Metrics & Querying Overview

This document provides an overview of the metrics in Arthur, as well as how to write queries against them to build
dashboards and alert rules.

# Introduction to Arthur Metrics

Arthur reports pre-aggregated metrics on 5 minute cadences, based on the source data for user's models. Each metric reported has the following format:

`(Model ID, Metric Name, Timestamp, Value, Dimensions)`

1. **Model ID** - the UUID of the model
2. **Metric Name** - the name of the metric, see the metric overview section [below](#list-of-current-metrics) for a
   description of each
3. **Timestamp** - the 5-minute aligned timestamp of the metric that summarizes the 5-minute interval. A timestamp of
   05:00 covers the interval [05:00-09:59)
4. **Value** - a floating point number (or sketch)
5. **Dimensions** - a set of key-value pairs that provide metadata for the metric

### Types of Metrics

Arthur supports two different types of `Value`s in its metrics.

For the first type, `Value` is a floating point number. These are called "numeric" metrics, and they generally represent counts of observable values. Some examples include inference count, hallucination count, rule failure count, true positive count, etc.

The second type of metrics support a `Value` that is a [data sketch](https://datasketches.apache.org). Data sketches provide a way to calculate summary statistics of a distribution like median, max, min, and quantiles, without saving the entire distribution. They are probabilistic summaries of the data with bounded error guarantees. Common examples of these metrics would be latencies, distributions, histograms, etc.

### Metrics Versioning

Arthur supports versioned metrics to deduplicate and update metrics across multiple Metrics Calculation job runs. Each metric is stored with a `metric_version` integer, that's a monotonically increasing version for each metric. Metrics are deduplicated based on the tuple `(metric name, timestamp, and metric version)`, and the latest version is queried by default for each time point. Each time a new metrics computation runs, the metrics uploaded from that run are given a new version number, effectively enabling a metric history that allows comparison across versions.

### Metrics Tables and Views

Arthur provides the latest version views for querying a model's metrics. They show only the latest version for each time point, so you can easily query across all metrics of the latest version.

Additionally, Arthur supports two views based on the type of metric:

1. numeric metrics
2. sketch metrics

Overall, this produces 2 different views that are available to query:

1. `metrics_numeric_latest_version` - a view of the numeric metrics with the latest version for each time point
2. `metrics_sketch_latest_version` - a view of the sketch metrics with the latest version for each time point

### Metrics Table Formats

All the metrics tables are organized similar to the tuple above, `(Model ID, Metric Name, Timestamp, Metric Version, Value, Dimensions)`.

An example of a numeric and sketch row in the table would look like:

| Model ID                             | Metric Name     | Timestamp                         | Metric Version | Value         | Dimensions                                                               |
| ------------------------------------ | --------------- | --------------------------------- | -------------- | ------------- | ------------------------------------------------------------------------ |
| 27a69cb5-29e7-4058-b426-fc5294a0a059 | inference_count | 2024-07-30 14:00:00.000000 +00:00 | 1              | 146           | `{"result": "Fail", "prompt_result": "Fail", "response_result": "Pass"}` |
| 27a69cb5-29e7-4058-b426-fc5294a0a059 | pii_score       | 2024-07-30 13:50:00.000000 +00:00 | 1              | (sketch type) | `{"entity": "US_SSN", "result": "Fail", "location": "prompt"}`           |

# Query Language

Arthur exposes two places where users can write queries to interact with their metrics, writing queries to generate
dashboards, and writing queries to generate alert rules. Both places allow users to write [PostgreSQL 16](https://www.postgresql.org/docs/16/index.html) with the [Timescale extension](https://docs.timescale.com) SQL to investigate and visualize their metrics.

### Considerations for Writing Queries

Since Arthur's data plane reports metrics on pre-aggregated 5-minute intervals, queries need to be written to perform final calculations on top of the raw count and sketch metrics it reports. For example, the data plane does not report "rates", because the division required to calculate them means they cannot be further aggregated into larger intervals. As a result, any calculations will perform the final rollups at query time in order to ensure metrics remain accurate at all time window aggregations. In general, metrics like rates, averages, etc. need to be calculated at query time based on the pre-aggregate metrics stored in the platform.

### Callouts

1. The queries below are taken from Arthur's standard dashboards. They contain syntax used by the dashboard to filter the range of data shown in the graph. The following lines/filters can be omitted when writing alert rule queries because the query API will add the time range and model filters automatically:
   ```sql
   AND model_id = '{{model_id}}'
   ```
   This line should not be omitted in its entirety, but the brackets will need to be removed:
   ```sql
   [[ AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}' ]]
   ```

2. The Arthur standard dashboards use dashboard-wide model ID filters, which means they are not specified in the
   queries. Be careful when creating a new dashboard or removing that dashboard-wide filter because the queries will no longer be filtered for a single model. A model ID filter can be added in the query SQL using the following dashboard query filter syntax.
   ```sql
   AND model_id = '{{model_id}}'
   ```

# Query Patterns and Examples

## Basic Patterns

### 1. Querying a Numeric Metric

This query is an example of how to query a numeric metric, and aggregate it on a daily roll up:

```sql
SELECT
  time_bucket(INTERVAL '1 day', timestamp) AS bucket,
  SUM(value) AS total
FROM metrics_numeric_latest_version
WHERE metric_name = 'inference_count'
  AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
GROUP BY bucket
ORDER BY bucket;
```

### 2. Hallucination Rate

This query is an example of a more advanced calculation finalized at query time. In this query, we select two metrics,
one for the count of hallucinations per interval, and one for the count of inferences in that interval. We join them on timestamp then divide to get the rate, or percentage, of hallucinations per interval. It includes a divide by zero protection in the case there were no inferences in the interval.

```sql
WITH
  hallucination_count AS (
    SELECT
      time_bucket(INTERVAL '1 day', timestamp) AS bucket,
      SUM(value) AS total
    FROM metrics_numeric_latest_version
    WHERE metric_name = 'hallucination_count'
      AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
    GROUP BY bucket
  ),
  total_count AS (
    SELECT
      time_bucket(INTERVAL '1 day', timestamp) AS bucket,
      SUM(value) AS total
    FROM metrics_numeric_latest_version
    WHERE metric_name = 'inference_count'
      AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
    GROUP BY bucket
  )
SELECT
  hallucination_count.bucket AS timestamp,
  CASE
    WHEN total_count.total = 0 THEN 0
    ELSE hallucination_count.total / total_count.total
  END AS hallucination_rate
FROM hallucination_count
JOIN total_count ON hallucination_count.bucket = total_count.bucket
ORDER BY hallucination_count.bucket DESC;
```

## Sketch Metric Patterns

### 3. Basic Sketch Operations

Sketch metric types allow for querying properties of a distribution from the stored values. For aggregating on intervals larger than 5 minutes, they can be merged to generate sketches that represent the combined properties of all data that were summarized by the individual sketches before merging. Some helpful functions include:

* `kll_float_sketch_merge(sketch)` - this function allows merging sketch values in a group into a single sketch
* `kll_float_sketch_get_quantile(sketch, quantile)` - this function returns the value of the requested quantile from the distribution summarized by the sketch. Getting the median is the same as the `0.5`th quantile. Getting the 95% percentile is the `0.95`th quantile.
* `kll_float_sketch_get_n(sketch)` - returns the number of values summarized by the sketch
* `kll_float_sketch_get_max_item(sketch)` - returns the max item seen by the sketch
* `kll_float_sketch_get_min_item(sketch)` - returns the min item seen by the sketch
* `kll_float_sketch_get_pmf(sketch, [points])` - returns the probability mass function value evaluated at each of the points. This can be multiplied by the result of the `kll_float_sketch_get_n` value to obtain counts for a distribution.

### 4. Querying a Sketch Metric

This query is an example of how to query a sketch based metric. This query returns the median latency grouped by
the `rule_type` dimension on the `rule_latency` metric per day.

```sql
SELECT
  time_bucket(INTERVAL '1 day', timestamp) AS bucket,
  kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.5) AS median_latency,
  dimensions ->> 'rule_type' AS rule_type
FROM metrics_sketch_latest_version
WHERE metric_name = 'rule_latency'
  AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
GROUP BY bucket, rule_type
ORDER BY bucket, rule_type;
```

### 5. Creating a Distribution

This query creates a table of the values of a distribution for a variable that varies between 0 and 1. It creates a
bucket at 0.05 intervals for all data within the time range, so it is not grouped by time buckets. It uses the `get_pmf` sketch function to obtain the percentage of values in each interval, then multiplies it by the total count of values seen by the sketch to get the number in each interval.

```sql
WITH merged AS (
  SELECT
    kll_float_sketch_get_pmf(
      kll_float_sketch_merge(value),
      ARRAY[0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95]
    ) AS sketch,
    kll_float_sketch_get_n(kll_float_sketch_merge(value)) AS total
  FROM metrics_sketch_latest_version
  WHERE metric_name = 'toxicity_score'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
)
SELECT
  ROUND(((ordinality) / 20.0), 2)::VARCHAR AS num_claims,
  val * merged.total AS inf_count
FROM merged,
UNNEST(merged.sketch) WITH ORDINALITY AS val;
```

## Advanced Query Patterns

### 6. Multi-Dimensional Metrics

Query metrics with multiple dimension columns (e.g., label co-occurrence with label_1 and label_2):

```sql
SELECT
  time_bucket(INTERVAL '1 day', timestamp) AS bucket,
  dimensions ->> 'label_1' AS label_1,
  dimensions ->> 'label_2' AS label_2,
  SUM(value) AS cooccurrence_count
FROM metrics_numeric_latest_version
WHERE metric_name = 'pred_cooccurrence_count'
  AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
GROUP BY bucket, label_1, label_2
ORDER BY bucket, cooccurrence_count DESC;
```

**Use case**: Understand which label pairs frequently appear together in predictions.

### 7. Filtering by Dimension Values

Filter metrics to specific dimension values:

```sql
SELECT
  time_bucket(INTERVAL '1 day', timestamp) AS bucket,
  dimensions ->> 'series' AS label,
  AVG(value) AS avg_f1_score
FROM metrics_numeric_latest_version
WHERE metric_name = 'f1_score'
  AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  -- Filter to specific labels
  AND dimensions ->> 'series' IN ('cat', 'dog', 'bird')
GROUP BY bucket, label
ORDER BY bucket, label;
```

**Use case**: Focus analysis on specific labels or categories of interest.

### 8. Top N by Dimension

Identify top performing or problematic labels:

```sql
WITH label_performance AS (
  SELECT
    dimensions ->> 'series' AS label,
    AVG(value) AS avg_f1_score
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'f1_score'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  GROUP BY label
)
SELECT
  label,
  avg_f1_score
FROM label_performance
ORDER BY avg_f1_score ASC  -- Lowest F1 scores
LIMIT 10;
```

**Use case**: Identify the 10 worst performing labels for improvement focus.

### 9. Comparing Multiple Metrics per Dimension

Compare precision, recall, and F1 for each label:

```sql
WITH precision_data AS (
  SELECT
    time_bucket(INTERVAL '1 day', timestamp) AS bucket,
    dimensions ->> 'series' AS label,
    AVG(value) AS precision
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'precision'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  GROUP BY bucket, label
),
recall_data AS (
  SELECT
    time_bucket(INTERVAL '1 day', timestamp) AS bucket,
    dimensions ->> 'series' AS label,
    AVG(value) AS recall
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'recall'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  GROUP BY bucket, label
),
f1_data AS (
  SELECT
    time_bucket(INTERVAL '1 day', timestamp) AS bucket,
    dimensions ->> 'series' AS label,
    AVG(value) AS f1_score
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'f1_score'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  GROUP BY bucket, label
)
SELECT
  p.bucket,
  p.label,
  p.precision,
  r.recall,
  f.f1_score
FROM precision_data p
JOIN recall_data r ON p.bucket = r.bucket AND p.label = r.label
JOIN f1_data f ON p.bucket = f.bucket AND p.label = f.label
ORDER BY p.bucket, p.label;
```

**Use case**: Comprehensive view of label performance metrics for debugging.

### 10. Aggregating Across All Dimensions

Calculate overall metrics across all labels:

```sql
WITH per_label AS (
  SELECT
    time_bucket(INTERVAL '1 day', timestamp) AS bucket,
    dimensions ->> 'series' AS label,
    SUM(value) AS tp
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'tp'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  GROUP BY bucket, label
)
SELECT
  bucket,
  SUM(tp) AS total_tp,
  AVG(tp) AS avg_tp_per_label,
  COUNT(DISTINCT label) AS num_labels
FROM per_label
GROUP BY bucket
ORDER BY bucket;
```

**Use case**: Macro-level view of model performance across all labels.

### 11. Dimension Cardinality Check

Understand dimension cardinality to optimize queries:

```sql
SELECT
  metric_name,
  COUNT(DISTINCT dimensions ->> 'series') AS unique_series_values,
  COUNT(DISTINCT dimensions ->> 'label_1') AS unique_label_1_values,
  COUNT(DISTINCT dimensions ->> 'label_2') AS unique_label_2_values
FROM metrics_numeric_latest_version
WHERE timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
GROUP BY metric_name;
```

**Use case**: Identify high-cardinality dimensions that may impact query performance.

### 12. Trend Detection with Window Functions

Detect increasing or decreasing trends:

```sql
WITH daily_metrics AS (
  SELECT
    time_bucket(INTERVAL '1 day', timestamp) AS bucket,
    dimensions ->> 'series' AS label,
    AVG(value) AS f1_score
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'f1_score'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  GROUP BY bucket, label
)
SELECT
  bucket,
  label,
  f1_score,
  LAG(f1_score, 1) OVER (PARTITION BY label ORDER BY bucket) AS prev_f1_score,
  f1_score - LAG(f1_score, 1) OVER (PARTITION BY label ORDER BY bucket) AS day_over_day_change,
  AVG(f1_score) OVER (
    PARTITION BY label
    ORDER BY bucket
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS rolling_7day_avg
FROM daily_metrics
ORDER BY bucket, label;
```

**Use case**: Identify labels with degrading performance over time.

### 13. Percentile Analysis

Compute percentiles across labels:

```sql
WITH label_metrics AS (
  SELECT
    dimensions ->> 'series' AS label,
    AVG(value) AS avg_f1_score
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'f1_score'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  GROUP BY label
)
SELECT
  PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY avg_f1_score) AS p10,
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY avg_f1_score) AS p25,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY avg_f1_score) AS median,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_f1_score) AS p75,
  PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY avg_f1_score) AS p90
FROM label_metrics;
```

**Use case**: Understand the distribution of performance across all labels.

### 14. Cohort Analysis

Compare metrics across different time periods:

```sql
WITH week_1 AS (
  SELECT
    dimensions ->> 'series' AS label,
    AVG(value) AS week1_f1
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'f1_score'
    AND timestamp BETWEEN '2025-01-01' AND '2025-01-07'
  GROUP BY label
),
week_2 AS (
  SELECT
    dimensions ->> 'series' AS label,
    AVG(value) AS week2_f1
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'f1_score'
    AND timestamp BETWEEN '2025-01-08' AND '2025-01-14'
  GROUP BY label
)
SELECT
  w1.label,
  w1.week1_f1,
  w2.week2_f1,
  w2.week2_f1 - w1.week1_f1 AS change,
  CASE
    WHEN w1.week1_f1 > 0
    THEN ((w2.week2_f1 - w1.week1_f1) / w1.week1_f1) * 100
    ELSE NULL
  END AS percent_change
FROM week_1 w1
JOIN week_2 w2 ON w1.label = w2.label
ORDER BY ABS(w2.week2_f1 - w1.week1_f1) DESC;
```

**Use case**: Identify labels with significant week-over-week performance changes.

### 15. Cross-Metric Correlations

Analyze relationships between different metrics:

```sql
WITH coverage AS (
  SELECT
    dimensions ->> 'series' AS label,
    AVG(value) AS avg_coverage
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'coverage_ratio'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  GROUP BY label
),
f1 AS (
  SELECT
    dimensions ->> 'series' AS label,
    AVG(value) AS avg_f1
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'f1_score'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  GROUP BY label
)
SELECT
  c.label,
  c.avg_coverage,
  f.avg_f1,
  CASE
    WHEN c.avg_coverage < 0.05 THEN 'Rare'
    WHEN c.avg_coverage < 0.3 THEN 'Moderate'
    ELSE 'Common'
  END AS label_frequency,
  CASE
    WHEN f.avg_f1 < 0.5 THEN 'Poor'
    WHEN f.avg_f1 < 0.7 THEN 'Fair'
    WHEN f.avg_f1 < 0.9 THEN 'Good'
    ELSE 'Excellent'
  END AS label_quality
FROM coverage c
JOIN f1 f ON c.label = f.label
ORDER BY c.avg_coverage DESC;
```

**Use case**: Understand if label frequency correlates with performance quality.

## Timescale-Specific Features

### 16. Time Bucket Gap Filling

[time_bucket_gapfill](https://docs.timescale.com/api/latest/hyperfunctions/gapfilling/time_bucket_gapfill/#:~:text=Group%20data%20into%20buckets%20based,NULL%20in%20the%20returned%20data.\\&text=A%20PostgreSQL%20time%20interval%20to%20specify%20the%20length%20of%20each%20bucket.) - this function can be used to fill in all time buckets in a range in case values are not present in all time intervals. A common place this is used is to visualize `inference_count` over time. If there weren't any inferences in a time bucket, there would be no count to show, so the graph would be empty. Using this function allows queries to fill in NULL values for missing time buckets, which can be converted to zero or other defaults. Here's an example query:

```sql
SELECT
  time_bucket_gapfill(INTERVAL '1 hour', timestamp) AS bucket,
  CASE
    WHEN SUM(value) IS NULL THEN 0
    ELSE SUM(value)
  END AS total
FROM metrics_numeric_latest_version
WHERE metric_name = 'inference_count'
  AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
GROUP BY bucket
ORDER BY bucket;
```

### 17. Gap Filling with LOCF (Last Observation Carried Forward)

Fill gaps with the last observed value:

```sql
SELECT
  time_bucket_gapfill(INTERVAL '1 day', timestamp) AS bucket,
  dimensions ->> 'series' AS label,
  LOCF(AVG(value)) AS f1_score  -- Carries forward last value
FROM metrics_numeric_latest_version
WHERE metric_name = 'f1_score'
  AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
  AND dimensions ->> 'series' = 'important_label'
GROUP BY bucket, label
ORDER BY bucket;
```

**Use case**: Smooth out missing data points in time series visualizations.

## Best Practices

### Query Optimization

1. **Always use timestamp filters**
   ```sql
   WHERE timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
   ```
   This leverages time-based partitioning for faster queries.

2. **Filter by metric name early**
   ```sql
   WHERE metric_name = 'your_metric'
     AND timestamp BETWEEN ...
   ```
   Reduces the data scanned.

3. **Use CTEs for readability**
   Break complex queries into logical steps with `WITH` clauses.

4. **Limit dimension cardinality**
   Filter to specific dimension values when possible:
   ```sql
   AND dimensions ->> 'series' IN ('label1', 'label2', 'label3')
   ```

5. **Use appropriate time buckets**
   Larger buckets = faster queries:
   - 5 minutes for real-time monitoring
   - 1 hour for recent trends
   - 1 day for historical analysis
   - 1 week for long-term trends

### Dimension Extraction

Extract dimension values using PostgreSQL's JSON operators:

```sql
-- Single dimension
dimensions ->> 'dimension_name'

-- Check if dimension exists
dimensions ? 'dimension_name'

-- Extract multiple dimensions
dimensions ->> 'label_1' AS label_1,
dimensions ->> 'label_2' AS label_2
```

### NULL Handling in Aggregations

Always handle potential NULL values:

```sql
-- Prevent division by zero
CASE WHEN denominator = 0 THEN 0 ELSE numerator / denominator END

-- Or use NULLIF
numerator / NULLIF(denominator, 0)

-- Default NULL sums to zero
COALESCE(SUM(value), 0)
```

### Working with Multi-Dimensional Metrics

For metrics with multiple dimensions (e.g., co-occurrence matrix):

```sql
-- Extract both dimensions
SELECT
  dimensions ->> 'label_1' AS label_1,
  dimensions ->> 'label_2' AS label_2,
  SUM(value) AS count
FROM metrics_numeric_latest_version
WHERE metric_name = 'cooccurrence_count'
GROUP BY label_1, label_2;
```

**Important**: Cartesian product of dimensions can create many combinations (N × M values).

## Common Use Cases

### Monitoring Label Performance

Track F1 scores for all labels with alerting thresholds:

```sql
WITH current_f1 AS (
  SELECT
    dimensions ->> 'series' AS label,
    AVG(value) AS f1_score
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'f1_score'
    AND timestamp >= CURRENT_DATE - INTERVAL '7 days'
  GROUP BY label
)
SELECT
  label,
  f1_score,
  CASE
    WHEN f1_score < 0.5 THEN 'CRITICAL'
    WHEN f1_score < 0.7 THEN 'WARNING'
    ELSE 'OK'
  END AS status
FROM current_f1
WHERE f1_score < 0.7  -- Alert threshold
ORDER BY f1_score ASC;
```

### Detecting Data Drift

Compare label distributions across time periods:

```sql
WITH baseline AS (
  SELECT
    dimensions ->> 'series' AS label,
    AVG(value) AS baseline_coverage
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'coverage_ratio'
    AND timestamp BETWEEN '2025-01-01' AND '2025-01-07'
  GROUP BY label
),
current AS (
  SELECT
    dimensions ->> 'series' AS label,
    AVG(value) AS current_coverage
  FROM metrics_numeric_latest_version
  WHERE metric_name = 'coverage_ratio'
    AND timestamp >= CURRENT_DATE - INTERVAL '7 days'
  GROUP BY label
)
SELECT
  b.label,
  b.baseline_coverage,
  c.current_coverage,
  ABS(c.current_coverage - b.baseline_coverage) AS drift,
  CASE
    WHEN ABS(c.current_coverage - b.baseline_coverage) > 0.1 THEN 'SIGNIFICANT DRIFT'
    WHEN ABS(c.current_coverage - b.baseline_coverage) > 0.05 THEN 'MODERATE DRIFT'
    ELSE 'STABLE'
  END AS drift_status
FROM baseline b
JOIN current c ON b.label = c.label
WHERE ABS(c.current_coverage - b.baseline_coverage) > 0.05
ORDER BY drift DESC;
```

### Model Version Comparison

Compare metrics across different model versions:

```sql
SELECT
  dimensions ->> 'model_version' AS version,
  AVG(value) AS avg_accuracy,
  STDDEV(value) AS stddev_accuracy,
  MIN(value) AS min_accuracy,
  MAX(value) AS max_accuracy
FROM metrics_numeric_latest_version
WHERE metric_name = 'accuracy'
  AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
GROUP BY version
ORDER BY avg_accuracy DESC;
```

## Troubleshooting

### Query Returns No Results

- Check timestamp range includes data
- Verify metric_name spelling
- Ensure model_id filter is correct
- Check if dimensions filter is too restrictive

### Query is Slow

- Add timestamp filters
- Reduce time range
- Increase bucket size (day instead of 5-minute)
- Filter to specific dimensions
- Check for expensive DISTINCT operations
- Use EXPLAIN to analyze query plan

### Unexpected NULL Values

- Use COALESCE for default values
- Check if metric exists for all time buckets
- Use time_bucket_gapfill for missing timestamps
- Verify dimension values are populated

### Dimension Values Missing

- Verify dimensions are populated in metric
- Check JSON extraction syntax: `dimensions ->> 'key'`
- Ensure dimension name spelling is correct
- Check if dimension is NULL vs empty string

## Additional Resources

For creating custom metrics with advanced SQL patterns, see:

* **[How to Create a Custom Metric](how-to-create-a-custom-metric.md)** - Complete guide with 7 advanced patterns
* **[examples/binary-classification](../examples/binary-classification/)** - 7 production metrics
* **[examples/multi-classification](../examples/multi-classification/)** - 10 production metrics with array operations
* **[Arthur Custom Metrics Repository](../README.md)** - 17 metrics, 39 charts, comprehensive documentation
