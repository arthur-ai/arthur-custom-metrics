# Chart: Maximum Errors Over Time

## Metrics Used

From **Maximum Errors**:
- `max_error` — Maximum absolute error (worst prediction)
- `max_relative_error` — Maximum percentage error

## SQL Query

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
        WHEN metric_name = 'max_error' THEN 'Maximum Absolute Error'
        WHEN metric_name = 'max_relative_error' THEN 'Maximum Relative Error'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'max_error',
    'max_relative_error'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A dual-axis time series showing both absolute and relative worst-case errors over time. This reveals:
- Worst-case prediction performance
- Safety bounds for applications
- Outlier frequency and severity
- Model reliability trends

## How to interpret it

**Both metrics stable**:
- Consistent worst-case performance
- Predictable reliability bounds
- **Good**: No degradation in worst case

**Max error increasing**:
- Worst predictions getting worse
- Model reliability declining
- **Action**: Investigate outlier causes

**Max relative error increasing**:
- Worst percentage errors growing
- Scale-independent decline
- Check for small value predictions

**Both metrics spiking together**:
- Single very bad prediction
- Affects both absolute and relative
- Likely large actual value with large error

**Max error high, max relative low**:
- Worst error on large value prediction
- Percentage-wise not terrible
- Absolute impact may still be significant

**Max error low, max relative high**:
- Worst error on small value prediction
- Small absolute error but large percentage
- May be acceptable depending on use case

**Frequent spikes**:
- Regular outliers
- Model struggles with certain cases
- **Action**: Identify outlier patterns

**Decreasing trend**:
- Worst-case improving
- Better reliability
- **Good**: Model updates working

**Max error >> average error (MAE)**:
- Outliers dominate worst case
- Most predictions good, few very bad
- Focus outlier handling separately

**Max error ≈ average error**:
- Uniform error distribution
- No extreme outliers
- Either consistently good or bad

**Typical ratios**:
- **Max/MAE ratio 3-5×**: Normal distribution
- **Max/MAE ratio > 10×**: Significant outliers
- **Max/MAE ratio < 2×**: Very uniform errors

**Safety thresholds**:
- **Max error > safety_limit**: Critical alert
- **Max relative > 100%**: Prediction off by > 100%
- **Consecutive high max**: Persistent issue

**Use this chart to**:
- Monitor worst-case performance
- Set safety thresholds for alerts
- Identify when outlier frequency increases
- Compare absolute vs relative worst-case
- Ensure reliability for critical applications
