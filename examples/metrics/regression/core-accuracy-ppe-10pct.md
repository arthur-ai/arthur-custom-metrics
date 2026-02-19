# Core Accuracy at PPE 10% Threshold

## Overview

**Core Accuracy at PPE 10% Threshold** measures the proportion of predictions that fall within 10% of the actual value, providing an intuitive pass/fail assessment of model reliability. Unlike traditional error metrics that average errors, this metric counts each prediction as either "accurate" (within threshold) or "inaccurate" (outside threshold), making it ideal for SLAs, operational monitoring, and communicating model quality to non-technical stakeholders.

**Key Insights:**
- Binary accuracy assessment: predictions either pass (≤10% error) or fail (>10% error)
- Intuitive interpretation: "85% of predictions were accurate" is clearer than "MAPE is 7.3%"
- Operational alignment: matches business decision-making (good enough vs. not good enough)
- Robust to outliers: single extreme error doesn't skew metric as much as MAPE or RMSE
- SLA-ready: enables clear quality gates and service level objectives

**When to Use:**
- **SLA monitoring**: Set contractual accuracy requirements ("model must achieve 80% core accuracy")
- **Operational dashboards**: Real-time quality monitoring ("95 of last 100 predictions accurate")
- **A/B testing**: Compare model versions ("Model B has 5% higher core accuracy")
- **Quality gates**: Deployment criteria ("only deploy if core accuracy >85% on validation set")
- **Stakeholder communication**: Business-friendly metric for executive dashboards
- **Regression model evaluation**: Complement to MAPE, MAE, RMSE for comprehensive assessment

***

## Step 1: Write the SQL

This SQL computes the proportion of predictions that fall within a specified percentage error threshold (default 10%).

```sql
WITH
  valid_predictions AS (
    -- Filter to valid predictions with non-zero actuals for percentage calculation
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_col}}::float AS prediction,
      {{ground_truth_col}}::float AS actual
    FROM {{dataset}}
    WHERE {{timestamp_col}} IS NOT NULL
      AND {{prediction_col}} IS NOT NULL
      AND {{ground_truth_col}} IS NOT NULL
      -- Exclude zero actuals to avoid division by zero in percentage error
      AND {{ground_truth_col}} != 0
      -- Precision safeguard: exclude very small actuals to prevent numerical instability
      AND ABS({{ground_truth_col}}) > 0.0001
  ),

  accuracy_flags AS (
    -- Flag each prediction as accurate (1.0) or inaccurate (0.0) based on threshold
    SELECT
      ts,
      prediction,
      actual,
      -- Calculate absolute percentage error
      ABS((prediction - actual) / actual) AS abs_pct_error,
      -- Binary flag: 1.0 if within threshold, 0.0 if outside
      CASE
        WHEN ABS((prediction - actual) / actual) <= {{threshold}} THEN 1.0
        ELSE 0.0
      END AS is_accurate
    FROM valid_predictions
  )

-- Aggregate to get accuracy rate, accurate count, and total count per day
SELECT
  ts,
  AVG(is_accurate)::float AS core_accuracy_rate,
  SUM(is_accurate)::int AS accurate_predictions_count,
  COUNT(*)::int AS total_predictions_count,
  AVG(abs_pct_error)::float AS avg_percentage_error
FROM accuracy_flags
GROUP BY ts
ORDER BY ts;
```

**What this query returns:**

* `ts` — timestamp bucket (1 day)
* `core_accuracy_rate` — proportion of accurate predictions (float, 0.0 to 1.0)
* `accurate_predictions_count` — count of predictions within threshold (integer)
* `total_predictions_count` — total number of valid predictions evaluated (integer)
* `avg_percentage_error` — average absolute percentage error across all predictions (float)

**SQL Logic:**

1. **valid_predictions CTE**:
   - Filters out NULL values in timestamp, prediction, and ground truth columns
   - Excludes zero actuals (`!= 0`) to prevent division by zero
   - Applies precision safeguard (`ABS(actual) > 0.0001`) to exclude very small values that could cause numerical instability
   - Casts predictions and actuals to float for consistent calculation
   - Groups by daily time buckets using `time_bucket(INTERVAL '1 day', ...)`

2. **accuracy_flags CTE**:
   - Calculates absolute percentage error: `|prediction - actual| / |actual|`
   - Applies binary threshold test: `error <= threshold`
   - Returns `1.0` for accurate predictions (within threshold), `0.0` for inaccurate
   - Preserves individual percentage errors for additional reporting

3. **Final aggregation**:
   - `AVG(is_accurate)::float` computes accuracy rate (proportion of 1.0s)
   - `SUM(is_accurate)::int` counts accurate predictions (sum of 1.0s)
   - `COUNT(*)::int` counts total predictions evaluated
   - `AVG(abs_pct_error)::float` provides complementary error metric
   - Groups by day for time-series tracking

