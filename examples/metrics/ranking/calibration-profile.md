# Calibration Profile

## Overview

The **Calibration Profile** bucket checks whether a model's predicted probabilities are **honest**: when the model says 10%, does the event happen about 10% of the time? It is the day-to-day calibration monitor used by ads and recommendation teams, where predicted click-through or conversion rates feed directly into **bids, expected-value ranking, budget pacing, and reporting**. A model can keep a perfect ranking order while its probabilities drift, and that drift silently changes every downstream number.

It produces:

* **calibration_ratio** — total predicted positives divided by total observed positives (1.0 = perfectly calibrated in aggregate, > 1 over-predicts, < 1 under-predicts)
* **expected_calibration_error (ECE)** — volume-weighted average gap between predicted and observed rates across score bins
* **max_calibration_error (MCE)** — the worst single bin's gap
* **avg_predicted_probability** and **observed_positive_rate** — the two sides of the ratio, for context
* **prediction_count** — volume

Pair it with [Reliability Diagram Bins](reliability-diagram-bins.md), which reports the per-bin breakdown as a dimensioned metric.

This metric applies to **any binary probability** (click, conversion, fraud, default), not only to ranking systems.

## Metrics

Let `score ∈ [0, 1]` be the predicted probability and `label ∈ {0, 1}` the outcome. Predictions are split into `n_bins` equal-width bins on the score, `[i/n, (i+1)/n)`, with the top bin closed at 1.

**calibration_ratio**

```text
calibration_ratio = Σ score / Σ label
```

**expected_calibration_error**

```text
ECE = Σ_b (n_b / N) · | mean_score_b − observed_rate_b |
```

**max_calibration_error**

```text
MCE = max_b | mean_score_b − observed_rate_b |
```

## Data Requirements

* `{{timestamp_col}}` — timestamp of the prediction
* `{{score_col}}` — predicted probability in [0, 1]
* `{{label_col}}` — binary outcome (0/1 or boolean)
* `{{n_bins}}` — number of equal-width score bins (literal, typically 10 or 20)
* `{{dataset}}` — dataset containing the predictions

## Base Metric SQL

This SQL bins predictions by score, then derives the calibration ratio, ECE and MCE per time bucket.

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

  -- Assign each prediction to an equal-width score bin [i/n, (i+1)/n)
  binned AS (
    SELECT
      ts,
      score,
      label,
      LEAST(FLOOR(score * {{n_bins}}), {{n_bins}} - 1)::int AS bin_index
    FROM
      base
  ),

  -- Per bin: volume, mean predicted probability, observed positive rate
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
  )

SELECT
  ts,
  -- Overall calibration ratio: total predicted positives / total observed positives
  SUM(n * avg_score) / NULLIF(SUM(n * observed_rate), 0)              AS calibration_ratio,
  -- Expected Calibration Error: volume-weighted |predicted - observed| across bins
  SUM(n * ABS(avg_score - observed_rate)) / NULLIF(SUM(n), 0)         AS expected_calibration_error,
  -- Maximum Calibration Error: worst single bin
  MAX(ABS(avg_score - observed_rate))                                 AS max_calibration_error,
  SUM(n * avg_score) / NULLIF(SUM(n), 0)                              AS avg_predicted_probability,
  SUM(n * observed_rate) / NULLIF(SUM(n), 0)                          AS observed_positive_rate,
  SUM(n)                                                              AS prediction_count
FROM
  per_bin
GROUP BY
  ts
ORDER BY
  ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `calibration_ratio` — Σ predicted / Σ observed (1.0 is ideal)
* `expected_calibration_error` — volume-weighted mean |predicted − observed| across bins (0 is ideal)
* `max_calibration_error` — largest per-bin gap (0 is ideal)
* `avg_predicted_probability` — mean score in the bucket
* `observed_positive_rate` — mean label in the bucket
* `prediction_count` — rows evaluated

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
3. **Description:** `Model's predicted probability of the positive outcome, in [0, 1] (e.g. pCTR, pCVR).`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `prediction, continuous`
8. **Allowed Column Types:** `float`

### Argument 3 — Label Column

1. **Parameter Key:** `label_col`
2. **Friendly Name:** `Outcome Column`
3. **Description:** `Binary outcome: 1/true if the event happened (click, conversion), else 0/false.`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `ground_truth`
8. **Allowed Column Types:** `int, bool`

### Argument 4 — Number of Bins

