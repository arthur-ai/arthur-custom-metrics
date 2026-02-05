# Chart: End of Term Error by Period

## Metrics Used

From **End of Term Absolute Error**:
- `end_of_term_error` — Absolute error at term boundaries

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
        WHEN metric_name = 'end_of_term_error' THEN 'End of Term Error'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'end_of_term_error'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

A time series showing prediction accuracy at critical business milestones (month/quarter/year end). This reveals:
- Accuracy at key reporting periods
- Term-end forecasting reliability
- Business planning accuracy
- Milestone-specific performance

## How to interpret it

**Low end-of-term errors**:
- Accurate at critical milestones
- Reliable for planning
- **Good**: Trustworthy for reporting

**High end-of-term errors**:
- Poor accuracy at milestones
- Planning targets frequently missed
- **Action**: Improve term-end forecasting

**Increasing over time**:
- Term-end accuracy degrading
- Model struggling with milestones
- **Action**: Investigate and retrain

**Spikes at certain periods**:
- Some terms harder to predict
- Seasonal or cyclical challenges
- Plan for difficult periods

**End-of-term error >> average daily error**:
- Worse at term boundaries
- May need specialized term-end models
- Common: harder to predict aggregates

**End-of-term error ≈ average daily error**:
- Consistent accuracy
- No special difficulty at milestones
- **Good**: Reliable forecasting

**Quarterly patterns**:
- Q4 often hardest (year-end)
- Seasonal business patterns
- Account for in planning

**Typical targets by domain**:
- **Financial (quarterly)**: < 5% error
- **Retail (monthly)**: < 10% error
- **Manufacturing (annual)**: < 8% error

**Use this chart to**:
- Monitor milestone prediction accuracy
- Set term-end accuracy targets
- Plan for difficult reporting periods
- Validate model performance for planning
- Track improvement in term-end forecasting
