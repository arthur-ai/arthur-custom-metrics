# Drift Score

## Overview

**Drift Score** quantifies how much the distribution of a feature or prediction has changed over time compared to a reference period using Population Stability Index (PSI). This metric is essential for detecting distribution shifts before they degrade model performance, enabling proactive monitoring and timely retraining decisions.

**Key Insights:**
- Detects distributional changes in features, predictions, or other numeric columns
- Industry-standard PSI-based measurement for drift quantification
- Early warning system for model degradation before accuracy drops
- Supports both fixed baseline and rolling window comparisons
- Universal metric applicable to any model type and data distribution

**When to Use:**
- **Production ML monitoring**: Detect when input data or predictions drift from training distribution
- **Fraud detection**: Identify emerging fraud patterns not seen during training
- **Credit scoring**: Catch demographic or economic shifts requiring model updates
- **Demand forecasting**: Detect market condition changes affecting predictions
- **Regulatory compliance**: Document population stability for model risk management
- **Feature monitoring**: Track individual feature distributions over time
- **Prediction drift**: Monitor if model outputs have shifted systematically

***

## Step 1: Write the SQL

This SQL computes drift score using Population Stability Index (PSI) by comparing current distribution to a reference baseline. It bins numeric values and measures distribution divergence.

```sql
WITH
  -- Reference period statistics (baseline distribution)
  ref_range AS (
    SELECT
      MIN({{target_col}}::float) AS ref_min,
      MAX({{target_col}}::float) AS ref_max
    FROM {{dataset}}
    WHERE {{timestamp_col}} >= '{{reference_start_date}}'::timestamptz
      AND {{timestamp_col}} < '{{reference_end_date}}'::timestamptz
      AND {{target_col}} IS NOT NULL
  ),

  -- Reference distribution binning
  ref_bins AS (
    SELECT
      CASE
        -- Handle edge case where all values are identical
        WHEN rr.ref_max = rr.ref_min THEN 1
        ELSE LEAST(
          {{num_bins}},
          GREATEST(
            1,
            CAST(
              FLOOR(
                ({{target_col}}::float - rr.ref_min) / NULLIF(rr.ref_max - rr.ref_min, 0) * {{num_bins}}
              ) AS integer
            ) + 1
          )
        )
      END AS bin_id,
      COUNT(*)::float AS ref_count
    FROM {{dataset}} r
    CROSS JOIN ref_range rr
    WHERE r.{{timestamp_col}} >= '{{reference_start_date}}'::timestamptz
      AND r.{{timestamp_col}} < '{{reference_end_date}}'::timestamptz
      AND r.{{target_col}} IS NOT NULL
    GROUP BY bin_id
  ),

  -- Total reference count for normalization
  ref_totals AS (
    SELECT SUM(ref_count) AS total_ref_count
    FROM ref_bins
  ),

  -- Reference distribution (proportions per bin)
  ref_dist AS (
    SELECT
      rb.bin_id,
      rb.ref_count / NULLIF(rt.total_ref_count, 0) AS p_ref_raw
    FROM ref_bins rb
    CROSS JOIN ref_totals rt
  ),

  -- Current distribution per time bucket
  cur_bins AS (
    SELECT
      time_bucket(INTERVAL '1 day', d.{{timestamp_col}}) AS bucket,
      CASE
        WHEN rr.ref_max = rr.ref_min THEN 1
        ELSE LEAST(
          {{num_bins}},
          GREATEST(
            1,
            CAST(
              FLOOR(
                ({{target_col}}::float - rr.ref_min) / NULLIF(rr.ref_max - rr.ref_min, 0) * {{num_bins}}
              ) AS integer
            ) + 1
          )
        )
      END AS bin_id,
      COUNT(*)::float AS cur_count
    FROM {{dataset}} d
    CROSS JOIN ref_range rr
    WHERE d.{{timestamp_col}} IS NOT NULL
      AND d.{{target_col}} IS NOT NULL
      -- Only compute for dates after reference period
      AND d.{{timestamp_col}} >= '{{reference_end_date}}'::timestamptz
    GROUP BY bucket, bin_id
  ),

  -- Total current count per bucket for normalization
  cur_totals AS (
    SELECT
      bucket,
      SUM(cur_count) AS total_cur_count
    FROM cur_bins
    GROUP BY bucket
  ),

  -- Current distribution (proportions per bin per time bucket)
  cur_dist AS (
    SELECT
      cb.bucket,
      cb.bin_id,
      cb.cur_count / NULLIF(ct.total_cur_count, 0) AS p_cur_raw
    FROM cur_bins cb
    JOIN cur_totals ct ON cb.bucket = ct.bucket
  ),

  -- Join current and reference, apply smoothing to prevent log(0)
  psi_input AS (
    SELECT
      c.bucket,
      c.bin_id,
      -- Apply epsilon smoothing: max(proportion, 1e-6)
      GREATEST(COALESCE(c.p_cur_raw, 0), 1e-6) AS p_cur,
      GREATEST(COALESCE(r.p_ref_raw, 0), 1e-6) AS p_ref
    FROM cur_dist c
    LEFT JOIN ref_dist r ON c.bin_id = r.bin_id

    UNION ALL

    -- Also include bins that exist in reference but not in current
    SELECT
      (SELECT MIN(bucket) FROM cur_dist) AS bucket,
      r.bin_id,
      1e-6 AS p_cur,  -- Epsilon for missing bins
      GREATEST(r.p_ref_raw, 1e-6) AS p_ref
    FROM ref_dist r
    WHERE NOT EXISTS (
      SELECT 1 FROM cur_dist c WHERE c.bin_id = r.bin_id
    )
  ),

  -- Calculate PSI terms: (p_cur - p_ref) * ln(p_cur / p_ref)
  psi_terms AS (
    SELECT
      bucket,
      (p_cur - p_ref) * LN(p_cur / p_ref) AS term
    FROM psi_input
  )

-- Final aggregation: sum PSI terms per time bucket
SELECT
  bucket AS ts,
  SUM(term) AS drift_score,
  '{{target_col}}' AS monitored_column
FROM psi_terms
GROUP BY bucket
ORDER BY bucket;
```

