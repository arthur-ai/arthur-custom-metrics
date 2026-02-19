# Log Loss

## Overview

**Log Loss** (also known as logarithmic loss or cross-entropy loss) is a probabilistic metric that evaluates the quality of predicted probabilities by measuring how close they are to actual outcomes. Unlike accuracy metrics that only assess whether predictions are correct or incorrect, log loss quantifies prediction confidence—heavily penalizing confident wrong predictions while rewarding well-calibrated probability estimates. This makes it essential for applications where understanding "how sure" the model is matters as much as the prediction itself.

**Key Insights:**
- Evaluates probability calibration, not just classification correctness
- Lower values indicate better calibrated models (0 = perfect, higher = worse)
- Penalizes overconfident wrong predictions severely
- Rewards honest, well-calibrated probability estimates
- Proper scoring rule: incentivizes models to output true probabilities
- Sensitive to miscalibration even when accuracy remains unchanged

**When to Use:**
- **Confidence-based workflows**: Fraud detection where 95% probability triggers blocking but 55% triggers manual review
- **Risk assessment**: Credit scoring where probabilities determine interest rates and loan terms
- **Model selection**: Comparing calibration quality across candidate models
- **Production monitoring**: Detecting probability drift and miscalibration over time
- **Regulatory compliance**: Demonstrating probability reliability for risk models
- **Threshold optimization**: Understanding confidence distribution for decision boundaries
- **A/B testing**: Evaluating which model produces more reliable probabilities

***

## Step 1: Write the SQL

This SQL computes log loss for binary classification by measuring the cross-entropy between predicted probabilities and actual labels.

```sql
WITH
  valid_predictions AS (
    -- Filter to valid predictions with probabilities in [0,1] range
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_prob_col}}::float AS predicted_prob,
      {{ground_truth_col}}::int AS actual_label
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
      AND {{prediction_prob_col}} IS NOT NULL
      AND {{ground_truth_col}} IS NOT NULL
      -- Ensure probability is in valid range [0,1]
      AND {{prediction_prob_col}} >= 0.0
      AND {{prediction_prob_col}} <= 1.0
  ),

  clipped_predictions AS (
    -- Apply epsilon smoothing to prevent log(0) = -∞
    -- Clip probabilities to [epsilon, 1-epsilon] range
    SELECT
      ts,
      actual_label,
      -- Clip predicted probability away from 0 and 1 to prevent numerical issues
      GREATEST({{epsilon}}, LEAST(1.0 - {{epsilon}}, predicted_prob)) AS prob_clipped,
      predicted_prob AS prob_original
    FROM valid_predictions
  ),

  log_loss_per_sample AS (
    -- Calculate log loss for each individual prediction
    -- Formula: -[y*ln(p) + (1-y)*ln(1-p)]
    SELECT
      ts,
      actual_label,
      prob_clipped,
      prob_original,
      -- Log loss calculation
      CASE
        WHEN actual_label = 1 THEN
          -- When actual is positive (1): -ln(p)
          -LN(prob_clipped)
        ELSE
          -- When actual is negative (0): -ln(1-p)
          -LN(1.0 - prob_clipped)
      END AS sample_log_loss
    FROM clipped_predictions
  )

-- Aggregate to get average log loss per day
SELECT
  ts,
  AVG(sample_log_loss)::float AS log_loss,
  COUNT(*)::int AS total_predictions,
  AVG(prob_original)::float AS avg_predicted_probability,
  SUM(CASE WHEN actual_label = 1 THEN 1 ELSE 0 END)::int AS positive_class_count,
  SUM(CASE WHEN actual_label = 0 THEN 1 ELSE 0 END)::int AS negative_class_count
FROM log_loss_per_sample
GROUP BY ts
ORDER BY ts;
```

**What this query returns:**

* `ts` — timestamp bucket (1 day)
* `log_loss` — average log loss across all predictions (float, lower is better, 0 = perfect)
* `total_predictions` — total number of valid predictions evaluated (integer)
* `avg_predicted_probability` — average predicted probability for positive class (float, 0-1)
* `positive_class_count` — number of actual positive labels (integer)
* `negative_class_count` — number of actual negative labels (integer)

**SQL Logic:**

1. **valid_predictions CTE**:
   - Filters NULL values in timestamp, probability, and label columns
   - Validates probabilities are in [0,1] range (excludes invalid probabilities)
   - Casts probability to float and label to int for consistent calculation
   - Groups by daily time buckets using `time_bucket(INTERVAL '1 day', ...)`

2. **clipped_predictions CTE**:
   - Applies epsilon smoothing to prevent `log(0) = -∞` errors
   - Clips probabilities to `[epsilon, 1-epsilon]` range (e.g., `[1e-15, 1-1e-15]`)
   - Preserves original probabilities for reporting
   - Critical for numerical stability when model outputs extreme probabilities (0.0 or 1.0)

3. **log_loss_per_sample CTE**:
   - Calculates log loss for each individual prediction using binary cross-entropy formula
   - **For actual positive (y=1)**: `log_loss = -ln(p)` — penalizes low probabilities for true positives
   - **For actual negative (y=0)**: `log_loss = -ln(1-p)` — penalizes high probabilities for true negatives
   - Uses natural logarithm (`LN()`) function
   - Stores both clipped (for calculation) and original (for reporting) probabilities

4. **Final aggregation**:
   - `AVG(sample_log_loss)::float` computes mean log loss per day
   - `COUNT(*)::int` counts total predictions
   - `AVG(prob_original)::float` provides average predicted probability (calibration indicator)
   - Class distribution counts help identify imbalance issues
   - Groups by day for time-series tracking

**Key Features:**
- **Epsilon smoothing**: Configurable epsilon (default `1e-15`) prevents mathematical errors
- **Probability clipping**: Ensures numerical stability for extreme probabilities
- **Type safety**: Explicit float/int casting for Arthur metrics storage
- **Comprehensive metrics**: Returns log loss plus contextual information
- **Edge case handling**: Validates input ranges and handles NULL values

