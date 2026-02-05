# Label Coverage Ratio

## Overview

This metric tracks the **proportion of inferences that contain each class label** in multi-label classification models. It helps monitor:

* What percentage of inferences include each specific label
* Label prevalence and distribution patterns
* Changes in label coverage over time
* Which labels are common vs rare across your inference population

The coverage ratio ranges from 0 to 1 (or 0% to 100%), where:
- 1.0 means every inference contains this label
- 0.5 means half of all inferences contain this label
- 0.1 means 10% of inferences contain this label

This is useful for understanding how frequently each label appears in your predictions and detecting shifts in label distribution.

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{row_id_col}}` — unique identifier for each inference row
* `{{pred_labels_col}}` — array/list of predicted labels
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates the ratio of inferences containing each label to the total number of inferences per day.

```sql
WITH
  base AS (
    SELECT
      time_bucket (INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{row_id_col}}::text AS row_id,
      {{pred_labels_col}} AS pred_labels
    FROM
      {{dataset}}
    WHERE
      {{timestamp_col}} IS NOT NULL
  ),
  n_by_bucket AS (
    SELECT
      ts,
      COUNT(DISTINCT row_id)::float AS n
    FROM
      base
    GROUP BY
      1
  ),
  exploded AS (
    SELECT
      ts,
      row_id,
      lbl AS series
    FROM
      base
      CROSS JOIN LATERAL (
        SELECT DISTINCT
          unnest(COALESCE(pred_labels, ARRAY[]::TEXT[])) AS lbl
      ) u
    WHERE
      lbl IS NOT NULL
      AND lbl <> ''
  ),
  label_counts AS (
    SELECT
      ts,
      series,
      COUNT(DISTINCT row_id)::float AS label_n
    FROM
      exploded
    GROUP BY
      1,
      2
  )
SELECT
  c.ts AS ts,
  c.series AS series,
  (c.label_n / NULLIF(n.n, 0)) AS coverage_ratio
FROM
  label_counts c
  JOIN n_by_bucket n ON n.ts = c.ts
ORDER BY
  c.ts,
  c.series;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `series` — the class label name (dimension)
* `coverage_ratio` — proportion of inferences containing this label (0 to 1)

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
7. **Allowed Column Types:** `uuid`, `str`, `int`

### Argument 3 — Predicted Labels Column

1. **Parameter Key:** `pred_labels_col`
2. **Friendly Name:** `Pred_Labels_Col`
3. **Description:** `Column parameter: pred_labels_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `prediction`, `ground_truth`

### Argument 4 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Coverage Ratio

1. **Metric Name:** `coverage_ratio`
2. **Description:** `Proportion of inferences containing each label`
3. **Value Column:** `coverage_ratio`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `series`

## Interpreting the Metric

### Coverage Ratio Values

* **High coverage (0.7-1.0)**
  * Label appears in most inferences
  * Common or default label
  * May indicate a dominant class

* **Medium coverage (0.3-0.7)**
  * Label appears in a moderate portion of inferences
  * Balanced label usage
  * Typical for well-distributed multi-label scenarios

* **Low coverage (0.0-0.3)**
  * Label appears rarely
  * Rare class or edge case
  * May indicate class imbalance

### Trends Over Time

* **Increasing coverage**
  * Label becoming more common in predictions
  * May indicate data drift or changing model behavior
  * Could reflect actual changes in input data distribution

* **Decreasing coverage**
  * Label becoming less common
  * May indicate model becoming more selective
  * Could signal data quality issues or model degradation

* **Stable coverage**
  * Consistent label usage patterns
  * Indicates stable model behavior
  * Expected in steady-state production systems

* **Sudden spikes or drops**
  * Abrupt changes in label prevalence
  * May indicate data issues or model problems
  * Requires investigation

### Comparison Across Labels

* **Uniform coverage**
  * All labels have similar coverage ratios
  * Indicates balanced label distribution
  * Ideal for many multi-label scenarios

* **Imbalanced coverage**
  * Large variance in coverage ratios across labels
  * Some labels much more common than others
  * May require attention to rare labels

## Use Cases

* **Content tagging**: Monitor which tags are frequently applied
* **Image classification**: Track prevalence of different objects/scenes
* **Medical diagnosis**: Understand how often each symptom is predicted
* **Document categorization**: Monitor topic distribution
* **E-commerce**: Track frequency of product attributes
* **Content moderation**: Monitor prevalence of different violation types

## Analysis Examples

### Identifying Rare Labels

Labels with coverage ratio < 0.05 (5%) may be:
- Under-represented in training data
- Genuine rare events
- Candidates for specialized monitoring

### Detecting Data Drift

Significant changes in coverage ratios over time may indicate:
- Shifts in user behavior or input patterns
- Changes in upstream data sources
- Model retraining effects

### Capacity Planning

High coverage labels (>0.8) may require:
- More compute resources for downstream processing
- Specialized handling or routing logic
- Additional monitoring and alerting

## Relationship to Other Metrics

* **Label Coverage Ratio** measures label prevalence (% of inferences)
* **Multi-Label Class Count** measures absolute frequency (total count)
* **Multi-Label Prediction Volume** measures average labels per inference

Together, these metrics provide complementary views of label distribution:
- Coverage Ratio → How widespread is each label?
- Class Count → How many times does each label appear?
- Prediction Volume → How many labels per inference on average?
