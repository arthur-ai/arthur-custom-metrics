# Chart: Class Count by Label Over Time

## Metrics Used

From **Multi-Label Classification Count by Class Label**:
- `class_count` — Count of predictions containing each label (dimension: series)

## SQL Query

```sql
SELECT
  ts,
  series AS label,
  class_count
FROM
  multi_label_class_count
ORDER BY
  ts,
  label;
```

## What this shows

Multiple time series, one for each label, showing how many inferences contain each label over time. This reveals:
- Which labels are most/least frequently predicted
- Changes in label popularity over time
- Emerging or declining labels
- Label distribution patterns

## How to interpret it

**High count labels**:
- Frequently predicted across many inferences
- Core labels for your use case
- Monitor for over-prediction

**Low count labels**:
- Rare predictions
- May indicate edge cases or specialized scenarios
- Check if these are being under-predicted

**Increasing trend for a label**:
- Label becoming more common in predictions
- May reflect actual data changes or model drift
- Verify against ground truth trends

**Decreasing trend for a label**:
- Label becoming less common
- Could indicate model improvement or data shift
- Investigate if unexpected

**Parallel movements**:
- Labels moving together suggest correlation
- May indicate co-occurrence patterns
- Consider label relationships

**Visualization tip**: Use different colors for each label series. For large label sets (50+), consider showing only top N labels or filtering to labels of interest.
