# Arthur Platform Custom Metric Prompt Template

## Instructions for Claude Code

Create a custom model evaluation metric documentation called `drift-score.md` for Arthur Platform following the structure outlined below.

**Requirements:**
- Produce the document in the same folder as this prompt file
- Include SQL to generate the metric (base metric query)
- Include SQL for dashboard chart visualization
- Follow the standard metric documentation structure from `/examples/metrics/`
- Conduct web research from reputable sources if needed for metric definitions

---

## Metric Specification

### Basic Information

**Metric Name:** Drift Score

**Output Filename:** `drift-score.md`

**Metric Category:** Model Performance - Model Stability & Drift

**Description:**
A quantitative measure of how much the distribution of input data or model predictions has changed over time compared to a reference period.

**Detailed Description:**
Drift Score quantifies the statistical divergence between a current time period's data distribution and a baseline (reference) distribution. This metric detects when input features, predictions, or model behavior shift significantly from their expected patterns. Unlike simple mean or variance changes, drift score captures comprehensive distributional changes using statistical distance measures, helping identify data quality issues, concept drift, or model degradation before accuracy metrics decline.

**Business Use Case:**
Essential for production ML monitoring where undetected drift can silently degrade model performance. In fraud detection, drift indicates new fraud patterns the model wasn't trained on. In credit scoring, drift signals demographic or economic shifts requiring model retraining. In demand forecasting, drift captures market condition changes. This metric enables proactive model governance by alerting teams to distribution changes before they impact business KPIs, supporting decisions about when to retrain, recalibrate, or investigate data pipeline issues. Used by ML engineers, model validators, and MLOps teams for continuous monitoring.

---

## Technical Requirements

### Reference Documentation
Review these files to understand Arthur Platform custom metric structure:
- `/references/how-to-create-a-custom-metric.md` - Metric creation guide and structure
- `/references/overview-metrics-and-querying.md` - Querying patterns and best practices
- `/references/configuration-options.md` - Valid configuration values for parameters
- `/references/platform-default-metrics.md` - Out-of-the-box metrics for reference
- `/references/sql_schema_metrics_numeric_latest_version.md` - Schema for numeric metrics table (for Dashboard Chart SQL)
- `/references/sql_schema_metrics_sketch_latest_version.md` - Schema for sketch metrics table (for Dashboard Chart SQL)

### Example Implementations
Study similar metrics in `/examples/metrics/` for patterns:
- **Binary Classification:** `/examples/metrics/binary-classification/` - Review PSI (Population Stability Index) implementation
- **Regression:** `/examples/metrics/regression/` - Look at distribution-based metrics
- Review SQL patterns for:
  - Statistical distance calculations
  - Reference period vs. current period comparisons
  - Binning and distribution bucketing
  - Handling NULL values and edge cases

### Dataset Compatibility
Examine the `/data` folder and identify:
- Compatible with ALL datasets (universal metric applicable to any model type)
- Required columns:
  - Timestamp column (timestamp type) - for temporal bucketing
  - Target column (any numeric type) - the column to measure drift on (predictions, features, etc.)
  - Reference period parameter (date range or literal) - baseline distribution timeframe
- Works with:
  - `binary-classifier-card-fraud/` - Can measure drift on fraud_score predictions
  - `binary-classifier-cc-application/` - Can measure drift on approval_score predictions
  - `regression-loan-amount-prediction/` - Can measure drift on predicted_amount or features
  - `regression-housing-price-prediction/` - Can measure drift on predicted_price or features

---

## Metric-Specific Details

### Model Type Compatibility
- [x] Binary Classification
- [x] Multi-Class Classification
- [x] Multi-Label Classification
- [x] Regression
- [x] Ranking/Scoring
- [x] Generative AI/LLM
- [x] Custom/Business KPI

### Required Data Columns
- Timestamp column (timestamp type) - for time bucketing and period comparison
- Target column (int/float) - column to measure drift on (predictions, features, scores)
- Reference start date (literal parameter) - beginning of baseline period
- Reference end date (literal parameter) - end of baseline period
- Optional: Number of bins (literal integer) - for histogram-based drift calculation (default: 10)

### SQL Complexity (Optional - for guidance only)
- [ ] Simple (single table, basic aggregation)
- [ ] Medium (CTEs, multiple aggregations)
- [x] Complex (window functions, multiple CTEs, advanced logic)
- [ ] Let Claude Code determine based on metric requirements

### Additional Context

**Statistical Methods for Drift Detection:**
- **Population Stability Index (PSI):** Industry standard for categorical/binned distributions
  - Formula: `Σ ((Actual% - Expected%) * ln(Actual% / Expected%))`
  - Thresholds: PSI < 0.1 (no drift), 0.1-0.2 (moderate), >0.2 (significant)
- **Kolmogorov-Smirnov (KS) Statistic:** Maximum difference between CDFs
  - Range: 0 to 1, where 0 = identical distributions
- **Jensen-Shannon Divergence:** Symmetric version of KL divergence
  - Range: 0 to 1, normalized information-theoretic distance
- **Wasserstein Distance (Earth Mover's Distance):** Optimal transport distance
  - Captures geometric distance between distributions

**Implementation Recommendations:**
- Use PSI-based approach for compatibility with industry standards
- Calculate using equal-frequency binning (quantile-based) or equal-width bins
- Handle edge cases: zero counts, division by zero, single-valued distributions
- Consider separate metrics for different drift types:
  - Feature drift (input distribution changes)
  - Prediction drift (output distribution changes)
  - Label drift (target variable distribution changes - requires ground truth)

**Related Metrics:**
- Population Stability Index (PSI) - Specific drift measure for categorical data
- KL Divergence - Information-theoretic drift measure
- Data Quality Score - Broader data health indicator

**Common Thresholds (PSI-based):**
- 0.0 - 0.1: No significant drift (stable)
- 0.1 - 0.2: Moderate drift (monitor closely)
- > 0.2: Significant drift (investigate or retrain)

---

## Output Requirements

The generated documentation must include these sections in order:

1. **Overview** - What the metric tracks, key insights, when to use it
2. **Step 1: Write the SQL** - Complete base metric SQL query with TimescaleDB time_bucket
3. **Step 2: Fill Basic Information** - Name and description for Arthur UI
4. **Step 3: Configure Aggregate Arguments** - All parameters (Dataset, Column, Literal)
5. **Step 4: Configure Reported Metrics** - Output specification (value column, timestamp, metric kind)
6. **Step 5: Dashboard Chart SQL** (Recommended) - Query for visualization showing drift over time
7. **Interpreting the Metric** - How to read values, typical ranges, when to investigate
8. **Use Cases** - Real-world applications and examples
9. **Dataset Compatibility** - Which test datasets work with this metric

---

## Notes for Users

To create a new metric from this template:
1. Copy this file and rename it: `[your-metric-name]-prompt.md`
2. Update the "Metric Specification" section with your metric details
3. Provide this prompt file to Claude Code
4. Claude Code will generate the full metric documentation following Arthur Platform standards
