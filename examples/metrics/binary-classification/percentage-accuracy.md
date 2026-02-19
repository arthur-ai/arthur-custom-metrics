# Percentage Accuracy

## Overview

**Percentage Accuracy** is the most intuitive and widely understood metric in machine learning, measuring what percentage of all predictions are correct. If a model has 85% accuracy, it means that 85 out of every 100 predictions match the actual labels. Unlike complex metrics that evaluate probability calibration or ranking ability, percentage accuracy provides a straightforward, easy-to-communicate assessment that resonates with both technical and non-technical stakeholders. However, accuracy can be misleading for imbalanced datasets and should be complemented with other metrics for comprehensive evaluation.

**Key Insights:**
- Most intuitive metric: percentage format universally understood
- Overall correctness measure: treats all prediction types equally
- Threshold-free: uses hard predictions, no parameter tuning needed
- Balanced view: counts both correct positives and correct negatives
- Simple communication: perfect for executives, product managers, stakeholders
- Can be misleading: high accuracy possible on imbalanced data with naive models

**When to Use:**
- **High-level monitoring**: Executive dashboards showing model health at a glance
- **Stakeholder communication**: "94% accurate" is clearer than "log loss 0.28"
- **SLA compliance**: "Model must maintain ≥80% accuracy" is a simple quality gate
- **A/B testing**: Quick comparison—"Model B has 3% higher accuracy"
- **Deployment gates**: "Only promote if accuracy >85%"
- **Balanced datasets**: Where all classes roughly equally important
- **Quick sanity checks**: Fast assessment during model development

**When to Complement with Other Metrics:**
- **Imbalanced datasets**: Add precision, recall, F1-score, per-class accuracy
- **Asymmetric costs**: When false positives ≠ false negatives in business impact
- **Probabilistic decisions**: Add log loss, Brier score for confidence assessment
- **Class-specific needs**: Add confusion matrix, per-class metrics

***

## Step 1: Write the SQL

This SQL computes percentage accuracy by calculating what proportion of predictions match actual labels, expressed as a percentage (0-100%).

```sql
WITH
  valid_predictions AS (
    -- Filter to valid predictions with non-NULL labels
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_label_col}}::int AS predicted_label,
      {{ground_truth_col}}::int AS actual_label
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
      AND {{prediction_label_col}} IS NOT NULL
      AND {{ground_truth_col}} IS NOT NULL
  ),

  correctness_flags AS (
    -- Flag each prediction as correct (1.0) or incorrect (0.0)
    SELECT
      ts,
      predicted_label,
      actual_label,
      CASE
        WHEN predicted_label = actual_label THEN 1.0
        ELSE 0.0
      END AS is_correct
    FROM valid_predictions
  )

-- Aggregate to get percentage accuracy per day
SELECT
  ts,
  AVG(is_correct) * 100.0 AS percentage_accuracy,
  SUM(is_correct)::int AS correct_predictions_count,
  COUNT(*)::int AS total_predictions_count,
  -- Additional metrics for context
  (SUM(is_correct) / COUNT(*)::float * 100.0)::float AS accuracy_check
FROM correctness_flags
GROUP BY ts
ORDER BY ts;
```

**What this query returns:**

* `ts` — timestamp bucket (1 day)
* `percentage_accuracy` — proportion of correct predictions as percentage (float, 0-100, higher is better)
* `correct_predictions_count` — number of predictions that were correct (integer)
* `total_predictions_count` — total number of predictions evaluated (integer)
* `accuracy_check` — alternative calculation for verification (float, 0-100)

**SQL Logic:**

1. **valid_predictions CTE**:
   - Filters NULL values in timestamp, prediction, and ground truth columns
   - Casts prediction and ground truth to int for consistent comparison
   - Groups by daily time buckets using `time_bucket(INTERVAL '1 day', ...)`
   - Ensures only valid, comparable predictions are included

2. **correctness_flags CTE**:
   - Performs simple equality check: `predicted_label = actual_label`
   - Returns binary flag: `1.0` if correct, `0.0` if incorrect
   - Binary flag enables easy averaging to get proportion
   - Preserves individual labels for debugging if needed

3. **Final aggregation**:
   - `AVG(is_correct) * 100.0` computes proportion correct and converts to percentage
   - `SUM(is_correct)::int` counts how many predictions were correct
   - `COUNT(*)::int` counts total predictions in time bucket
   - `accuracy_check` provides alternative calculation as verification
   - Groups by day for time-series tracking

**Key Features:**
- **Simplicity**: Straightforward equality check, no complex math
- **Type safety**: Explicit int casting for label comparison
- **NULL handling**: Filters invalid records upfront
- **Percentage output**: Multiplies by 100 for intuitive 0-100 scale
- **Verification**: Includes alternative calculation to validate results

**Accuracy Calculation:**
- **Perfect predictions**: All predicted = actual → 100%
- **Random guessing (balanced)**: ~50% of predictions correct → 50%
- **Always predict majority class**: Can achieve high accuracy on imbalanced data

***

## Step 2: Fill Basic Information

When creating the custom metric in the Arthur UI:

1. **Name**:
   `Percentage Accuracy`

2. **Description** (optional but recommended):
   `Proportion of correct predictions expressed as percentage (0-100%). Measures overall model correctness: if accuracy is 85%, then 85 out of 100 predictions match actual labels. Simple, intuitive metric for stakeholder communication and high-level monitoring. Note: Can be misleading on imbalanced datasets; complement with precision, recall, and F1-score for comprehensive evaluation.`

