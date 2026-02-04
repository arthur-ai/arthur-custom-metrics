# Chart: Coverage Ratio by Label Over Time

## Metrics Used

From **Label Coverage Ratio**:
- `coverage_ratio` — Proportion of inferences containing each label (dimension: series)

## SQL Query

```sql
SELECT
  ts,
  series AS label,
  coverage_ratio
FROM
  label_coverage_ratio
ORDER BY
  ts,
  label;
```

## What this shows

Multiple time series showing what percentage of inferences contain each label over time (0-1 scale). This reveals:
- Which labels are most/least prevalent
- Changes in label usage patterns
- Emerging or declining labels
- Label distribution relative to inference population

## How to interpret it

**High coverage (0.7-1.0)**:
- Label appears in most inferences
- Very common or default label
- May indicate dominant class

**Medium coverage (0.3-0.7)**:
- Label appears in moderate portion of inferences
- Balanced usage
- Typical for well-distributed scenarios

**Low coverage (0.0-0.3)**:
- Label appears rarely
- Rare class or edge case
- Monitor for under-prediction

**Increasing coverage**:
- Label becoming more prevalent in predictions
- May indicate data drift or model behavior change

**Decreasing coverage**:
- Label becoming less common
- Could indicate model improvement or data shift

**Parallel movements**:
- Labels with similar trends may be correlated
- Consider co-occurrence analysis

**Visualization tip**: Use line chart with different colors per label. For large label sets, consider showing only top N labels by average coverage or allow filtering.
