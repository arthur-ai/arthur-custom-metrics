# Chart: Exact Match Ratio Over Time

## Metrics Used

From **Exact Match Ratio**:
- `exact_match_ratio` — Proportion of inferences with exact label set match

## SQL Query

```sql
SELECT
  ts,
  exact_match_ratio
FROM
  exact_match_ratio
ORDER BY
  ts;
```

## What this shows

A time series showing the percentage of predictions that exactly match ground truth label sets each day. This reveals:
- Overall model accuracy at the strictest level
- Trends in perfect prediction rate
- Impact of model changes on exact accuracy
- Quality consistency over time

## How to interpret it

**High ratio (>0.8)**:
- Excellent performance
- Most predictions are perfect
- Well-calibrated model

**Medium ratio (0.5-0.8)**:
- Good performance
- Many predictions perfect, some with minor errors
- Typical for moderate difficulty tasks

**Low ratio (0.2-0.5)**:
- Fair performance
- Many predictions have at least one error
- Room for improvement

**Very low ratio (<0.2)**:
- Poor performance
- Few perfect predictions
- Requires investigation

**Increasing trend**:
- Model improving
- More perfect predictions over time
- Positive signal

**Decreasing trend**:
- Model degrading
- Fewer perfect predictions
- Requires immediate attention

**Sudden drops**:
- Data quality issues
- Model deployment problems
- Data distribution shifts

**High variance**:
- Inconsistent performance
- May indicate batch effects
- Check for data issues

**Use this chart to**:
- Track overall model quality
- Set SLA thresholds
- Monitor for degradation
- Report to executives (% perfect predictions)
- Trigger alerts on drops
