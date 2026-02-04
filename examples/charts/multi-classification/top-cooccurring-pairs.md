# Chart: Top Co-occurring Label Pairs

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
  SUM(gt_cooccurrence_count) AS gt_count
FROM
  label_cooccurrence_matrix
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label_1,
  label_2
ORDER BY
  gt_count DESC
LIMIT 20;
```

## What this shows

A table or bar chart showing the top 20 label pairs that co-occur most frequently in ground truth, with comparison to predicted co-occurrence. This reveals:
- Strongest label relationships in the data
- Most important co-occurrences to model correctly
- How well model captures top relationships
- Key dependencies to monitor

## How to interpret it

**High GT count, High Pred count**:
- Important relationship
- Model captures it well
- Continue monitoring

**High GT count, Low Pred count**:
- Important relationship being missed
- Model doesn't learn this dependency
- **High priority**: Improve model to capture this

**High GT count, Very High Pred count**:
- Important relationship
- Model over-predicts it
- May need calibration

**Consistent patterns in top pairs**:
- Certain label families co-occur
- Domain structure evident
- Expected relationships

**Surprising top pairs**:
- Unexpected combinations frequent
- May indicate data issues or domain insights
- Validate with domain experts

**Missing expected pairs**:
- Important relationships not in top 20
- May be under-represented in data
- Check data collection

**Use cases**:

**For monitoring**:
- Track top relationships over time
- Ensure important pairs stay captured
- Alert if key relationships degrade

**For model development**:
- Focus on top pairs first
- Ensure model captures most important relationships
- Use as validation set

**For business insights**:
- Understand domain structure
- Discover unexpected correlations
- Inform product decisions

**Visualization tip**: Use grouped bar chart with GT (blue) and Pred (orange) side-by-side for each pair. Add difference annotation.