**Key Features:**
- Configurable threshold via `{{threshold}}` parameter
- Proper type casting for Arthur metrics storage (float for rates, int for counts)
- Comprehensive NULL and edge case handling
- Returns multiple metrics for detailed analysis
- Daily granularity balances detail with performance

***

## Step 2: Fill Basic Information

When creating the custom metric in the Arthur UI:

1. **Name**:
   `Core Accuracy at PPE 10% Threshold`

2. **Description** (optional but recommended):
   `Proportion of predictions where absolute percentage error is within 10% of actual value. Provides intuitive pass/fail assessment of model accuracy. Values represent the percentage of predictions considered "accurate" under the threshold criterion.`

***

## Step 3: Configure the Aggregate Arguments

You will set up five aggregate arguments to parameterize the SQL.

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Timestamp column for time-series bucketing and filtering`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Prediction Column

1. **Parameter Key:** `prediction_col`
2. **Friendly Name:** `Prediction Column`
3. **Description:** `Model's predicted value (continuous numeric)`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `prediction`
8. **Allowed Column Types:** `int, float`

### Argument 3 — Ground Truth Column

1. **Parameter Key:** `ground_truth_col`
2. **Friendly Name:** `Ground Truth Column`
3. **Description:** `Actual observed value (continuous numeric)`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `ground_truth`
8. **Allowed Column Types:** `int, float`

### Argument 4 — Accuracy Threshold

1. **Parameter Key:** `threshold`
2. **Friendly Name:** `Accuracy Threshold`
3. **Description:** `Maximum percentage error to be considered "accurate" (e.g., 0.10 for 10%, 0.05 for 5%, 0.20 for 20%)`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Float`
6. **Default Value:** `0.10` (10%)

**Threshold Selection Guidance:**
- **0.05 (5%)**: High-precision applications, strict accuracy requirements
- **0.10 (10%)**: Standard tolerance, recommended for most business applications
- **0.15 (15%)**: Lenient threshold for exploratory models or rough estimates
- **0.20 (20%)**: Very lenient, suitable for early-stage models or volatile domains

### Argument 5 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset containing predictions and ground truth values`
4. **Parameter Type:** `Dataset`

***

## Step 4: Configure Reported Metrics

This metric reports four values for comprehensive accuracy monitoring.

### Metric 1 — Core Accuracy Rate

1. **Metric Name:** `core_accuracy_rate`
2. **Description:** `Proportion of predictions where absolute percentage error is within the threshold (0.0 to 1.0 scale, multiply by 100 for percentage)`
3. **Value Column:** `core_accuracy_rate`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 2 — Accurate Predictions Count

