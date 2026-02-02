# Chart: Label Error Rates

## Metrics Used

From **Multi-Label Classification Confusion Matrix – Per Class**:
- `tp` — True positives per label (dimension: series)
- `fp` — False positives per label (dimension: series)
- `fn` — False negatives per label (dimension: series)

## SQL Query

```sql
SELECT
  series AS label,
  SUM(fp) / NULLIF(SUM(tp + fp), 0) AS false_positive_rate,
  SUM(fn) / NULLIF(SUM(tp + fn), 0) AS false_negative_rate,
  (SUM(fp) + SUM(fn)) / NULLIF(SUM(tp + fp + fn), 0) AS total_error_rate
FROM
  multi_label_confusion_matrix
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label
ORDER BY
  total_error_rate DESC;
```

## What this shows

Error rates for each label showing:
- **False Positive Rate**: FP / (TP + FP) — proportion of predictions that are wrong
- **False Negative Rate**: FN / (TP + FN) — proportion of actual labels that are missed
- **Total Error Rate**: (FP + FN) / (TP + FP + FN) — overall error proportion

This reveals which labels have the highest error rates and what type of errors dominate.

## How to interpret it

**High FP rate, low FN rate**:
- Over-prediction issue
- Model is too aggressive for this label
- Precision problem
- **Action**: Raise confidence threshold

**Low FP rate, high FN rate**:
- Under-prediction issue
- Model is too conservative
- Recall problem
- **Action**: Lower threshold or add training data

**Both rates high**:
- Fundamental performance issue
- Model struggles with this label
- **Action**: Investigate features, training data, label definition

**Both rates low**:
- Excellent performance
- Model handles this label well
- Use as benchmark

**Total error rate interpretation**:
- < 0.10 (10%): Excellent
- 0.10-0.20: Good
- 0.20-0.30: Fair
- \> 0.30: Needs improvement

**Visualization tip**: Use a scatter plot with FP rate on X-axis, FN rate on Y-axis, with label names as points. Size points by total error rate. This shows both error types and total quality at once.
