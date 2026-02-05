# Chart: Normalized MAD Over Time

## Metrics Used

From **Normalized Mean Absolute Deviation**:
- `normalized_mad` — MAE divided by mean of absolute actuals

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
        WHEN metric_name = 'normalized_mad' THEN 'Normalized MAD'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'normalized_mad'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A time series showing scale-independent error magnitude (error relative to typical values). This reveals:
- Relative accuracy across different scales
- Error as proportion of typical values
- Scale-normalized performance
- Comparable accuracy metric

## How to interpret it

**Normalized MAD stable**:
- Consistent relative accuracy
- Predictable performance
- Scale-independent view

**Normalized MAD increasing**:
- Relative accuracy degrading
- Errors growing relative to scale
- **Action**: Investigate performance decline

**Normalized MAD decreasing**:
- Relative accuracy improving
- Better scale-independent performance
- **Good**: Model improvements effective

**Normalized MAD < 0.05 (5%)**:
- Errors < 5% of typical values
- **Excellent**: High relative accuracy

**Normalized MAD 0.05-0.15 (5-15%)**:
- Errors 5-15% of typical values
- **Good**: Acceptable relative accuracy

**Normalized MAD 0.15-0.30 (15-30%)**:
- Errors 15-30% of typical values
- **Fair**: Moderate relative accuracy

**Normalized MAD > 0.30 (>30%)**:
- Errors > 30% of typical values
- **Poor**: Low relative accuracy

**Normalized MAD vs MAPE**:
- Similar scale-independent views
- Normalized MAD: aggregate ratio
- MAPE: average of individual ratios
- Compare to understand outlier impact

**Use this chart to**:
- Monitor scale-independent accuracy
- Compare performance across datasets
- Track relative error trends
- Set scale-normalized targets
- Understand error magnitude relative to scale