**Log Loss Interpretation:**
- **Perfect model predicting p=1.0 for y=1**: log_loss = -ln(1.0) = 0 (perfect)
- **Confident wrong prediction p=0.99 for y=0**: log_loss = -ln(0.01) ≈ 4.6 (severe penalty)
- **Random guess p=0.5 for any y**: log_loss = -ln(0.5) ≈ 0.693 (baseline)
- **Uncertain wrong p=0.55 for y=0**: log_loss = -ln(0.45) ≈ 0.8 (moderate penalty)

***

## Step 2: Fill Basic Information

When creating the custom metric in the Arthur UI:

1. **Name**:
   `Log Loss`

2. **Description** (optional but recommended):
   `Measures prediction confidence by calculating cross-entropy between predicted probabilities and actual labels. Lower values indicate better calibrated models. Values near 0 are excellent, values >0.693 are worse than random guessing. Essential for confidence-based decision workflows and probability calibration monitoring.`

***

## Step 3: Configure the Aggregate Arguments

You will set up five aggregate arguments to parameterize the SQL.

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Timestamp column for time-series bucketing and temporal analysis`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Predicted Probability Column

1. **Parameter Key:** `prediction_prob_col`
2. **Friendly Name:** `Predicted Probability Column`
3. **Description:** `Model's predicted probability for the positive class (float, range 0-1). Examples: fraud_score, approval_score, churn_probability`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `prediction`
8. **Allowed Column Types:** `float`

### Argument 3 — Ground Truth Label Column

1. **Parameter Key:** `ground_truth_col`
2. **Friendly Name:** `Ground Truth Label Column`
3. **Description:** `Actual outcome label (int or bool: 0/1 or false/true). Examples: is_fraud, is_approved, churned`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `ground_truth`
8. **Allowed Column Types:** `int, bool`

### Argument 4 — Epsilon (Smoothing Parameter)

1. **Parameter Key:** `epsilon`
2. **Friendly Name:** `Epsilon (Smoothing Parameter)`
3. **Description:** `Small value added to prevent log(0) = -∞ errors. Clips probabilities to [epsilon, 1-epsilon] range. Default: 1e-15 (recommended)`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Float`
6. **Default Value:** `1e-15`

**Epsilon Selection Guidance:**
- **1e-15 (default)**: Standard choice, minimal impact on log loss calculation
- **1e-10**: More conservative, slightly larger clipping boundary
- **1e-7**: Very conservative, may slightly inflate log loss for well-calibrated models
- **Trade-off**: Smaller epsilon = closer to true log loss but risks numerical instability

### Argument 5 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset containing predicted probabilities and ground truth labels`
4. **Parameter Type:** `Dataset`

***

## Step 4: Configure Reported Metrics

This metric reports five values for comprehensive calibration monitoring.

### Metric 1 — Log Loss

1. **Metric Name:** `log_loss`
2. **Description:** `Average log loss (cross-entropy) measuring probability calibration quality. Lower is better: 0 = perfect, ~0.693 = random guessing, higher = poor calibration`
3. **Value Column:** `log_loss`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 2 — Total Predictions Count

1. **Metric Name:** `total_predictions`
2. **Description:** `Total number of valid predictions evaluated (excludes NULL values and invalid probabilities)`
3. **Value Column:** `total_predictions`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 3 — Average Predicted Probability

1. **Metric Name:** `avg_predicted_probability`
2. **Description:** `Average predicted probability for positive class across all predictions. Well-calibrated models should match true positive rate.`
3. **Value Column:** `avg_predicted_probability`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 4 — Positive Class Count

1. **Metric Name:** `positive_class_count`
2. **Description:** `Number of predictions where actual label was positive (1/true)`
3. **Value Column:** `positive_class_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 5 — Negative Class Count

1. **Metric Name:** `negative_class_count`
2. **Description:** `Number of predictions where actual label was negative (0/false)`
3. **Value Column:** `negative_class_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

***

## Step 5: Dashboard Chart SQL

This query reads from the **metrics_numeric_latest_version** table to visualize log loss and calibration metrics over time.

**Metrics Table Schema:**
The `metrics_numeric_latest_version` table contains:
- `model_id` (uuid) - Model identifier
- `project_id` (uuid) - Project identifier
- `workspace_id` (uuid) - Workspace identifier
- `organization_id` (uuid) - Organization identifier
- `metric_name` (varchar) - Name of the metric (from Step 4)
- `timestamp` (timestamptz) - Time bucket timestamp
- `metric_version` (integer) - Version of the metric definition
- `value` (double precision) - Computed metric value
- `dimensions` (jsonb) - Optional dimension data

**Chart SQL Query:**

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,

    metric_name,

    CASE
        WHEN metric_name = 'log_loss' THEN 'Log Loss'
        WHEN metric_name = 'avg_predicted_probability' THEN 'Avg Probability'
        WHEN metric_name = 'total_predictions' THEN 'Prediction Volume'
        WHEN metric_name = 'positive_class_count' THEN 'Positive Class'
        WHEN metric_name = 'negative_class_count' THEN 'Negative Class'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'log_loss',
    'avg_predicted_probability',
    'total_predictions',
    'positive_class_count',
    'negative_class_count'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**Query Explanation:**
- **`time_bucket_gapfill()`** - Creates continuous daily time series with no gaps
- **`{{dateStart}}` and `{{dateEnd}}`** - Template variables for configurable time range
- **`[[AND ...]]`** - Optional filter syntax in Arthur Platform
- **`metric_name IN (...)`** - Filters to the five metrics defined in Step 4
- **CASE for friendly_name** - Provides user-friendly display names
- **`COALESCE(AVG(value), 0)`** - Handles missing values gracefully

**Chart Configuration:**

**Option 1: Log Loss Trend with Threshold Zones (Recommended)**

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,

    COALESCE(AVG(CASE WHEN metric_name = 'log_loss' THEN value END), 0) AS log_loss,

    -- Add calibration quality indicator
    CASE
        WHEN AVG(CASE WHEN metric_name = 'log_loss' THEN value END) < 0.3 THEN 'Excellent'
        WHEN AVG(CASE WHEN metric_name = 'log_loss' THEN value END) < 0.5 THEN 'Good'
        WHEN AVG(CASE WHEN metric_name = 'log_loss' THEN value END) < 0.7 THEN 'Moderate'
        ELSE 'Poor'
    END AS calibration_quality

