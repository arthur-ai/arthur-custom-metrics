# Multi-Label Precision, Recall, and F1 Score per Label

## Overview

This metric tracks **precision, recall, and F1 score for each individual class label** in multi-label classification models. It helps monitor:

* **Precision**: What percentage of predictions for this label are correct?
* **Recall**: What percentage of actual instances of this label are captured?
* **F1 Score**: Harmonic mean balancing precision and recall
* Per-label performance trends over time
* Which labels have quality issues

These are derived from the confusion matrix components (TP, FP, FN) and provide the most actionable performance metrics for multi-label classification.

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{row_id_col}}` — unique identifier for each inference row
* `{{predicted_labels_col}}` — array/list of predicted labels
* `{{ground_truth_labels_col}}` — array/list of ground truth labels
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates precision, recall, and F1 score for each label by first computing confusion matrix components.

```sql
WITH
  base AS (
    SELECT
      time_bucket (INTERVAL '1 day', {{timestamp_col}}) AS bucket,
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
      bucket,
      row_id,
      label,
      1 AS predicted
    FROM
      base
      CROSS JOIN LATERAL (
        SELECT DISTINCT
          unnest(pred_labels) AS label
      ) p
    WHERE
      label IS NOT NULL
      AND label <> ''
  ),
  gt_exploded AS (
    SELECT
      bucket,
      row_id,
      label,
      1 AS actual
    FROM
      base
      CROSS JOIN LATERAL (
        SELECT DISTINCT
          unnest(gt_labels) AS label
      ) g
    WHERE
      label IS NOT NULL
      AND label <> ''
  ),
  joined AS (
    SELECT
      COALESCE(p.bucket, g.bucket) AS bucket,
      COALESCE(p.row_id, g.row_id) AS row_id,
      COALESCE(p.label, g.label) AS label,
      COALESCE(predicted, 0) AS predicted,
      COALESCE(actual, 0) AS actual
    FROM
      pred_exploded p
      FULL OUTER JOIN gt_exploded g ON p.row_id = g.row_id
      AND p.label = g.label
  ),
  confusion AS (
    SELECT
      bucket AS ts,
      label AS series,
      SUM(
        CASE
          WHEN predicted = 1
          AND actual = 1 THEN 1
          ELSE 0
        END
      )::float AS tp,
      SUM(
        CASE
          WHEN predicted = 1
          AND actual = 0 THEN 1
          ELSE 0
        END
      )::float AS fp,
      SUM(
        CASE
          WHEN predicted = 0
          AND actual = 1 THEN 1
          ELSE 0
        END
      )::float AS fn
    FROM
      joined
    GROUP BY
      1,
      2
  )
SELECT
  ts,
  series,
  tp / NULLIF(tp + fp, 0) AS precision,
  tp / NULLIF(tp + fn, 0) AS recall,
  (2.0 * tp) / NULLIF(2.0 * tp + fp + fn, 0) AS f1_score
FROM
  confusion
ORDER BY
  ts,
  series;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `series` — the class label name (dimension)
* `precision` — TP / (TP + FP) for this label
* `recall` — TP / (TP + FN) for this label
* `f1_score` — 2 × (Precision × Recall) / (Precision + Recall)

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

### Metric 1 — Precision

1. **Metric Name:** `precision`
2. **Description:** `Precision per class label (TP / (TP + FP))`
3. **Value Column:** `precision`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `series`

### Metric 2 — Recall

1. **Metric Name:** `recall`
2. **Description:** `Recall per class label (TP / (TP + FN))`
3. **Value Column:** `recall`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `series`

### Metric 3 — F1 Score

1. **Metric Name:** `f1_score`
2. **Description:** `F1 score per class label (harmonic mean of precision and recall)`
3. **Value Column:** `f1_score`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `series`

## Interpreting the Metrics

### Precision (TP / (TP + FP))

**What it measures**: Of all predictions for this label, what % are correct?

* **High precision (>0.9)**: Model rarely over-predicts this label
* **Medium precision (0.7-0.9)**: Some false positives, acceptable for most use cases
* **Low precision (<0.7)**: Model over-predicts this label frequently
* **Decreasing trend**: Model becoming less precise, investigate FP causes

**When to focus on precision:**
- High cost of false alarms
- Content moderation (avoid false accusations)
- Medical diagnosis (avoid unnecessary treatments)

### Recall (TP / (TP + FN))

**What it measures**: Of all actual instances of this label, what % did we catch?

* **High recall (>0.9)**: Model rarely misses this label
* **Medium recall (0.7-0.9)**: Some false negatives, acceptable for most use cases
* **Low recall (<0.7)**: Model frequently misses this label
* **Decreasing trend**: Model missing more instances, investigate FN causes

**When to focus on recall:**
- High cost of missing instances
- Safety-critical applications (detect all hazards)
- Medical screening (catch all potential cases)

### F1 Score (Harmonic Mean)

**What it measures**: Balanced metric combining precision and recall

* **High F1 (>0.9)**: Excellent overall performance
* **Medium F1 (0.7-0.9)**: Good performance, typical for production systems
* **Low F1 (<0.7)**: Poor performance, needs attention
* **F1 closer to precision**: Recall is the limiting factor
* **F1 closer to recall**: Precision is the limiting factor

**When to use F1:**
- Need balanced performance
- Equal concern for FP and FN
- Single metric for ranking/comparison

## Common Patterns

### High Precision, Low Recall
- Model is conservative, only predicts when very confident
- Missing many instances (high FN)
- **Fix**: Lower prediction threshold, add more training examples

### Low Precision, High Recall
- Model is aggressive, predicts frequently
- Many false alarms (high FP)
- **Fix**: Raise prediction threshold, improve model discrimination

### Both Low
- Model struggles with this label entirely
- **Fix**: Check training data quality/quantity, feature engineering

### Imbalanced Across Labels
- Some labels perform well, others poorly
- **Fix**: Address class imbalance, per-label tuning

## Use Cases

* **Performance monitoring**: Track quality metrics per label over time
* **Model comparison**: Compare precision/recall across model versions
* **Label prioritization**: Identify which labels need improvement
* **Threshold tuning**: Understand precision-recall tradeoffs
* **Alerting**: Set thresholds for minimum acceptable F1 per label
* **Client reporting**: Clear, interpretable quality metrics

## Relationship to Confusion Matrix

This metric is derived from the Multi-Label Confusion Matrix:
- Confusion Matrix provides raw counts (TP, FP, FN)
- This metric provides quality ratios (Precision, Recall, F1)
- Use together for complete picture: counts show magnitude, ratios show quality
