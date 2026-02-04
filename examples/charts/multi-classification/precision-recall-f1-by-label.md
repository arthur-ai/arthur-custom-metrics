# Chart: Precision, Recall, and F1 by Label Over Time

## Metrics Used

From **Multi-Label Precision, Recall, and F1 Score per Label**:
- `precision` — Precision per label (dimension: series)
- `recall` — Recall per label (dimension: series)
- `f1_score` — F1 score per label (dimension: series)

## SQL Query

```sql
SELECT
  ts,
  series AS label,
  precision,
  recall,
  f1_score
FROM
  multi_label_precision_recall_f1
ORDER BY
  ts,
  label;
```

## What this shows

Three time series for each label showing precision, recall, and F1 score over time. This reveals:
- Per-label quality metrics
- Precision vs recall tradeoffs
- Balanced performance (F1)
- Performance trends over time

## How to interpret it

**High precision (>0.9), high recall (>0.9)**:
- Excellent performance
- Label is well-learned
- Maintain and monitor

**High precision, low recall**:
- Conservative predictions
- Few false positives, many false negatives
- Consider lowering threshold

**Low precision, high recall**:
- Aggressive predictions
- Many false positives, few false negatives
- Consider raising threshold

**Low precision, low recall**:
- Poor performance overall
- Fundamental issues with this label
- Needs investigation and improvement

**F1 close to both precision and recall**:
- Balanced performance
- Both metrics are similar

**F1 much lower than precision or recall**:
- Imbalanced performance
- One metric is dragging down overall quality

**Trends**:
- Improving trends → Model learning
- Degrading trends → Model or data issues
- Stable → Consistent performance

**Visualization tip**: Use three different colored lines for each metric. Consider separate panels/subplots for each label if visualizing many labels.
