# Chart: Prediction Volume Over Time

## Metrics Used

From **Multi-Label Prediction Volume per Inference**:
- `pred_label_count` — Average number of predicted labels per inference

## SQL Query

```sql
SELECT
  ts,
  pred_label_count
FROM
  multi_label_prediction_volume
ORDER BY
  ts;
```

## What this shows

A time series showing the average number of labels predicted per inference each day. This reveals:
- Overall prediction behavior trends
- Whether the model is becoming more or less comprehensive
- Seasonal or cyclical patterns in prediction volume
- Impact of model changes on label volume

## How to interpret it

**Increasing trend**:
- Model predicting more labels per inference
- Could indicate increased confidence or broader categorization
- May be desirable for comprehensive tagging tasks

**Decreasing trend**:
- Model becoming more selective
- Could indicate increased precision or simpler cases
- May warrant investigation if unexpected

**Stable line**:
- Consistent prediction behavior
- Expected in steady-state production
- Monitor for sudden changes

**High variance**:
- Inconsistent prediction patterns
- May indicate data quality issues or model instability
- Check for batch effects or data drift

**Typical values**:
- Simple tasks: 1-3 labels average
- Moderate tasks: 3-6 labels average
- Complex tasks: 6+ labels average
