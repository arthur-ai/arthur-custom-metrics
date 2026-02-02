# Chart: Ground Truth Label Co-occurrence Heatmap

## Metrics Used

From **Label Co-occurrence Matrix**:
- `gt_cooccurrence_count` — Count of inferences where label pairs appeared in ground truth together (dimensions: label_1, label_2)

## SQL Query

```sql
SELECT
  label_1,
  label_2,
  SUM(gt_cooccurrence_count) AS total_cooccurrence
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

A heatmap showing how often label pairs actually appear together in ground truth. This reveals:
- True label relationships in the data
- Natural label dependencies
- Domain structure and patterns
- Baseline for comparing with predictions

## How to interpret it

**Dark/hot colors (high co-occurrence)**:
- Label pairs frequently occur together
- Natural correlation in the domain
- Strong true relationship

**Light/cold colors (low co-occurrence)**:
- Label pairs rarely occur together
- Independent or mutually exclusive labels
- Weak relationship

**Diagonal patterns**:
- Natural label clusters
- Semantic categories
- Domain structure

**Perfect independence (uniform light)**:
- Labels can appear in any combination
- No strong dependencies
- High label independence

**Strong dependencies**:
- Some labels almost always together
- Consider if labels are redundant
- May inform label consolidation

**Mutually exclusive patterns**:
- Some pairs never co-occur (count=0)
- Conflicting labels
- Domain constraints

**Visualization tips**:
- Same color scheme as predicted co-occurrence for comparison
- Show labels on both axes
- Consider filtering to top N×N labels
- Add actual count values in cells
- Sort labels by hierarchy if applicable

**Use this chart to**:
- Understand true label relationships
- Baseline for model learning
- Identify domain patterns
- Validate data quality
- Inform label taxonomy design
- Compare with predicted co-occurrence
