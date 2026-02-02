# Chart: Exact Match vs Jaccard Similarity

## Metrics Used

From **Exact Match Ratio**:
- `exact_match_ratio` — Proportion of perfect predictions

From **Jaccard Similarity Score**:
- `jaccard_similarity` — Average Jaccard score

## SQL Query

```sql
SELECT
  COALESCE(e.ts, j.ts) AS ts,
  e.exact_match_ratio,
  j.jaccard_similarity
FROM
  exact_match_ratio e
  FULL OUTER JOIN jaccard_similarity j ON e.ts = j.ts
ORDER BY
  ts;
```

## What this shows

Two time series on the same chart comparing exact match ratio and Jaccard similarity over time. This reveals:
- Relationship between strict and lenient accuracy
- How often predictions are "almost right"
- Quality patterns and trends
- Overall model behavior

## How to interpret it

**Both metrics high (>0.8)**:
- Excellent performance
- Most predictions perfect or near-perfect
- Model performing very well

**Both metrics low (<0.5)**:
- Poor performance overall
- Many significant errors
- Fundamental issues

**Large gap (Jaccard >> Exact Match)**:
- Many predictions are "close but not perfect"
- Small errors in many predictions (1 label off)
- **Opportunity**: Threshold tuning may help
- Example: Jaccard=0.75, Exact=0.35

**Small gap (Jaccard ≈ Exact Match)**:
- Predictions tend to be either perfect or very wrong
- Few "almost right" predictions
- Binary quality pattern
- Example: Jaccard=0.45, Exact=0.40

**Parallel movements**:
- Both metrics move together
- Consistent relationship
- Expected behavior

**Diverging trends**:
- Gap widening or shrinking
- Changing error patterns
- May indicate drift or model changes

**Typical relationships**:
- Simple tasks: Small gap (0.1-0.2)
- Moderate tasks: Medium gap (0.2-0.3)
- Complex tasks: Large gap (0.3-0.5)

**Use this chart to**:
- Understand prediction error patterns
- Decide if threshold tuning can help
- Report on quality with context
- Monitor both strict and lenient accuracy
- Identify opportunities for improvement
