# Chart: Predicted Label Co-occurrence Heatmap

## Metrics Used

From **Label Co-occurrence Matrix**:
- `pred_cooccurrence_count` — Count of inferences where label pairs were predicted together (dimensions: label_1, label_2)

## SQL Query

```sql
SELECT
  label_1,
  label_2,
  SUM(pred_cooccurrence_count) AS total_cooccurrence
FROM
  label_cooccurrence_matrix
WHERE
  ts >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
  label_1,
  label_2
ORDER BY
  total_cooccurrence DESC;
```

## What this shows

A heatmap showing how often label pairs appear together in predictions. This reveals:
- Which labels the model predicts together
- Label correlation patterns
- Model's learned label dependencies
- Strongest label relationships

## How to interpret it

**Dark/hot colors (high co-occurrence)**:
- Label pairs frequently predicted together
- Strong learned association
- Model believes these labels correlate

**Light/cold colors (low co-occurrence)**:
- Label pairs rarely predicted together
- Weak or no association
- Independent labels

**Diagonal patterns**:
- Clusters of labels that co-occur
- Natural groupings
- Label families or categories

**Symmetric patterns**:
- Co-occurrence is symmetric (A with B = B with A)
- Expected property of co-occurrence

**Unexpected high co-occurrence**:
- Labels that shouldn't correlate but do
- May indicate model confusion
- Verify against business logic

**Unexpected low co-occurrence**:
- Labels that should correlate but don't
- Model may not learn relationship
- Check training data

**Visualization tips**:
- Use color gradient (white=0, dark blue/red=high)
- Show labels on both axes
- Consider showing only top N×N labels by frequency
- Add tooltips with exact counts
- Sort labels by similarity for clustering effect

**Use this chart to**:
- Understand model's learned dependencies
- Validate against domain knowledge
- Identify unexpected correlations
- Guide model architecture decisions
- Inform feature engineering
