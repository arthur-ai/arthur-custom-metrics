# Chart: F1 Score Comparison Across Labels

## Metrics Used

From **Multi-Label Precision, Recall, and F1 Score per Label**:
- `f1_score` — F1 score per label (dimension: series)

## SQL Query

```sql
SELECT
  series AS label,
  AVG(f1_score) AS avg_f1_score
FROM
  multi_label_precision_recall_f1
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label
ORDER BY
  avg_f1_score DESC;
```

## What this shows

A bar chart ranking labels by their average F1 score over the last 30 days. This reveals:
- Which labels perform best/worst
- Overall quality distribution across labels
- Labels requiring improvement
- Relative performance at a glance

## How to interpret it

**F1 > 0.9 (Excellent)**:
- Best performing labels
- High quality predictions
- Use as benchmark

**F1 0.7-0.9 (Good)**:
- Solid performance
- Acceptable for most production use cases
- Minor room for improvement

**F1 0.5-0.7 (Fair)**:
- Moderate performance
- Noticeable errors
- Should be improved if important

**F1 < 0.5 (Poor)**:
- Significant performance issues
- High priority for improvement
- Consider if label is well-defined

**Large variance across labels**:
- Some labels easy, others difficult
- Natural for imbalanced datasets
- Focus on improving lowest performers

**Uniform high F1**:
- Model performs well across all labels
- Well-trained and balanced

**Uniform low F1**:
- Systematic model issues
- May need architecture changes or more data

**Use this chart to**:
- Prioritize improvement efforts
- Report on overall model quality
- Set SLA thresholds per label
- Identify problematic labels
- Make training data collection decisions