FROM metrics_numeric_latest_version
WHERE metric_name = 'log_loss'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

**Visualization:**
- **Chart Type**: Line chart with colored threshold zones
- **Y-axis**: Log loss (0 to 1.0+)
- **Threshold zones**:
  - Green zone (< 0.3): Excellent calibration
  - Light green zone (0.3-0.5): Good calibration
  - Yellow zone (0.5-0.7): Moderate calibration
  - Red zone (> 0.7): Poor calibration (worse than random)
- **Baseline**: Horizontal line at 0.693 (random guessing for balanced binary)
- **Target**: Horizontal line at 0.3 (good calibration threshold)

**Option 2: Log Loss vs. Calibration Dashboard**

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,

    AVG(CASE WHEN metric_name = 'log_loss' THEN value END) AS log_loss,
    AVG(CASE WHEN metric_name = 'avg_predicted_probability' THEN value END) AS avg_prob,

    -- Calculate true positive rate for calibration comparison
    SUM(CASE WHEN metric_name = 'positive_class_count' THEN value END) /
    NULLIF(
        SUM(CASE WHEN metric_name = 'total_predictions' THEN value END),
        0
    ) AS true_positive_rate

FROM metrics_numeric_latest_version
WHERE metric_name IN ('log_loss', 'avg_predicted_probability', 'positive_class_count', 'total_predictions')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

**Visualization:**
- **Chart Type**: Dual Y-axis line chart
- **Left Y-axis**: Log loss (lower is better)
- **Right Y-axis**: Probabilities (avg_prob and true_positive_rate)
- **Calibration check**: `avg_prob` should approximately equal `true_positive_rate` for well-calibrated models

**What these charts show:**
- **Daily log loss trend**: Track calibration quality over time
- **Threshold breaches**: Identify periods when model becomes poorly calibrated
- **Calibration drift**: Detect when probabilities become unreliable
- **Impact of changes**: Visualize log loss before/after model updates or retraining
- **Seasonality**: Identify temporal patterns in calibration quality
- **Volume context**: Correlate log loss with prediction volume

***

## Interpreting the Metric

### Value Ranges

**Log Loss < 0.3 (Excellent Calibration)**:
- Model produces highly reliable probabilities
- Confident predictions are usually correct
- Suitable for automated decision-making
- Comparable to best-in-class models
- **Action**: No changes needed, maintain monitoring

**Log Loss 0.3 - 0.5 (Good Calibration)**:
- Model produces generally reliable probabilities
- Acceptable for most production use cases
- May require manual review for high-stakes decisions
- **Action**: Continue monitoring, consider improvements if business-critical

**Log Loss 0.5 - 0.7 (Moderate Calibration)**:
- Model probabilities are somewhat reliable but imperfect
- Not suitable for fully automated decisions
- Requires manual review or threshold tuning
- **Action**: Investigate calibration issues, consider recalibration techniques (Platt scaling, isotonic regression)

**Log Loss ≈ 0.693 (Random Guessing Baseline)**:
- For balanced binary classification, random guessing achieves log loss ≈ 0.693
- **Formula**: `-[0.5*ln(0.5) + 0.5*ln(0.5)] = -ln(0.5) ≈ 0.693`
- Log loss near this value indicates model provides no useful information
- **Action**: Major model improvement needed; investigate features, training data, architecture

**Log Loss > 0.7 (Poor Calibration)**:
- Model worse than random guessing
- Probabilities are unreliable and potentially misleading
- Should not be used for decision-making
- May indicate inverse relationship or systematic miscalibration
- **Action**: Do not deploy; requires fundamental model rework

**Log Loss > 1.0 (Very Poor Calibration)**:
- Severe miscalibration issues
- Model may be confidently wrong on most predictions
- Potentially harmful if used for decision-making
- **Action**: Immediately investigate or replace model

### Understanding Log Loss Through Examples

**Example 1: Perfect Prediction**
- Prediction: p = 0.99, Actual: y = 1
- Log loss: -ln(0.99) ≈ 0.01
- **Interpretation**: Confident correct prediction, minimal penalty

**Example 2: Confident Wrong Prediction**
- Prediction: p = 0.99, Actual: y = 0
- Log loss: -ln(0.01) ≈ 4.6
- **Interpretation**: Severe penalty for overconfidence on wrong prediction

**Example 3: Uncertain Correct Prediction**
- Prediction: p = 0.55, Actual: y = 1
- Log loss: -ln(0.55) ≈ 0.6
- **Interpretation**: Moderate penalty for lack of confidence on correct prediction

**Example 4: Uncertain Wrong Prediction**
- Prediction: p = 0.55, Actual: y = 0
- Log loss: -ln(0.45) ≈ 0.8
- **Interpretation**: Moderate penalty; model appropriately uncertain

**Example 5: Random Guess**
- Prediction: p = 0.5, Actual: y = 0 or y = 1
- Log loss: -ln(0.5) ≈ 0.693
- **Interpretation**: Baseline for balanced binary classification

### Trends to Watch

**Increasing log loss over time:**
- **Calibration drift**: Model probabilities becoming less reliable
- **Population shift**: Distribution of features or labels changing
- **Seasonal effects**: Temporary patterns affecting probability estimates
- **Action**: Investigate drift metrics, consider recalibration or retraining

**Sudden log loss spike:**
- **Data quality issue**: Incorrect labels or probability scores
- **System change**: New feature engineering, data source, or integration
- **Outlier event**: Unusual conditions not seen in training
- **Action**: Check recent deployments, validate data pipeline, review error logs

**Decreasing log loss (improving):**
- **Model update**: Recent retraining improving calibration
- **Better features**: New or improved features enhancing predictions
- **Data quality improvements**: Fixes to upstream issues
- **Action**: Document improvements, monitor stability

**Oscillating log loss:**
- **Small sample size**: Daily variance from low prediction volume
- **Periodic patterns**: Day-of-week or time-of-day effects
- **Segmentation issues**: Mixed populations with different calibration
- **Action**: Increase time bucket size, segment analysis, investigate periodicity

