# Chart: Predicted vs Ground Truth Co-occurrence Comparison

## Metrics Used

From **Label Co-occurrence Matrix**:
- `pred_cooccurrence_count` — Predicted co-occurrence (dimensions: label_1, label_2)
- `gt_cooccurrence_count` — Ground truth co-occurrence (dimensions: label_1, label_2)

## SQL Query

```sql
SELECT
  label_1,
  label_2,
  SUM(pred_cooccurrence_count) AS pred_count,
  SUM(gt_cooccurrence_count) AS gt_count,
  SUM(pred_cooccurrence_count) - SUM(gt_cooccurrence_count) AS difference
FROM
  label_cooccurrence_matrix
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label_1,
  label_2
HAVING
  SUM(gt_cooccurrence_count) > 10
ORDER BY
  ABS(SUM(pred_cooccurrence_count) - SUM(gt_cooccurrence_count)) DESC
LIMIT 50;
```

## What this shows

A comparison showing the difference between predicted and ground truth co-occurrence for label pairs. This reveals:
- Which label relationships are learned correctly
- Which pairs are over-associated by the model
- Which pairs are under-associated by the model
- Model's understanding of label dependencies

## How to interpret it

**Predicted ≈ Ground Truth (difference near 0)**:
- Model correctly learned this relationship
- Co-occurrence pattern matches reality
- Good performance for this pair

**Predicted >> Ground Truth (large positive difference)**:
- Model over-associates these labels
- Predicts them together more than they actually occur
- May indicate model bias or confusion
- **Example**: Predicts (cat, dog) together 500 times, actually co-occur 100 times

**Predicted << Ground Truth (large negative difference)**:
- Model under-associates these labels
- Misses this relationship
- Labels co-occur in reality but model doesn't capture it
- **Example**: Predicts (food, restaurant) together 50 times, actually co-occur 300 times

**Consistent over-association**:
- Model tends to over-predict correlations
- May be too aggressive
- Consider threshold tuning

**Consistent under-association**:
- Model misses relationships
- Too conservative
- May need more training on co-occurring examples

**Random errors**:
- Some pairs over, some under
- No systematic pattern
- Normal model variation

**Visualization options**:

1. **Diverging bar chart**: Show difference (red=over, blue=under)
2. **Scatter plot**: X=GT count, Y=Pred count, diagonal=perfect
3. **Heatmap**: Show difference matrix
4. **Table**: Top mismatches ranked by absolute difference

**Use this chart to**:
- Validate model learning of relationships
- Identify systematic biases
- Guide model improvement
- Understand prediction patterns
- Prioritize relationship modeling improvements