***

## Step 3: Configure the Aggregate Arguments

You will set up four aggregate arguments to parameterize the SQL.

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Timestamp column for time-series bucketing and temporal tracking`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Predicted Label Column

1. **Parameter Key:** `prediction_label_col`
2. **Friendly Name:** `Predicted Label Column`
3. **Description:** `Model's predicted class label (int or bool: 0/1, false/true, or multi-class integers). Examples: fraud_pred, approval_pred, predicted_class`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `prediction`
8. **Allowed Column Types:** `int, bool`

**Note on Allowed Column Types:**
- Set to `Yes` to allow both int and bool types
- Handles binary (0/1, false/true) and multi-class (0, 1, 2, ..., N) naturally

### Argument 3 — Ground Truth Label Column

1. **Parameter Key:** `ground_truth_col`
2. **Friendly Name:** `Ground Truth Label Column`
3. **Description:** `Actual class label (int or bool: 0/1, false/true, or multi-class integers). Examples: is_fraud, is_approved, actual_class`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `Yes`
7. **Tag Hints:** `ground_truth`
8. **Allowed Column Types:** `int, bool`

### Argument 4 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset containing predicted and actual class labels`
4. **Parameter Type:** `Dataset`

***

## Step 4: Configure Reported Metrics

This metric reports three values for comprehensive accuracy monitoring.

### Metric 1 — Percentage Accuracy

1. **Metric Name:** `percentage_accuracy`
2. **Description:** `Proportion of correct predictions as percentage (0-100%). Higher is better: 100% = perfect, 50% ≈ random guessing for balanced binary classification.`
3. **Value Column:** `percentage_accuracy`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 2 — Correct Predictions Count

1. **Metric Name:** `correct_predictions_count`
2. **Description:** `Number of predictions that matched actual labels`
3. **Value Column:** `correct_predictions_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 3 — Total Predictions Count

1. **Metric Name:** `total_predictions_count`
2. **Description:** `Total number of predictions evaluated (excludes NULL values)`
3. **Value Column:** `total_predictions_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

***

## Step 5: Dashboard Chart SQL

This query reads from the **metrics_numeric_latest_version** table to visualize accuracy and volume metrics over time.

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
        WHEN metric_name = 'percentage_accuracy' THEN 'Accuracy (%)'
        WHEN metric_name = 'correct_predictions_count' THEN 'Correct Predictions'
        WHEN metric_name = 'total_predictions_count' THEN 'Total Predictions'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'percentage_accuracy',
    'correct_predictions_count',
    'total_predictions_count'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**Query Explanation:**
- **`time_bucket_gapfill()`** - Creates continuous daily time series with no gaps
- **`{{dateStart}}` and `{{dateEnd}}`** - Template variables for configurable time range
- **`[[AND ...]]`** - Optional filter syntax in Arthur Platform
- **`metric_name IN (...)`** - Filters to the three metrics defined in Step 4
- **CASE for friendly_name** - Provides user-friendly display names
- **`COALESCE(AVG(value), 0)`** - Handles missing values gracefully

**Chart Configuration:**

**Option 1: Accuracy Trend with SLA Threshold (Recommended)**

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,

    COALESCE(AVG(CASE WHEN metric_name = 'percentage_accuracy' THEN value END), 0) AS accuracy_pct,

    -- Add quality indicator
    CASE
        WHEN AVG(CASE WHEN metric_name = 'percentage_accuracy' THEN value END) >= 90 THEN 'Excellent'
        WHEN AVG(CASE WHEN metric_name = 'percentage_accuracy' THEN value END) >= 80 THEN 'Good'
        WHEN AVG(CASE WHEN metric_name = 'percentage_accuracy' THEN value END) >= 70 THEN 'Fair'
        ELSE 'Poor'
    END AS performance_tier

FROM metrics_numeric_latest_version
WHERE metric_name = 'percentage_accuracy'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

**Visualization:**
- **Chart Type**: Line chart with colored threshold zones
- **Y-axis**: Percentage accuracy (0-100%)
- **Threshold zones**:
  - Dark green (90-100%): Excellent
  - Green (80-90%): Good
  - Yellow (70-80%): Fair
  - Red (< 70%): Poor
- **SLA line**: Horizontal line at target (e.g., 80%)
- **Baseline**: Horizontal line at 50% (random guessing for balanced binary)

**Option 2: Accuracy with Volume Context**

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,

    AVG(CASE WHEN metric_name = 'percentage_accuracy' THEN value END) AS accuracy_pct,
    SUM(CASE WHEN metric_name = 'total_predictions_count' THEN value END) AS prediction_volume,
    SUM(CASE WHEN metric_name = 'correct_predictions_count' THEN value END) AS correct_count

FROM metrics_numeric_latest_version
WHERE metric_name IN ('percentage_accuracy', 'total_predictions_count', 'correct_predictions_count')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

**Visualization:**
- **Chart Type**: Dual Y-axis line chart
- **Left Y-axis**: Accuracy percentage (0-100%)
- **Right Y-axis**: Prediction volume (count)
- **Use case**: Identify if accuracy drops correlate with volume spikes

**What these charts show:**
- **Daily accuracy trend**: Track model correctness over time
- **SLA compliance**: Visual indicator of threshold breaches
- **Volume correlation**: Understand if accuracy varies with prediction volume
- **Impact of changes**: Before/after model updates or retraining
- **Seasonality**: Identify temporal patterns in accuracy
- **Quality tiers**: Quick visual assessment of performance level