**Log loss stable but accuracy declining:**
- **Severe issue**: Model maintaining confidence while becoming less correct
- **Overconfident miscalibration**: Probabilities don't reflect true uncertainty
- **Action**: Immediate investigation; model may be dangerously miscalibrated

**Low log loss but poor business outcomes:**
- **Threshold misalignment**: Decision thresholds not optimal for business objectives
- **Asymmetric costs**: Business costs of false positives vs false negatives not reflected in log loss
- **Action**: Review threshold tuning, consider cost-sensitive metrics

### When to Investigate

**Immediate investigation (within 24 hours):**
1. **Log loss > 0.7** - Model worse than random guessing
2. **Log loss increases >50%** in one day - Major calibration breakdown
3. **Log loss spikes to >1.0** - Severe miscalibration event
4. **Zero predictions recorded** - Data pipeline failure

**Planned investigation (within 1 week):**
1. **Log loss > 0.5 for 3+ consecutive days** - Sustained moderate miscalibration
2. **Log loss increasing >10% per week** - Gradual calibration drift
3. **Log loss and accuracy diverging** - Confidence/correctness mismatch
4. **High variance in log loss** - Stability issues

**Regular review (monthly):**
1. **Log loss 0.3-0.5 (good range)** - Assess if improvement possible
2. **Compare to baseline models** - Benchmark against simpler alternatives
3. **Segment-specific log loss** - Identify subpopulations with poor calibration
4. **Seasonal patterns** - Document expected variations

### Investigation Checklist

When log loss degrades:

1. **Verify data quality:**
   ```sql
   SELECT
       COUNT(*) FILTER (WHERE {{prediction_prob_col}} IS NULL) as null_probs,
       COUNT(*) FILTER (WHERE {{ground_truth_col}} IS NULL) as null_labels,
       COUNT(*) FILTER (WHERE {{prediction_prob_col}} < 0 OR {{prediction_prob_col}} > 1) as invalid_probs,
       MIN({{prediction_prob_col}}) as min_prob,
       MAX({{prediction_prob_col}}) as max_prob,
       AVG({{prediction_prob_col}}) as avg_prob,
       AVG({{ground_truth_col}}::float) as true_positive_rate,
       COUNT(*) as total
   FROM {{dataset}}
   WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days';
   ```

2. **Analyze calibration:**
   ```sql
   -- Binned calibration analysis
   WITH binned AS (
       SELECT
           CASE
               WHEN {{prediction_prob_col}} < 0.1 THEN '0.0-0.1'
               WHEN {{prediction_prob_col}} < 0.2 THEN '0.1-0.2'
               WHEN {{prediction_prob_col}} < 0.3 THEN '0.2-0.3'
               WHEN {{prediction_prob_col}} < 0.4 THEN '0.3-0.4'
               WHEN {{prediction_prob_col}} < 0.5 THEN '0.4-0.5'
               WHEN {{prediction_prob_col}} < 0.6 THEN '0.5-0.6'
               WHEN {{prediction_prob_col}} < 0.7 THEN '0.6-0.7'
               WHEN {{prediction_prob_col}} < 0.8 THEN '0.7-0.8'
               WHEN {{prediction_prob_col}} < 0.9 THEN '0.8-0.9'
               ELSE '0.9-1.0'
           END as prob_bin,
           AVG({{prediction_prob_col}}) as avg_predicted_prob,
           AVG({{ground_truth_col}}::float) as actual_positive_rate,
           COUNT(*) as count
       FROM {{dataset}}
       WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days'
       GROUP BY prob_bin
   )
   SELECT
       prob_bin,
       avg_predicted_prob,
       actual_positive_rate,
       ABS(avg_predicted_prob - actual_positive_rate) as calibration_error,
       count
   FROM binned
   ORDER BY prob_bin;
   ```
   **Expected**: `avg_predicted_prob` ≈ `actual_positive_rate` for well-calibrated models

3. **Check prediction distribution:**
   ```sql
   SELECT
       COUNT(*) FILTER (WHERE {{prediction_prob_col}} < 0.1) as very_low,
       COUNT(*) FILTER (WHERE {{prediction_prob_col}} BETWEEN 0.1 AND 0.3) as low,
       COUNT(*) FILTER (WHERE {{prediction_prob_col}} BETWEEN 0.3 AND 0.7) as medium,
       COUNT(*) FILTER (WHERE {{prediction_prob_col}} BETWEEN 0.7 AND 0.9) as high,
       COUNT(*) FILTER (WHERE {{prediction_prob_col}} > 0.9) as very_high,
       COUNT(*) as total
   FROM {{dataset}}
   WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days';
   ```
   **Expected**: Reasonable distribution across bins; extreme concentration may indicate issues

4. **Compare to baseline:**
   - Calculate log loss on validation set or holdout data
   - Compare current log loss to historical baseline
   - Check if degradation aligns with known events

5. **Segment analysis:**
   - Break down log loss by customer segment, region, or other dimensions
   - Identify if miscalibration is global or segment-specific

6. **Review recent changes:**
   - Model deployments or updates
   - Feature engineering modifications
   - Data pipeline changes
   - Upstream system integrations

***

## Use Cases

### Fraud Detection Model Selection

**Problem**: Financial institution evaluating three fraud detection models; need to select the one with most reliable probability estimates for confidence-based workflows.

**Setup**:
- **Dataset**: `binary-classifier-card-fraud`
- **Prediction column**: `fraud_score` (probability 0-1)
- **Ground truth column**: `is_fraud` (0/1)
- **Evaluation period**: 30 days
- **Decision thresholds**: p < 0.3 = auto-approve, 0.3 ≤ p < 0.7 = manual review, p ≥ 0.7 = auto-block

**Results**:

| Model | Accuracy | AUC-ROC | Log Loss | Avg Prob | True Fraud Rate |
|-------|----------|---------|----------|----------|-----------------|
| Rule-based | 92% | 0.88 | 0.45 | 0.08 | 0.05 |
| Random Forest | 94% | 0.93 | 0.28 | 0.06 | 0.05 |
| XGBoost | 94% | 0.94 | 0.22 | 0.05 | 0.05 |
| Neural Net | 95% | 0.95 | 0.31 | 0.09 | 0.05 |

