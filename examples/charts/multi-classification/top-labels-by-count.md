# Chart: Top Labels by Count

## Metrics Used

From **Multi-Label Classification Count by Class Label**:
- `class_count` — Count of predictions containing each label (dimension: series)

## SQL Query

```sql
SELECT
  series AS label,
  SUM(class_count) AS total_count
FROM
  multi_label_class_count
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label
ORDER BY
  total_count DESC
LIMIT 20;
```

## What this shows

A bar chart showing the top 20 most frequently predicted labels over the last 30 days. This reveals:
- Which labels dominate predictions
- Label distribution skew
- Most important labels to monitor
- Potential class imbalance issues

## How to interpret it

**Heavily skewed distribution**:
- Few labels account for most predictions
- High imbalance in label usage
- May need to focus on rare labels

**Relatively balanced top labels**:
- Similar counts across top labels
- More even distribution
- Healthy label diversity

**Very long tail**:
- Many labels with low counts not shown
- Consider if all labels are necessary
- May have catalog bloat

**Unexpected top labels**:
- Labels that shouldn't be common appear at top
- Investigate for over-prediction issues
- Verify against business expectations

**Missing expected labels**:
- Important labels not in top 20
- May indicate under-prediction
- Check model performance on these labels

**Use this chart to**:
- Identify which labels need most attention
- Understand label importance distribution
- Guide monitoring and alerting priorities
- Make decisions about label catalog management