1. **Parameter Key:** `n_bins`
2. **Friendly Name:** `Number of Bins`
3. **Description:** `Number of equal-width score bins used for ECE and MCE.`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Integer`
6. **Default Value:** `10`

### Argument 5 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

## Reported Metrics

### Metric 1 — Calibration Ratio

1. **Metric Name:** `calibration_ratio`
2. **Description:** `Sum of predicted probabilities divided by sum of observed positives (1.0 = calibrated)`
3. **Value Column:** `calibration_ratio`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 2 — Expected Calibration Error

1. **Metric Name:** `expected_calibration_error`
2. **Description:** `Volume-weighted mean absolute gap between predicted and observed rates across score bins`
3. **Value Column:** `expected_calibration_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 3 — Maximum Calibration Error

1. **Metric Name:** `max_calibration_error`
2. **Description:** `Largest absolute gap between predicted and observed rate in any score bin`
3. **Value Column:** `max_calibration_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 4 — Average Predicted Probability

1. **Metric Name:** `avg_predicted_probability`
2. **Description:** `Mean predicted probability in the bucket`
3. **Value Column:** `avg_predicted_probability`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 5 — Observed Positive Rate

1. **Metric Name:** `observed_positive_rate`
2. **Description:** `Observed rate of the positive outcome in the bucket`
3. **Value Column:** `observed_positive_rate`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

### Metric 6 — Prediction Count

1. **Metric Name:** `calibration_prediction_count`
2. **Description:** `Number of predictions evaluated in the bucket`
3. **Value Column:** `prediction_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

## Plots

See the [charts](../../charts/ranking/) folder for visualization examples:

* [Calibration Ratio Over Time](../../charts/ranking/calibration-ratio-over-time.md)
* [Expected Calibration Error Over Time](../../charts/ranking/expected-calibration-error-over-time.md)
* [Reliability Diagram](../../charts/ranking/reliability-diagram.md) (uses Reliability Diagram Bins)

## Interpreting the Metric

### Calibration ratio

* **0.95 – 1.05** — well calibrated in aggregate; bids and expected-value estimates can be trusted
* **> 1.05** — over-prediction. In ads this means **over-bidding** and inflated forecasts; in recommendations it inflates expected engagement
* **< 0.95** — under-prediction: **under-bidding**, lost auctions, and under-stated forecasts
* A ratio of 1.0 can still hide offsetting errors (over-predicting low scores while under-predicting high ones). That is what ECE catches.

### ECE and MCE

* **ECE < 0.01** — excellent; **0.01 – 0.03** — acceptable for most ad systems; **> 0.05** — investigate
* **MCE** is driven by the worst bin, usually a sparsely populated high-score bin. A high MCE with a low ECE means a small slice of confident predictions is wrong; check the per-bin `bin_share` in the Reliability Diagram before reacting.
* ECE depends on `n_bins`. Keep it fixed when comparing over time.

### Trends to watch

* **Ratio drifts up or down steadily** — base-rate shift (seasonality, a new traffic source, a new placement) that the model has not been retrained for
* **Step change in ratio at a deployment** — the new model's scores are on a different scale; common after changing negative sampling or loss weighting
* **ECE rises while ratio stays near 1** — the model is becoming less discriminating in its probabilities (compressing toward the mean) or over-confident at the tails
* **Observed positive rate changes but predicted does not** — the model is stale; the environment moved and the scores did not follow

### Caveats

* Delayed labels (conversions that arrive days after the impression) make recent buckets look **under**-converted and the ratio look **high**. Compare only buckets whose labels have matured.
* If scores are position-dependent (a pCTR model that includes position as a feature), calibration should hold per position as well as overall. Segment by position or placement when debugging.

## Use Cases

* **Ad auctions** — a calibration ratio alert is often the first signal that a pCTR/pCVR model is over- or under-bidding
* **Expected-value ranking** — recommenders that rank by `p(click) × value` rely on the probabilities being comparable across items and surfaces
* **Budget pacing and forecasting** — predicted-rate drift propagates directly into spend and revenue forecasts
* **Model deployment checks** — compare the ratio and ECE of a challenger against the incumbent before switching traffic
* **Risk and fraud models** — the same metric validates probability-of-default or probability-of-fraud scores used in pricing

## Relationship to Other Metrics

* **Log Loss** is a proper scoring rule that mixes calibration and discrimination; the Calibration Profile isolates the calibration component and is easier to act on
* **AUC / Gini / NDCG** measure ordering and are blind to a uniform scale shift; a model can be perfectly ranked and badly calibrated
* **Reliability Diagram Bins** provides the per-bin detail behind ECE and MCE
* **PSI on the score column** detects distribution shift in predictions, but not whether the new distribution is correct; the calibration ratio answers that
