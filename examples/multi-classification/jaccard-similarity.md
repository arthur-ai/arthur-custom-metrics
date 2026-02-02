# Jaccard Similarity Score

## Overview

This metric tracks the **Jaccard similarity (Intersection over Union) between predicted and ground truth label sets** in multi-label classification models. It helps monitor:

* How similar predictions are to ground truth (0 to 1 scale)
* Model accuracy with partial credit for correct labels
* Overall prediction quality that rewards partial correctness
* Changes in prediction-ground truth overlap over time

The Jaccard Index (also called Intersection over Union or IoU) measures set similarity:
* **Formula**: J(A,B) = |A ∩ B| / |A ∪ B|
* **Range**: 0 (no overlap) to 1 (perfect match)
* **More lenient than exact match**: Rewards predictions that are mostly correct

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{row_id_col}}` — unique identifier for each inference row
* `{{predicted_labels_col}}` — array/list of predicted labels
* `{{ground_truth_labels_col}}` — array/list of ground truth labels
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates the Jaccard similarity score for each inference, then averages by day.

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
  sets AS (
    SELECT
      ts,
      row_id,
      COALESCE(pred_labels, ARRAY[]::TEXT[]) AS pred_set,
      COALESCE(gt_labels, ARRAY[]::TEXT[]) AS gt_set
    FROM
      base
  ),
  jaccard_per_row AS (
    SELECT
      ts,
      row_id,
      CARDINALITY(
        ARRAY(
          SELECT
            unnest(pred_set)
          INTERSECT
          SELECT
            unnest(gt_set)
        )
      )::float AS intersection_size,
      CARDINALITY(
        ARRAY(
          SELECT DISTINCT
            unnest(pred_set || gt_set)
        )
      )::float AS union_size
    FROM
      sets
  ),
  scores AS (
    SELECT
      ts,
      row_id,
      CASE
        WHEN union_size = 0 THEN 1.0
        ELSE intersection_size / union_size
      END AS jaccard_score
    FROM
      jaccard_per_row
  )
SELECT
  ts,
  AVG(jaccard_score) AS jaccard_similarity
FROM
  scores
GROUP BY
  1
ORDER BY
  ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `jaccard_similarity` — average Jaccard score across all inferences (0 to 1)

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

### Metric 1 — Jaccard Similarity

1. **Metric Name:** `jaccard_similarity`
2. **Description:** `Average Jaccard similarity score (Intersection over Union)`
3. **Value Column:** `jaccard_similarity`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

### Score Values

* **Excellent (0.8-1.0)**
  * Predictions highly similar to ground truth
  * Most labels correct with few errors
  * Model performing very well

* **Good (0.6-0.8)**
  * Predictions reasonably similar
  * Some missing or extra labels
  * Acceptable for many production use cases

* **Fair (0.4-0.6)**
  * Moderate similarity
  * Significant number of errors
  * May need model improvement

* **Poor (<0.4)**
  * Low similarity to ground truth
  * Many missing or incorrect labels
  * Requires investigation and fixes

### Trends Over Time

* **Increasing score**
  * Model improving
  * Better prediction quality
  * Positive performance trend

* **Decreasing score**
  * Model degrading
  * Prediction quality declining
  * May indicate data drift or model issues

* **Stable score**
  * Consistent performance
  * Expected in steady-state
  * Monitor for sudden changes

* **High variance**
  * Inconsistent predictions
  * May indicate data quality issues
  * Check for batch effects

## Understanding the Math

### Example Calculations

**Example 1: Perfect Match**
- Predicted: {cat, dog, bird}
- Ground Truth: {cat, dog, bird}
- Intersection: {cat, dog, bird} → 3 labels
- Union: {cat, dog, bird} → 3 labels
- Jaccard: 3/3 = **1.0**

**Example 2: Partial Match**
- Predicted: {cat, dog, fish}
- Ground Truth: {cat, dog, bird}
- Intersection: {cat, dog} → 2 labels
- Union: {cat, dog, fish, bird} → 4 labels
- Jaccard: 2/4 = **0.5**

**Example 3: One Extra Label**
- Predicted: {cat, dog, bird, fish}
- Ground Truth: {cat, dog, bird}
- Intersection: {cat, dog, bird} → 3 labels
- Union: {cat, dog, bird, fish} → 4 labels
- Jaccard: 3/4 = **0.75**

**Example 4: One Missing Label**
- Predicted: {cat, dog}
- Ground Truth: {cat, dog, bird}
- Intersection: {cat, dog} → 2 labels
- Union: {cat, dog, bird} → 3 labels
- Jaccard: 2/3 = **0.67**

**Example 5: No Overlap**
- Predicted: {cat, dog}
- Ground Truth: {bird, fish}
- Intersection: {} → 0 labels
- Union: {cat, dog, bird, fish} → 4 labels
- Jaccard: 0/4 = **0.0**

## Comparison with Other Metrics

### Jaccard vs Exact Match

| Predicted | Ground Truth | Exact Match | Jaccard |
|-----------|--------------|-------------|---------|
| {A, B, C} | {A, B, C}    | 1.0         | 1.0     |
| {A, B}    | {A, B, C}    | 0.0         | 0.67    |
| {A, B, C, D} | {A, B, C} | 0.0         | 0.75    |
| {A, B}    | {C, D}       | 0.0         | 0.0     |

**Key difference**: Jaccard gives partial credit, Exact Match is all-or-nothing

### Jaccard vs F1 Score

* **Jaccard**: Set-level metric (entire prediction evaluated together)
* **F1**: Per-label metric (averaged across individual labels)
* **Both**: Provide complementary views of performance

## Use Cases

* **Primary accuracy KPI**: More practical than exact match for most use cases
* **Model comparison**: Compare models with partial credit for correctness
* **Performance tracking**: Monitor overall prediction quality over time
* **SLA definitions**: Set minimum acceptable Jaccard scores
* **Regression testing**: Ensure new models meet Jaccard thresholds
* **Client reporting**: Intuitive metric (0-100% similarity)

## Advantages

* **Partial credit**: Rewards mostly-correct predictions
* **Symmetric**: Treats FP and FN equally
* **Bounded**: Always 0 to 1, easy to interpret
* **Standard**: Widely used in ML literature
* **Intuitive**: Can explain as "overlap percentage"

## Limitations

* **No per-label granularity**: Can't identify which specific labels are problematic
* **Averages across inferences**: Can hide per-instance variability
* **Equal weight to all errors**: Treats all labels as equally important

**Recommendation**: Use alongside per-label metrics (Precision/Recall/F1) for complete analysis

## Alerting Thresholds

Suggested thresholds for production monitoring:

* **Critical**: Jaccard < 0.4 (poor performance)
* **Warning**: Jaccard < 0.6 (degraded performance)
* **Target**: Jaccard > 0.7 (good performance)
* **Excellent**: Jaccard > 0.8 (high quality)

*Adjust based on your specific use case and baseline performance*