***

## Interpreting the Metric

### Value Ranges

**Percentage Accuracy 95-100% (Excellent)**:
- 95-100 out of 100 predictions are correct
- Model exceeds most production standards significantly
- Suitable for high-stakes applications with confidence
- May indicate perfect fit on test set (check for overfitting if 100%)
- **Action**: Deploy with confidence, maintain monitoring for drift

**Percentage Accuracy 85-95% (Very Good)**:
- 85-95 out of 100 predictions are correct
- Meets or exceeds typical production quality standards
- Acceptable for most business applications
- Room for improvement but not urgent
- **Action**: Deploy to production, plan incremental improvements

**Percentage Accuracy 70-85% (Good)**:
- 70-85 out of 100 predictions are correct
- Acceptable for many applications, especially complex ones
- May require human review for high-stakes decisions
- Consider if improvement would justify additional effort
- **Action**: Deploy with monitoring, investigate improvement opportunities

**Percentage Accuracy 50-70% (Moderate)**:
- 50-70 out of 100 predictions are correct
- Below typical production standards
- Not suitable for fully automated decisions
- Improvement needed for most use cases
- **Action**: Investigate model issues, consider retraining or feature engineering

**Percentage Accuracy < 50% (Poor)**:
- Fewer than half of predictions are correct
- For balanced binary classification, worse than random guessing (50%)
- Severe model issues or inverse relationship
- Should not be deployed
- **Action**: Major investigation required; check labels, features, training process

**Special Case: High Accuracy on Imbalanced Data**:
- **Example**: 99% accuracy with 99% negative, 1% positive class
- **Reality**: Model may just predict majority class always
- **Diagnosis**: Check confusion matrix, precision, recall
- **Action**: Use balanced accuracy, F1-score, per-class metrics

### Understanding Accuracy Through Examples

**Example 1: Balanced Binary Classification (50/50 split)**
- Total predictions: 1,000 (500 positive, 500 negative)
- Correct positive predictions (TP): 450
- Correct negative predictions (TN): 470
- Accuracy: (450 + 470) / 1,000 = 92%
- **Interpretation**: Strong performance, both classes predicted well

**Example 2: Imbalanced Dataset (95% negative, 5% positive)**
- Total predictions: 1,000 (50 positive, 950 negative)
- Naive model: Always predict negative
- Correct predictions: 950 (all negatives)
- Accuracy: 950 / 1,000 = 95%
- **Interpretation**: High accuracy but useless model; misses all positives!

**Example 3: Multi-Class Classification (3 classes)**
- Total predictions: 900 (300 per class)
- Correct predictions: Class A: 270, Class B: 240, Class C: 225
- Total correct: 735
- Accuracy: 735 / 900 = 81.7%
- **Interpretation**: Good overall, but check per-class accuracy for balance

### Trends to Watch

**Declining accuracy over time:**
- **Model drift**: Input features changing distribution (covariate shift)
- **Concept drift**: Relationship between features and target changing
- **Data quality degradation**: Issues in upstream pipelines
- **Population shift**: Different types of users or transactions
- **Action**: Investigate drift metrics, validate data quality, consider retraining

**Sudden accuracy drop:**
- **Data pipeline failure**: Missing features, incorrect feature engineering
- **Label issues**: Ground truth labels incorrect or delayed
- **System integration change**: New data source or API
- **Outlier event**: Unusual conditions not in training data
- **Action**: Check recent deployments, validate data pipeline, review logs

**Improving accuracy trend:**
- **Model update**: Recent retraining with new data
- **Better features**: New or improved feature engineering
- **Data quality fix**: Resolution of upstream issues
- **Population stabilization**: Initial deployment volatility settling
- **Action**: Document improvements, monitor for stability

**High variance day-to-day:**
- **Small sample size**: Few predictions per day causing noise
- **Periodic patterns**: Day-of-week or time-of-day effects
- **Segmentation issues**: Mixed populations with different accuracy
- **Action**: Increase time bucket size (weekly), segment analysis

**Accuracy stable but business metrics declining:**
- **Threshold misalignment**: Wrong decision threshold for business objectives
- **Class-specific issues**: One class doing poorly but overall accuracy masked
- **Cost asymmetry**: False positives and false negatives have different business impact
- **Action**: Analyze confusion matrix, review thresholds, consider cost-sensitive metrics

### When to Investigate

**Immediate investigation (within 24 hours):**
1. **Accuracy drops below 60%** (or 10pp below baseline) - Severe degradation
2. **Accuracy drops >15pp in one day** - Likely system issue
3. **Accuracy at 0% or 100%** (suspicious) - Possible metric error or data issue
4. **Zero predictions recorded** - Data pipeline failure

**Planned investigation (within 1 week):**
1. **Accuracy below SLA for 3+ consecutive days** - Sustained underperformance
2. **Accuracy declining >5pp per week** - Gradual drift
3. **High accuracy variance (>10pp daily swings)** - Stability concerns
4. **Accuracy improvement plateau** - Assess if further gains possible

**Regular review (monthly):**
1. **Accuracy at 70-80% (fair range)** - Room for improvement
2. **Benchmark against alternatives** - Simpler models, baselines
3. **Segment-specific accuracy** - Per-class or per-population analysis
4. **Seasonal patterns** - Document expected variations

### Investigation Checklist

