# Chart: TP/FP/FN Comparison Across Labels

## Metrics Used

From **Multi-Label Classification Confusion Matrix – Per Class**:
- `tp` — True positives per label (dimension: series)
- `fp` — False positives per label (dimension: series)
- `fn` — False negatives per label (dimension: series)

## SQL Query

```sql
SELECT
  series AS label,
  SUM(tp) AS total_tp,
  SUM(fp) AS total_fp,
  SUM(fn) AS total_fn
FROM
  multi_label_confusion_matrix
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label
ORDER BY
  total_tp DESC;
```

## What this shows

A grouped bar chart comparing TP, FP, and FN totals for each label over the last 30 days. This reveals:
- Which labels perform best/worst
- Relative error rates across labels
- Labels with precision vs recall issues
- Overall label quality at a glance

## How to interpret it

**Labels with high TP, low FP/FN**:
- Best performing labels
- Good precision and recall
- Use as baseline for other labels

**Labels with high FP**:
- Over-prediction problem
- Low precision
- Consider raising confidence threshold

**Labels with high FN**:
- Under-prediction problem
- Low recall
- May need more training examples

**Labels with balanced TP/FP/FN**:
- Poor performance overall
- ~33% accuracy
- Requires significant improvement

**Labels with very low counts**:
- Rare labels
- Hard to evaluate performance
- May need more data collection

**Comparison patterns**:
- Similar FP/FN ratios across labels → systematic issue
- Varying ratios → label-specific problems
- Focus efforts on highest error labels

**Use this chart to**:
- Prioritize which labels need improvement
- Understand error type distribution
- Make threshold tuning decisions
- Report on label-level quality