1. **Metric Name:** `accurate_predictions_count`
2. **Description:** `Number of predictions that fell within the accuracy threshold`
3. **Value Column:** `accurate_predictions_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 3 — Total Predictions Count

1. **Metric Name:** `total_predictions_count`
2. **Description:** `Total number of valid predictions evaluated (excludes NULL values and zero actuals)`
3. **Value Column:** `total_predictions_count`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

### Metric 4 — Average Percentage Error

1. **Metric Name:** `avg_percentage_error`
2. **Description:** `Average absolute percentage error across all predictions (complementary metric to core accuracy)`
3. **Value Column:** `avg_percentage_error`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `-`

***

## Step 5: Dashboard Chart SQL

This query reads from the **metrics_numeric_latest_version** table to visualize stored accuracy metrics over time.

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
        WHEN metric_name = 'core_accuracy_rate' THEN 'Core Accuracy (%)'
        WHEN metric_name = 'accurate_predictions_count' THEN 'Accurate Count'
        WHEN metric_name = 'total_predictions_count' THEN 'Total Predictions'
        WHEN metric_name = 'avg_percentage_error' THEN 'Avg Error (%)'
        ELSE metric_name
    END AS friendly_name,

    -- Multiply rate by 100 for percentage display, keep others as-is
    CASE
        WHEN metric_name = 'core_accuracy_rate' THEN COALESCE(AVG(value), 0) * 100
        WHEN metric_name = 'avg_percentage_error' THEN COALESCE(AVG(value), 0) * 100
        ELSE COALESCE(AVG(value), 0)
    END AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'core_accuracy_rate',
    'accurate_predictions_count',
    'total_predictions_count',
    'avg_percentage_error'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**Query Explanation:**
- **`time_bucket_gapfill()`** - Creates continuous daily time series with no gaps
- **`{{dateStart}}` and `{{dateEnd}}`** - Template variables for configurable time range
- **`[[AND ...]]`** - Optional filter syntax in Arthur Platform
- **`metric_name IN (...)`** - Filters to the four metrics defined in Step 4
- **CASE for friendly_name** - Provides user-friendly display names
- **CASE for metric_value** - Multiplies rates/percentages by 100 for intuitive display (0.85 → 85%)
- **`COALESCE(AVG(value), 0)`** - Handles missing values gracefully

**Chart Configuration:**

**Option 1: Dual Y-Axis Line Chart (Recommended)**
- **Primary Y-axis (left)**: `core_accuracy_rate` (0-100%, target: >80%)
- **Secondary Y-axis (right)**: `total_predictions_count` (volume)
- **X-axis**: `time_bucket_1d` (daily time buckets)
- **Target line**: Horizontal line at 80% (or business-defined threshold)
- **Color coding**: Green if ≥80%, yellow if 70-80%, red if <70%

**Option 2: Multi-Metric Dashboard**
Create separate charts for each metric:

1. **Core Accuracy Trend** (line chart):
   - Y-axis: `core_accuracy_rate` (%)
   - Target band: 80-100% (green zone)
   - Alert threshold: <80% (red zone)

2. **Prediction Volume** (bar chart):
   - Y-axis: `total_predictions_count`
   - Shows daily prediction volume for context

3. **Accuracy vs Error Comparison** (dual-axis line chart):
   - Left Y-axis: `core_accuracy_rate` (%)
   - Right Y-axis: `avg_percentage_error` (%)
   - Inverse correlation expected

**What this shows:**
- Daily trend of core accuracy (how many predictions meet quality standard)
- Prediction volume (context for accuracy—low volume may inflate variance)
- Correlation between accuracy rate and average error
- Time periods with accuracy drops requiring investigation
- SLA compliance tracking (days above/below target threshold)
- Impact of model changes or retraining on accuracy

***

## Interpreting the Metric

### Value Ranges

**Threshold = 10% (0.10)**:

**Excellent (≥90% accuracy)**:
- 9 out of 10 predictions within 10% of actual value
- Model exceeds business requirements significantly
- Strong candidate for production deployment
- Maintain current model, monitor for drift

**Good (80-90% accuracy)**:
- 8-9 out of 10 predictions accurate
- Meets typical business SLA requirements
- Acceptable for most production use cases
- Continue monitoring, plan periodic retraining

**Fair (70-80% accuracy)**:
- 7-8 out of 10 predictions accurate
- Below typical production standards
- May be acceptable for non-critical applications or early-stage models
- Investigate improvement opportunities (features, architecture, training data)

**Poor (<70% accuracy)**:
- Fewer than 7 out of 10 predictions accurate
- Insufficient for most production deployments
- Significant model improvement needed
- Consider alternative approaches, additional features, or more training data

**Critical (<50% accuracy)**:
- Fewer than half of predictions accurate
- Model provides little value over simple baselines
- Major issues with model, features, or data quality
- Do not deploy; fundamental rework required

### Threshold Impact

The same model will show different accuracy rates with different thresholds:

**Example**: Model with 8% median error
- **5% threshold**: 45% accuracy (strict)
- **10% threshold**: 85% accuracy (standard)
- **20% threshold**: 95% accuracy (lenient)

**Choosing the right threshold:**
- Analyze your model's error distribution first
- Set threshold based on business tolerance, not model performance
- Consider consequences of inaccurate predictions in your domain
- Document threshold rationale for stakeholders

### Trends to Watch

**Declining accuracy over time:**
- **Model drift**: Input data distribution changing (features drifting from training distribution)
- **Concept drift**: Relationship between features and target changing
- **Data quality degradation**: Issues in upstream data pipelines
- **Seasonal effects**: Model trained on one season, deployed in another
- **Action**: Investigate drift metrics, check data quality, consider retraining

**Sudden accuracy drop:**
- **Data pipeline failure**: Missing features, incorrect feature engineering, unit changes
- **System integration issue**: New data source, API changes, schema modifications
- **Outlier event**: Unusual conditions not represented in training data
- **Action**: Check recent deployments, validate data pipeline, review error logs

**Improving accuracy trend:**
- **Model retraining**: Recent update with newer data improving performance
- **Data quality improvements**: Fixes to upstream data issues
- **Feature engineering**: New or improved features added
- **Population stabilization**: Initial deployment volatility settling
- **Action**: Document what worked, consider further improvements

**High variance day-to-day:**
- **Small sample size**: Few predictions per day causing statistical noise
- **Heterogeneous predictions**: Different subpopulations with varying accuracy
- **Intermittent data issues**: Sporadic data quality problems
- **Action**: Segment by subpopulation, increase time bucket size, investigate data stability

**Consistently high accuracy with high average error:**
- **Possible**: Many predictions just barely meet threshold (9.9% error)
- **Interpretation**: Model meets quality gate but not by comfortable margin
- **Action**: Review error distribution, consider tightening threshold or improving model

### When to Investigate

**Immediate investigation (within 24 hours):**
1. **Accuracy drops below 70%** (standard threshold) - Missing business SLA
2. **Accuracy drops >15 percentage points** in one day - Likely system issue
3. **Zero predictions recorded** - Data pipeline failure
4. **Accuracy at 0% or 100%** (suspicious) - Potential metric calculation error

**Planned investigation (within 1 week):**
1. **Accuracy below 80% for 3+ consecutive days** - Sustained performance degradation
2. **Accuracy declining >2% per week** - Gradual drift requiring attention
3. **Accuracy variance increases significantly** - Stability issues emerging
4. **Accuracy improvement opportunity** - Benchmark suggests headroom for gains

**Regular review (monthly):**
1. **Accuracy stable at 80-85%** - Meeting minimum SLA but room for improvement
2. **Seasonal accuracy patterns** - Document expected variations
3. **Segment-specific accuracy differences** - Some populations more accurate than others
4. **Benchmark against alternative approaches** - Opportunity cost analysis

### Investigation Checklist

When accuracy degrades:

1. **Check data quality:**
   ```sql
   SELECT
       COUNT(*) FILTER (WHERE {{prediction_col}} IS NULL) as null_predictions,
       COUNT(*) FILTER (WHERE {{ground_truth_col}} IS NULL) as null_actuals,
       COUNT(*) FILTER (WHERE {{ground_truth_col}} = 0) as zero_actuals,
       AVG({{prediction_col}}) as avg_prediction,
       AVG({{ground_truth_col}}) as avg_actual,
       COUNT(*) as total
   FROM {{dataset}}
   WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days';
   ```

2. **Analyze error distribution:**
   ```sql
   SELECT
       CASE
           WHEN ABS(({{prediction_col}} - {{ground_truth_col}}) / {{ground_truth_col}}) <= 0.05 THEN '0-5%'
           WHEN ABS(({{prediction_col}} - {{ground_truth_col}}) / {{ground_truth_col}}) <= 0.10 THEN '5-10%'
           WHEN ABS(({{prediction_col}} - {{ground_truth_col}}) / {{ground_truth_col}}) <= 0.20 THEN '10-20%'
           ELSE '>20%'
       END as error_bucket,
       COUNT(*) as count,
       ROUND(COUNT(*)::float / SUM(COUNT(*)) OVER () * 100, 1) as pct
   FROM {{dataset}}
   WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days'
       AND {{ground_truth_col}} != 0
   GROUP BY error_bucket
   ORDER BY error_bucket;
   ```

3. **Compare to baseline:**
   - Calculate accuracy on validation set or holdout data
   - Compare current accuracy to historical baseline
   - Check if accuracy drop aligns with known events

4. **Segment analysis:**
   - Break down accuracy by region, product type, or other segments
   - Identify if accuracy issues are global or segment-specific
   - Consider segment-specific models or recalibration

5. **Review recent changes:**
   - Model deployments or updates
   - Feature engineering changes
   - Data pipeline modifications
   - Upstream system integrations

***

## Use Cases

### Loan Amount Prediction SLA Monitoring

**Problem**: Credit union needs to ensure loan amount predictions are accurate enough for lending decisions; inaccurate predictions lead to defaults (overestimation) or lost revenue (underestimation).

**Setup**:
- **Prediction column**: `predicted_loan_amount`
- **Ground truth column**: `actual_loan_amount`
- **Threshold**: `0.10` (10%)
- **SLA requirement**: Core accuracy ≥ 80%

**Interpretation**:
- **85% accuracy** → 85 out of 100 loans predicted within 10% of approved amount
- **10% error on $50,000 loan** = ±$5,000 tolerance (acceptable for most lending decisions)
- **Drop to 75% accuracy** → Triggers investigation and possible model recalibration

**Dashboard Setup**:
- Primary chart: Daily core accuracy with 80% SLA line
- Alert: Email to ML team if accuracy <80% for 2+ consecutive days
- Monthly report: Accuracy trend, prediction volume, error distribution

**Action Plan**:
- **≥85% accuracy**: No action, continue monitoring
- **80-85% accuracy**: Monthly review, assess improvement opportunities
- **75-80% accuracy**: Weekly monitoring, plan retraining within 1 month
- **<75% accuracy**: Immediate investigation, expedite model refresh

### Demand Forecasting Quality Gate

**Problem**: Retail company needs reliable demand forecasts to optimize inventory; inaccurate forecasts cause either stockouts (lost sales) or excess inventory (waste/markdowns).

**Setup**:
- **Prediction column**: `predicted_demand`
- **Ground truth column**: `actual_sales`
- **Threshold**: `0.15` (15%, more lenient due to demand volatility)
- **Quality gate**: Must achieve ≥75% accuracy to deploy

**Interpretation**:
- **78% accuracy with 15% threshold** → Good enough for inventory planning
- **15% error on 1,000 unit forecast** = ±150 units (acceptable buffer for orders)
- **Seasonal variation**: Expect lower accuracy during holiday peaks

**Model Comparison**:
- **Baseline (seasonal average)**: 68% accuracy
- **Model A (LSTM)**: 76% accuracy (+8pp vs. baseline)
- **Model B (Prophet)**: 81% accuracy (+13pp vs. baseline, +5pp vs. Model A)
- **Decision**: Deploy Model B, 5pp improvement justifies complexity

**Action Plan**:
- Track accuracy by product category (apparel more volatile than staples)
- Accept 70-75% accuracy for highly volatile categories
- Use core accuracy as primary deployment criterion, complement with MAE

### Real Estate Pricing Model A/B Test

**Problem**: Real estate platform testing new pricing model; need to determine if Model B justifies replacing production Model A.

**Setup**:
- **Model A (production)**: Rule-based pricing
- **Model B (candidate)**: ML-based pricing
- **Threshold**: `0.05` (5%, strict for pricing accuracy)
- **Test period**: 30 days, 50/50 traffic split

**Results**:
- **Model A**: 72% core accuracy at 5% threshold
- **Model B**: 79% core accuracy at 5% threshold (+7pp)
- **Statistical significance**: p < 0.01 (significant improvement)

**Business Impact**:
- **7pp improvement** = 70 more accurate predictions per 1,000 properties
- **Pricing within 5%** critical for competitiveness and conversion
- **Expected revenue impact**: +3% conversion from better pricing

**Decision**:
- Deploy Model B to 100% of traffic
- Monitor core accuracy weekly for 3 months
- Target: Maintain ≥75% accuracy at 5% threshold

### Revenue Forecasting Executive Dashboard

**Problem**: CFO needs confidence in quarterly revenue forecasts for investor guidance; must communicate forecast reliability clearly.

**Setup**:
- **Prediction column**: `predicted_quarterly_revenue`
- **Ground truth column**: `actual_quarterly_revenue`
- **Threshold**: `0.10` (10%, ±10% revenue variance acceptable)
- **Audience**: Executive team, board of directors

**Communication**:
- **Core accuracy**: "Our forecast was accurate within 10% in 8 of the last 10 quarters (80% accuracy)"
- **Compare to MAPE**: "Average forecast error was 6.2%" (less intuitive)
- **Confidence**: "Based on historical accuracy, we expect Q4 forecast of $50M to fall between $45M-$55M"

**Dashboard Elements**:
- Line chart: Quarterly accuracy over 2 years (8 quarters)
- Bar chart: Actual vs predicted revenue by quarter with 10% error bands
- Scorecard: "Forecast Accuracy: 80%" in large text
- Trend: "Accuracy improving: 70% (2023) → 80% (2024)"

**Value**:
- **Business-friendly metric**: Non-technical audience understands "8 out of 10 accurate"
- **Builds trust**: Transparency about forecast limitations
- **Informs decisions**: Sets realistic expectations for revenue guidance

### Model Monitoring & Retraining Schedule

**Problem**: ML team manages 12 production models; need systematic approach to prioritize retraining efforts based on performance degradation.

**Setup**:
- Deploy core accuracy metric on all regression models
- **Threshold**: 0.10 (standardized across models)
- **Monitoring frequency**: Daily
- **Review frequency**: Weekly team review of all models

**Retraining Priority Matrix**:

| Model | Current Accuracy | Baseline Accuracy | Delta | Priority |
|-------|-----------------|-------------------|-------|----------|
| Loan Amount | 72% | 85% | -13pp | High (retrain this sprint) |
| House Price | 79% | 82% | -3pp | Medium (retrain within month) |
| Demand Forecast | 84% | 84% | 0pp | Low (monitor only) |
| Revenue Forecast | 88% | 85% | +3pp | None (no action) |

**Workflow**:
1. **Daily**: Automated alerts if accuracy drops >10pp from baseline
2. **Weekly**: Team reviews accuracy dashboard for all models
3. **Monthly**: Detailed accuracy report with error analysis
4. **Quarterly**: Baseline recalibration (update baseline to recent 3-month avg)

**Benefits**:
- **Objective prioritization**: Data-driven retraining decisions
- **Standardized metric**: Comparable across different model types
- **Early warning**: Catch degradation before business impact
- **Resource optimization**: Focus ML effort where impact is greatest

### Credit Scoring Fairness Analysis

**Problem**: Ensure credit scoring model performs equally well across demographic groups; accuracy disparities may indicate bias or data quality issues.

**Setup**:
- **Prediction column**: `predicted_credit_limit`
- **Ground truth column**: `actual_credit_limit`
- **Threshold**: `0.10` (10%)
- **Segmentation**: Age groups, income brackets, geographic regions

**Accuracy by Segment** (example results):

| Segment | Accuracy | Sample Size | Action |
|---------|----------|-------------|--------|
| Age 18-30 | 76% | 5,000 | Investigate (low) |
| Age 31-50 | 84% | 12,000 | Good |
| Age 51+ | 82% | 8,000 | Good |
| Income <$50K | 78% | 6,000 | Monitor |
| Income $50-100K | 85% | 10,000 | Good |
| Income >$100K | 88% | 9,000 | Good |
| Urban | 83% | 15,000 | Good |
| Suburban | 84% | 8,000 | Good |
| Rural | 74% | 2,000 | Investigate (low) |

**Findings**:
- Young adults (18-30) and rural applicants have lower accuracy
- May indicate: insufficient training data, unique behaviors not captured, or data quality issues
- Not necessarily discrimination, but requires investigation

**Action Plan**:
1. Collect more training data for underrepresented segments
2. Add features specific to young adults and rural applicants
3. Consider segment-specific models or recalibration
4. Document accuracy differences in model card for transparency
5. Set minimum accuracy thresholds for all segments (e.g., ≥75% for deployment)

***

## Debugging & Verification

If the metric returns empty or unexpected values, use these queries to diagnose the issue:

### 1. Verify data exists and is valid

```sql
SELECT
    COUNT(*) as total_rows,
    COUNT({{timestamp_col}}) as non_null_timestamps,
    COUNT({{prediction_col}}) as non_null_predictions,
    COUNT({{ground_truth_col}}) as non_null_actuals,
    COUNT(*) FILTER (WHERE {{ground_truth_col}} != 0) as non_zero_actuals,
    COUNT(*) FILTER (WHERE ABS({{ground_truth_col}}) > 0.0001) as actuals_above_threshold,
    MIN({{timestamp_col}}) as earliest_timestamp,
    MAX({{timestamp_col}}) as latest_timestamp