**What this query returns:**

* `ts` — timestamp bucket (1 day)
* `drift_score` — Population Stability Index measuring distribution drift (float, 0 = no drift, higher = more drift)
* `monitored_column` — name of the column being monitored for drift (for multi-metric tracking)

**SQL Logic:**

1. **ref_range CTE**: Computes global min/max from reference period to define consistent bin boundaries
2. **ref_bins CTE**: Bins reference period data into equal-width bins (default 10)
3. **ref_totals & ref_dist CTEs**: Normalizes reference bins into proportions (p_ref)
4. **cur_bins CTE**: Bins current data per day using same bin boundaries as reference
5. **cur_totals & cur_dist CTEs**: Normalizes current bins into proportions per day (p_cur)
6. **psi_input CTE**: Joins current and reference distributions with epsilon smoothing (1e-6) to prevent log(0) errors
7. **psi_terms CTE**: Calculates PSI formula for each bin: `(p_cur - p_ref) * ln(p_cur / p_ref)`
8. **Final SELECT**: Aggregates PSI terms to get drift score per day

**Key Features:**
- Uses industry-standard PSI for comparability with existing drift monitoring tools
- Epsilon smoothing (1e-6) prevents mathematical errors with zero probabilities
- Equal-width binning based on reference period range ensures stable measurement
- Handles edge cases: identical values, missing bins, NULL values
- Computes daily drift scores for trend analysis

***

## Step 2: Fill Basic Information

When creating the custom metric in the Arthur UI:

1. **Name**:
   `Drift Score`

