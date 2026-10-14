# Reliability Diagram Bins

## Overview

This metric reports, for each **score bin**, the model's mean predicted probability and the observed positive rate. Plotted against each other they form a **reliability diagram** (calibration curve): a perfectly calibrated model lies on the diagonal, an over-confident model sits below it at high scores, and an under-confident model sits above it.

It is the dimensioned companion to the [Calibration Profile](calibration-profile.md): where that metric summarizes calibration in one number per bucket (ratio, ECE, MCE), this one shows **where** in the score range the miscalibration lives, and **how much traffic** each bin carries.

It produces, per time bucket and per `score_bin` dimension:

* **predicted_rate** — mean predicted probability in the bin
* **observed_rate** — observed positive rate in the bin
* **calibration_gap** — predicted − observed (positive = over-prediction)
* **bin_share** — share of predictions falling in the bin
* **bin_count** — number of predictions in the bin

## Data Requirements

* `{{timestamp_col}}` — timestamp of the prediction
* `{{score_col}}` — predicted probability in [0, 1]
* `{{label_col}}` — binary outcome (0/1 or boolean)
* `{{n_bins}}` — number of equal-width score bins (literal)
* `{{dataset}}` — dataset containing the predictions

## Base Metric SQL

This SQL assigns each prediction to an equal-width score bin and reports per-bin predicted and observed rates, using the bin label as a dimension.

```sql
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{score_col}}::float                              AS score,
      {{label_col}}::int::float                         AS label
    FROM
      {{dataset}}
    WHERE
      {{timestamp_col}} IS NOT NULL
      AND {{score_col}} IS NOT NULL
      AND {{label_col}} IS NOT NULL
      AND {{score_col}} >= 0
      AND {{score_col}} <= 1
  ),

  binned AS (
    SELECT
      ts,
      score,
      label,
      LEAST(FLOOR(score * {{n_bins}}), {{n_bins}} - 1)::int AS bin_index
    FROM
      base
  ),

  per_bin AS (
    SELECT
      ts,
      bin_index,
      COUNT(*)::float AS n,
      AVG(score)      AS avg_score,
      AVG(label)      AS observed_rate
    FROM
      binned
    GROUP BY
      ts,
      bin_index
  ),

  per_bucket AS (
    SELECT
      ts,
      SUM(n) AS n_total
    FROM
      per_bin
    GROUP BY
      ts
  )

SELECT
  b.ts,
  -- Dimension: human-readable bin label, e.g. "0.1-0.2"
  ROUND((b.bin_index::numeric) / {{n_bins}}, 2)::text
    || '-'
    || ROUND(((b.bin_index + 1)::numeric) / {{n_bins}}, 2)::text   AS score_bin,
  b.avg_score                                                     AS predicted_rate,
  b.observed_rate                                                 AS observed_rate,
  (b.avg_score - b.observed_rate)                                 AS calibration_gap,
  b.n / NULLIF(t.n_total, 0)                                      AS bin_share,
  b.n                                                             AS bin_count
FROM
  per_bin b
  JOIN per_bucket t ON t.ts = b.ts
ORDER BY
  b.ts,
  b.bin_index;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `score_bin` — bin label such as `0.1-0.2` (dimension)
* `predicted_rate` — mean predicted probability in the bin
* `observed_rate` — observed positive rate in the bin
* `calibration_gap` — `predicted_rate − observed_rate`
* `bin_share` — share of the bucket's predictions in this bin (0 to 1)
* `bin_count` — number of predictions in the bin

Bins with no predictions in a bucket are not emitted.

## Aggregate Arguments

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Timestamp of the prediction.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Score Column

1. **Parameter Key:** `score_col`
2. **Friendly Name:** `Predicted Probability Column`
3. **Description:** `Model's predicted probability of the positive outcome, in [0, 1].`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `prediction, continuous`
8. **Allowed Column Types:** `float`

### Argument 3 — Label Column

1. **Parameter Key:** `label_col`
2. **Friendly Name:** `Outcome Column`
3. **Description:** `Binary outcome: 1/true if the event happened, else 0/false.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `ground_truth`
8. **Allowed Column Types:** `int, bool`

### Argument 4 — Number of Bins

1. **Parameter Key:** `n_bins`
2. **Friendly Name:** `Number of Bins`
3. **Description:** `Number of equal-width score bins. 10 gives deciles; 20 gives finer resolution at the cost of noisier sparse bins.`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Integer`
6. **Default Value:** `10`

### Argument 5 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Predicted Rate by Bin

1. **Metric Name:** `reliability_predicted_rate`
2. **Description:** `Mean predicted probability within each score bin`
3. **Value Column:** `predicted_rate`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `score_bin`

### Metric 2 — Observed Rate by Bin

1. **Metric Name:** `reliability_observed_rate`
2. **Description:** `Observed positive rate within each score bin`
3. **Value Column:** `observed_rate`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `score_bin`

### Metric 3 — Calibration Gap by Bin

1. **Metric Name:** `reliability_calibration_gap`
2. **Description:** `Predicted rate minus observed rate within each score bin (positive = over-prediction)`
3. **Value Column:** `calibration_gap`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `score_bin`

### Metric 4 — Bin Share

1. **Metric Name:** `reliability_bin_share`
2. **Description:** `Share of predictions that fall in each score bin`
3. **Value Column:** `bin_share`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `score_bin`

### Metric 5 — Bin Count

1. **Metric Name:** `reliability_bin_count`
2. **Description:** `Number of predictions in each score bin`
3. **Value Column:** `bin_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `score_bin`

## Plots

See the [charts](../../charts/ranking/) folder for visualization examples:

* [Reliability Diagram](../../charts/ranking/reliability-diagram.md)
* [Calibration Gap by Score Bin](../../charts/ranking/calibration-gap-by-bin.md)

## Interpreting the Metric

### Reading the diagram

* **Points on the diagonal** (`observed_rate ≈ predicted_rate`) — calibrated in that bin
* **Points below the diagonal at high scores** — over-confidence: the model says 60% but only 30% happen. In ads this bin is over-bid.
* **Points above the diagonal at low scores** — under-confidence in the long tail; common when the training set down-samples negatives without re-weighting
* **S-shaped curve** — probabilities are compressed toward the mean; a monotone recalibration (Platt or isotonic) usually fixes it

### Use bin_share before reacting

Sparse bins swing wildly. On click models most traffic lands in the lowest one or two bins, and a bin with a handful of predictions can show a gap of 0.5 by chance. Alert on gaps only in bins whose `bin_share` is meaningful (for example above 1%), or aggregate with the ECE from the Calibration Profile.

### Trends to watch

* **Gap grows in the top bins only** — the model is becoming over-confident on its best candidates; expect over-bidding on premium inventory
* **Share shifts toward higher bins while observed rates do not move** — the score distribution inflated; usually a model deployment or a feature pipeline change
* **Gap sign flips across a deployment** — the new model's calibration differs from the old; recalibrate or adjust bid multipliers

## Use Cases

* Diagnosing **which score range** is driving a calibration-ratio or ECE alert
* Deciding whether to apply a **global bid multiplier** (uniform gap) or a **recalibration layer** (gap varies by bin)
* Comparing calibration curves between **surfaces or model versions** by filtering the dataset or adding a dimension
* Reviewing probability quality for **risk models** where pricing depends on specific score bands

## Relationship to Other Metrics

* **Calibration Profile** summarizes these bins into ratio, ECE and MCE
* **Numeric distribution of the score** (platform default) shows how scores are spread but not whether they are correct
* **Log Loss** penalizes the same over-confidence but cannot say where it occurs