FROM {{dataset}};
```

**Expected**:
- All counts > 0
- `non_zero_actuals` and `actuals_above_threshold` should be high (most records valid)
- Timestamp range should cover recent data

### 2. Check prediction and actual value ranges

```sql
SELECT
    MIN({{prediction_col}}::float) as min_prediction,
    MAX({{prediction_col}}::float) as max_prediction,
    AVG({{prediction_col}}::float) as avg_prediction,
    STDDEV({{prediction_col}}::float) as stddev_prediction,
    MIN({{ground_truth_col}}::float) as min_actual,
    MAX({{ground_truth_col}}::float) as max_actual,
    AVG({{ground_truth_col}}::float) as avg_actual,
    STDDEV({{ground_truth_col}}::float) as stddev_actual
FROM {{dataset}}
WHERE {{timestamp_col}} IS NOT NULL
    AND {{prediction_col}} IS NOT NULL
    AND {{ground_truth_col}} IS NOT NULL
    AND {{ground_truth_col}} != 0;
```

**Expected**:
- Prediction and actual ranges should overlap significantly
- Averages should be relatively close (model not systematically biased)
- Check for unreasonable values (negative prices, impossible amounts)

### 3. Manually test accuracy calculation

```sql
WITH test_data AS (
    SELECT
        {{timestamp_col}} as ts,
        {{prediction_col}}::float as pred,
        {{ground_truth_col}}::float as actual,
        ABS(({{prediction_col}}::float - {{ground_truth_col}}::float) / {{ground_truth_col}}::float) as abs_pct_error,
        ABS(({{prediction_col}}::float - {{ground_truth_col}}::float) / {{ground_truth_col}}::float) <= {{threshold}} as is_accurate
    FROM {{dataset}}
    WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '7 days'
        AND {{timestamp_col}} IS NOT NULL
        AND {{prediction_col}} IS NOT NULL
        AND {{ground_truth_col}} IS NOT NULL
        AND {{ground_truth_col}} != 0
        AND ABS({{ground_truth_col}}) > 0.0001
    LIMIT 100
)
SELECT
    COUNT(*) as sample_size,
    SUM(CASE WHEN is_accurate THEN 1 ELSE 0 END) as accurate_count,
    AVG(CASE WHEN is_accurate THEN 1.0 ELSE 0.0 END) as accuracy_rate,
    MIN(abs_pct_error) as min_error,
    MAX(abs_pct_error) as max_error,
    AVG(abs_pct_error) as avg_error,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY abs_pct_error) as median_error