**Analysis**:
- **XGBoost**: Lowest log loss (0.22) indicates best calibration
- **Random Forest**: Good log loss (0.28), comparable calibration
- **Neural Net**: Higher log loss (0.31) despite best accuracy/AUC; probabilities less reliable
- **Avg prob ≈ true fraud rate**: XGBoost (0.05 ≈ 0.05) shows excellent global calibration

**Decision**:
- **Deploy XGBoost**: Best probability calibration enables reliable confidence-based routing
- **Business impact**: Can auto-approve more transactions safely (low false positive rate at p<0.3)
- **Monitoring**: Track log loss weekly; alert if >0.3 (degradation from baseline)

### Credit Approval Probability Recalibration

**Problem**: Credit approval model's probabilities have drifted; log loss increased from 0.35 to 0.52, indicating miscalibration affecting interest rate assignments.

**Setup**:
- **Dataset**: `binary-classifier-cc-application`
- **Prediction column**: `approval_score`
- **Ground truth column**: `is_approved`
- **Baseline log loss**: 0.35 (first 3 months of production)
- **Current log loss**: 0.52 (last 30 days)
- **Business impact**: Interest rates incorrectly assigned based on unreliable probabilities

**Investigation**:

```sql
-- Calibration analysis by probability bin
WITH binned AS (
    SELECT
        FLOOR(approval_score * 10) / 10.0 as prob_bin_start,
        AVG(approval_score) as avg_predicted,
        AVG(is_approved::float) as actual_approval_rate,
        COUNT(*) as count
    FROM credit_applications
    WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY prob_bin_start
)
SELECT
    prob_bin_start,
    ROUND(avg_predicted::numeric, 3) as avg_pred,
    ROUND(actual_approval_rate::numeric, 3) as actual_rate,
    ROUND((avg_predicted - actual_approval_rate)::numeric, 3) as calibration_error,
    count
FROM binned
ORDER BY prob_bin_start;
```

**Findings**:
- Probabilities in 0.4-0.6 range are overconfident (predicting 0.5 but actual rate 0.35)
- Probabilities in 0.7-0.9 range are underconfident (predicting 0.8 but actual rate 0.95)
- Systematic miscalibration introduced by population shift (more risky applications)

**Action Plan**:
1. **Apply Platt scaling**: Recalibrate probabilities using isotonic regression on recent data
2. **Retrain model**: Incorporate recent 3 months of data to adapt to population shift
3. **Monitor log loss**: Set up weekly monitoring with alert threshold at 0.4
4. **Audit interest rates**: Review assignments for past 30 days, consider adjustments

**Outcome**:
- Post-recalibration log loss: 0.33 (improved from 0.52)
- Avoided revenue loss from miscalibrated interest rates
- Established quarterly recalibration schedule

### Medical Diagnosis Confidence Thresholds

**Problem**: Hospital deploying ML model for disease screening; need to establish confidence thresholds for clinical decision workflows based on log loss analysis.

**Setup**:
- **Model**: Binary classifier for disease presence
- **Prediction column**: `disease_probability`
- **Ground truth column**: `has_disease`
- **Log loss**: 0.25 (excellent calibration)
- **Prevalence**: 8% positive cases

**Threshold Strategy**:

| Probability Range | Log Loss in Range | Decision Workflow | Rationale |
|------------------|-------------------|-------------------|-----------|
| p < 0.15 | 0.12 | Negative, routine follow-up | Low log loss, reliable low risk |
| 0.15 ≤ p < 0.40 | 0.28 | Manual physician review | Moderate log loss, uncertain |
| 0.40 ≤ p < 0.70 | 0.35 | Physician review + additional tests | Higher stakes, thorough review |
| p ≥ 0.70 | 0.18 | Immediate specialist referral | Low log loss, reliable high risk |

**Calibration Validation**:
- Probabilities in p < 0.15 range: 98.5% true negative rate (well-calibrated)
- Probabilities in p ≥ 0.70 range: 72% true positive rate (well-calibrated)
- Overall log loss 0.25 indicates probabilities are trustworthy for clinical use

**Regulatory Documentation**:
- **Log loss < 0.3**: Meets internal threshold for clinical decision support
- **Calibration curves**: Demonstrate probability reliability to regulatory reviewers
- **Monitoring plan**: Monthly log loss calculation; recalibration if >0.35

**Outcome**:
- 65% of cases routed to routine follow-up (p < 0.15), reducing unnecessary specialist visits
- 8% of cases flagged for immediate specialist (p ≥ 0.70), catching high-risk patients
- Confidence thresholds defensible due to excellent log loss

### A/B Testing Model Updates

**Problem**: Evaluating whether model update (Model B) improves over production model (Model A) for fraud detection; accuracy alone insufficient to determine which has better probability calibration.

**Setup**:
- **Model A (production)**: 60 days of history
- **Model B (candidate)**: 30 days of A/B test
- **Traffic split**: 50/50
- **Prediction column**: `fraud_score`
- **Ground truth column**: `is_fraud`

**Results**:

| Metric | Model A | Model B | Difference |
|--------|---------|---------|------------|
| Accuracy | 93.2% | 93.8% | +0.6pp |
| Precision | 85.1% | 86.3% | +1.2pp |
| Recall | 78.5% | 79.2% | +0.7pp |
| AUC-ROC | 0.92 | 0.93 | +0.01 |
| **Log Loss** | **0.38** | **0.29** | **-0.09 (24% improvement)** |

**Calibration Analysis**:

