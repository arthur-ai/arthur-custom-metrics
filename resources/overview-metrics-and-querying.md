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

### Example Queries

**1. Querying a numeric metric**

This query is an example of how to query a numeric metric, and aggregate it on a daily roll up:

```sql
select time_bucket(interval '1 day', timestamp) as bucket,
       sum(value)                               as total
from metrics_numeric_latest_version
where metric_name = 'inference_count'
    AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
group by bucket
```

**2. Hallucination Rate**

This query is an example of a more advanced calculation finalized at query time. In this query, we select two metrics,
one for the count of hallucinations per interval, and one for the count of inferences in that interval. We join them on timestamp then divide to get the rate, or percentage, of hallucinations per interval. It includes a divide by zero protection in the case there were no inferences in the interval.

```sql
with hallucination_count as (select time_bucket(interval '1 day', timestamp)             as bucket,
                                    sum(value)                                           as total
                             from metrics_numeric_latest_version
                             where metric_name = 'hallucination_count'
                                   AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
                             group by bucket
                             order by bucket DESC),
     total_count as (select time_bucket(interval '1 day', timestamp)                 as bucket,
                            sum(value)                                               as total
                     from metrics_numeric_latest_version
                     where metric_name = 'inference_count'
                           AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
                     group by bucket
                     order by bucket DESC)
select hallucination_count.bucket as timestamp,
    CASE WHEN total_count.total = 0 THEN 0 ELSE hallucination_count.total / total_count.total END as hallucination_rate
from hallucination_count
         join total_count on hallucination_count.bucket = total_count.bucket
order by hallucination_count.bucket DESC
```

**3. Basic Sketch Operations**

Sketch metric types allow for querying properties of a distribution from the stored values. For aggregating on intervals larger than 5 minutes, they can be merged to generate sketches that represent the combined properties of all data that were summarized by the individual sketches before merging. Some helpful functions include:

* `kll_float_sketch_merge(sketch)` - this function allows merging sketch values in a group into a single sketch
* `kll_float_sketch_get_quantile(sketch, quantile)` - this function returns the value of the requested quantile from the distribution summarized by the sketch. Getting the median is the same as the `0.5`th quantile. Getting the 95% percentile is the `0.95`th quantile.
* `kll_float_sketch_get_n(sketch)` - returns the number of values summarized by the sketch
* `kll_float_sketch_get_max_item(sketch)` - returns the max item seen by the sketch
* `kll_float_sketch_get_min_item(sketch)` - returns the min item seen by the sketch
* `kll_float_sketch_get_pmf(sketch, [points])` - returns the probability mass function value evaluated at each of the points. This can be multiplied by the result of the `kll_float_sketch_get_n` value to obtain counts for a distribution.

**4. Querying a sketch metric**

This query is an example of how to query a sketch based metric. This query returns the median latency grouped by
the `rule_type` dimension on the `rule_latency` metric per day.

```sql
select time_bucket(interval '1 day', timestamp)                         as bucket,
      kll_float_sketch_get_quantile(kll_float_sketch_merge(value), 0.5) as median_latency,
      dimensions ->> 'rule_type'                                        as rule_type
from metrics_sketch_latest_version
where metric_name = 'rule_latency'
  AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
group by bucket, rule_type;
```

**5. Creating a distribution**

This query creates a table of the values of a distribution for a variable that varies between 0 and 1. It creates a
bucket at 0.05 intervals for all data within the time range, so it is not grouped by time buckets. It uses the `get_pmf` sketch function to obtain the percentage of values in each interval, then multiplies it by the total count of values seen by the sketch to get the number in each interval.

```sql
with merged
         as (select kll_float_sketch_get_pmf(kll_float_sketch_merge(value),
                                             ARRAY [0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95]) as sketch,
                    kll_float_sketch_get_n(kll_float_sketch_merge(value))                                                                   as total
             from metrics_sketch_latest_version
             where metric_name = 'toxicity_score'
                 AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
             )
select ROUND(((ordinality) / 20.0), 2)::VARCHAR as num_claims,
       val * merged.total                       as inf_count
from merged,
     unnest(merged.sketch) with ordinality as val;
```

**6. Other helpful Timescale functions**

1. [time_bucket_gapfill](https://docs.timescale.com/api/latest/hyperfunctions/gapfilling/time_bucket_gapfill/#:~:text=Group%20data%20into%20buckets%20based,NULL%20in%20the%20returned%20data.\&text=A%20PostgreSQL%20time%20interval%20to%20specify%20the%20length%20of%20each%20bucket.) - this function can be used to fill in all time buckets in a range in case values are not present in all time intervals. A common place this is used is to visualize `inference_count` over time. If there weren't any inferences in a time bucket, there would be no count to show, so the graph would be empty. Using this function allows queries to fill in NULL values for missing time buckets, which can be converted to zero or other defaults. Here's an example query:
   ```sql
   select time_bucket_gapfill(interval '1 hour', timestamp)  as bucket,
     CASE WHEN sum(value) is NULL THEN 0 ELSE sum(value) END as total
   from metrics_numeric_latest_version
   where metric_name = 'inference_count'
     AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}'
   group by bucket;
   ```