FROM test_data;
```

**Expected**:
- `accuracy_rate` should be between 0 and 1 (0-100%)
- `avg_error` gives sense of typical error magnitude
- `median_error` shows typical prediction quality (less sensitive to outliers)

### 4. Check error distribution

```sql
SELECT
    CASE
        WHEN ABS(({{prediction_col}}::float - {{ground_truth_col}}::float) / {{ground_truth_col}}::float) <= 0.05 THEN '0-5% (Excellent)'
        WHEN ABS(({{prediction_col}}::float - {{ground_truth_col}}::float) / {{ground_truth_col}}::float) <= 0.10 THEN '5-10% (Good)'
        WHEN ABS(({{prediction_col}}::float - {{ground_truth_col}}::float) / {{ground_truth_col}}::float) <= 0.20 THEN '10-20% (Fair)'
        WHEN ABS(({{prediction_col}}::float - {{ground_truth_col}}::float) / {{ground_truth_col}}::float) <= 0.50 THEN '20-50% (Poor)'
        ELSE '>50% (Very Poor)'
    END as error_bucket,
    COUNT(*) as count,
    ROUND(COUNT(*)::float / SUM(COUNT(*)) OVER () * 100, 1) as percentage
FROM {{dataset}}
WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '30 days'
    AND {{ground_truth_col}} != 0
    AND ABS({{ground_truth_col}}) > 0.0001
