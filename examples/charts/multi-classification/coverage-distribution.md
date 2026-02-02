# Chart: Coverage Distribution

## Metrics Used

From **Label Coverage Ratio**:
- `coverage_ratio` — Proportion of inferences containing each label (dimension: series)

## SQL Query

```sql
SELECT
  series AS label,
  AVG(coverage_ratio) AS avg_coverage
FROM
  label_coverage_ratio
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label
ORDER BY
  avg_coverage DESC;
```

## What this shows

A bar chart ranking labels by their average coverage ratio over the last 30 days. This reveals:
- Which labels are most/least prevalent
- Label usage distribution
- Class imbalance patterns
- Rare vs common labels

## How to interpret it

**Steep decline in the chart**:
- Few labels account for most coverage
- High imbalance
- Long tail of rare labels

**Gradual decline**:
- More balanced label distribution
- Labels spread relatively evenly
- Healthier distribution

**Very low coverage for many labels**:
- Many rare labels (< 5% coverage)
- May indicate label catalog bloat
- Consider consolidating or removing unused labels

**Unexpected high coverage**:
- Labels that shouldn't be common appear at top
- May indicate over-prediction
- Verify against business expectations

**Unexpected low coverage**:
- Important labels have low coverage
- May indicate under-prediction
- Check model performance

**Use this chart to**:
- Identify which labels need attention
- Understand label importance
- Guide threshold tuning decisions
- Make label catalog management decisions
- Set monitoring priorities