2. **Description** (optional but recommended):
   `Measures distribution drift using Population Stability Index (PSI) by comparing current data to a reference baseline period. Values < 0.1 indicate stable distribution, 0.1-0.2 indicate moderate drift, > 0.2 indicate significant drift requiring investigation.`

***

## Step 3: Configure the Aggregate Arguments

You will set up seven aggregate arguments to parameterize the SQL.

### Argument 1 — Timestamp Column

1. **Parameter Key:** `timestamp_col`
2. **Friendly Name:** `Timestamp Column`
3. **Description:** `Timestamp column used for time bucketing and reference period filtering`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `primary_timestamp`
8. **Allowed Column Types:** `timestamp`

### Argument 2 — Target Column

1. **Parameter Key:** `target_col`
2. **Friendly Name:** `Target Column`
3. **Description:** `Numeric column to monitor for drift (prediction, feature, or score)`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `dataset`
6. **Allow Any Column Type:** `No`
7. **Tag Hints:** `prediction, continuous`
8. **Allowed Column Types:** `int, float`

### Argument 3 — Reference Start Date

1. **Parameter Key:** `reference_start_date`
2. **Friendly Name:** `Reference Start Date`
3. **Description:** `Start of reference period baseline (e.g., training data start date or stable production period start)`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Timestamp`
6. **Example Value:** `2025-01-01T00:00:00Z`

### Argument 4 — Reference End Date

1. **Parameter Key:** `reference_end_date`
2. **Friendly Name:** `Reference End Date`
3. **Description:** `End of reference period baseline (exclusive). Drift is computed for all data after this date.`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Timestamp`
6. **Example Value:** `2025-01-31T23:59:59Z`

### Argument 5 — Number of Bins

1. **Parameter Key:** `num_bins`
2. **Friendly Name:** `Number of Bins`
3. **Description:** `Number of equal-width bins for histogram construction (default: 10, typical range: 5-20)`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Integer`
6. **Default Value:** `10`

**Guidance on choosing bins:**
- **5 bins**: Coarse-grained drift detection, less sensitive to small changes
- **10 bins**: Standard choice, good balance of sensitivity and stability (recommended)
- **20 bins**: Fine-grained detection, more sensitive but may be noisy with small sample sizes

### Argument 6 — Dataset

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset containing both reference and current data for drift comparison`
4. **Parameter Type:** `Dataset`

### Argument 7 — (Optional) Monitored Column Name

*Note: This is handled automatically via the SQL with `'{{target_col}}'` but can be configured if you want a custom display name*

***

## Step 4: Configure Reported Metrics

This metric reports two values for comprehensive drift monitoring.

### Metric 1 — Drift Score

1. **Metric Name:** `drift_score`
2. **Description:** `PSI-based drift score measuring distribution divergence from reference period. Values: <0.1 (stable), 0.1-0.2 (moderate drift), >0.2 (significant drift)`
3. **Value Column:** `drift_score`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`
6. **Dimension Column:** `monitored_column`

### Metric 2 — (Optional) Monitored Column

*This is captured as a dimension in Metric 1, allowing tracking of multiple columns with the same metric definition*

***

## Step 5: Dashboard Chart SQL

This query reads from the **metrics_numeric_latest_version** table to visualize stored drift scores over time.

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
- `dimensions` (jsonb) - Optional dimension data (contains monitored_column)

**Chart SQL Query:**

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,

    dimensions ->> 'monitored_column' AS column_name,

    COALESCE(AVG(value), 0) AS drift_score,

    -- Add visual threshold indicators
    CASE
        WHEN AVG(value) < 0.1 THEN 'Stable'
        WHEN AVG(value) < 0.2 THEN 'Moderate Drift'
        ELSE 'Significant Drift'
    END AS drift_status

FROM metrics_numeric_latest_version
WHERE metric_name = 'drift_score'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, column_name
ORDER BY time_bucket_1d, column_name;
```