When accuracy degrades:

1. **Check data quality:**
   ```sql
   SELECT
       COUNT(*) as total_rows,
       COUNT({{prediction_label_col}}) as non_null_preds,
       COUNT({{ground_truth_col}}) as non_null_labels,
       COUNT(DISTINCT {{prediction_label_col}}) as unique_pred_labels,
       COUNT(DISTINCT {{ground_truth_col}}) as unique_actual_labels
   FROM {{dataset}}
   WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days';
   ```
   **Expected**: Both columns non-NULL, reasonable number of unique labels

2. **Analyze confusion matrix:**
   ```sql
   SELECT
       {{prediction_label_col}} as predicted,
       {{ground_truth_col}} as actual,
       COUNT(*) as count,
       ROUND(COUNT(*)::float / SUM(COUNT(*)) OVER () * 100, 1) as percentage
   FROM {{dataset}}
   WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days'
   GROUP BY predicted, actual
   ORDER BY predicted, actual;
   ```
   **Use**: Identify which predictions are wrong (false positives vs false negatives)

3. **Check class balance:**
   ```sql
   SELECT
       {{ground_truth_col}} as actual_label,
       COUNT(*) as count,
       ROUND(COUNT(*)::float / SUM(COUNT(*)) OVER () * 100, 1) as percentage
   FROM {{dataset}}
   WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '30 days'
   GROUP BY actual_label
   ORDER BY actual_label;
   ```
   **Expected**: Reasonable balance (if 99/1, accuracy may be misleading)

4. **Per-class accuracy:**
   ```sql
   WITH predictions AS (
       SELECT
           {{ground_truth_col}} as actual,
           {{prediction_label_col}} as predicted,
           CASE WHEN {{prediction_label_col}} = {{ground_truth_col}} THEN 1.0 ELSE 0.0 END as correct
       FROM {{dataset}}
       WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days'
   )
   SELECT
       actual as class_label,
       COUNT(*) as total_in_class,
       SUM(correct) as correct_in_class,
       AVG(correct) * 100 as per_class_accuracy
   FROM predictions
   GROUP BY actual
   ORDER BY actual;
   ```
   **Use**: Identify if specific classes have poor accuracy

5. **Compare to baseline:**
   - Calculate accuracy on validation set
   - Compare current to historical baseline (first 30/60 days)
   - Check if degradation aligns with known events

6. **Review recent changes:**
   - Model deployments or updates
   - Feature engineering changes
   - Data pipeline modifications
   - Upstream system integrations

***

## Use Cases

### Executive Dashboard KPI

**Problem**: CEO needs single-number model health indicator for monthly board presentations; accuracy is most intuitive metric for non-technical executives.

**Setup**:
- **Dataset**: `binary-classifier-card-fraud`
- **Prediction column**: `fraud_pred` (0/1)
- **Ground truth column**: `is_fraud` (0/1)
- **Reporting frequency**: Monthly average
- **Target**: ≥90% accuracy

**Dashboard Design**:
- **Primary metric**: Large number display "93.5% Accuracy"
- **Trend**: Arrow indicating change from previous month (+1.2%)
- **Sparkline**: 6-month trend showing stability
- **Context**: "Out of 100 transactions, model correctly identifies 93-94"

**Business Communication**:
- **To CEO**: "Our fraud detection model is 93.5% accurate, exceeding our 90% target"
- **To Board**: "Model accuracy improved 1.2% this quarter through retraining"
- **To Investors**: "High accuracy enables 70% of transactions to be auto-approved, reducing operational costs"

**Complementary Metrics** (technical appendix):
- Precision: 85% (of predicted fraud, 85% were actually fraud)
- Recall: 78% (of actual fraud, we caught 78%)
- F1-Score: 81% (harmonic mean of precision and recall)

**Outcome**:
- Clear communication of model value to stakeholders
- Simple target for accountability ("maintain 90% accuracy")
- Easy comparison across time periods and model versions

### SLA Monitoring for Production Models

**Problem**: Technology company manages 15 ML models in production; need standardized quality metric for SLA compliance and alerting.

**Setup**:
- **All models**: Deploy percentage accuracy metric
- **SLA tiers**:
  - **Critical models** (fraud, credit): ≥90% accuracy
  - **High-priority models** (recommendations, search): ≥85% accuracy
  - **Standard models** (categorization, tagging): ≥75% accuracy
- **Monitoring**: Daily calculation, automated alerts

**SLA Dashboard**:

| Model | Accuracy Target | Current Accuracy | Status | Days Below SLA |
|-------|----------------|------------------|--------|----------------|
| Fraud Detection | ≥90% | 92.3% | ✅ Pass | 0 |
| Credit Scoring | ≥90% | 88.7% | ⚠️ Warning | 2 |
| Product Recommendations | ≥85% | 87.1% | ✅ Pass | 0 |
| Search Ranking | ≥85% | 83.4% | ⚠️ Warning | 5 |
| Image Tagging | ≥75% | 79.2% | ✅ Pass | 0 |

**Alerting Rules**:
- **Warning**: Accuracy 5pp below target for 3+ days
- **Critical**: Accuracy 10pp below target for 1+ day
- **Escalation**: Critical alert unresolved for 48 hours → page on-call

**Response Workflow**:
1. **Warning alert**: ML engineer investigates within 24 hours
2. **Analysis**: Check data quality, drift metrics, confusion matrix
3. **Action**: If systemic issue, schedule retraining; if data issue, fix pipeline
4. **Resolution**: Monitor for 7 days to confirm accuracy recovered