GROUP BY error_bucket
ORDER BY
    CASE
        WHEN error_bucket = '0-5% (Excellent)' THEN 1
        WHEN error_bucket = '5-10% (Good)' THEN 2
        WHEN error_bucket = '10-20% (Fair)' THEN 3
        WHEN error_bucket = '20-50% (Poor)' THEN 4
        ELSE 5
    END;
```

**Expected**:
- Majority of predictions in lower error buckets
- Helps understand what threshold would be appropriate
- Identifies outliers (very poor predictions)

### 5. Test with known values

```sql
WITH test_cases AS (
    SELECT 100.0 as actual, 95.0 as prediction, 0.10 as threshold
    UNION ALL SELECT 100.0, 110.0, 0.10
    UNION ALL SELECT 100.0, 90.0, 0.10
    UNION ALL SELECT 100.0, 89.0, 0.10
    UNION ALL SELECT 100.0, 111.0, 0.10
    UNION ALL SELECT 50000.0, 48000.0, 0.10
    UNION ALL SELECT 50000.0, 52000.0, 0.10
)
SELECT
    actual,
    prediction,
    threshold,
    ABS((prediction - actual) / actual) as abs_pct_error,
    ABS((prediction - actual) / actual) <= threshold as is_accurate,
    CASE
        WHEN ABS((prediction - actual) / actual) <= threshold THEN 'PASS'
        ELSE 'FAIL'
    END as result
