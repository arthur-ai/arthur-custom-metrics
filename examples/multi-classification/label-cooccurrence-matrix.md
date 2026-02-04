# Label Co-occurrence Matrix

## Overview

This metric tracks **how often pairs of labels appear together in the same inference** for multi-label classification models. It helps monitor:

* Which labels frequently co-occur in predictions
* Which labels frequently co-occur in ground truth
* Label dependency patterns and relationships
* Changes in label correlation over time
* Differences between predicted and actual label associations

This metric provides two separate co-occurrence matrices:
1. **Predicted co-occurrence**: Which label pairs the model predicts together
2. **Ground truth co-occurrence**: Which label pairs actually occur together

Understanding label relationships helps with model architecture decisions, feature engineering, and identifying unexpected label correlations.

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{row_id_col}}` — unique identifier for each inference row
* `{{predicted_labels_col}}` — array/list of predicted labels
* `{{ground_truth_labels_col}}` — array/list of ground truth labels
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL generates all label pairs that co-occur within each inference, counted separately for predictions and ground truth.

```sql
WITH
  base AS (
    SELECT
      time_bucket (INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{row_id_col}}::text AS row_id,
      {{predicted_labels_col}} AS pred_labels,
      {{ground_truth_labels_col}} AS gt_labels
    FROM
      {{dataset}}
    WHERE
      {{timestamp_col}} IS NOT NULL
  ),
  pred_exploded AS (
    SELECT
      ts,
      row_id,
      unnest(COALESCE(pred_labels, ARRAY[]::TEXT[])) AS label
    FROM
      base
    WHERE
      pred_labels IS NOT NULL
  ),
  gt_exploded AS (
    SELECT
      ts,
      row_id,
      unnest(COALESCE(gt_labels, ARRAY[]::TEXT[])) AS label
    FROM
      base
    WHERE
      gt_labels IS NOT NULL
  ),
  pred_pairs AS (
    SELECT
      ts,
      row_id,
      LEAST(p1.label, p2.label) AS label_1,
      GREATEST(p1.label, p2.label) AS label_2
    FROM
      pred_exploded p1
      JOIN pred_exploded p2 ON p1.row_id = p2.row_id
      AND p1.ts = p2.ts
    WHERE
      p1.label < p2.label
      AND p1.label IS NOT NULL
      AND p1.label <> ''
      AND p2.label IS NOT NULL
      AND p2.label <> ''
  ),
  gt_pairs AS (
    SELECT
      ts,
      row_id,
      LEAST(g1.label, g2.label) AS label_1,
      GREATEST(g1.label, g2.label) AS label_2
    FROM
      gt_exploded g1
      JOIN gt_exploded g2 ON g1.row_id = g2.row_id
      AND g1.ts = g2.ts
    WHERE
      g1.label < g2.label
      AND g1.label IS NOT NULL
      AND g1.label <> ''
      AND g2.label IS NOT NULL
      AND g2.label <> ''
  ),
  pred_counts AS (
    SELECT
      ts,
      label_1,
      label_2,
      COUNT(DISTINCT row_id)::float AS pred_cooccurrence_count
    FROM
      pred_pairs
    GROUP BY
      1,
      2,
      3
  ),
  gt_counts AS (
    SELECT
      ts,
      label_1,
      label_2,
      COUNT(DISTINCT row_id)::float AS gt_cooccurrence_count
    FROM
      gt_pairs
    GROUP BY
      1,
      2,
      3
  )
SELECT
  COALESCE(p.ts, g.ts) AS ts,
  COALESCE(p.label_1, g.label_1) AS label_1,
  COALESCE(p.label_2, g.label_2) AS label_2,
  COALESCE(p.pred_cooccurrence_count, 0) AS pred_cooccurrence_count,
  COALESCE(g.gt_cooccurrence_count, 0) AS gt_cooccurrence_count
FROM
  pred_counts p
  FULL OUTER JOIN gt_counts g ON p.ts = g.ts
  AND p.label_1 = g.label_1
  AND p.label_2 = g.label_2
ORDER BY
  ts,
  label_1,
  label_2;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `label_1` — first label in the pair (dimension)
* `label_2` — second label in the pair (dimension)
* `pred_cooccurrence_count` — count of inferences where both labels were predicted
* `gt_cooccurrence_count` — count of inferences where both labels were in ground truth

## Aggregate Arguments

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp_Col`
3. **Description:** `Column parameter: timestamp_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Row ID Column

1. **Parameter Key:** `row_id_col`
2. **Friendly Name:** `Row_Id_Col`
3. **Description:** `Column parameter: row_id_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Allowed Column Types:** `str`, `uuid`, `int`

### Argument 3 — Predicted Labels Column

1. **Parameter Key:** `predicted_labels_col`
2. **Friendly Name:** `Predicted_Labels_Col`
3. **Description:** `Column parameter: predicted_labels_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `prediction`

### Argument 4 — Ground Truth Labels Column

