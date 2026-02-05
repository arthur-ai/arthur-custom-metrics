# Average Confidence Score per Label

## Overview

This metric tracks the **average confidence/probability score for each class label** in multi-label classification models. It helps monitor:

* Model confidence levels for each specific label
* Which labels the model is uncertain about
* Changes in prediction confidence over time
* Potential calibration issues per label
* Low confidence predictions that may need review

This metric includes ALL labels in the catalog:
- **Predicted labels**: Use their actual confidence scores
- **Non-predicted labels**: Assigned confidence of 0

This provides a complete view of model confidence across the entire label space.

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{row_id_col}}` — unique identifier for each inference row
* `{{predicted_labels_col}}` — array/list of predicted labels
* `{{confidence_scores_col}}` — array/list of confidence scores (parallel to predicted labels)
* `{{dataset}}` — dataset containing the inferences

**Important**: The confidence_scores array must be parallel to the predicted_labels array, where confidence_scores[i] is the confidence for predicted_labels[i].

## Base Metric SQL

This SQL calculates average confidence per label, including 0 for non-predicted labels.

```sql
WITH
  base AS (
    SELECT
      time_bucket (INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{row_id_col}}::text AS row_id,
      {{predicted_labels_col}} AS pred_labels,
      {{confidence_scores_col}} AS confidence_scores
    FROM
      {{dataset}}
    WHERE
      {{timestamp_col}} IS NOT NULL
  ),
  label_catalog AS (
    SELECT DISTINCT
      ts,
      unnest(COALESCE(pred_labels, ARRAY[]::TEXT[])) AS label
    FROM
      base
    WHERE
      pred_labels IS NOT NULL
  ),
  predictions_with_confidence AS (
    SELECT
      b.ts,
      b.row_id,
      l.label,
      l.confidence
    FROM
      base b
      CROSS JOIN LATERAL (
        SELECT
          pred_labels[i] AS label,
          confidence_scores[i] AS confidence
        FROM
          generate_series(1, COALESCE(array_length(pred_labels, 1), 0)) AS i
        WHERE
          pred_labels[i] IS NOT NULL
          AND pred_labels[i] <> ''
          AND confidence_scores[i] IS NOT NULL
      ) l
  ),
  all_labels_with_inferences AS (
    SELECT
      c.ts,
      b.row_id,
      c.label
    FROM
      label_catalog c
      CROSS JOIN (
        SELECT DISTINCT
          ts,
          row_id
        FROM
          base
      ) b
    WHERE
      c.ts = b.ts
  ),
  complete_data AS (
    SELECT
      a.ts,
      a.row_id,
      a.label,
      COALESCE(p.confidence, 0.0)::float AS confidence
    FROM
      all_labels_with_inferences a
      LEFT JOIN predictions_with_confidence p ON a.ts = p.ts
      AND a.row_id = p.row_id
      AND a.label = p.label
  )
SELECT
  ts,
  label AS series,
  AVG(confidence) AS avg_confidence
FROM
  complete_data
GROUP BY
  1,
  2
ORDER BY
  ts,
  series;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `series` — the class label name (dimension)
* `avg_confidence` — average confidence score for this label (0 to 1, includes 0 for non-predictions)

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

### Argument 4 — Confidence Scores Column

1. **Parameter Key:** `confidence_scores_col`
2. **Friendly Name:** `Confidence_Scores_Col`
3. **Description:** `Column parameter: confidence_scores_col (array parallel to predicted labels)`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `prediction_score`

### Argument 5 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Average Confidence

1. **Metric Name:** `avg_confidence`
2. **Description:** `Average confidence score per label (includes 0 for non-predicted)`
3. **Value Column:** `avg_confidence`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `series`

## Interpreting the Metric

### Confidence Score Ranges

* **High confidence (0.8-1.0)**
  * Model very certain about this label
  * Strong signal for prediction
  * Typically indicates well-learned labels

* **Medium confidence (0.5-0.8)**
  * Moderate certainty
  * Predicted but not with high confidence
  * May benefit from more training data

* **Low confidence (0.2-0.5)**
  * Model uncertain
  * Predictions may be unreliable
  * Consider as candidates for human review

* **Very low confidence (0.0-0.2)**
  * Rarely predicted or high non-prediction rate
  * Includes effect of 0s for non-predicted labels
  * May indicate rare or difficult labels