**Outcome**:
- Standardized quality measurement across all models
- Automated early warning system
- Clear accountability and response protocols
- Documented SLA compliance for audits

### A/B Testing Model Versions

**Problem**: E-commerce company testing new product recommendation model (Model B) against production model (Model A); need to determine if accuracy improvement justifies deployment complexity.

**Setup**:
- **Traffic split**: 50/50 for 30 days
- **Prediction column**: `recommended_category_pred`
- **Ground truth column**: `actual_category` (based on purchase)
- **Primary metric**: Percentage accuracy
- **Secondary metrics**: Per-category accuracy, click-through rate

**Results**:

| Metric | Model A (Production) | Model B (Candidate) | Improvement |
|--------|---------------------|---------------------|-------------|
| **Overall Accuracy** | **81.3%** | **84.7%** | **+3.4pp** |
| Electronics Accuracy | 78.5% | 85.2% | +6.7pp |
| Apparel Accuracy | 83.1% | 84.9% | +1.8pp |
| Home Goods Accuracy | 82.0% | 83.9% | +1.9pp |
| Click-Through Rate | 12.3% | 13.8% | +1.5pp |
| Revenue per User | $4.52 | $4.89 | +8.2% |

**Statistical Analysis**:
- Sample size: Model A: 245,000 predictions, Model B: 238,000 predictions
- Statistical significance: p < 0.001 (highly significant)
- Confidence interval: Model B is 2.9-3.9pp better than Model A (95% CI)

**Business Decision**:
- **Deploy Model B**: 3.4pp accuracy improvement is significant
- **Expected impact**: 3,400 more correct recommendations per 100,000 users
- **Revenue impact**: +8.2% revenue per user justifies deployment effort
- **Rollout plan**: Gradual rollout over 2 weeks, monitor daily accuracy

**Presentation to Leadership**:
- "Model B is 84.7% accurate vs. 81.3% for current model"
- "3.4% improvement means 3,400 more users see relevant recommendations per 100,000"
- "Translates to 8.2% revenue increase per user, or ~$3M annual impact"

### Credit Approval Quality Gate

**Problem**: Financial institution implementing new credit scoring model; regulatory requirements demand accuracy threshold before production deployment.

**Setup**:
- **Dataset**: `binary-classifier-cc-application`
- **Prediction column**: `approval_pred`
- **Ground truth column**: `is_approved`
- **Validation period**: 90 days historical data
- **Quality gate**: Accuracy ≥80% on validation set

**Validation Results**:

| Time Period | Accuracy | Sample Size | Status |
|-------------|----------|-------------|--------|
| Month 1 (Jan) | 82.3% | 15,423 | ✅ Pass |
| Month 2 (Feb) | 81.7% | 14,891 | ✅ Pass |
| Month 3 (Mar) | 83.1% | 16,204 | ✅ Pass |
| **Overall (90 days)** | **82.4%** | **46,518** | **✅ Pass** |

**Per-Segment Validation**:
- **Prime credit (>720)**: 89.2% accuracy
- **Near-prime (660-720)**: 81.5% accuracy
- **Subprime (<660)**: 74.8% accuracy ⚠️

**Regulatory Documentation**:
1. **Overall accuracy**: 82.4% exceeds 80% threshold
2. **Temporal stability**: Consistent across 3 months (81.7-83.1%)
3. **Segment analysis**: Prime and near-prime meet standards; subprime flagged for improvement
4. **Complementary metrics**:
   - False positive rate: 14.2% (approve denied applications)
   - False negative rate: 21.4% (deny approved applications)
   - Bias analysis: No significant disparities by protected class

**Deployment Decision**:
- **Approved for production** with conditions:
  - Deploy for prime and near-prime segments only (89.2% and 81.5% accuracy)
  - Manual review required for subprime segment (74.8% accuracy below threshold)
  - Quarterly revalidation to maintain accuracy above 80%
  - Subprime model improvement project initiated

**Outcome**:
- Clear, defensible quality gate based on industry standards
- Regulatory approval with documented validation
- Risk mitigation through segmented deployment
- Continuous improvement roadmap for underperforming segments

### Production Monitoring with Drill-Down

**Problem**: Fraud detection model accuracy dropped from 94% to 87% over 2 weeks; need to identify root cause and implement fix.

**Setup**:
- **Baseline accuracy**: 94% (first 60 days of production)
- **Current accuracy**: 87% (last 7 days)
- **Alert triggered**: Accuracy below 90% threshold for 5 consecutive days
- **Investigation approach**: Drill down from overall to segment-specific accuracy

**Overall Accuracy Trend**:
```
Week 1: 94%
Week 2: 93%
Week 3: 92%
Week 4: 91%
Week 5: 89% ⚠️ Alert
Week 6: 87% 🚨 Critical
```

**Drill-Down Analysis**:

**1. By Channel:**
```sql
SELECT
    channel,
    AVG(CASE WHEN fraud_pred = is_fraud THEN 1.0 ELSE 0.0 END) * 100 as accuracy
FROM fraud_transactions
WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY channel;
```

| Channel | Baseline Accuracy | Current Accuracy | Change |
|---------|------------------|------------------|--------|
| In-Store | 96% | 95% | -1pp |
| E-Commerce | 93% | 82% | **-11pp** 🚨 |
| ATM | 92% | 91% | -1pp |

