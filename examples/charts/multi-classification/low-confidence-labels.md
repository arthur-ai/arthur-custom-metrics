# Chart: Low Confidence Labels

## Metrics Used

From **Average Confidence Score per Label**:
- `avg_confidence` — Average confidence per label (dimension: series)

## SQL Query

```sql
SELECT
  series AS label,
  AVG(avg_confidence) AS avg_confidence,
  COUNT(*) AS days_measured
FROM
  average_confidence_per_label
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label
HAVING
  AVG(avg_confidence) < 0.5
ORDER BY
  avg_confidence ASC
LIMIT 20;
```

## What this shows

A focused view on the 20 labels with lowest average confidence (below 0.5 threshold). This reveals:
- Which labels the model is most uncertain about
- Priority labels for improvement
- Candidates for human review
- Potential data collection targets

## How to interpret it

**Very low confidence (<0.2)**:
- Rarely predicted or very uncertain
- May be rare/difficult labels
- **Action**: Collect more training data or consider removing

**Low confidence (0.2-0.3)**:
- Significant uncertainty
- Unreliable predictions
- **Action**: Improve training or add features

**Moderate-low confidence (0.3-0.5)**:
- Noticeable uncertainty
- May benefit from tuning
- **Action**: Consider threshold adjustment

**Many labels below threshold**:
- Widespread uncertainty issues
- May indicate model architecture problems
- Consider systematic improvements

**Few labels below threshold**:
- Most labels confident, few outliers
- Normal for some rare/difficult labels
- Focus on these specific labels

**Expected low-confidence labels**:
- Rare events or edge cases
- Acceptable if accuracy is reasonable
- Set up human review workflow

**Unexpected low-confidence labels**:
- Important labels that should be confident
- High priority for investigation
- Check training data quality/quantity

**Actions by confidence level**:

- **< 0.2**: Route to human review, collect more data
- **0.2-0.3**: Additional model training, feature engineering
- **0.3-0.4**: Threshold tuning, validation
- **0.4-0.5**: Monitor and optimize

**Use this chart to**:
- Focus improvement efforts
- Set up human review workflows
- Prioritize data collection
- Guide threshold setting
- Identify problematic labels
- Plan training data augmentation