**Query Explanation:**
- **`time_bucket_gapfill()`** - Creates continuous daily time series with no gaps
- **`{{dateStart}}` and `{{dateEnd}}`** - Template variables for configurable time range
- **`[[AND ...]]`** - Optional filter syntax in Arthur Platform
- **`dimensions ->> 'monitored_column'`** - Extracts column name from JSON dimensions
- **`COALESCE(AVG(value), 0)`** - Handles missing values gracefully
- **CASE statement** - Provides visual drift severity classification

**Chart Configuration:**
- **Chart Type:** Line chart with threshold zones
- **Y-axis:** `drift_score` (PSI value, typically 0 to 0.5+)
- **X-axis:** `time_bucket_1d` (daily time buckets)
- **Series:** `column_name` (if monitoring multiple columns)
- **Threshold zones:**
  - Green zone (< 0.1): Stable distribution
  - Yellow zone (0.1-0.2): Moderate drift, monitor closely
  - Red zone (> 0.2): Significant drift, investigate immediately

**What this shows:**
- Daily drift scores tracking distribution changes over time
- Threshold breaches indicating when drift becomes concerning
- Comparison across multiple monitored columns (if applicable)
- Trend patterns: gradual drift vs. sudden shifts
- Time periods requiring investigation or model retraining

**Alternative Chart: Multi-Column Heatmap**

For monitoring multiple features/columns:

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,

    dimensions ->> 'monitored_column' AS column_name,

    COALESCE(AVG(value), 0) AS drift_score

