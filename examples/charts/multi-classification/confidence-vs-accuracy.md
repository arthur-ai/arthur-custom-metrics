# Chart: Confidence vs Accuracy Calibration

## Metrics Used

From **Average Confidence Score per Label**:
- `avg_confidence` — Average confidence per label (dimension: series)

From **Multi-Label Precision, Recall, and F1 Score per Label**:
- `precision` — Precision per label (dimension: series)

## SQL Query

```sql
SELECT
  c.series AS label,
  AVG(c.avg_confidence) AS avg_confidence,
  AVG(p.precision) AS avg_precision
FROM
  average_confidence_per_label c
  JOIN multi_label_precision_recall_f1 p ON c.ts = p.ts
  AND c.series = p.series
WHERE
  c.ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  c.series;
```

## What this shows

A scatter plot comparing confidence vs accuracy (precision) for each label. This reveals:
- Model calibration quality
- Whether high confidence correlates with high accuracy
- Over-confident or under-confident labels
- Calibration issues per label

## How to interpret it

**Ideal: Points near diagonal (Confidence ≈ Precision)**:
- Well-calibrated model
- Confidence matches actual accuracy
- Example: 0.8 confidence → 0.8 precision

**Above diagonal (Confidence > Precision)**:
- Over-confident model
- Claims higher certainty than accuracy warrants
- **Risk**: Unreliable high-confidence predictions
- **Example**: 0.9 confidence but 0.6 precision

**Below diagonal (Confidence < Precision)**:
- Under-confident model
- More accurate than confidence suggests
- **Opportunity**: Could be more aggressive
- **Example**: 0.5 confidence but 0.8 precision

**Top-right quadrant (High conf, High prec)**:
- Excellent labels
- Confident and accurate
- Best performing labels

**Top-left quadrant (Low conf, High prec)**:
- Under-confident
- Accurate but not reflecting it
- Consider lowering thresholds

**Bottom-right quadrant (High conf, Low prec)**:
- Over-confident
- Dangerous: wrong but certain
- **Critical issue**: Requires calibration

**Bottom-left quadrant (Low conf, Low prec)**:
- Poor performance overall
- At least model knows it's uncertain
- Needs improvement

**Systematic patterns**:
- All points above diagonal → Model over-confident overall
- All points below diagonal → Model under-confident overall
- Random scatter → Calibration varies by label

**Visualization tips**:
- Add diagonal reference line (y=x)
- Color code by label frequency or importance
- Size points by sample size
- Add labels for outliers
- Show confidence intervals if available

**Actions by quadrant**:

- **Over-confident (above diagonal)**: Apply calibration techniques, raise thresholds
- **Under-confident (below diagonal)**: Lower thresholds, allow more predictions
- **High-quality (top-right)**: Maintain and monitor
- **Low-quality (bottom-left)**: Focus improvement efforts

**Use this chart to**:
- Validate model calibration
- Identify miscalibrated labels
- Guide threshold tuning per label
- Assess reliability of confidence scores
- Prioritize calibration improvements
- Report on prediction quality vs certainty
