## Overview

The **Detection & Acceptance Profile** bucket characterizes how your model’s **detection power** and **acceptance behavior** change as you move the decision threshold on the positive-class score.

It answers questions like:

* “If I tighten my threshold to reduce volume, how much recall do I lose?”
* “Where is the best operating point to balance business capacity and risk?”

This bucket supports:

* **Binary classification**, directly on the positive-class score
* **Multiclass classification**, via per-class one-vs-rest profiles

## Metrics

Let `TP`, `FP`, `FN`, `TN` be computed at a given threshold, with `Total = TP + FP + FN + TN`.

**capture_rate**  
Fraction of the population that the model “captures” as positive (acceptance volume):

```text
capture_rate = (TP + FP) / Total
```

**correct_detection_rate**  
Overall fraction of correct decisions (global accuracy):

```text
correct_detection_rate = (TP + TN) / Total
```

**true_detection_rate**  
Quality of the accepted positives, i.e., precision:

```text
true_detection_rate = TP / (TP + FP)
```

**true_positive_rate**  
Classic recall / TPR:

```text
true_positive_rate = TP / (TP + FN)
```

**correct_acceptance_rate**  
Fraction of all cases that are **correctly accepted** as positive:

```text
correct_acceptance_rate = TP / Total
```

**valid_detection_rate**  
Same quantity as accuracy but used explicitly in plots with “acceptance”:

```text
valid_detection_rate = (TP + TN) / Total
```

> You can compute all of these from a single confusion matrix per threshold and bucket.

## Data Requirements

* `{{label_col}}` – ground truth binary label (or per-class label for multiclass)
* `{{score_col}}` – predicted probability or score for the positive class
* `{{timestamp_col}}` – event or prediction time

## Base Metric SQL

This SQL computes detection and acceptance metrics at a fixed threshold (default 0.5). It calculates capture rate, precision, recall, and accuracy per time bucket.

```sql
WITH counts AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    SUM(
      CASE WHEN {{ground_truth}} = 1 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END
    )::float AS tp,
    SUM(
      CASE WHEN {{ground_truth}} = 0 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END
    )::float AS fp,
    SUM(
      CASE WHEN {{ground_truth}} = 0 AND {{prediction}} < {{threshold}} THEN 1 ELSE 0 END
    )::float AS tn,
    SUM(
      CASE WHEN {{ground_truth}} = 1 AND {{prediction}} < {{threshold}} THEN 1 ELSE 0 END
    )::float AS fn
  FROM
    {{dataset}}
  GROUP BY
    1
),
prepared AS (
  SELECT
    bucket,
    tp,
    fp,
    tn,
    fn,
    (tp + tn + fp + fn) AS total,
    (tp + fn)           AS pos_total,   -- actual positives (Recall/TPR denominator)
    (tn + fp)           AS neg_total,   -- actual negatives (Specificity denominator)
    (tp + fp)           AS prec_total   -- predicted positives (Precision denominator)
  FROM
    counts
)
SELECT
  bucket as bucket,

  -- Capture Rate: proportion of actual positives correctly identified
  CASE
    WHEN pos_total > 0 THEN tp / pos_total
    ELSE 0
  END AS capture_rate,

  -- Correct Detection Rate: correctly detected cases out of all cases
  CASE
    WHEN total > 0 THEN tp / total
    ELSE 0
  END AS correct_detection_rate,

  -- True Positive Rate (Recall): actual positives correctly classified as positives
  CASE
    WHEN pos_total > 0 THEN tp / pos_total
    ELSE 0
  END AS true_positive_rate,

  -- True Detection Rate: proportion of actual positives correctly identified
  CASE
    WHEN pos_total > 0 THEN tp / pos_total
    ELSE 0
  END AS true_detection_rate,

  -- Precision: true positives among all predicted positives
  CASE
    WHEN prec_total > 0 THEN tp / prec_total
    ELSE 0
  END AS precision,

  -- Correct Acceptance Rate: correctly accepted cases out of all cases
  CASE
    WHEN total > 0 THEN tn / total
    ELSE 0
  END AS correct_acceptance_rate,

  -- Valid Detection Rate: valid cases correctly detected (accuracy)
  CASE
    WHEN total > 0 THEN (tp + tn) / total
    ELSE 0
  END AS valid_detection_rate

FROM
  prepared
ORDER BY
  bucket;
```

**What this query returns**

* `bucket` — timestamp bucket (1 day)
* `capture_rate` — Fraction of population captured as positive
* `correct_detection_rate` — Overall correct decisions
* `true_positive_rate` — Recall / TPR
* `true_detection_rate` — Precision among positives
* `precision` — Precision (TP / predicted positives)
* `correct_acceptance_rate` — Correctly accepted cases
* `valid_detection_rate` — Overall accuracy

## Plots

See the [charts](../charts/binary-classification/) folder for visualization examples:

* [Plot 1: Recall Variants Over Time](../charts/binary-classification/recall-variants-over-time.md)
* [Plot 2: Acceptance + Accuracy](../charts/binary-classification/acceptance-accuracy.md)
* [Plot 3: Detection vs Acceptance Trade-Off](../charts/binary-classification/detection-vs-acceptance-tradeoff.md)

## Binary vs Multiclass

* **Binary:** use the natural positive class and its probability as `score`.
* **Multiclass:** for each class `c` of interest:
  * Define `label = 1` when the ground truth label is `c`, else 0.
  * Use the model's predicted probability for class `c` as `score`.
  * Compute a Detection & Acceptance profile per class.