```sql
-- Compare calibration between models
WITH model_a_calibration AS (
    SELECT
        'Model A' as model,
        FLOOR(fraud_score * 10) / 10.0 as prob_bin,
        AVG(fraud_score) as avg_pred_prob,
        AVG(is_fraud::float) as true_fraud_rate,
        COUNT(*) as count
    FROM fraud_transactions
    WHERE model_version = 'A'
        AND timestamp >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY prob_bin
),
model_b_calibration AS (
    SELECT
        'Model B' as model,
        FLOOR(fraud_score * 10) / 10.0 as prob_bin,
        AVG(fraud_score) as avg_pred_prob,
        AVG(is_fraud::float) as true_fraud_rate,
        COUNT(*) as count
    FROM fraud_transactions
    WHERE model_version = 'B'
        AND timestamp >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY prob_bin
)
SELECT * FROM model_a_calibration
UNION ALL
SELECT * FROM model_b_calibration
ORDER BY model, prob_bin;
```

**Findings**:
- **Model B**: Better calibration across all probability ranges
- **High probability range (0.7-0.9)**: Model A overconfident (predicts 0.8, actual 0.65), Model B well-calibrated (predicts 0.8, actual 0.78)
- **Low probability range (0.1-0.3)**: Both models well-calibrated
- **Business impact**: Model B's better calibration enables more reliable auto-blocking at high probabilities

**Decision**:
- **Deploy Model B to 100%**: 24% log loss improvement indicates significantly better probability calibration
- **Confidence-based routing**: Update thresholds based on Model B's calibration
- **Expected impact**: Reduce manual review queue by 15% while maintaining fraud catch rate

### Production Monitoring & Drift Detection

**Problem**: Monitor fraud detection model in production for calibration drift; need to detect when probabilities become unreliable before business impact.

**Setup**:
- **Monitoring frequency**: Daily log loss calculation
- **Baseline**: First 60 days of production (log loss = 0.32)
- **Alert thresholds**:
  - Warning: log loss > 0.40 (25% degradation)
  - Critical: log loss > 0.50 (56% degradation)
- **Action plan**: Predefined workflow for drift investigation and remediation

**Month 3 Alert: Log Loss = 0.45 (Warning)**

Investigation workflow:
1. **Data quality check**: No issues found
2. **Calibration analysis**: Probabilities in 0.6-0.8 range overconfident
3. **Population analysis**: Shift in transaction types (more e-commerce vs. in-store)
4. **Feature drift check**: `transaction_amount` distribution shifted higher

**Root cause**: Population shift from in-store to e-commerce transactions during holiday season; model not trained on sufficient e-commerce examples.

**Action taken**:
- Short-term: Apply temperature scaling to recalibrate probabilities (log loss reduced to 0.37)
- Long-term: Retrain model with recent 90 days including holiday e-commerce surge
- Post-retraining: Log loss = 0.29 (improvement over baseline)

**Month 6: Log Loss Stable at 0.30**

- Quarterly recalibration maintained log loss < 0.35
- Seasonal patterns documented (holiday surge, tax season)
- Automated alerts prevented 2 potential calibration crises

**Monitoring Dashboard**:
- **Primary chart**: Daily log loss with 0.40 warning threshold
- **Secondary charts**:
  - Calibration curve (actual vs predicted by bin)
  - Prediction distribution histogram
  - Class balance over time
- **Weekly reports**: Log loss trend, outlier days, calibration analysis

**Business value**:
- Caught population shift 3 weeks before customer complaints about false blocks
- Maintained SLA of log loss < 0.40 for 95% of days
- Reduced manual review costs by identifying optimal confidence thresholds based on calibration

### Regulatory Compliance for Risk Models

**Problem**: Bank needs to demonstrate to regulators that credit risk model produces reliable probability estimates for capital reserve calculations.

**Setup**:
- **Model**: Credit default probability prediction
- **Regulatory requirement**: Demonstrate probability calibration for Basel III compliance
- **Validation approach**: Log loss as primary calibration metric
- **Prediction column**: `default_probability`
- **Ground truth column**: `did_default`
- **Evaluation period**: 12 months

**Regulatory Metrics**:

| Metric | Value | Regulatory Threshold | Status |
|--------|-------|---------------------|--------|
| Log Loss | 0.31 | < 0.40 | ✅ Pass |
| Brier Score | 0.045 | < 0.06 | ✅ Pass |
| Expected Calibration Error | 0.028 | < 0.05 | ✅ Pass |
| Calibration Slope | 0.98 | 0.90-1.10 | ✅ Pass |
| Calibration Intercept | 0.012 | -0.05 to 0.05 | ✅ Pass |

**Calibration Documentation**:

```sql
-- Generate calibration curve for regulatory submission
WITH decile_bins AS (
    SELECT
        NTILE(10) OVER (ORDER BY default_probability) as decile,
        default_probability,
        did_default
    FROM credit_applications
    WHERE evaluation_period = 'validation'
)
SELECT
    decile,
    AVG(default_probability) as avg_predicted_prob,
    AVG(did_default::float) as observed_default_rate,
    COUNT(*) as sample_size,
    -- Calculate log loss contribution per decile
    AVG(
        CASE
            WHEN did_default = 1 THEN -LN(GREATEST(1e-15, default_probability))
            ELSE -LN(GREATEST(1e-15, 1 - default_probability))
        END
    ) as decile_log_loss
FROM decile_bins
GROUP BY decile
ORDER BY decile;
```

**Regulatory Submission**:
- **Calibration curve**: Visual demonstration that predicted probabilities match observed rates
- **Log loss trend**: Shows stability over 12-month validation period (0.29 to 0.33 range)
- **Segment analysis**: Log loss calculated separately for different risk segments (prime, subprime, etc.)
- **Backtesting results**: Historical predictions vs. actual defaults align with probability estimates

**Outcome**:
- Regulatory approval for model use in capital reserve calculations
- Annual recalibration requirement to maintain log loss < 0.40
- Quarterly monitoring reports submitted to risk committee

***

## Debugging & Verification

If the metric returns empty or unexpected values, use these queries to diagnose:

### 1. Verify data exists and is valid

```sql
SELECT
    COUNT(*) as total_rows,
    COUNT({{timestamp_col}}) as non_null_timestamps,
    COUNT({{prediction_prob_col}}) as non_null_probs,
    COUNT({{ground_truth_col}}) as non_null_labels,
    COUNT(*) FILTER (WHERE {{prediction_prob_col}} >= 0 AND {{prediction_prob_col}} <= 1) as valid_probs,
    MIN({{prediction_prob_col}}) as min_prob,
    MAX({{prediction_prob_col}}) as max_prob,
    MIN({{timestamp_col}}) as earliest_ts,
    MAX({{timestamp_col}}) as latest_ts
FROM {{dataset}};
```

