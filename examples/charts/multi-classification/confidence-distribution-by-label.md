# Chart: Confidence Distribution by Label

## Metrics Used

From **Average Confidence Score per Label**:
- `avg_confidence` — Average confidence per label (dimension: series)

## SQL Query

```sql
SELECT
  series AS label,
  AVG(avg_confidence) AS avg_confidence
FROM
  average_confidence_per_label
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label
ORDER BY
  avg_confidence DESC;
```

## What this shows

A bar chart ranking labels by their average confidence score over the last 30 days. This reveals:
- Which labels have highest/lowest confidence
- Confidence distribution across labels
- Uncertain labels requiring attention
- Overall model certainty patterns

## How to interpret it

**Top of chart (high confidence)**:
- Most confident labels
- Model has strong signal
- Typically high-frequency, well-learned labels
- Monitor for over-confidence

**Middle of chart (moderate confidence)**:
- Decent confidence
- Typical performance
- Most labels should be here

**Bottom of chart (low confidence)**:
- Least confident labels
- Model uncertain
- May need more training data
- Consider for human review workflow

**Large variance**:
- Some labels much more confident than others
- Expected for varied difficulty
- Focus improvement on low-confidence labels

**Uniform high confidence**:
- Model confident across all labels
- Good sign if accuracy is also high
- If accuracy is low → calibration problem

**Uniform low confidence**:
- Model uncertain about everything
- May indicate model issues
- Check training and features

**Unexpected low confidence**:
- Important labels with low confidence
- High priority for improvement
- May need more training examples

**Unexpected high confidence**:
- Difficult labels with high confidence
- Verify accuracy matches confidence
- May indicate over-confidence

**Use this chart to**:
- Identify uncertain labels
- Prioritize data collection
- Set up human review thresholds
- Validate model calibration
- Guide model improvement efforts