FROM metrics_numeric_latest_version
WHERE metric_name = 'drift_score'
  AND dimensions ->> 'monitored_column' IN (
      'predicted_loan_amount',
      'credit_score',
      'annual_income'
  )
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, column_name
ORDER BY time_bucket_1d, column_name;
```

Display as heatmap with columns on Y-axis, time on X-axis, and color intensity showing drift score.

***

## Interpreting the Metric

### Value Ranges

Population Stability Index (PSI) interpretation follows industry standards:

**PSI < 0.1 (Stable)**:
- Little to no distribution change
- Population is stable relative to reference period
- No action needed, continue monitoring
- Typical for well-behaved features in stable environments

**PSI 0.1 - 0.2 (Moderate Drift)**:
- Moderate distribution shift detected
- Monitor closely and investigate cause
- May indicate:
  - Seasonal patterns
  - Gradual population evolution
  - Early signs of data quality issues
  - Minor shifts in user behavior or market conditions
- Consider investigating if drift persists or accelerates

**PSI > 0.2 (Significant Drift)**:
- Substantial distribution change detected
- Immediate investigation required
- Often triggers model retraining or recalibration
- May indicate:
  - Major data quality issues or pipeline breaks
  - Significant population shift (new user segments, market changes)
  - Concept drift (relationship between features and target changed)
  - System integration changes or data source modifications
- Used as regulatory threshold for model review in many institutions

**PSI > 0.5 (Extreme Drift)**:
- Dramatic distribution change
- Critical issue requiring immediate attention
- Almost certainly indicates:
  - Data pipeline failure
  - Fundamental population change
  - Model completely out of distribution

### Trends to Watch

**Gradual increase over time:**
- Natural population evolution (demographics, market maturity)
- Slow concept drift requiring eventual model retraining
- May reflect business growth (new customer segments, geographic expansion)
- **Action**: Plan model refresh within 3-6 months if approaching 0.2

**Sudden spikes:**
- Data quality issues (missing values, incorrect formatting, unit changes)
- System or integration changes (new data source, changed feature engineering)
- One-time events (promotions, seasonal peaks, external shocks)
- **Action**: Investigate immediately, check data pipeline and recent deployments

**Persistent elevation above 0.2:**
- Model is out of sync with current population
- Training data no longer representative
- **Action**: Prioritize model retraining, consider interim recalibration

**Periodic oscillations:**
- Seasonal patterns in data distribution
- Time-based effects (day of week, month of year)
- **Action**: Document seasonality, consider seasonal adjustments or separate models

**Multiple columns drifting simultaneously:**
- Systematic change across feature space
- Likely indicates major population shift or data pipeline issue
- **Action**: Comprehensive investigation of data sources and feature engineering

### When to Investigate

**Immediate investigation (within 24 hours):**
1. **Drift score > 0.25** - Significant drift threshold breached
2. **Sudden spike** (>0.15 increase in one day) - Likely data quality issue
3. **Multiple features drifting** (>3 columns showing moderate drift) - Systematic problem
4. **Core features drifting** (key predictive features showing any drift > 0.1)

**Planned investigation (within 1 week):**
1. **Drift score 0.15-0.25** - Approaching significant threshold
2. **Sustained moderate drift** (0.1-0.2 for >2 weeks) - Persistent shift
3. **Gradual upward trend** - Even if below thresholds, persistent increase warrants analysis

**Monitoring and documentation (monthly review):**
1. **Drift score 0.05-0.1** - Minor drift, track but no action yet
2. **Seasonal patterns** - Document expected drift windows
3. **Feature-specific drift** - Some drift expected for certain features

### Investigation Checklist

When drift is detected:

1. **Verify data quality:**
   - Check for NULL values, outliers, or data type changes
   - Compare data volume and completeness to reference period
   - Validate upstream data sources haven't changed

2. **Review recent changes:**
   - Deployment history (model, feature engineering, data pipeline)
   - System integrations or vendor changes
   - Business process modifications

3. **Analyze distribution specifics:**
   - Plot histograms of current vs. reference distributions
   - Identify which bins contribute most to PSI
   - Check for mean/variance shifts vs. shape changes

4. **Assess business context:**
   - Known external events (market changes, campaigns, seasonality)
   - Customer segment changes (new regions, demographics)
   - Product or service modifications

5. **Check model performance:**
   - Has accuracy decreased alongside drift?
   - Are predictions still calibrated?
   - Any bias or fairness concerns emerging?

***

## Use Cases

### Feature Drift in Fraud Detection

**Problem**: Fraudsters adapt tactics, causing feature distributions to drift from training data, degrading model effectiveness.

**Setup**:
- Target column: `transaction_amount`, `merchant_category_code`, `time_since_last_transaction`
- Reference period: Training data (e.g., 2025-01-01 to 2025-01-31)
- Number of bins: 10
- Alert threshold: PSI > 0.15 (tighter than standard due to high-stakes domain)

**Interpretation**:
- `transaction_amount` drift > 0.2 → Fraud patterns shifting to different amount ranges
- `merchant_category_code` drift > 0.15 → Fraudsters targeting new merchant types
- Multiple features drifting → Systematic fraud evolution requiring model update

**Action**:
- PSI > 0.15: Review recent fraud cases, update fraud rules
- PSI > 0.25: Expedite model retraining with recent fraud examples
- Trend analysis: Monthly review to identify gradual vs. sudden shifts

### Prediction Drift in Credit Scoring

**Problem**: Model predictions should remain stable unless population changes; drift in prediction scores may indicate model degradation or bias.

**Setup**:
- Target column: `credit_approval_score` (model's predicted score, 0-1000)
- Reference period: First month of production (stable baseline)
- Number of bins: 15 (finer granularity for score distributions)
- Alert threshold: PSI > 0.2

**Interpretation**:
- Score drift < 0.1 → Model behaving consistently, population stable
- Score drift 0.1-0.2 → Population evolution (demographics, economy)
- Score drift > 0.2 → Model recalibration needed or significant population shift

**Action**:
- Monitor alongside application approval rates and default rates
- If drift increases while accuracy holds → Population change requiring model update
- If drift increases and accuracy decreases → Model degradation, urgent retraining

### Input Feature Monitoring for Loan Prediction

**Problem**: Drift in input features (income, credit score) indicates changing applicant population requiring model recalibration.

**Setup**:
- Target columns: `annual_income`, `credit_score`, `debt_to_income_ratio`
- Reference period: Q1 2025 (representative baseline quarter)
- Number of bins: 10
- Monitor: 5+ features simultaneously

**Interpretation**:
- `annual_income` drift > 0.2 → Economic conditions or customer targeting changed
- `credit_score` drift > 0.15 → Applicant quality shifting (expansion to new segments)
- `debt_to_income_ratio` drift > 0.2 → Financial stress patterns changing

**Action**:
- Single feature drift → Investigate data quality and population segments
- Multiple features drifting → Systematic change, plan model retraining
- Create monthly drift report for model risk management committee

### Demand Forecasting Feature Drift

**Problem**: Seasonal products have expected drift; need to distinguish normal seasonality from anomalous changes.

**Setup**:
- Target columns: `previous_week_sales`, `promotional_flag_pct`, `competitor_price_index`
- Reference period: Same period last year (seasonal baseline)
- Number of bins: 10
- Track: Year-over-year drift comparison

**Interpretation**:
- Drift < 0.1 → Seasonality pattern consistent with last year
- Drift 0.1-0.2 → Market evolution, competitive dynamics changing
- Drift > 0.2 → Significant market shift or data quality issue

**Action**:
- Compare current drift to historical seasonal drift patterns
- Adjust forecast model if drift persistent across multiple weeks
- Document drift patterns for future seasonal adjustments

### Real Estate Price Prediction

**Problem**: Housing market conditions change over time; drift in features like `median_neighborhood_price` indicates market shifts requiring model updates.

**Setup**:
- Target columns: `predicted_house_value`, `median_neighborhood_price`, `days_on_market`
- Reference period: 6 months ago (recent stable market period)
- Number of bins: 12
- Alert threshold: PSI > 0.2

**Interpretation**:
- `median_neighborhood_price` drift > 0.2 → Market appreciation/depreciation accelerating
- `days_on_market` drift > 0.15 → Market liquidity changing (hot vs. cold market)
- `predicted_house_value` drift → Model predictions shifting systematically (check calibration)

**Action**:
- Quarterly model retraining to track market conditions
- Adjust pricing strategies based on drift patterns
- Use drift scores in model monitoring dashboards for stakeholders

### Multi-Model Comparison

**Problem**: Monitoring drift across multiple models (fraud, credit, pricing) to identify system-wide vs. model-specific issues.

**Setup**:
- Deploy same drift metric across all models
- Monitor common features (timestamp-based features, transaction amounts)
- Use dimension column to distinguish models

**Interpretation**:
- Drift in common features across all models → Data pipeline issue
- Drift isolated to one model → Model-specific population change
- Synchronized drift spikes → External event (economic shock, policy change)

**Action**:
- Centralized drift monitoring dashboard
- Alert routing based on drift patterns (data engineering vs. ML team)
- Standardized investigation playbooks

***

## Debugging & Verification

If the metric returns empty or unexpected values, use these queries to diagnose the issue:

### 1. Verify reference period data exists

```sql
SELECT
    COUNT(*) as ref_count,
    MIN({{target_col}}::float) as ref_min,
    MAX({{target_col}}::float) as ref_max,
    AVG({{target_col}}::float) as ref_avg,
    STDDEV({{target_col}}::float) as ref_stddev
