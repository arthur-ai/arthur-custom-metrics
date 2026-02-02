# Multi-Label Prediction Volume per Inference

## Overview

This metric tracks the **average number of labels predicted per inference** in multi-label classification models. It helps monitor:

* How many labels your model predicts on average
* Changes in prediction behavior over time
* Whether your model is becoming more or less confident in multi-label scenarios

This is useful for multi-label classification where each input can have multiple predicted labels (e.g., image tagging, document categorization, symptom detection).

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{row_id_col}}` — unique identifier for each inference row
* `{{pred_labels_col}}` — array/list of predicted labels
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL computes the average number of predicted labels per inference, aggregated by day.

```sql
WITH
  per_row AS (
    SELECT
      time_bucket (INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{row_id_col}}::text AS row_id,
      COALESCE(array_length({{pred_labels_col}}), 0)::float AS pred_label_count
    FROM
      {{dataset}}
    WHERE
      {{timestamp_col}} IS NOT NULL
  )
SELECT
  ts,
  AVG(pred_label_count) AS pred_label_count
FROM
  per_row
GROUP BY
  1
ORDER BY
  ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `pred_label_count` — average number of predicted labels per inference

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
7. **Allowed Column Types:** `int`, `uuid`, `str`

### Argument 3 — Predicted Labels Column

1. **Parameter Key:** `pred_labels_col`
2. **Friendly Name:** `Pred_Labels_Col`
3. **Description:** `Column parameter: pred_labels_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`

### Argument 4 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Predicted Label Count

1. **Metric Name:** `pred_label_count`
2. **Description:** `Average number of predicted labels per inference`
3. **Value Column:** `pred_label_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

* **Increasing trend**
  * Model is predicting more labels per inference
  * Could indicate increased confidence or a shift in data distribution
  * May be desirable if aligned with business needs (e.g., more comprehensive tagging)

* **Decreasing trend**
  * Model is becoming more selective
  * Could indicate increased precision or a shift toward simpler cases
  * May warrant investigation if unexpected

* **High variance**
  * Inconsistent prediction behavior
  * May indicate data quality issues or model instability

## Use Cases

* Multi-label image classification (object detection, scene tagging)
* Document categorization (multiple topics per document)
* Medical diagnosis (multiple symptoms or conditions)
* Content tagging (multiple tags per article/video)
* Product classification (multiple categories per product)
