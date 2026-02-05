# Chart: Cumulative Error Over Time

## Metrics Used

From **Cumulative Error**:
- `cumulative_error` — Running sum of signed errors

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
        WHEN metric_name = 'cumulative_error' THEN 'Cumulative Error'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'cumulative_error'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A time series showing the running sum of forecast errors (bias accumulation). This reveals:
- Systematic over/under-prediction patterns
- Long-term bias trends
- Whether errors cancel out or compound
- Model calibration health

## How to interpret it

**Line trending upward (positive)**:
- Cumulative over-prediction
- Model consistently predicts too high
- **Action**: Recalibrate downward

**Line trending downward (negative)**:
- Cumulative under-prediction
- Model consistently predicts too low
- **Action**: Recalibrate upward

**Oscillating around zero**:
- Errors canceling out over time
- No systematic bias
- **Excellent**: Well-calibrated

**Stable near zero**:
- Minimal net error accumulation
- Balanced predictions
- **Excellent**: Unbiased model

**Accelerating growth (steeper slope)**:
- Bias worsening over time
- Model drift accelerating
- **Critical**: Immediate action needed

**Sudden direction change**:
- Shift in model behavior
- Data distribution change
- Model update or deployment

**Magnitude interpretation**:
- **Small cumulative vs total volume**: Well-calibrated
- **Large cumulative vs total volume**: Significant systematic bias

**Use this chart to**:
- Detect systematic prediction bias
- Track long-term calibration
- Identify when recalibration needed
- Monitor bias after model updates
- Plan inventory/capacity based on bias