FROM {{dataset}}
WHERE {{timestamp_col}} >= '{{reference_start_date}}'::timestamptz
  AND {{timestamp_col}} < '{{reference_end_date}}'::timestamptz
  AND {{target_col}} IS NOT NULL;
```

**Expected**: `ref_count` > 100 (ideally 1000+), `ref_min` < `ref_max`, reasonable avg/stddev for your feature.

### 2. Verify current period data exists

```sql
SELECT
    COUNT(*) as cur_count,
    MIN({{target_col}}::float) as cur_min,
    MAX({{target_col}}::float) as cur_max,
    AVG({{target_col}}::float) as cur_avg,
    STDDEV({{target_col}}::float) as cur_stddev
FROM {{dataset}}
WHERE {{timestamp_col}} >= '{{reference_end_date}}'::timestamptz
  AND {{target_col}} IS NOT NULL;
```

**Expected**: `cur_count` > 0, values should overlap with reference period but may differ.

### 3. Check bin distributions manually

```sql
WITH bins AS (
    SELECT
        CASE
            WHEN {{target_col}}::float < 10000 THEN '0-10K'
            WHEN {{target_col}}::float < 50000 THEN '10K-50K'
            WHEN {{target_col}}::float < 100000 THEN '50K-100K'
            ELSE '100K+'
        END as bin,
        CASE
            WHEN {{timestamp_col}} >= '{{reference_start_date}}'::timestamptz
             AND {{timestamp_col}} < '{{reference_end_date}}'::timestamptz
            THEN 'Reference'
            ELSE 'Current'
        END as period
    FROM {{dataset}}
    WHERE {{target_col}} IS NOT NULL
      AND {{timestamp_col}} IS NOT NULL
)
SELECT
    period,
    bin,
    COUNT(*) as count,
    ROUND(COUNT(*)::float / SUM(COUNT(*)) OVER (PARTITION BY period) * 100, 2) as pct