**Root cause identified**: E-commerce accuracy dropped significantly

**2. By Transaction Amount (E-Commerce):**
| Amount Range | Baseline | Current | Change |
|--------------|----------|---------|--------|
| $0-$50 | 95% | 94% | -1pp |
| $50-$200 | 94% | 93% | -1pp |
| $200-$500 | 92% | 78% | **-14pp** 🚨 |
| $500+ | 90% | 89% | -1pp |

**Root cause refined**: E-commerce transactions in $200-$500 range

**3. Temporal Analysis:**
```sql
-- Daily accuracy for affected segment
SELECT
    DATE(timestamp) as date,
    AVG(CASE WHEN fraud_pred = is_fraud THEN 1.0 ELSE 0.0 END) * 100 as accuracy,
    COUNT(*) as volume
FROM fraud_transactions
WHERE channel = 'ecom'
    AND txn_amount BETWEEN 200 AND 500
    AND timestamp >= CURRENT_DATE - INTERVAL '14 days'
GROUP BY date
ORDER BY date;
```

**Finding**: Accuracy drop started 10 days ago, coinciding with holiday sale promotion

**Investigation Results**:
- **Population shift**: Holiday promotions drove 3x increase in $200-$500 e-commerce transactions
- **New fraud patterns**: Promotional abuse not represented in training data
- **Feature drift**: `average_transaction_amount` feature now less predictive

**Remediation**:
1. **Short-term**: Lower confidence threshold for $200-$500 e-commerce (more manual review)
2. **Medium-term**: Add promotional fraud indicators as features
3. **Long-term**: Retrain model with last 90 days including promotion period

**Post-Fix Results**:
- Week 7: 89% accuracy (improved 2pp from short-term fix)
- Week 8: 91% accuracy (new features deployed)
- Week 10: 93% accuracy (retrained model deployed)

**Outcome**:
- Drill-down analysis identified specific segment causing overall drop
- Targeted remediation more efficient than full model retraining
- Documented pattern for future seasonal events

### Multi-Model Comparison and Selection

**Problem**: Healthcare system evaluating three disease screening models; need to select best model considering accuracy, interpretability, and operational constraints.

**Setup**:
- **Task**: Binary classification (disease present/absent)
- **Evaluation dataset**: 50,000 patients (10% disease prevalence)
- **Models**:
  - **Model A**: Logistic regression (highly interpretable)
  - **Model B**: Random forest (moderate complexity)
  - **Model C**: Deep neural network (black box)

**Accuracy Results**:

| Model | Overall Accuracy | Positive Class Accuracy | Negative Class Accuracy |
|-------|-----------------|------------------------|------------------------|
| Model A (Logistic) | 89.2% | 72.0% | 91.1% |
| Model B (Random Forest) | 91.5% | 78.5% | 92.7% |
| Model C (Neural Net) | 92.8% | 81.2% | 93.5% |

**Additional Metrics**:

| Model | Precision | Recall | F1-Score | Inference Time |
|-------|-----------|--------|----------|----------------|
| Model A | 68% | 72% | 70% | 1ms |
| Model B | 73% | 78% | 75% | 15ms |
| Model C | 77% | 81% | 79% | 45ms |

**Decision Framework**:

**Technical Perspective**:
- **Model C**: Highest accuracy (92.8%), best recall (81%)
- **Trade-off**: Black box, slower inference (45ms vs 1ms)

**Clinical Perspective**:
- **Interpretability requirement**: Physicians need to understand model reasoning
- **Model A**: Easily explainable coefficients
- **Model C**: Difficult to explain to patients and clinicians

**Operational Perspective**:
- **Volume**: 10,000 screenings per day
- **Latency requirement**: <100ms per screening
- **All models**: Meet latency requirement (max 45ms)

**Regulatory Perspective**:
- **FDA requirement**: Model validation and documentation
- **Model A**: Simple, well-documented, easy to validate
- **Model C**: Complex, requires extensive validation

**Decision**:
- **Deploy Model B (Random Forest)**: 91.5% accuracy
- **Rationale**:
  - **Good accuracy**: 91.5% vs 92.8% for Model C (only 1.3pp difference)
  - **Interpretable**: Feature importance readily available
  - **Operationally viable**: 15ms inference time acceptable
  - **Regulatory friendly**: Simpler validation than neural network
  - **Risk-aware**: 78% recall acceptable with physician review workflow

**Deployment Plan**:
- Model B deployed with 70% confidence threshold
- Predictions <70% routed to physician review
- Model C kept in staging for continued evaluation
- Annual revalidation to compare all three models

**Outcome**:
- Accuracy not the sole decision criterion
- Holistic evaluation considering interpretability, operations, regulation
- 91.5% accuracy sufficient for clinical workflow with human oversight

***

## Debugging & Verification

If the metric returns empty or unexpected values, use these queries to diagnose:

### 1. Verify data exists and is valid

```sql
SELECT
    COUNT(*) as total_rows,
    COUNT({{timestamp_col}}) as non_null_timestamps,
    COUNT({{prediction_label_col}}) as non_null_predictions,
    COUNT({{ground_truth_col}}) as non_null_labels,
    COUNT(*) FILTER (WHERE {{prediction_label_col}} = {{ground_truth_col}}) as correct_predictions,
    MIN({{timestamp_col}}) as earliest_timestamp,
    MAX({{timestamp_col}}) as latest_timestamp
FROM {{dataset}};
```

