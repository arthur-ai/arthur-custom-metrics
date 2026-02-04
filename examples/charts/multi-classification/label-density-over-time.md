# Chart: Label Density Over Time

## Metrics Used

From **Label Density**:
- `label_density` — Average labels per inference / Total catalog size (0-1)

## SQL Query

```sql
SELECT
  ts,
  label_density
FROM
  label_density
ORDER BY
  ts;
```

## What this shows

A time series showing how much of the label catalog is being used on average (0-1 scale). This reveals:
- Label space utilization over time
- Whether model is becoming more/less comprehensive
- Sparsity patterns
- Changes in prediction behavior relative to catalog

## How to interpret it

**Very sparse (0.0-0.1)**:
- Using only small fraction of catalog
- Typical for specialized tasks
- Example: 2 labels from 50 available (0.04)
- May indicate many unused labels

**Sparse (0.1-0.3)**:
- Modest catalog utilization
- Typical for most multi-label tasks
- Example: 5 labels from 30 available (0.17)
- Healthy balance

**Moderate (0.3-0.6)**:
- Significant catalog usage
- Dense predictions
- Example: 8 labels from 20 available (0.40)
- Comprehensive tagging

**Dense (0.6-1.0)**:
- Using most of catalog
- Very dense predictions
- Rare - check for over-prediction
- Example: 15 labels from 20 available (0.75)

**Increasing density**:
- Model predicting more labels
- Expanding catalog usage
- May indicate increased confidence

**Decreasing density**:
- Model becoming more selective
- Using fewer labels from catalog
- May indicate increased precision

**Stable density**:
- Consistent behavior
- Expected in production
- Monitor for changes

**Sudden changes**:
- Data distribution shifts
- Model changes
- Requires investigation

**Use this chart to**:
- Monitor prediction behavior
- Understand catalog utilization
- Identify if catalog is too large
- Track impact of model changes
- Compare across model versions