FROM bins
GROUP BY period, bin
ORDER BY period, bin;
```

**Expected**: See distribution differences between Reference and Current periods.

### 4. Test PSI calculation manually

```sql
-- Simplified PSI calculation to verify logic
WITH
  ref_dist AS (
    SELECT 0.4 as p_ref UNION ALL SELECT 0.3 UNION ALL SELECT 0.2 UNION ALL SELECT 0.1
  ),
  cur_dist AS (
    SELECT 0.3 as p_cur UNION ALL SELECT 0.4 UNION ALL SELECT 0.2 UNION ALL SELECT 0.1
  ),
  combined AS (
    SELECT
      r.p_ref,
      c.p_cur,
      (c.p_cur - r.p_ref) * LN(c.p_cur / r.p_ref) as psi_term
    FROM ref_dist r, cur_dist c
    WHERE r.p_ref IS NOT NULL AND c.p_cur IS NOT NULL
    LIMIT (SELECT COUNT(*) FROM ref_dist)
  )
SELECT SUM(psi_term) as total_psi FROM combined;
```

**Expected**: Small positive PSI value (this example should give ~0.02).

### 5. Check for edge cases

```sql
SELECT
    COUNT(DISTINCT {{target_col}}) as unique_values,
    COUNT(*) FILTER (WHERE {{target_col}} IS NULL) as null_count,
    COUNT(*) as total_count