### Patterns to Monitor

* **Decreasing confidence over time**
  * Model becoming less certain
  * May indicate data drift
  * Could signal model degradation

* **Increasing confidence over time**
  * Model becoming more certain
  * May indicate improved learning
  * Could also mean over-confidence

* **Confidence not correlated with accuracy**
  * Calibration problem
  * High confidence on incorrect predictions
  * Requires calibration tuning

* **Large variance in confidence across labels**
  * Some labels easy to predict (high confidence)
  * Others difficult (low confidence)
  * Natural for imbalanced or varied datasets

## Confidence vs Accuracy Analysis

**Ideal relationship**: High confidence → High accuracy

**Calibration issues**:
- High confidence + Low accuracy → Over-confident model
- Low confidence + High accuracy → Under-confident model
- Use with Precision/Recall metrics to validate calibration

## Use Cases

### Quality Control

* **Low confidence filtering**: Flag predictions below confidence threshold
* **Human review**: Send low-confidence predictions for manual review
* **Confidence-based routing**: Route uncertain predictions to specialists

### Model Monitoring

* **Confidence drift**: Track changes in confidence distribution
* **Per-label uncertainty**: Identify which labels need more training
* **Calibration tracking**: Monitor confidence-accuracy alignment

### Business Logic

* **Threshold tuning**: Set per-label confidence thresholds
* **Cost-benefit analysis**: Balance automation vs human review based on confidence
* **Risk management**: Higher stakes → require higher confidence

### Model Development

* **Training focus**: Identify low-confidence labels needing more data
* **Architecture evaluation**: Compare confidence distributions across models
* **Calibration tuning**: Adjust model to improve confidence calibration

## Example Scenarios

### Scenario 1: Well-Learned Label

**Label**: "outdoor"
- Average confidence: 0.92
- Precision: 0.95
- **Interpretation**: Model confident and accurate, performing well

### Scenario 2: Uncertain Label

**Label**: "vintage"
- Average confidence: 0.45
- Precision: 0.70
- **Interpretation**: Model uncertain, consider collecting more training data

### Scenario 3: Over-Confident Label

**Label**: "modern"
- Average confidence: 0.88
- Precision: 0.62
- **Interpretation**: Model over-confident, calibration issue, needs adjustment

### Scenario 4: Rare Label

**Label**: "impressionist"
- Average confidence: 0.08
- Precision: 0.90 (when predicted)
- **Interpretation**: Rarely predicted (many 0s), but accurate when it is

## Confidence Thresholds

Common threshold strategies:

**Conservative** (High precision):
- Predict only if confidence > 0.8
- Reduces false positives
- May miss some true positives

**Balanced** (F1 optimization):
- Predict if confidence > 0.5
- Balances precision and recall
- Typical default threshold

**Aggressive** (High recall):
- Predict if confidence > 0.3
- Captures more true positives
- Increases false positives

**Per-label thresholds**:
- Set different thresholds per label based on importance
- Critical labels → higher threshold
- Less critical → lower threshold

## Including Non-Predicted Labels

This metric includes 0 confidence for non-predicted labels, which:

**Advantages**:
- ✅ Complete view of all labels
- ✅ Shows prediction selectivity
- ✅ Identifies rarely-used labels
- ✅ Provides context for label importance

**Considerations**:
- ⚠️ Lowers average confidence for rare labels
- ⚠️ Makes comparison across labels more nuanced
- ⚠️ Requires understanding of non-prediction = 0

**Alternative**: Track separately for predicted-only vs all labels

## Relationship to Other Metrics

* **Precision/Recall**: Accuracy of predictions
* **Average Confidence**: Certainty of predictions
* **Together**: Understand both quality and certainty

**Ideal**: High confidence + High precision/recall
**Problem**: High confidence + Low precision (over-confident)

## Alerting Thresholds

**Critical**: Avg confidence < 0.3 for important labels
**Warning**: Avg confidence < 0.5 for important labels
**Target**: Avg confidence > 0.6 for well-learned labels

**Calibration check**:
- Confidence 0.8-1.0 → Precision should be >0.8
- Confidence 0.6-0.8 → Precision should be >0.6
- Large gap = calibration issue
