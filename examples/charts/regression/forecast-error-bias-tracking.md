# Chart: Forecast Error Bias Tracking

## Metrics Used

From **Error Distribution**:
- `forecast_error` — Signed prediction error per inference (Numeric)

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
        WHEN metric_name = 'forecast_error' THEN 'Forecast Error'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'forecast_error'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A time series showing the mean and median signed forecast error over time with standard deviation bands. This reveals:
- Systematic over/under-prediction bias
- Bias stability or drift
- Symmetry of error distribution
- Whether errors cancel out

## How to interpret it

**Mean ≈ 0, Median ≈ 0**:
- Unbiased predictions
- Errors balance out
- **Excellent**: Well-calibrated model

**Mean > 0 (positive)**:
- Systematic over-prediction
- Model predicts too high on average
- **Action**: Recalibrate predictions downward

**Mean < 0 (negative)**:
- Systematic under-prediction
- Model predicts too low on average
- **Action**: Recalibrate predictions upward

**Mean ≈ Median**:
- Symmetric error distribution
- Normal-like error pattern
- No extreme skew

**Mean >> Median**:
- Right-skewed errors
- Extreme over-predictions pulling mean up
- Median represents typical case better

**Mean << Median**:
- Left-skewed errors
- Extreme under-predictions pulling mean down
- Outlier analysis needed

**Increasing trend (bias growing)**:
- Model drifting
- Systematic issue developing
- **Critical**: Retrain or recalibrate

**Oscillating around zero**:
- Bias changing but canceling out
- May indicate seasonal patterns
- Overall balanced but investigate pattern

**Large std_dev**:
- High variability in errors
- Wide error distribution
- Predictions inconsistent

**Typical bias values**:
- **|Mean| < 2% of scale**: Excellent calibration
- **|Mean| 2-5% of scale**: Good calibration
- **|Mean| 5-10% of scale**: Noticeable bias
- **|Mean| > 10% of scale**: Significant bias, action needed

**Use this chart to**:
- Detect systematic prediction bias
- Identify model drift over time
- Determine if recalibration is needed
- Monitor bias after model updates
- Set calibration adjustment factors
