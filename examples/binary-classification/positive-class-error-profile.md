

## Overview

The **Positive-Class Error Profile** bucket describes how your classifier makes mistakes on the _positive_ class across the score distribution. It focuses on:

* Where false positives and false negatives concentrate
* How error behavior changes as scores increase
* How much “bad” volume you get when you target a given positive-class segment

This bucket is most natural for **binary classification** but can be applied to **multiclass** by defining a _one-vs-rest_ positive class (e.g., “fraud” vs “not fraud”).

## Metrics

All metrics are defined in terms of the confusion-matrix counts within a segment (e.g., score bin, time bucket):

* `TP` – true positives
* `FP` – false positives
* `FN` – false negatives
* `TN` – true negatives  
  `Total = TP + FP + FN + TN`

**adjusted_false_positive_rate**  
False positive rate on _negative_ cases (optionally smoothed to avoid divide-by-zero):

```text
adjusted_false_positive_rate = FP / (FP + TN)
```

**bad_case_rate**  
Fraction of all cases that are **classified as bad** (prediction = 0):

```text
bad_case_rate = (FN + TN) / (TP + FP + FN + TN)
```

**false_positive_ratio**  
Share of predicted positive cases that are actually negative (how “dirty” your positive bucket is):

```text
false_positive_ratio = FP / (TP + FP)
```

**total_false_positive_rate**  
Fraction of _all_ cases that are false positives:

```text
total_false_positive_rate = FP / (TP + FP + FN + TN)
```

**overprediction_rate**  
Rate at which the model **over-predicts positives** relative to the negative population (conceptually FPR):

```text
overprediction_rate = FP / (FP + TN)
```

**underprediction_rate**  
Rate at which the model **under-predicts positives** (missed positives) relative to actual positives (FNR):

```text
underprediction_rate = FN / (TP + FN)
```

**valid_detection_rate**  
Overall fraction of correctly classified cases (global accuracy):

```text
valid_detection_rate = (TP + TN) / (TP + FP + FN + TN)
```

## Data Requirements

Your dataset must include:

* `{{label_col}}` – ground truth label (0/1 for binary; specific class for multiclass one-vs-rest)
* `{{score_col}}` – predicted probability or score for the positive class
* `{{timestamp_col}}` – event or prediction timestamp
* Optional: `{{weight_col}}` – sample weight (if used)

## Base Metric SQL

This SQL computes positive-class error profile metrics at a fixed threshold (default 0.5). It calculates various false positive rates, bad case rates, and detection rates per time bucket.

```sql
WITH counts AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    SUM(CASE WHEN {{ground_truth}} = 1 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END) AS tp,
    SUM(CASE WHEN {{ground_truth}} = 0 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END) AS fp,
    SUM(CASE WHEN {{ground_truth}} = 0 AND {{prediction}} <  {{threshold}} THEN 1 ELSE 0 END) AS tn,
    SUM(CASE WHEN {{ground_truth}} = 1 AND {{prediction}} <  {{threshold}} THEN 1 ELSE 0 END) AS fn
  FROM {{dataset}}
  GROUP BY 1
),
prepared AS (
  SELECT
    bucket,
    tp::float AS tp,
    fp::float AS fp,
    tn::float AS tn,
    fn::float AS fn,
    (tp + fp + tn + fn)::float AS total,
    (tp + fp)::float          AS predicted_pos,
    (tp + fn)::float          AS actual_pos,
    (fp + tn)::float          AS negatives
  FROM counts
)
SELECT
  bucket AS bucket,

  -- Adjusted False Positive Rate: FP / negatives
  CASE WHEN negatives > 0 THEN fp / negatives ELSE 0 END
    AS adjusted_false_positive_rate,

  -- Bad Case Rate: actual "bad" cases / total
  CASE WHEN total > 0 THEN (tp + fn) / total ELSE 0 END
    AS bad_case_rate,

  -- False Positive Ratio: FP / total
  CASE WHEN total > 0 THEN fp / total ELSE 0 END
    AS false_positive_ratio,

  -- Valid Detection Rate: (TP + TN) / total
  CASE WHEN total > 0 THEN (tp + tn) / total ELSE 0 END
    AS valid_detection_rate,

  -- Overprediction: (predicted_pos - actual_pos) / total, floored at 0
  CASE WHEN total > 0 THEN GREATEST((predicted_pos - actual_pos) / total, 0)
       ELSE 0 END
    AS overprediction_rate,

  -- Underprediction: (actual_pos - predicted_pos) / total, floored at 0
  CASE WHEN total > 0 THEN GREATEST((actual_pos - predicted_pos) / total, 0)
       ELSE 0 END
    AS underprediction_rate,

  -- Total False Positive Rate: global FP / global total
  CASE WHEN SUM(total) OVER () > 0
       THEN SUM(fp) OVER () / SUM(total) OVER ()
       ELSE 0 END
    AS total_false_positive_rate

FROM prepared
ORDER BY bucket;
```

**What this query returns**

* `bucket` — timestamp bucket (1 day)
* `adjusted_false_positive_rate` — FP rate among negatives
* `bad_case_rate` — Fraction of cases classified as bad
* `false_positive_ratio` — False positives as fraction of all cases
* `valid_detection_rate` — Overall accuracy
* `overprediction_rate` — Rate of over-predicting positives
* `underprediction_rate` — Rate of under-predicting positives
* `total_false_positive_rate` — Global FP rate

## Plots

See the [charts](../charts/binary-classification/) folder for visualization examples:

* [Plot 1: FP & Bad Case Rates Over Time](../charts/binary-classification/fp-bad-case-rates-over-time.md)
* [Plot 2: Overprediction vs Underprediction](../charts/binary-classification/overprediction-vs-underprediction.md)
* [Plot 3: False Positive Ratio vs Valid Detection Rate](../charts/binary-classification/false-positive-ratio-vs-valid-detection-rate.md)

## Binary vs Multiclass

* **Binary:** use `label ∈ {0,1}` and `score` as the probability `p(y=1 | x)`.
* **Multiclass:** choose a `{{positive_class_value}}` and convert to one-vs-rest:

  ```sql
  CASE WHEN {{label_col}} = '{{positive_class_value}}' THEN 1 ELSE 0 END AS label
  ```

  Use the probability for that class as `score`. Repeat the metric for each class of interest.

## Use Cases

* Risk scoring (fraud, credit, abuse detection)
* Triage models where analysts work the top-scoring cases
* Any binary decisioning system with high cost asymmetry between FP and FN
