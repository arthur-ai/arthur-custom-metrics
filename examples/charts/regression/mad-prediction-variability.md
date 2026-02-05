# Chart: MAD - Prediction Variability

## Metrics Used

From **Mean Absolute Deviation**:
- `mad` — Mean absolute deviation of predictions from their mean

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
        WHEN metric_name = 'mad' THEN 'Mean Absolute Deviation'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'mad'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A time series showing how much predictions vary from their mean. This reveals:
- Prediction consistency/stability
- Model output variability
- Whether predictions are clustered or spread
- Changes in prediction behavior

## How to interpret it

**Low MAD**:
- Predictions clustered near mean
- Consistent model outputs
- Low variability
- May indicate good stability or lack of responsiveness

**High MAD**:
- Predictions widely spread
- Variable model outputs
- High dispersion
- Could indicate diverse inputs or instability

**MAD ≈ 0**:
- All predictions nearly identical
- **Warning**: Model may not be adapting to inputs
- Check if model is "stuck"

**MAD increasing**:
- Predictions becoming more variable
- Model behavior changing
- May indicate data drift or instability

**MAD decreasing**:
- Predictions converging
- Less variability in outputs
- Verify model still responsive

**MAD vs StdDev**:
- MAD ≈ 0.8 × StdDev for normal distribution
- MAD more robust to outliers
- Ratio indicates distribution shape

**Typical use**:
- Monitor model stability
- Detect behavior changes
- Validate deployment impact
- Ensure prediction diversity

**Use this chart to**:
- Track prediction consistency
- Detect model behavior changes
- Validate model deployment
- Ensure appropriate output variability
- Monitor for model "freezing"
