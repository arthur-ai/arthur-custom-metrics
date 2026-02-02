# Multi-Label Classification Confusion Matrix – Per Class

## Overview

This metric tracks **confusion matrix components (TP, FP, FN) for each individual class label** in multi-label classification models. It helps monitor:

* True Positives (TP): Correctly predicted labels
* False Positives (FP): Incorrectly predicted labels (not in ground truth)
* False Negatives (FN): Missing labels (in ground truth but not predicted)
* Performance of each class label separately
* Class-specific precision and recall patterns over time

This is useful for multi-label classification where you need to understand model performance at the class level, identify which labels are problematic, and track performance trends for each label independently.

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{row_id_col}}` — unique identifier for each inference row
* `{{predicted_labels_col}}` — array/list of predicted labels
* `{{ground_truth_labels_col}}` — array/list of ground truth labels
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL explodes both predicted and ground truth label arrays, performs a full outer join to match them, and computes confusion matrix components for each label.

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
  tp,
  fp,
  fn
FROM
  confusion
ORDER BY
  ts,
  series;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `series` — the class label name (dimension)
* `tp` — true positives for this label
* `fp` — false positives for this label
* `fn` — false negatives for this label

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

### Metric 1 — True Positives

1. **Metric Name:** `tp`
2. **Description:** `True positives per class label`
3. **Value Column:** `tp`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `series`

### Metric 2 — False Positives

1. **Metric Name:** `fp`
2. **Description:** `False positives per class label`
3. **Value Column:** `fp`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `series`

### Metric 3 — False Negatives

1. **Metric Name:** `fn`
2. **Description:** `False negatives per class label`
3. **Value Column:** `fn`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `series`

## Interpreting the Metric

### True Positives (TP)

* **High TP**: Model correctly identifies this label frequently
* **Low TP**: Model struggles to identify this label, may need more training data
* **Increasing trend**: Model improving at detecting this label
* **Decreasing trend**: Model performance degrading for this label

### False Positives (FP)

* **High FP**: Model over-predicts this label (low precision)
* **Low FP**: Model is conservative, rarely predicts this label incorrectly
* **Increasing trend**: Model becoming less precise for this label
* **Sudden spike**: May indicate data distribution shift or model issues

### False Negatives (FN)

* **High FN**: Model frequently misses this label (low recall)
* **Low FN**: Model rarely misses this label when it's present
* **Increasing trend**: Model missing more instances of this label
* **Decreasing trend**: Model improving at catching this label

### Derived Metrics

From these components, you can calculate:

* **Precision** = TP / (TP + FP) — How many predicted labels are correct
* **Recall** = TP / (TP + FN) — How many actual labels are captured
* **F1 Score** = 2 × (Precision × Recall) / (Precision + Recall)

## Use Cases

* **Multi-label image tagging**: Track which tags have high precision/recall
* **Medical diagnosis**: Monitor which symptoms are correctly/incorrectly identified
* **Content moderation**: Understand which violation types are detected accurately
* **Document categorization**: Identify which topics have poor performance
* **Product classification**: Track accuracy of individual attribute predictions
* **Scene understanding**: Monitor performance on different object/scene labels

## Analysis Examples

### Identifying Problematic Labels

* Labels with high FN → Need better recall (model missing these)
* Labels with high FP → Need better precision (model over-predicting)
* Labels with low TP → Overall poor performance (need investigation)

### Class Imbalance Detection

* Compare TP counts across labels to identify rare vs common labels
* Rare labels may have lower TP counts but good precision/recall ratios

### Monitoring Performance Trends

* Track TP/FP/FN ratios over time to detect performance degradation
* Compare trends across labels to identify systematic vs label-specific issues