FROM {{dataset}}
WHERE {{timestamp_col}} >= '{{reference_start_date}}'::timestamptz;
```

**Expected**:
- `unique_values` > `num_bins` (if not, consider reducing bins)
- `null_count` = 0 or very small percentage
- `total_count` sufficient for stable statistics (1000+)

### Common Issues

- **All zeros**: Current period matches reference perfectly (no drift), or date ranges wrong
- **Empty results**: Check date format (must be timestamptz), verify timestamp_col name
- **Very high PSI (>1.0)**: Suggests disjoint distributions, check for data pipeline issues or wrong reference period
- **Negative PSI**: Impossible (mathematical error), check for epsilon smoothing and NULLIF usage
- **Erratic values**: Sample size too small, consider larger time buckets or more data
- **Same values across days**: Check if current period date filter is working correctly

***

## Dataset Compatibility

This metric is universally compatible with any dataset containing numeric columns and timestamps. It works across all model types and problem domains.

### Compatible Datasets from `/data` folder:

#### 1. regression-loan-amount-prediction

**Prediction Drift:**
- `timestamp` (timestamp) → `timestamp_col`
- `predicted_loan_amount` (float) → `target_col`
- Reference: First 30 days of production data

**Feature Drift:**
- `credit_score` (int) → `target_col`
- `annual_income` (int) → `target_col`
- `debt_to_income_ratio` (float) → `target_col`
- Reference: Training data date range

**Use case**: Monitor if loan predictions or applicant features shift over time, indicating model recalibration needs.

#### 2. regression-housing-price-prediction

**Prediction Drift:**
- `timestamp` (timestamp) → `timestamp_col`
- `predicted_house_value` (float) → `target_col`
- Reference: January 2025 (stable market period)

**Feature Drift:**
- Any numeric feature in the dataset → `target_col`
- Monitor market indicators, property characteristics

**Use case**: Detect housing market shifts, seasonal patterns, or model calibration issues.

#### 3. binary-classifier-card-fraud

**Score Drift:**
- `timestamp` (timestamp) → `timestamp_col`
- `fraud_score` (float, 0-1) → `target_col`
- Reference: Training data or early production period

**Feature Drift:**
- Transaction features (amounts, counts, ratios) → `target_col`

**Use case**: Identify emerging fraud patterns causing score distribution shifts.

#### 4. binary-classifier-cc-application

**Score Drift:**
- `timestamp` (timestamp) → `timestamp_col`
- `approval_score` (float, 0-1) → `target_col`
- Reference: Pre-deployment validation period

**Feature Drift:**
- Applicant features (credit indicators, ratios) → `target_col`

**Use case**: Monitor if credit approval scores drift, indicating population changes or model degradation.

### Data Requirements

**Essential:**
- Timestamp column for time-series aggregation
- Numeric column to monitor (int or float)
- Sufficient data in reference period (1000+ records recommended)
- Sufficient data in current periods (100+ records per day recommended)

**Optional but Recommended:**
- Multiple numeric features to monitor (deploy metric multiple times)
- Segmentation columns for drill-down analysis (region, product type)
- Ground truth labels to correlate drift with accuracy changes

### Best Practices

**Reference Period Selection:**
- **Training data**: Use when you want to track drift from model training distribution (regulatory compliance, long-term stability)
- **Early production**: Use when training data unavailable or when production data is more representative
- **Rolling window**: For dynamic environments, consider re-computing metric monthly with updated reference period
- **Duration**: 2-4 weeks minimum, 3-6 months ideal for stable baseline

**Binning Strategy:**
- **Default 10 bins**: Works well for most distributions
- **5-7 bins**: Use for small sample sizes (<1000 records) or low-cardinality features
- **15-20 bins**: Use for large sample sizes (>10,000 records) and high-resolution drift detection
- **Equal-width**: Current implementation (based on min/max)
- **Equal-frequency**: Consider adapting SQL for percentile-based binning for skewed distributions

**Monitoring Setup:**
- Deploy one metric instance per monitored column
- Monitor top 5-10 most important features
- Always monitor model predictions (prediction drift)
- Set up alerts at PSI thresholds: 0.15 (warning), 0.25 (critical)
- Create dashboards showing drift scores for all monitored columns
- Review drift trends weekly, investigate immediately if thresholds breached

**Multi-Column Monitoring:**
To monitor multiple columns, deploy the metric multiple times with different configurations:
- Metric 1: `drift_score_predictions` (target_col = predicted_loan_amount)
- Metric 2: `drift_score_credit` (target_col = credit_score)
- Metric 3: `drift_score_income` (target_col = annual_income)

Each will produce separate time series with dimension `monitored_column` for identification.

### Notes

- PSI is symmetric: comparing current to reference gives same score as reference to current
- Sensitive to sample size: small samples may show high PSI due to noise
- Handles negative values naturally (uses min/max for binning, not just positive ranges)
- Works with scores (0-1), counts, amounts, ratios, or any continuous numeric feature
- Can adapt SQL for categorical features by using categories as bins instead of numeric ranges
- Consider pairing with accuracy metrics to distinguish benign drift from harmful drift
- Document expected seasonal drift patterns to avoid false alarms
- Use dimension column to track multiple features in a single metric definition
