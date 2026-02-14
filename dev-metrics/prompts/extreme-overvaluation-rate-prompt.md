# Arthur Platform Custom Metric Prompt Template

## Instructions for Claude Code

Create a custom model evaluation metric documentation called `extreme-overvaluation-rate.md` for Arthur Platform following the structure outlined below.

**Requirements:**
- Produce the document in the same folder as this prompt file
- Include SQL to generate the metric (base metric query)
- Include SQL for dashboard chart visualization
- Follow the standard metric documentation structure from `/examples/metrics/`
- Conduct web research from reputable sources if needed for metric definitions

---

## Metric Specification

### Basic Information

**Metric Name:** Extreme Overvaluation Rate

**Output Filename:** `extreme-overvaluation-rate.md`

**Metric Category:** Model Performance - Extreme Value & Outlier

**Description:**
The proportion of cases where predictions are significantly higher than actual values.

**Detailed Description:**
Extreme Overvaluation Rate measures the percentage of predictions that substantially exceed the actual values, typically by more than a specified threshold (e.g., >20% or >50%). This metric helps identify systematic optimistic bias in model predictions and highlights cases where the model consistently overestimates values, which can lead to poor business decisions.

**Business Use Case:**
Critical for risk management in scenarios where overestimation has serious consequences. For example, in loan amount prediction, overestimating repayment capacity can lead to defaults. In demand forecasting, overestimating demand leads to excess inventory and waste. In pricing models, overestimating willingness to pay results in lost sales. This metric helps identify when and where the model is dangerously optimistic, allowing teams to adjust predictions or add safety margins.

---

## Technical Requirements

### Reference Documentation
Review these files to understand Arthur Platform custom metric structure:
- `/references/how-to-create-a-custom-metric.md` - Metric creation guide and structure
- `/references/overview-metrics-and-querying.md` - Querying patterns and best practices
- `/references/configuration-options.md` - Valid configuration values for parameters
- `/references/platform-default-metrics.md` - Out-of-the-box metrics for reference

### Example Implementations
Study similar metrics in `/examples/metrics/` for patterns:
- **Regression:** `/examples/metrics/regression/` - For continuous value metrics
- Look at error-based metrics (percentage errors, MAPE)
- Review SQL patterns for threshold-based filtering
- Examine patterns for handling NULL values and division by zero

### Dataset Compatibility
Examine the `/data` folder and identify:
- Compatible datasets: `regression-loan-amount-prediction` and `regression-housing-price-prediction`
- Required columns:
  - Timestamp column (timestamp type)
  - Prediction column (float) - e.g., `predicted_amount`, `predicted_price`
  - Ground truth column (float) - e.g., `actual_amount`, `actual_price`
  - Optional: Threshold parameter (float) - percentage threshold for "extreme" (e.g., 0.20 for 20%)

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
- Threshold parameter (float) - defines "extreme" overvaluation (e.g., 0.20 = 20%)

### SQL Complexity (Optional - for guidance only)
- [ ] Simple (single table, basic aggregation)
- [ ] Medium (CTEs, multiple aggregations)
- [ ] Complex (window functions, multiple CTEs, advanced logic)
- [x] Let Claude Code determine based on metric requirements

### Additional Context
- Formula: `(prediction - ground_truth) / ground_truth > threshold`
- Common thresholds: 20% (moderate), 50% (severe), 100% (critical)
- Must handle division by zero when ground_truth = 0
- Related metrics: Extreme Undervaluation Rate, MAPE, percentage error
- Useful for asymmetric loss functions where overestimation is costlier than underestimation

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
