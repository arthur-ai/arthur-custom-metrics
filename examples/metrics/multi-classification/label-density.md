# Label Density

## Overview

This metric tracks the **average number of predicted labels per inference normalized by the total possible labels** in multi-label classification models. It helps monitor:

* How "dense" or "sparse" predictions are (0 to 1 scale)
* Whether model uses a small or large portion of available labels
* Changes in label usage patterns over time
* Model behavior relative to label catalog size

**Formula**: Label Density = (Average labels per inference) / (Total unique labels in catalog)

**Range**:
* 0 = No labels predicted
* 1 = Every possible label predicted on average (rarely achieved)
* Typical values: 0.05-0.30 for most multi-label tasks

This metric is particularly useful when working with fixed label catalogs (10-100 labels) to understand how much of the label space is being utilized.

## Data Requirements

* `{{timestamp_col}}` — timestamp of the inference
* `{{row_id_col}}` — unique identifier for each inference row
* `{{pred_labels_col}}` — array/list of predicted labels
* `{{dataset}}` — dataset containing the inferences

## Base Metric SQL

This SQL calculates the average number of labels per inference, divided by the total distinct labels observed in the dataset.

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
  total_label_catalog AS (
    SELECT
      COUNT(DISTINCT label)::float AS total_labels
    FROM
      base
      CROSS JOIN LATERAL (
        SELECT
          unnest(COALESCE(pred_labels, ARRAY[]::TEXT[])) AS label
      ) u
    WHERE
      label IS NOT NULL
      AND label <> ''
  ),
  per_row AS (
    SELECT
      ts,
      row_id,
      COALESCE(array_length(pred_labels, 1), 0)::float AS label_count
    FROM
      base
  ),
  avg_per_bucket AS (
    SELECT
      ts,
      AVG(label_count) AS avg_labels
    FROM
      per_row
    GROUP BY
      1
  )
SELECT
  a.ts AS ts,
  a.avg_labels / NULLIF(c.total_labels, 0) AS label_density
FROM
  avg_per_bucket a
  CROSS JOIN total_label_catalog c
ORDER BY
  ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `label_density` — ratio of average labels per inference to total possible labels (0 to 1)

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

1. **Parameter Key:** `pred_labels_col`
2. **Friendly Name:** `Pred_Labels_Col`
3. **Description:** `Column parameter: pred_labels_col`
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

### Metric 1 — Label Density

1. **Metric Name:** `label_density`
2. **Description:** `Average labels per inference divided by total possible labels`
3. **Value Column:** `label_density`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

## Interpreting the Metric

### Density Values

* **Very sparse (0.0-0.1)**
  * Model uses only a small fraction of available labels
  * Typical for specialized classification tasks
  * Example: 2 labels used on average from 50 total labels
  * May indicate many rare/unused labels in catalog

* **Sparse (0.1-0.3)**
  * Model uses a modest portion of label catalog
  * Typical for most multi-label classification tasks
  * Example: 5 labels used on average from 30 total labels
  * Healthy balance of common and rare labels

* **Moderate (0.3-0.6)**
  * Model uses a significant portion of label catalog
  * Dense predictions with many labels per inference
  * Example: 8 labels used on average from 20 total labels
  * May indicate comprehensive tagging tasks

* **Dense (0.6-1.0)**
  * Model uses most available labels
  * Very dense predictions
  * Rare - may indicate every-inference default labels
  * Check if some labels are over-applied

### Trends Over Time

* **Increasing density**
  * Model predicting more labels per inference
  * Expanding use of label catalog
  * May indicate model becoming more comprehensive
  * Could also indicate over-prediction issues

* **Decreasing density**
  * Model becoming more selective
  * Using fewer labels from catalog
  * May indicate increased precision
  * Could also signal under-prediction problems

* **Stable density**
  * Consistent label usage patterns
  * Expected in steady-state production
  * Monitor for sudden changes

## Example Calculations

**Example 1: Sparse Classification**
- Total labels in catalog: 50
- Average labels per inference: 2
- Label Density: 2/50 = **0.04 (4%)**
- Interpretation: Very sparse, specialized task

**Example 2: Moderate Classification**
- Total labels in catalog: 20
- Average labels per inference: 5
- Label Density: 5/20 = **0.25 (25%)**
- Interpretation: Typical multi-label task

**Example 3: Dense Classification**
- Total labels in catalog: 10
- Average labels per inference: 7
- Label Density: 7/10 = **0.70 (70%)**
- Interpretation: Very dense predictions

## Relationship to Other Metrics

* **Multi-Label Prediction Volume**: Absolute count (avg labels per inference)
* **Label Density**: Normalized version (relative to catalog size)
* **Label Coverage Ratio**: Per-label prevalence (% of inferences with each label)

**Use together**:
- Prediction Volume → How many labels on average?
- Label Density → What % of catalog is used?
- Coverage Ratio → Which specific labels are common?

## Use Cases

* **Catalog utilization**: Understand how much of label space is actually used
* **Model behavior monitoring**: Track if model becomes more/less selective
* **Comparison across systems**: Compare models with different catalog sizes
* **Label catalog management**: Identify if catalog is too large for task
* **Sparsity analysis**: Understand prediction density patterns
* **Threshold tuning**: See impact of threshold changes on density

## Analysis Examples

### High Density with Low Performance
- Model predicting too many labels per inference
- Over-prediction problem
- Consider raising prediction threshold

### Low Density with Many Rare Labels
- Large catalog with many unused labels
- Consider catalog cleanup
- Focus on commonly used labels

### Increasing Density Over Time
- If performance improves: Model learning to be comprehensive
- If performance declines: Model over-predicting, needs tuning

### Density Varies by Data Segment
- Some data types naturally denser than others
- Expected variation, not necessarily a problem

## Auto-Detection of Label Catalog

This metric automatically detects the total label catalog size by:
1. Finding all distinct labels that appear in predictions
2. Counting them across the entire dataset
3. Using this count as the denominator

**Note**: This approach:
- ✅ Adapts to actual label usage
- ✅ No configuration needed
- ✅ Works with evolving catalogs
- ⚠️ Only counts labels that are predicted (misses never-predicted labels)
- ⚠️ Changes if new labels appear in predictions

## Typical Values by Domain

* **Image tagging** (many possible tags): 0.05-0.15
* **Document classification** (topic categories): 0.10-0.25
* **Medical coding** (symptoms/conditions): 0.03-0.10
* **Content moderation** (violation types): 0.05-0.20
* **Product attributes** (features/specs): 0.15-0.35

*Actual values depend on task complexity and catalog size*
