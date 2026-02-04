# Chart: Average Confidence by Label Over Time

## Metrics Used

From **Average Confidence Score per Label**:
- `avg_confidence` — Average confidence per label including 0 for non-predicted (dimension: series)

## SQL Query

```sql
SELECT
  ts,
  series AS label,
  avg_confidence
FROM
  average_confidence_per_label
ORDER BY
  ts,
  label;
```

## What this shows

Multiple time series showing average confidence score for each label over time (0-1 scale). This reveals:
- Which labels have high/low model confidence
- Confidence trends per label
- Changes in model certainty
- Potential calibration issues

## How to interpret it

**High confidence (0.8-1.0)**:
- Model very certain about this label
- Strong predictions
- Well-learned label

**Medium confidence (0.5-0.8)**:
- Moderate certainty
- Decent predictions
- Some uncertainty

**Low confidence (0.2-0.5)**:
- Model uncertain
- Unreliable predictions
- Consider human review

**Very low confidence (0.0-0.2)**:
- Rarely predicted or many 0s
- Very uncertain when predicted
- Difficult or rare label

**Increasing confidence**:
- Model becoming more certain
- May indicate improved learning
- Could also mean over-confidence

**Decreasing confidence**:
- Model becoming less certain
- May indicate degradation or drift
- Requires investigation

**Stable confidence**:
- Consistent behavior
- Expected in production
- Monitor for changes

**Wide variance across labels**:
- Some labels easy, others hard
- Natural for varied datasets
- Focus on low-confidence labels

**Visualization tip**: Use line chart with different colors per label. Consider showing only top N labels or filtering by label of interest. Add reference lines at 0.5, 0.7, 0.9.