FROM test_cases;
```

**Expected output**:
- 95.0: 5% error → PASS
- 110.0: 10% error → PASS (exactly at threshold)
- 90.0: 10% error → PASS
- 89.0: 11% error → FAIL
- 111.0: 11% error → FAIL
- 48000.0: 4% error → PASS
- 52000.0: 4% error → PASS

### 6. Check for systematic bias

```sql
SELECT
    COUNT(*) FILTER (WHERE {{prediction_col}} > {{ground_truth_col}}) as overestimates,
    COUNT(*) FILTER (WHERE {{prediction_col}} < {{ground_truth_col}}) as underestimates,
    COUNT(*) FILTER (WHERE {{prediction_col}} = {{ground_truth_col}}) as exact_matches,
    AVG(({{prediction_col}}::float - {{ground_truth_col}}::float) / {{ground_truth_col}}::float) as avg_relative_error,
    CASE
        WHEN AVG(({{prediction_col}}::float - {{ground_truth_col}}::float) / {{ground_truth_col}}::float) > 0.05 THEN 'Systematic Overestimation'
        WHEN AVG(({{prediction_col}}::float - {{ground_truth_col}}::float) / {{ground_truth_col}}::float) < -0.05 THEN 'Systematic Underestimation'
        ELSE 'Balanced'
    END as bias_assessment
FROM {{dataset}}
WHERE {{timestamp_col}} >= CURRENT_DATE - INTERVAL '30 days'
    AND {{ground_truth_col}} != 0
    AND ABS({{ground_truth_col}}) > 0.0001;