**Expected**:
- All counts > 0
- `valid_probs` should equal `non_null_probs` (all probabilities in [0,1])
- Timestamp range should cover recent data

### 2. Check label distribution

```sql
SELECT
    {{ground_truth_col}} as label,
    COUNT(*) as count,
    ROUND(COUNT(*)::float / SUM(COUNT(*)) OVER () * 100, 2) as percentage
FROM {{dataset}}
WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY label
ORDER BY label;
```

**Expected**:
- Both classes (0 and 1) should be present
- Extreme imbalance (e.g., 99%/1%) may affect log loss interpretation

### 3. Manually calculate log loss on sample

```sql
WITH sample_data AS (
    SELECT
        {{prediction_prob_col}}::float as prob,
        {{ground_truth_col}}::int as label,
        GREATEST(1e-15, LEAST(1.0 - 1e-15, {{prediction_prob_col}}::float)) as prob_clipped
    FROM {{dataset}}
    WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days'
        AND {{prediction_prob_col}} IS NOT NULL
        AND {{ground_truth_col}} IS NOT NULL
    LIMIT 100
),
log_loss_calc AS (
    SELECT
        prob,
        label,
        prob_clipped,
        CASE
            WHEN label = 1 THEN -LN(prob_clipped)
            ELSE -LN(1.0 - prob_clipped)
        END as sample_log_loss
    FROM sample_data
)
SELECT
    COUNT(*) as sample_size,
    MIN(sample_log_loss) as min_log_loss,
    MAX(sample_log_loss) as max_log_loss,
    AVG(sample_log_loss) as avg_log_loss,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sample_log_loss) as median_log_loss,
    AVG(prob) as avg_prob,
    AVG(label::float) as true_positive_rate
FROM log_loss_calc;
```

**Expected**:
- `avg_log_loss` should be between 0 and ~2 for reasonable models
- `avg_prob` ≈ `true_positive_rate` for well-calibrated models

### 4. Test with known values

```sql
WITH test_cases AS (
    SELECT 1 as label, 0.99 as prob, 1e-15 as epsilon
    UNION ALL SELECT 1, 0.50, 1e-15
    UNION ALL SELECT 1, 0.01, 1e-15
    UNION ALL SELECT 0, 0.99, 1e-15
    UNION ALL SELECT 0, 0.50, 1e-15
    UNION ALL SELECT 0, 0.01, 1e-15
)
SELECT
    label,
    prob,
    GREATEST(epsilon, LEAST(1.0 - epsilon, prob)) as prob_clipped,
    CASE
        WHEN label = 1 THEN -LN(GREATEST(epsilon, LEAST(1.0 - epsilon, prob)))
        ELSE -LN(1.0 - GREATEST(epsilon, LEAST(1.0 - epsilon, prob)))
    END as log_loss,
    CASE
        WHEN label = 1 AND prob > 0.5 THEN 'Correct confident'
        WHEN label = 1 AND prob < 0.5 THEN 'Correct uncertain'
        WHEN label = 0 AND prob < 0.5 THEN 'Correct confident'
        WHEN label = 0 AND prob > 0.5 THEN 'Incorrect confident'
        ELSE 'Neutral'
    END as interpretation
FROM test_cases;
```

**Expected output**:
- label=1, prob=0.99: log_loss ≈ 0.01 (excellent)
- label=1, prob=0.50: log_loss ≈ 0.693 (neutral)
- label=1, prob=0.01: log_loss ≈ 4.6 (very poor)
- label=0, prob=0.99: log_loss ≈ 4.6 (very poor)
- label=0, prob=0.50: log_loss ≈ 0.693 (neutral)
- label=0, prob=0.01: log_loss ≈ 0.01 (excellent)

### 5. Check for extreme probabilities

```sql
SELECT
    COUNT(*) FILTER (WHERE {{prediction_prob_col}} = 0.0) as prob_exactly_zero,
    COUNT(*) FILTER (WHERE {{prediction_prob_col}} = 1.0) as prob_exactly_one,
    COUNT(*) FILTER (WHERE {{prediction_prob_col}} < 0.01) as prob_very_low,
    COUNT(*) FILTER (WHERE {{prediction_prob_col}} > 0.99) as prob_very_high,
    COUNT(*) as total
FROM {{dataset}}
WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days';
```

**Expected**:
- Few or no exact 0.0 or 1.0 probabilities (epsilon smoothing will clip these)
- Reasonable number of very confident predictions (< 1% and > 99%)

### 6. Compare log loss to random baseline

```sql
-- Calculate what log loss would be for random guessing
WITH class_distribution AS (
    SELECT
        AVG({{ground_truth_col}}::float) as positive_rate
    FROM {{dataset}}
    WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '30 days'
),
random_baseline AS (
    SELECT
        positive_rate,
        -((positive_rate * LN(positive_rate)) + ((1 - positive_rate) * LN(1 - positive_rate))) as baseline_log_loss
    FROM class_distribution
)
SELECT
    ROUND(positive_rate::numeric, 3) as class_balance,
    ROUND(baseline_log_loss::numeric, 3) as random_guess_log_loss,
    '0.693 for balanced (50/50) dataset' as note
FROM random_baseline;
```

**Expected**:
- For balanced dataset (50/50): random baseline ≈ 0.693
- For imbalanced dataset: baseline lower than 0.693
- Your model's log loss should be lower than this baseline

### Common Issues

- **Log loss is negative**: Impossible; check for errors in LN() calculation or label encoding
- **Log loss > 10**: Extremely confident wrong predictions; check for inverted labels (0/1 swapped)
- **Log loss = NaN or NULL**: Epsilon smoothing not applied; probabilities of exactly 0 or 1 causing log(0)
- **Log loss near 0.693 consistently**: Model no better than random guessing; investigate features/training
- **Empty results**: Check timestamp range, verify probability and label columns exist and have valid data
- **Very high log loss (>2)**: Severe miscalibration; check if model outputs are actually probabilities (0-1 range)
- **Log loss decreasing but accuracy not improving**: Possible overfitting on probability calibration

