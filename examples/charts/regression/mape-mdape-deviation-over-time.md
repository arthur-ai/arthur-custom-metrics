# Chart: MAPE, MdAPE, and Deviation Ratio Over Time

## Metrics Used

From **Percentage Error Metrics**:
- `mape` — Mean absolute percentage error
- `mdape` — Median absolute percentage error
- `deviation_ratio` — Average signed relative deviation

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
        WHEN metric_name = 'mape' THEN 'Mean Absolute Percentage Error'
        WHEN metric_name = 'mdape' THEN 'Median Absolute Percentage Error'
        WHEN metric_name = 'deviation_ratio' THEN 'Deviation Ratio'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'mape',
    'mdape',
    'deviation_ratio'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A multi-line time series showing three scale-independent accuracy metrics over time. This reveals:
- Average percentage error (MAPE)
- Typical percentage error robust to outliers (MdAPE)
- Bias direction and magnitude (Deviation Ratio)
- Accuracy trends and calibration

## How to interpret it

**MAPE and MdAPE tracking together**:
- Consistent error distribution
- No major outliers
- Both metrics equally valid

**MAPE > MdAPE (gap widening)**:
- Outliers inflating MAPE
- Median represents typical case better
- Use MdAPE for reporting

**MAPE ≈ MdAPE ≈ |Deviation Ratio|**:
- Errors all in one direction
- Systematic bias dominates
- Calibration needed

**Deviation Ratio near 0**:
- Unbiased predictions
- Errors balance out
- **Excellent**: Well-calibrated

**Deviation Ratio > 0 (positive)**:
- Systematic over-prediction
- Model predicts too high
- Magnitude shows severity

**Deviation Ratio < 0 (negative)**:
- Systematic under-prediction
- Model predicts too low
- Magnitude shows severity

**All three decreasing**:
- Accuracy improving
- Both typical and average errors declining
- Bias also reducing

**MAPE/MdAPE stable, Deviation Ratio changing**:
- Error magnitude constant
- Bias direction shifting
- Monitor for systematic drift

**All three increasing**:
- Accuracy degrading
- Model performance declining
- **Action**: Investigate and retrain

**MAPE increasing, MdAPE stable**:
- More outliers appearing
- Typical performance OK
- Focus on outlier handling

**Typical target values**:
- **MAPE/MdAPE < 10%**: Excellent
- **MAPE/MdAPE 10-20%**: Good
- **MAPE/MdAPE > 20%**: Poor
- **|Deviation Ratio| < 5%**: Well-calibrated
- **|Deviation Ratio| > 10%**: Significant bias

**Use this chart to**:
- Monitor scale-independent accuracy
- Detect and quantify bias
- Understand outlier impact (MAPE vs MdAPE)
- Determine if recalibration needed
- Track accuracy trends over time