1. **Parameter Key:** `ground_truth_labels_col`
2. **Friendly Name:** `Ground_Truth_Labels_Col`
3. **Description:** `Column parameter: ground_truth_labels_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `ground_truth`

### Argument 5 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Predicted Co-occurrence Count

1. **Metric Name:** `pred_cooccurrence_count`
2. **Description:** `Count of inferences where both labels were predicted together`
3. **Value Column:** `pred_cooccurrence_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `label_1, label_2`

### Metric 2 — Ground Truth Co-occurrence Count

1. **Metric Name:** `gt_cooccurrence_count`
2. **Description:** `Count of inferences where both labels appeared in ground truth together`
3. **Value Column:** `gt_cooccurrence_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `label_1, label_2`

## Interpreting the Metrics

### Predicted Co-occurrence

**What it shows**: Which label pairs the model believes go together

* **High count**: Model frequently predicts these labels together
* **Low count**: Labels rarely co-occur in predictions
* **Increasing trend**: Model learning to associate these labels
* **Decreasing trend**: Model reducing correlation between labels

**Use cases**:
- Understand model's learned label dependencies
- Identify unexpected label correlations
- Validate model behavior against business logic

### Ground Truth Co-occurrence

**What it shows**: Which label pairs actually occur together in reality

* **High count**: Labels naturally co-occur in the data
* **Low count**: Labels are independent or mutually exclusive
* **Stable**: Expected label relationships
* **Changing**: Real-world label distribution shifting

**Use cases**:
- Understand true label dependencies
- Identify natural label clusters
- Baseline for comparing predicted co-occurrence

### Comparing Predicted vs Ground Truth

**Predicted ≈ Ground Truth**: Model correctly learns label relationships
**Predicted > Ground Truth**: Model over-associates these labels
**Predicted < Ground Truth**: Model under-associates these labels

## Example Analysis

### Example 1: Strong Co-occurrence

**Label Pair**: (outdoor, sunny)
- Predicted co-occurrence: 450/day
- Ground truth co-occurrence: 480/day
- **Interpretation**: Model correctly learned these labels often go together

### Example 2: Over-association

**Label Pair**: (vehicle, person)
- Predicted co-occurrence: 320/day
- Ground truth co-occurrence: 180/day
- **Interpretation**: Model over-predicts these together, may need correction

### Example 3: Under-association

**Label Pair**: (food, restaurant)
- Predicted co-occurrence: 80/day
- Ground truth co-occurrence: 250/day
- **Interpretation**: Model missing this relationship, needs improvement

### Example 4: Unexpected Correlation

**Label Pair**: (error_code, weekend)
- Predicted co-occurrence: 0/day
- Ground truth co-occurrence: 150/day
- **Interpretation**: Real pattern not captured by model, investigate

## Visualization

This metric is best visualized as:

1. **Heatmap**: Matrix showing co-occurrence strength
   - Rows: label_1
   - Columns: label_2
   - Color intensity: co-occurrence count

2. **Network Graph**: Labels as nodes, co-occurrence as edges
   - Node: label
   - Edge thickness: co-occurrence strength
   - Clusters: frequently co-occurring label groups

3. **Top Pairs Table**: Most frequent co-occurrences
   - Sorted by count
   - Shows strongest relationships

## Use Cases

### Model Development

* **Feature engineering**: Identify label relationships for feature design
* **Architecture decisions**: Inform hierarchical or conditional models
* **Training data**: Ensure training data covers important co-occurrences

### Monitoring

* **Drift detection**: Changes in co-occurrence patterns indicate drift
* **Anomaly detection**: Unusual co-occurrences may signal issues
* **Quality assurance**: Validate predictions match expected relationships

### Business Insights

* **Label dependencies**: Understand which labels naturally cluster
* **Data patterns**: Discover unexpected label correlations
* **Domain validation**: Verify model aligns with domain knowledge

### Label Management

* **Catalog cleanup**: Identify redundant or highly correlated labels
* **Label consolidation**: Merge always-co-occurring labels
* **Taxonomy design**: Organize labels based on relationships

## Analysis Patterns

### Independent Labels
- Co-occurrence count low for all pairs
- Labels can appear independently
- No strong dependencies

### Label Clusters
- High co-occurrence within groups
- Low co-occurrence across groups
- Natural label categories

### Conditional Labels
- Label B only appears when Label A present
- Asymmetric relationship
- Consider hierarchical structure

### Mutually Exclusive Labels
- Never co-occur (count = 0)
- Conflicting labels
- May indicate classification alternatives

## Performance Considerations

**For large label catalogs (50-100 labels)**:
- Number of pairs = N × (N-1) / 2
- 50 labels = 1,225 pairs
- 100 labels = 4,950 pairs

**Recommendations**:
- Filter to pairs with count > threshold (e.g., >10)
- Focus on top N most frequent pairs
- Aggregate over longer time windows to reduce data volume

## Derived Metrics

From co-occurrence counts, you can calculate:

**Conditional Probability**:
P(B|A) = Count(A and B) / Count(A)

**Lift**:
Lift(A,B) = P(A and B) / (P(A) × P(B))

**Jaccard Similarity**:
J(A,B) = Count(A and B) / Count(A or B)

These can be computed as follow-up analyses using this metric's output.
