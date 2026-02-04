# Chart: Jaccard Similarity Over Time

## Metrics Used

From **Jaccard Similarity Score**:
- `jaccard_similarity` — Average Jaccard score (Intersection over Union)

## SQL Query

```sql
SELECT
  ts,
  jaccard_similarity
FROM
  jaccard_similarity
ORDER BY
  ts;
```

## What this shows

A time series showing the average Jaccard similarity score (0-1) between predictions and ground truth each day. This reveals:
- Overall prediction quality with partial credit
- How similar predictions are to ground truth
- Quality trends over time
- More forgiving accuracy metric than exact match

## How to interpret it

**Excellent (0.8-1.0)**:
- Predictions highly similar to ground truth
- Most labels correct with few errors
- Strong performance

**Good (0.6-0.8)**:
- Reasonably similar predictions
- Some missing or extra labels
- Acceptable for most production systems

**Fair (0.4-0.6)**:
- Moderate similarity
- Significant errors
- Improvement needed

**Poor (<0.4)**:
- Low similarity
- Many incorrect or missing labels
- Requires investigation

**Increasing trend**:
- Model improving
- Better prediction quality
- Positive development

**Decreasing trend**:
- Model degrading
- Quality declining
- Data drift or model issues

**Stable line**:
- Consistent performance
- Expected in production
- Monitor for changes

**Comparison with exact match**:
- Jaccard > Exact Match (always)
- Large gap → Many predictions "almost right"
- Small gap → Predictions either perfect or very wrong

**Use this chart to**:
- Monitor overall model quality
- Track improvement over time
- Set SLA thresholds (more lenient than exact match)
- Understand prediction quality trends
- Report on model performance