**Expected**:
- All counts > 0
- `correct_predictions` should be reasonable percentage of total
- Timestamp range should cover recent data

### 2. Check label distributions

```sql
-- Predicted labels
SELECT
    {{prediction_label_col}} as predicted_label,
    COUNT(*) as count,
    ROUND(COUNT(*)::float / SUM(COUNT(*)) OVER () * 100, 2) as percentage
FROM {{dataset}}
WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY predicted_label
ORDER BY predicted_label;

-- Actual labels
SELECT
    {{ground_truth_col}} as actual_label,
    COUNT(*) as count,
    ROUND(COUNT(*)::float / SUM(COUNT(*)) OVER () * 100, 2) as percentage
FROM {{dataset}}
WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY actual_label
ORDER BY actual_label;
```

**Expected**:
- Both predicted and actual should have same label values (e.g., 0 and 1)
- Predicted distribution should be somewhat close to actual distribution
- Extreme imbalance (99/1) may indicate issues

### 3. Manual accuracy calculation on sample

```sql
WITH sample_data AS (
    SELECT
        {{prediction_label_col}} as pred,
        {{ground_truth_col}} as actual,
        CASE WHEN {{prediction_label_col}} = {{ground_truth_col}} THEN 1 ELSE 0 END as correct
    FROM {{dataset}}
    WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days'
    LIMIT 100
)
SELECT
    COUNT(*) as sample_size,
    SUM(correct) as correct_count,
    AVG(correct::float) * 100 as accuracy_pct,
    COUNT(*) FILTER (WHERE pred = 1 AND actual = 1) as true_positives,
    COUNT(*) FILTER (WHERE pred = 0 AND actual = 0) as true_negatives,
    COUNT(*) FILTER (WHERE pred = 1 AND actual = 0) as false_positives,
    COUNT(*) FILTER (WHERE pred = 0 AND actual = 1) as false_negatives
FROM sample_data;
```

**Expected**:
- `accuracy_pct` should match your metric value
- Confusion matrix components should sum to `sample_size`

### 4. Test with known values

```sql
WITH test_cases AS (
    SELECT 1 as pred, 1 as actual, 'True Positive' as type
    UNION ALL SELECT 0, 0, 'True Negative'
    UNION ALL SELECT 1, 0, 'False Positive'
    UNION ALL SELECT 0, 1, 'False Negative'
)
SELECT
    type,
    pred,
    actual,
    CASE WHEN pred = actual THEN 1 ELSE 0 END as is_correct,
    CASE WHEN pred = actual THEN 'Correct' ELSE 'Incorrect' END as result
FROM test_cases;
```

**Expected output**:
- True Positive: Correct
- True Negative: Correct
- False Positive: Incorrect
- False Negative: Incorrect

### 5. Check for label mismatch

```sql
-- Identify unique label values in each column
WITH pred_labels AS (
    SELECT DISTINCT {{prediction_label_col}} as label, 'predicted' as source
    FROM {{dataset}}
    WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days'
),
actual_labels AS (
    SELECT DISTINCT {{ground_truth_col}} as label, 'actual' as source
    FROM {{dataset}}
    WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days'
)
SELECT * FROM pred_labels
UNION ALL
SELECT * FROM actual_labels
ORDER BY source, label;
```

**Expected**:
- Same label values in both columns (e.g., both have 0 and 1)
- No unexpected values (e.g., -1, 2, NULL)

### 6. Verify accuracy calculation method

```sql
SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) as day,
    -- Method 1: AVG of binary flags
    AVG(CASE WHEN {{prediction_label_col}} = {{ground_truth_col}} THEN 1.0 ELSE 0.0 END) * 100 as accuracy_method1,
    -- Method 2: SUM / COUNT
    SUM(CASE WHEN {{prediction_label_col}} = {{ground_truth_col}} THEN 1 ELSE 0 END)::float / COUNT(*) * 100 as accuracy_method2,
    COUNT(*) as total_count
FROM {{dataset}}
WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY day
ORDER BY day;
```

**Expected**:
- `accuracy_method1` should equal `accuracy_method2` (verification)
- Both should match your metric value

### Common Issues

- **Accuracy at 0%**: All predictions wrong; check if labels are inverted (0/1 swapped)
- **Accuracy at 100%**: All predictions correct; check for data leakage or test set contamination
- **Accuracy near 50%**: Random guessing (for balanced binary); model not learning
- **Accuracy at class balance %**: Model may be predicting only majority class (e.g., 95% accuracy with 95% negative class)
- **Empty results**: Check timestamp range, verify prediction and label columns exist
- **Unexpected labels**: Check if labels are encoded correctly (0/1 vs 1/2, or false/true)
- **Accuracy differs from manual**: Check NULL handling, ensure same time range

***

## Dataset Compatibility

This metric is compatible with any classification dataset containing predicted and actual class labels.

### Compatible Datasets from `/data` folder:

#### 1. binary-classifier-card-fraud

**Column Mapping:**
- `timestamp` (timestamp) → `timestamp_col`
- `fraud_pred` (int, 0/1) → `prediction_label_col`
- `is_fraud` (int, 0/1) → `ground_truth_col`

**Recommended Configuration:**
- **Target accuracy**: ≥90% (high-stakes fraud detection)
- **Monitoring frequency**: Daily
- **Alert threshold**: Accuracy <88% for 2+ days

