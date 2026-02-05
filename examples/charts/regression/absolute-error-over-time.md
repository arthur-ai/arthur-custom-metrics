# Chart: Absolute Error Over Time

## Metrics Used

* `absolute_error`

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
        WHEN metric_name = 'absolute_error' THEN 'Absolute Error'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'absolute_error'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A time series showing absolute error values for each inference over time. This reveals:
- Individual prediction errors
- Error magnitude patterns
- Outlier occurrences
- Error trends at inference level

## How to interpret it

**Scattered plot with stable range**:
- Consistent error magnitude
- Predictable performance
- **Good**: No degradation

**Increasing trend**:
- Errors getting larger
- Model accuracy declining
- **Action**: Investigate model drift

**High variance (wide scatter)**:
- Inconsistent prediction quality
- Some predictions much worse than others
- Consider error analysis by segment

**Low variance (tight cluster)**:
- Consistent prediction quality
- Uniform accuracy
- Either consistently good or bad

**Outliers (extreme spikes)**:
- Individual very bad predictions
- May warrant investigation
- Check for data quality issues

**Typical values**:
- Depends on scale of predictions
- Compare to mean actual value
- **< 5% of scale**: Excellent
- **5-15% of scale**: Good
- **> 15% of scale**: Poor
