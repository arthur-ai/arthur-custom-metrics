# Chart: TTM Error Smoothed Trend

## Metrics Used

From **Trailing Twelve Months Error**:
- `ttm_error` — Rolling 12-month mean absolute error

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
        WHEN metric_name = 'ttm_error' THEN 'TTM Error'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'ttm_error'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A smoothed time series showing 12-month rolling average error. This reveals:
- Long-term accuracy trends
- Seasonality-adjusted performance
- Strategic model health
- Year-over-year comparisons

## How to interpret it

**Decreasing TTM error**:
- Long-term accuracy improving
- Sustained performance gains
- **Good**: Model improvements working

**Increasing TTM error**:
- Long-term accuracy degrading
- Persistent performance decline
- **Action**: Strategic intervention needed

**Stable TTM error**:
- Consistent long-term performance
- Predictable accuracy
- Monitor for changes

**Smooth line (low volatility)**:
- Seasonality removed
- True performance trend visible
- Ideal for executive reporting

**TTM error vs monthly/daily trends**:
- Daily: Volatile, short-term changes
- TTM: Smooth, strategic trend
- Use both for complete picture

**Year-over-year comparison**:
- Compare same month different years
- Account for seasonal patterns
- Fair performance comparison

**Step changes in TTM**:
- Major model update impact
- Data source change
- Takes 12 months to fully reflect

**Typical uses**:
- Executive dashboards
- Strategic planning
- Model comparison across years
- Budget allocation decisions

**Target values**:
- Set based on business requirements
- Track improvement over time
- Year-over-year improvement expected

**Use this chart to**:
- Report long-term model health
- Remove seasonal noise
- Track strategic improvements
- Make year-over-year comparisons
- Set executive-level KPIs