**Example Interpretation**:
- **94% accuracy**: 94 out of 100 fraud predictions are correct
- **Confusion matrix context**:
  - True positives: Correctly flagged fraud
  - True negatives: Correctly approved legitimate transactions
  - False positives: Legitimate transactions flagged as fraud (customer friction)
  - False negatives: Fraud transactions missed (financial loss)

**Use Cases**:
- High-level dashboard for fraud operations team
- SLA compliance monitoring ("maintain ≥90% accuracy")
- A/B testing fraud model updates
- Executive reporting on fraud prevention effectiveness

**Important Note**:
- Fraud is typically imbalanced (~5% positive in this dataset)
- Accuracy alone may be misleading
- **Must pair with**:
  - Precision: Of flagged transactions, how many are actually fraud?
  - Recall: Of actual fraud, what percentage do we catch?
  - F1-Score: Harmonic mean of precision and recall

#### 2. binary-classifier-cc-application

**Column Mapping:**
- `timestamp` (timestamp) → `timestamp_col`
- Derived from `approval_score` or separate `approval_pred` column → `prediction_label_col`
- `is_approved` (int, 0/1) → `ground_truth_col`

**Note on Prediction Column**:
- If dataset has `approval_score` (probability), derive binary prediction:
  ```sql
  CASE WHEN approval_score >= 0.5 THEN 1 ELSE 0 END as approval_pred
  ```
- Or create separate column in data generation

**Recommended Configuration:**
- **Target accuracy**: ≥82% (credit decision typical)
- **Monitoring frequency**: Weekly (less volatile than fraud)
- **Alert threshold**: Accuracy <78% for 1+ week

**Example Interpretation**:
- **85% accuracy**: 85 out of 100 credit decisions are correct
- **Business context**:
  - True positives: Correctly approved creditworthy applicants (revenue)
  - True negatives: Correctly denied risky applicants (avoid defaults)
  - False positives: Approved risky applicants (potential defaults/losses)
  - False negatives: Denied creditworthy applicants (lost revenue)

**Use Cases**:
- Credit risk committee reporting
- Regulatory compliance documentation
- Model performance tracking for annual revalidation
- Comparison across demographic segments (fairness analysis)

**Important Note**:
- Credit approval has asymmetric costs
- False positives (approve defaulters) more costly than false negatives (reject good applicants)
- **Must pair with**:
  - Default rate among approved applications
  - Approval rate by risk segment
  - Per-segment accuracy (fairness analysis)

### Data Requirements

**Essential:**
- Timestamp column (for time-series aggregation)
- Predicted label column (int or bool: 0/1, false/true, or multi-class integers)
- Ground truth label column (int or bool: 0/1, false/true, or multi-class integers)
- **Labels must be comparable** (same encoding: both 0/1, not one 0/1 and other 1/2)

**Optional but Recommended:**
- Segmentation columns (region, customer type, product category) for drill-down
- Model version identifier (for A/B testing and version comparison)
- Prediction confidence/probability (for threshold analysis and calibration)
- Feature columns (for investigating accuracy drops)

### Notes

**Interpreting High Accuracy on Imbalanced Data:**

When class imbalance exists (e.g., 95% negative, 5% positive):

1. **Calculate balanced accuracy**:
   ```
   Balanced Accuracy = (Sensitivity + Specificity) / 2
                     = (Recall_positive + Recall_negative) / 2
   ```

2. **Check per-class accuracy**:
   ```sql
   -- Accuracy for positive class (sensitivity/recall)
   SELECT
       SUM(CASE WHEN {{prediction_label_col}} = 1 AND {{ground_truth_col}} = 1 THEN 1 ELSE 0 END)::float /
       NULLIF(SUM(CASE WHEN {{ground_truth_col}} = 1 THEN 1 ELSE 0 END), 0) * 100
       as positive_class_accuracy
   FROM {{dataset}};

   -- Accuracy for negative class (specificity)
   SELECT
       SUM(CASE WHEN {{prediction_label_col}} = 0 AND {{ground_truth_col}} = 0 THEN 1 ELSE 0 END)::float /
       NULLIF(SUM(CASE WHEN {{ground_truth_col}} = 0 THEN 1 ELSE 0 END), 0) * 100
       as negative_class_accuracy
   FROM {{dataset}};
   ```

3. **Baseline comparison**:
   - Always-predict-majority-class baseline
   - For 95% negative, baseline accuracy = 95%
   - Your model must exceed this to be useful

**When Accuracy is Sufficient Alone:**
- Balanced datasets (40-60% each class)
- Equal costs of false positives and false negatives
- High-level monitoring and communication

**When Accuracy is Insufficient:**
- Imbalanced datasets (>70/30 split)
- Asymmetric costs (one error type more costly)
- Need for confidence calibration
- Class-specific performance requirements

**Best Practices:**
- Always report accuracy alongside precision, recall, F1
- Visualize confusion matrix for complete picture
- Document class balance in dataset
- Set accuracy targets based on business requirements, not arbitrary thresholds
- Monitor per-class accuracy for fairness and balance
- Use accuracy for communication, complement with technical metrics for decisions

**Multi-Class Extension:**
For multi-class classification (K > 2 classes):
- Same formula: (correct predictions / total) × 100
- Consider per-class accuracy: accuracy for each class separately
- Macro-average accuracy: average of per-class accuracies (treats all classes equally)
- Micro-average accuracy: same as overall accuracy (treats all predictions equally)
- Works without SQL modifications (prediction = ground_truth comparison handles any number of classes)
