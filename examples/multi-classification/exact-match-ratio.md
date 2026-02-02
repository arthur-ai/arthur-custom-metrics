# Exact Match Ratio

## Overview

This metric tracks the **proportion of inferences where predicted labels exactly match ground truth labels** in multi-label classification models. It helps monitor:

* Overall model accuracy at the strictest level
* What percentage of predictions are "perfect"
* Changes in exact match performance over time
* Whether model improvements affect perfect prediction rate

This is the most stringent accuracy metric for multi-label classification - a prediction only counts as correct if the predicted label set is identical to the ground truth label set (no extra labels, no missing labels).

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{row_id_col}}` — unique identifier for each inference row
* `{{predicted_labels_col}}` — array/list of predicted labels
* `{{ground_truth_labels_col}}` — array/list of ground truth labels
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL compares predicted and ground truth label sets for exact equality, aggregated by day.

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
  normalized AS (
    SELECT
      ts,
      row_id,
      ARRAY(
        SELECT DISTINCT
          unnest(COALESCE(pred_labels, ARRAY[]::TEXT[]))
        ORDER BY
          1
      ) AS pred_set,
      ARRAY(
        SELECT DISTINCT
          unnest(COALESCE(gt_labels, ARRAY[]::TEXT[]))
        ORDER BY
          1
      ) AS gt_set
    FROM
      base
  ),
  matches AS (
    SELECT
      ts,
      row_id,
      CASE
        WHEN pred_set = gt_set THEN 1.0
        ELSE 0.0
      END AS is_exact_match
    FROM
      normalized
  )
SELECT
  ts,
  AVG(is_exact_match) AS exact_match_ratio
FROM
  matches
GROUP BY
  1
ORDER BY
  ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `exact_match_ratio` — proportion of inferences with exact label set match (0 to 1)

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

### Metric 1 — Exact Match Ratio

1. **Metric Name:** `exact_match_ratio`
2. **Description:** `Proportion of inferences with exact label set match`
3. **Value Column:** `exact_match_ratio`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

### Ratio Values

* **High ratio (>0.8)**
  * Excellent performance - most predictions are perfect
  * Model is well-calibrated and confident
  * May indicate simpler classification task

* **Medium ratio (0.5-0.8)**
  * Good performance - many predictions are perfect
  * Some predictions have minor errors
  * Typical for moderate difficulty multi-label tasks

* **Low ratio (0.2-0.5)**
  * Fair performance - some exact matches
  * Many predictions have at least one error
  * May indicate difficult classification task or model issues

* **Very low ratio (<0.2)**
  * Poor performance - few perfect predictions
  * Most predictions have errors
  * Requires investigation and improvement

### Trends Over Time

* **Increasing ratio**
  * Model improving overall
  * Better calibration or training
  * Positive trend for reporting

* **Decreasing ratio**
  * Model degrading
  * Possible data drift
  * Requires immediate attention

* **Stable ratio**
  * Consistent model behavior
  * Expected in production
  * Monitor for sudden changes

* **High variance**
  * Inconsistent performance
  * May indicate batch effects
  * Check for data quality issues

## Context and Comparisons

### Relationship to Other Metrics

* **Exact Match Ratio**: Strictest measure (all labels must be perfect)
* **Jaccard Similarity**: More lenient (rewards partial correctness)
* **Precision/Recall**: Per-label quality (identifies specific problem labels)
* **F1 Score**: Balanced per-label metric

**Use together for complete picture:**
- Low exact match + high F1 → Small errors in many predictions
- Low exact match + low F1 → Fundamental performance issues
- High exact match + high F1 → Excellent overall performance

### Typical Values by Task Difficulty

* **Simple tasks** (2-3 labels, clear distinctions): 0.7-0.9
* **Moderate tasks** (4-10 labels, some overlap): 0.4-0.7
* **Complex tasks** (10+ labels, high correlation): 0.1-0.4

### Impact of Label Set Size

* **Small label sets** (avg 1-2 labels): Higher exact match ratio
* **Medium label sets** (avg 3-5 labels): Moderate exact match ratio
* **Large label sets** (avg 6+ labels): Lower exact match ratio

*Note: More labels = more opportunities for mismatch = lower exact match ratio*

## Use Cases

* **Executive KPI**: Single number showing "% of perfect predictions"
* **Model comparison**: Compare exact match across model versions
* **SLA monitoring**: Set minimum acceptable exact match ratio
* **Performance dashboard**: Key metric for stakeholder reporting
* **Quality gates**: Require minimum exact match before deployment
* **Trend analysis**: Track long-term model performance

## Limitations

* **Very strict**: Single missing or extra label counts as failure
* **No credit for partial correctness**: 4/5 labels correct = same as 0/5
* **Difficulty dependent**: Harder tasks naturally have lower ratios
* **Set size dependent**: More labels generally means lower ratios

**Recommendation**: Use alongside Jaccard Similarity and F1 Score for balanced view

## Analysis Examples

### High Exact Match + High Jaccard
- Model performs excellently
- Predictions are accurate and complete
- Continue monitoring

### Low Exact Match + High Jaccard
- Model mostly correct but not perfect
- Small errors in many predictions (missing 1 label, extra 1 label)
- Consider threshold tuning

### Low Exact Match + Low Jaccard
- Model has fundamental issues
- Many significant errors
- Requires model improvement or retraining

### Decreasing Trend
- Monitor for data drift
- Check for model degradation
- Investigate recent changes
