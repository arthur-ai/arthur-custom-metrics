# Chart: Confusion Matrix Components per Label

## Metrics Used

From **Multi-Label Classification Confusion Matrix – Per Class**:
- `tp` — True positives per label (dimension: series)
- `fp` — False positives per label (dimension: series)
- `fn` — False negatives per label (dimension: series)

## SQL Query

```sql
SELECT
  ts,
  series AS label,
  tp,
  fp,
  fn
FROM
  multi_label_confusion_matrix
ORDER BY
  ts,
  label;
```

## What this shows

Three time series for each label showing TP, FP, and FN counts over time. This reveals:
- Raw confusion matrix components for each label
- Which labels have high false positive rates
- Which labels have high false negative rates
- Error patterns and trends per label

## How to interpret it

**High TP (True Positives)**:
- Label is correctly predicted frequently
- Good performance indicator
- Scale correlates with label frequency

**High FP (False Positives)**:
- Model over-predicts this label
- Precision issue
- May need threshold adjustment

**High FN (False Negatives)**:
- Model misses this label frequently
- Recall issue
- May need more training data or features

**TP >> FP and FN**:
- Excellent performance for this label
- Model is both precise and recalls well

**FP ≈ TP or FN ≈ TP**:
- Poor performance
- As many errors as correct predictions
- Requires investigation

**Trends over time**:
- Increasing FP/FN → Performance degrading
- Decreasing FP/FN → Performance improving
- Stable → Consistent behavior

**Visualization tip**: Use stacked area chart or separate lines with different colors (TP=green, FP=red, FN=orange) for easy comparison.