***

## Dataset Compatibility

This metric is compatible with any binary classification dataset containing predicted probabilities and ground truth labels.

### Compatible Datasets from `/data` folder:

#### 1. binary-classifier-card-fraud

**Column Mapping:**
- `timestamp` (timestamp) → `timestamp_col`
- `fraud_score` (float, 0-1) → `prediction_prob_col`
- `is_fraud` (int, 0/1) → `ground_truth_col`

**Recommended Configuration:**
- **Epsilon**: `1e-15` (default)
- **Target log loss**: < 0.35 (good calibration for fraud detection)
- **Monitoring frequency**: Daily

**Example Interpretation**:
- **Log loss 0.28**: Excellent calibration; probabilities reliable for confidence-based routing
- **Fraud score 0.85, is_fraud=1**: Log loss = -ln(0.85) ≈ 0.16 (good confident correct prediction)
- **Fraud score 0.95, is_fraud=0**: Log loss = -ln(0.05) ≈ 3.0 (severe penalty for confident wrong prediction)

**Use Cases**:
- Establish confidence thresholds: p < 0.3 auto-approve, 0.3 ≤ p < 0.7 manual review, p ≥ 0.7 auto-block
- Monitor calibration drift over time as fraud patterns evolve
- Compare calibration quality across model versions
- Validate that high fraud scores accurately reflect high fraud probability

#### 2. binary-classifier-cc-application

**Column Mapping:**
- `timestamp` (timestamp) → `timestamp_col`
- `approval_score` (float, 0-1) → `prediction_prob_col`
- `is_approved` (int, 0/1) → `ground_truth_col`

**Recommended Configuration:**
- **Epsilon**: `1e-15` (default)
- **Target log loss**: < 0.40 (acceptable calibration for credit decisions)
- **Monitoring frequency**: Weekly (less volatile than fraud)

**Example Interpretation**:
- **Log loss 0.32**: Good calibration; probabilities suitable for interest rate assignment
- **Approval score 0.70, is_approved=1**: Log loss = -ln(0.70) ≈ 0.36 (moderate confidence, correct)
- **Approval score 0.90, is_approved=0**: Log loss = -ln(0.10) ≈ 2.3 (high penalty for confident rejection that was approved)

**Use Cases**:
- Assign interest rates based on approval probabilities (requires good calibration)
- Set approval thresholds that balance risk and revenue
- Monitor calibration to detect population shifts (economic changes, new customer segments)
- Regulatory reporting: demonstrate probability reliability for credit risk models

### Data Requirements

**Essential:**
- Timestamp column (for time-series aggregation)
- Predicted probability column (float, range 0-1, continuous probabilities not just 0/1)
- Ground truth label column (int or bool: 0/1 or false/true)
- Sufficient sample size (100+ predictions per time bucket for stable log loss)

**Optional but Recommended:**
- Model version identifier (for A/B testing)
- Segmentation columns (for calibration analysis by subpopulation)
- Prediction confidence scores or alternative probability estimates (for comparison)
- Feature columns (for drift analysis when log loss degrades)

### Notes

**Log Loss vs. Other Calibration Metrics:**
- **Brier Score**: MSE of probabilities; similar to log loss but uses quadratic penalty instead of logarithmic
- **Expected Calibration Error (ECE)**: Measures calibration in binned probability ranges
- **Calibration curves**: Visual assessment; log loss provides single number for tracking
- **Recommendation**: Use log loss as primary metric, complement with calibration curves for investigation

**Handling Class Imbalance:**
- Log loss inherently handles imbalance (no need for weighted log loss)
- Baseline log loss for imbalanced dataset: `-[p*ln(p) + (1-p)*ln(1-p)]` where p = positive class rate
- For 95% negative, 5% positive: baseline ≈ 0.20 (not 0.693)
- Interpret log loss relative to this baseline

**Probability Calibration Techniques:**
When log loss indicates miscalibration:
1. **Platt Scaling**: Fit logistic regression on model outputs
2. **Isotonic Regression**: Non-parametric calibration method
3. **Temperature Scaling**: Divide logits by temperature parameter before softmax
4. **Beta Calibration**: Generalization of Platt scaling with beta distribution

**Multi-Class Extension:**
For multi-class classification, modify SQL to:
```sql
-- Assuming probabilities stored as array or separate columns
SELECT
    time_bucket(INTERVAL '1 day', timestamp) AS ts,
    -AVG(
        CASE
            WHEN ground_truth_class = 0 THEN LN(GREATEST(epsilon, prob_class_0))
            WHEN ground_truth_class = 1 THEN LN(GREATEST(epsilon, prob_class_1))
            WHEN ground_truth_class = 2 THEN LN(GREATEST(epsilon, prob_class_2))
            -- Add more classes as needed
        END
    ) as log_loss
FROM dataset
GROUP BY ts;
```

**Threshold Selection Based on Log Loss:**
After establishing good calibration (low log loss), use probability distribution to set decision thresholds:
1. Analyze cost matrix (false positive vs false negative costs)
2. Evaluate threshold sweep: for each threshold 0.1, 0.2, ..., 0.9
3. Calculate expected cost at each threshold
4. Select threshold minimizing expected cost
5. Confidence in threshold selection depends on low log loss (well-calibrated probabilities)

**Continuous Monitoring:**
- Track log loss daily/weekly in production
- Set alert thresholds: warning at 25% increase, critical at 50% increase from baseline
- Investigate calibration when log loss increases even if accuracy stable
- Document seasonal patterns (holidays, quarter-end effects)
- Establish quarterly recalibration schedule if log loss shows gradual drift

**Documentation for Stakeholders:**
- **Technical teams**: Provide log loss values, trends, and calibration curves
- **Business teams**: Translate to "confidence reliability" - "probabilities are X% reliable" based on calibration error
- **Regulatory**: Include log loss in model documentation alongside accuracy, AUC-ROC
- **Executives**: "Model probabilities are well-calibrated (log loss < 0.3), enabling confident automation"
