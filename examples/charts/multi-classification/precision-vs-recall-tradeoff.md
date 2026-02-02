# Chart: Precision vs Recall Tradeoff

## Metrics Used

From **Multi-Label Precision, Recall, and F1 Score per Label**:
- `precision` — Precision per label (dimension: series)
- `recall` — Recall per label (dimension: series)
- `f1_score` — F1 score per label (dimension: series)

## SQL Query

```sql
SELECT
  series AS label,
  AVG(precision) AS avg_precision,
  AVG(recall) AS avg_recall,
  AVG(f1_score) AS avg_f1_score
FROM
  multi_label_precision_recall_f1
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label;
```

## What this shows

A scatter plot with precision on X-axis, recall on Y-axis, one point per label. This reveals:
- Precision-recall balance for each label
- Which labels favor precision vs recall
- Overall model behavior patterns
- Labels in different quadrants have different issues

## How to interpret it

**Top-right quadrant (High P, High R)**:
- Excellent labels
- Both precision and recall > 0.8
- Ideal performance

**Top-left quadrant (Low P, High R)**:
- Aggressive predictions
- Catches most instances but many false positives
- **Action**: Raise confidence threshold

**Bottom-right quadrant (High P, Low R)**:
- Conservative predictions
- Few false positives but misses many instances
- **Action**: Lower threshold or add training data

**Bottom-left quadrant (Low P, Low R)**:
- Poor performance
- Both metrics low
- **Action**: Fundamental improvement needed

**Diagonal line (P ≈ R)**:
- Balanced precision and recall
- F1 will be close to both
- Neither metric dominates

**Far from diagonal**:
- Imbalanced performance
- One metric much better than the other
- Threshold tuning opportunity

**Visualization tips**:
- Use point size to show F1 score (larger = better)
- Color code by label category if applicable
- Add reference lines at 0.5, 0.7, 0.9 thresholds
- Show diagonal line (P=R) for reference
- Label outlier points with label names

**Use this chart to**:
- Understand precision-recall tradeoffs per label
- Identify which labels need threshold tuning
- Visualize overall model behavior
- Prioritize improvements based on quadrant
