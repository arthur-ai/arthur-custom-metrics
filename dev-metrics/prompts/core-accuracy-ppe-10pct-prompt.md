# Arthur Platform Custom Metric Prompt Template

## Instructions for Claude Code

Create a custom model evaluation metric documentation called `core-accuracy-ppe-10pct.md` for Arthur Platform following the structure outlined below.

**Requirements:**
- Produce the document in the same folder as this prompt file
- Include SQL to generate the metric (base metric query)
- Include SQL for dashboard chart visualization
- Follow the standard metric documentation structure from `/examples/metrics/`
- Conduct web research from reputable sources if needed for metric definitions

---

## Metric Specification

### Basic Information

**Metric Name:** Core Accuracy at PPE 10% Threshold

**Output Filename:** `core-accuracy-ppe-10pct.md`

**Metric Category:** Model Performance - Prediction Accuracy & Error

**Description:**
The proportion of predictions that fall within 10% of the actual value (Percentage Prediction Error ≤ 10%).

**Detailed Description:**
Core Accuracy at PPE 10% Threshold measures the percentage of predictions where the absolute percentage error is within a 10% tolerance band. This metric provides an intuitive measure of model reliability by counting predictions as "accurate" if they're within ±10% of the true value. Unlike traditional error metrics (MAE, RMSE) that average errors, this metric gives a binary pass/fail assessment per prediction, making it easier to communicate model performance to business stakeholders and set operational quality targets.

**Business Use Case:**
Critical for setting and monitoring Service Level Agreements (SLAs) in production ML systems. In loan amount prediction, 10% accuracy means predictions differ from actual amounts by no more than $5,000 on a $50,000 loan—an acceptable tolerance for most lending decisions. In demand forecasting, 10% accuracy prevents both stockouts and excess inventory. In pricing models, it ensures quotes are competitive without leaving money on the table. This metric enables clear quality gates ("model must achieve 80% core accuracy"), operational dashboards ("95 of last 100 predictions were within 10%"), and A/B testing comparisons ("Model B has 5% higher core accuracy than Model A"). Used by product managers, ML engineers, and operations teams to assess if a model meets business requirements.

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
- **Regression:** `/examples/metrics/regression/` - For continuous value metrics
- Look at percentage error metrics (MAPE, percentage error metrics)
- Review extreme-overvaluation-rate and extreme-undervaluation-rate for threshold-based patterns
- Examine SQL patterns for handling NULL values and division by zero

### Dataset Compatibility
Examine the `/data` folder and identify:
- Compatible datasets: `regression-loan-amount-prediction` and `regression-housing-price-prediction`
- Required columns:
  - Timestamp column (timestamp type)
  - Prediction column (float) - e.g., `predicted_amount`, `predicted_price`
  - Ground truth column (float) - e.g., `actual_amount`, `actual_price`
  - Threshold parameter (float) - accuracy threshold (e.g., 0.10 for 10%)

---

## Metric-Specific Details

### Model Type Compatibility
- [ ] Binary Classification
- [ ] Multi-Class Classification
- [ ] Multi-Label Classification
- [x] Regression
- [ ] Ranking/Scoring
- [ ] Generative AI/LLM
- [ ] Custom/Business KPI

### Required Data Columns
- Timestamp column (timestamp type) - for time bucketing
- Prediction column (float/int) - model's predicted value
- Ground truth column (float/int) - actual observed value
- Threshold parameter (float) - defines "accurate" prediction (default: 0.10 = 10%)

### SQL Complexity (Optional - for guidance only)
- [ ] Simple (single table, basic aggregation)
- [x] Medium (CTEs, multiple aggregations)
- [ ] Complex (window functions, multiple CTEs, advanced logic)
- [ ] Let Claude Code determine based on metric requirements

### Additional Context

**Core Accuracy Formula:**
```
Core Accuracy = (Count of predictions where |prediction - actual| / |actual| <= threshold) / Total predictions
```

**Key Concepts:**
- **Percentage Prediction Error (PPE)**: `|(prediction - actual) / actual| × 100`
- **Core Accuracy**: Binary classification of each prediction as "within threshold" (1) or "outside threshold" (0)
- **Threshold as parameter**: Default 10%, but configurable for different use cases
  - **5% threshold**: Stricter accuracy for high-precision applications
  - **10% threshold**: Standard tolerance for most business applications
  - **20% threshold**: Lenient threshold for exploratory or rough predictions

**Related Metrics:**
- MAPE (Mean Absolute Percentage Error) - Average of percentage errors
- Mean Absolute Deviation - Average absolute error
- Extreme Overvaluation/Undervaluation Rate - Directional threshold-based metrics
- Root Mean Squared Error - Quadratic error metric

**Advantages over MAPE:**
- Easier to interpret: "85% of predictions were accurate" vs "MAPE is 7.3%"
- Natural business language for SLAs and quality gates
- Robust to extreme outliers (single bad prediction doesn't skew the metric as much)
- Binary pass/fail aligns with operational decision-making

**Division by Zero Handling:**
- Exclude predictions where `actual = 0` (percentage error undefined)
- Apply precision safeguard: `ABS(actual) > 0.0001` to handle very small actuals
- Document exclusions for transparency

**Threshold Selection Guidance:**
- Analyze model's error distribution before choosing threshold
- Set threshold slightly above median absolute percentage error for "good enough" bar
- Consider business impact: What error level causes operational problems?
- Common thresholds: 5% (high-precision), 10% (standard), 15% (lenient), 20% (very lenient)

---

## Output Requirements

The generated documentation must include these sections in order:

1. **Overview** - What the metric tracks, key insights, when to use it
2. **Step 1: Write the SQL** - Complete base metric SQL query with TimescaleDB time_bucket
3. **Step 2: Fill Basic Information** - Name and description for Arthur UI
4. **Step 3: Configure Aggregate Arguments** - All parameters (Dataset, Column, Literal)
5. **Step 4: Configure Reported Metrics** - Output specification (value column, timestamp, metric kind)
6. **Step 5: Dashboard Chart SQL** (Optional but recommended) - Query for visualization
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
