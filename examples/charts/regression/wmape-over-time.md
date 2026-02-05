# Chart: WMAPE Over Time

## Metrics Used

From **Weighted Mean Absolute Percentage Error**:
- `wmape` — Volume-weighted percentage error

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
        WHEN metric_name = 'wmape' THEN 'Weighted Mean Absolute Percentage Error'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'wmape'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A time series showing volume-weighted percentage error over time. This reveals:
- Accuracy weighted by magnitude/volume
- Performance on high-value predictions
- Business-relevant error trends
- Scale-independent accuracy that emphasizes important predictions

## How to interpret it

**WMAPE < MAPE**:
- Better on high-volume items
- Small items have higher % errors
- Volume-weighted view favorable

**WMAPE > MAPE**:
- Worse on high-volume items
- High-value predictions less accurate
- **Concerning**: Poor where it matters most

**WMAPE ≈ MAPE**:
- Consistent accuracy across volumes
- Uniform performance

**WMAPE increasing**:
- Accuracy declining on important items
- Business impact worsening
- **Action**: Focus on high-volume predictions

**WMAPE decreasing**:
- Improving on important items
- Better business outcomes
- **Good**: Effective improvements

**Typical target values**:
- **< 10%**: Excellent
- **10-20%**: Good
- **20-40%**: Fair
- **> 40%**: Poor

**Use this chart to**:
- Monitor business-relevant accuracy
- Track performance on high-value predictions
- Compare with MAPE to understand volume impact
- Set volume-weighted targets
