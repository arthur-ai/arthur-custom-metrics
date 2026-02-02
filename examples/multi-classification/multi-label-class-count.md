# Multi-Label Classification Count by Class Label

## Overview

This metric tracks the **count of predictions for each individual class label over time** in multi-label classification models. It helps monitor:

* How frequently each class appears in predictions
* Class distribution and imbalance patterns over time
* Which labels are most/least commonly predicted
* Shifts in label popularity or model behavior

This is useful for multi-label classification where each input can have multiple predicted labels, and you want to understand the distribution across all possible labels (e.g., tracking which tags are most used, which symptoms are most commonly predicted).

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{row_id_col}}` — unique identifier for each inference row
* `{{labels_array_col}}` — array/list of predicted labels
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL explodes the label arrays, counts occurrences of each unique label, and aggregates by day.

```sql
WITH
  base AS (
    SELECT
      time_bucket (INTERVAL '1 day', {{timestamp_col}}) AS bucket,
      {{row_id_col}}::text AS row_id,
      {{labels_array_col}} AS labels
    FROM
      {{dataset}}
    WHERE
      {{timestamp_col}} IS NOT NULL
      AND {{labels_array_col}} IS NOT NULL
  ),
  exploded AS (
    SELECT
      bucket,
      row_id,
      lbl AS label
    FROM
      base
      CROSS JOIN LATERAL (
        SELECT DISTINCT
          unnest(labels) AS lbl
      ) u
    WHERE
      lbl IS NOT NULL
      AND lbl <> ''
  ),
  counts AS (
    SELECT
      bucket AS ts,
      label AS series,
      COUNT(*)::float AS value
    FROM
      exploded
    GROUP BY
      1,
      2
  )
SELECT
  ts,
  series,
  value AS class_count
FROM
  counts
ORDER BY
  ts,
  series;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `series` — the class label name (dimension)
* `class_count` — count of predictions containing this label

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

### Argument 3 — Labels Array Column

1. **Parameter Key:** `labels_array_col`
2. **Friendly Name:** `Labels_Array_Col`
3. **Description:** `Column parameter: labels_array_col`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `prediction`

### Argument 4 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Class Count

1. **Metric Name:** `class_count`
2. **Description:** `Count of predictions containing each class label`
3. **Value Column:** `class_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `series`

## Interpreting the Metric

* **High count for specific labels**
  * These labels are frequently predicted
  * May indicate common patterns in your data
  * Could reveal model bias toward certain classes

* **Low count for specific labels**
  * These labels are rarely predicted
  * May indicate rare events or underrepresented classes
  * Could signal potential training data imbalance

* **Changing distribution over time**
  * Shifts in which labels are most common
  * May indicate data drift or changing user behavior
  * Could reveal seasonal patterns or trends

* **Sudden spikes or drops**
  * Unusual prediction behavior for specific labels
  * May indicate model issues or data quality problems
  * Could signal changes in input data distribution

## Use Cases

* Multi-label image tagging (tracking which tags are most common)
* Document categorization (monitoring category distribution)
* Medical diagnosis (tracking symptom frequency)
* Content moderation (monitoring violation type distribution)
* E-commerce product tagging (tracking attribute popularity)
* Multi-topic text classification (understanding topic distribution)
