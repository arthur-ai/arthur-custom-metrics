# Chart: RMSE Over Time

## Metrics Used

From **Root Mean Squared Error**:
- `rmse` — Root mean squared error

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
        WHEN metric_name = 'rmse' THEN 'Root Mean Squared Error'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'rmse'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A time series showing RMSE (emphasizes larger errors) over time. This reveals:
- Overall prediction accuracy with outlier emphasis
- Error magnitude trends
- Model performance stability
- Impact of large errors

## How to interpret it

**RMSE increasing**:
- Errors getting worse
- Especially larger errors growing
- **Action**: Investigate error sources

**RMSE decreasing**:
- Accuracy improving
- Large errors reducing
- **Good**: Model updates effective

**RMSE stable**:
- Consistent performance
- Predictable error magnitude
- Monitor for changes

**RMSE >> MAE**:
- Large errors dominate
- Outliers significantly affecting metric
- Focus on outlier reduction

**RMSE ≈ MAE**:
- Uniform error distribution
- No extreme outliers
- Consistent prediction quality

**High volatility**:
- Inconsistent performance
- Error magnitude varies widely
- Investigate causes

**Typical RMSE/MAE ratio**:
- **1.0-1.2**: Very uniform errors
- **1.2-1.5**: Normal distribution
- **> 1.5**: Significant outliers present

**Use this chart to**:
- Monitor accuracy with outlier emphasis
- Track large error impact
- Compare with MAE to assess outlier severity
- Set performance benchmarks
