# Chart: Percentage Error Distribution

## Metrics Used

From **Error Distribution**:
- `absolute_percentage_error` — Percentage error per inference (Numeric)

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
        WHEN metric_name = 'absolute_percentage_error' THEN 'Absolute Percentage Error'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'absolute_percentage_error'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A multi-line time series showing the distribution of percentage errors over time. This reveals:
- Typical percentage error (P50)
- Error spread (P25 to P75 range)
- Outlier behavior (P90)
- Scale-independent accuracy trends

## How to interpret it

**P50 (median) trends**:
- **< 5%**: Excellent typical accuracy
- **5-10%**: Good typical accuracy
- **10-20%**: Fair typical accuracy
- **> 20%**: Poor typical accuracy

**Mean > Median**:
- Outliers inflating average
- Use median for reporting
- Investigate high percentage errors

**Mean ≈ Median**:
- Symmetric distribution
- No major outliers
- Both metrics equally valid

**Wide P25-P75 range**:
- High variability in percentage errors
- Some predictions much better than others
- Consider segmentation by actual value

**Narrow P25-P75 range**:
- Consistent percentage accuracy
- Uniform performance across scales
- Well-calibrated model

**P90 >> P75**:
- Long tail of high percentage errors
- Few very bad predictions
- Set outlier thresholds at P90

**All percentiles increasing**:
- Accuracy degrading across board
- Model drift or data shift
- **Action**: Retrain model

**All percentiles decreasing**:
- Accuracy improving
- Model updates working
- **Good**: Monitor to maintain

**P90 spiking**:
- More extreme outliers
- Worst-case performance declining
- Investigate specific predictions

**Use this chart to**:
- Monitor scale-independent accuracy
- Compare performance across different value ranges
- Set percentage-based thresholds
- Detect accuracy degradation early
- Understand error distribution shape