```

**Expected**:
- Roughly 50/50 split between overestimates and underestimates (balanced model)
- `avg_relative_error` close to 0 (unbiased)
- Large bias suggests model calibration issues

### Common Issues

- **All 0% or 100% accuracy**: Check threshold value (must be decimal: 0.10, not 10)
- **Empty results**: Verify timestamp range, check for NULL values
- **Accuracy seems too low**: Threshold may be too strict; analyze error distribution
- **Accuracy at 100%**: Check if predictions = actuals (data leakage?) or threshold too lenient
- **Negative percentage errors**: Impossible; check for negative actual values
- **Division by zero errors**: Ensure `actual != 0` filter is applied
- **Inconsistent day-to-day**: Low sample size per day; consider weekly buckets
- **Metric differs from manual calculation**: Verify excluded records (NULLs, zeros, small actuals)

***

## Dataset Compatibility

This metric is compatible with any regression dataset containing continuous predictions and ground truth values.

### Compatible Datasets from `/data` folder:

#### 1. regression-loan-amount-prediction

**Column Mapping:**
- `timestamp` (timestamp) → `timestamp_col`
- `predicted_loan_amount` (float) → `prediction_col`
- `actual_loan_amount` (float) → `ground_truth_col`

**Recommended Configuration:**
- **Threshold**: `0.10` (10%)
- **Target accuracy**: ≥80% (8 out of 10 loans predicted within ±10%)
- **Business context**: $5,000 error on $50,000 loan is acceptable tolerance

**Example Interpretation**:
- **85% core accuracy** → 850 of 1,000 loan predictions within 10%
- **Loan #123**: Predicted $48,000, Actual $52,000 → 7.7% error → **Accurate** ✓
- **Loan #456**: Predicted $45,000, Actual $51,000 → 11.8% error → **Inaccurate** ✗

**Use Cases**:
- SLA monitoring for lending operations
- Model performance tracking for regulatory reporting
- A/B testing of credit risk models
- Quality gates for model deployment

#### 2. regression-housing-price-prediction

**Column Mapping:**
- `timestamp` (timestamp) → `timestamp_col`
- `predicted_house_value` (float) → `prediction_col`
- `actual_house_value` (float) → `ground_truth_col`

**Recommended Configuration:**
- **Threshold**: `0.05` (5%, stricter for pricing accuracy)
- **Alternative**: `0.10` (10%, standard)
- **Target accuracy**: ≥75% at 5% threshold, or ≥85% at 10% threshold
- **Business context**: 5% error on $500,000 home = $25,000 (significant for buyers/sellers)

**Example Interpretation**:
- **82% core accuracy at 5%** → 820 of 1,000 homes priced within ±5%
- **House #789**: Predicted $475,000, Actual $490,000 → 3.1% error → **Accurate** ✓
- **House #012**: Predicted $460,000, Actual $510,000 → 9.8% error → **Inaccurate** ✗ (at 5% threshold)

**Use Cases**:
- Real estate pricing accuracy for listings
- Valuation model performance for mortgage underwriting
- Comparative market analysis validation
- Automated valuation model (AVM) benchmarking

### Data Requirements

**Essential:**
- Timestamp column (for time-series aggregation and filtering)
- Continuous prediction values (int or float, >0 preferred but negative values supported)
- Continuous ground truth values (int or float, non-zero required)
- Sufficient sample size (100+ predictions per time bucket for stable statistics)

**Optional but Recommended:**
- Segmentation columns (region, product_type, customer_segment) for accuracy breakdown
- Prediction confidence scores for filtering or weighted accuracy analysis
- Feature columns for error root cause analysis (which features correlate with inaccuracy)
- Model version identifiers for A/B testing and version comparison

### Notes

**Threshold Selection:**
Before deploying, analyze your model's error distribution:
```sql
SELECT
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY ABS((pred - actual) / actual)) * 100 as p25_error_pct,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY ABS((pred - actual) / actual)) * 100 as p50_error_pct,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY ABS((pred - actual) / actual)) * 100 as p75_error_pct,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY ABS((pred - actual) / actual)) * 100 as p90_error_pct
FROM (
    SELECT
        {{prediction_col}}::float as pred,
        {{ground_truth_col}}::float as actual
    FROM {{dataset}}
    WHERE {{ground_truth_col}} != 0
) subq;
```

**Threshold guidelines based on error distribution:**
- Set threshold at 75th percentile error → 75% accuracy target
- Set threshold at 90th percentile error → 90% accuracy target
- Common industry practice: 10% threshold for ≥80% accuracy

**Comparison to Other Metrics:**
- **vs. MAPE**: Core accuracy is more interpretable ("8 out of 10 correct" vs "12.3% average error")
- **vs. MAE**: Core accuracy gives pass/fail, MAE gives average error magnitude
- **vs. RMSE**: Core accuracy doesn't penalize large errors as heavily (more robust to outliers)
- **Recommendation**: Use core accuracy as primary metric for communication, complement with MAPE/MAE for technical analysis

**Handling Edge Cases:**
- **Zero actuals**: Excluded (percentage error undefined)
- **Near-zero actuals**: Excluded with `ABS(actual) > 0.0001` safeguard
- **Negative values**: Supported (uses absolute value of actual in denominator)
- **NULL values**: Excluded from both numerator and denominator
- **Extreme outliers**: Count as inaccurate (0) but don't inflate error as much as MAPE

**Segmentation Analysis:**
To compute accuracy by segment, deploy multiple instances or modify SQL:
```sql
-- Add to final SELECT:
SELECT
  ts,
  {{segment_col}} as segment,
  AVG(is_accurate)::float AS core_accuracy_rate,
  ...
FROM accuracy_flags
GROUP BY ts, segment
ORDER BY ts, segment;
```

Then configure dimension column in Reported Metrics to track segment-level accuracy.

**Multi-Threshold Monitoring:**
Some teams deploy the metric multiple times with different thresholds:
- **Instance 1**: 5% threshold (strict quality bar)
- **Instance 2**: 10% threshold (standard SLA)
- **Instance 3**: 20% threshold (lenient for context)

This provides accuracy at multiple tolerance levels for comprehensive assessment.

**Seasonal Patterns:**
Document expected accuracy variations:
- Holiday periods (higher volatility in demand forecasting)
- Quarter-end (different behavior in financial predictions)
- Market events (housing market shifts affecting price predictions)

Use historical data to set season-specific baselines and avoid false alarms.

**Continuous Improvement:**
- Track accuracy trend over time (improving, stable, or degrading)
- Set quarterly accuracy improvement goals (e.g., improve from 82% to 85%)
- Document accuracy improvements from model updates
- Use accuracy gains to justify ML investment and team resources
