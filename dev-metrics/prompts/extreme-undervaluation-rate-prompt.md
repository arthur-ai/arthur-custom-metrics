# Arthur Platform Custom Metric Prompt Template

## Instructions for Claude Code

Create a custom model evaluation metric documentation called `extreme-undervaluation-rate.md` for Arthur Platform following the structure outlined below.

**Requirements:**
- Produce the document in the same folder as this prompt file
- Include SQL to generate the metric (base metric query)
- Include SQL for dashboard chart visualization
- Follow the standard metric documentation structure from `/examples/metrics/`
- Conduct web research from reputable sources if needed for metric definitions

---

## Metric Specification

### Basic Information

**Metric Name:** Extreme Undervaluation Rate

**Output Filename:** `extreme-undervaluation-rate.md`

**Metric Category:** Model Performance - Extreme Value & Outlier

**Description:**
The proportion of cases where predictions are significantly lower than actual values.

**Detailed Description:**
Extreme Undervaluation Rate measures the percentage of predictions that substantially fall below the actual values, typically by more than a specified threshold (e.g., >20% or >50%). This metric helps identify systematic pessimistic bias in model predictions and highlights cases where the model consistently underestimates values, which can lead to missed opportunities and conservative decisions.

**Business Use Case:**
Critical for identifying missed revenue opportunities and overly conservative strategies. In pricing models, underestimating willingness to pay leaves money on the table. In demand forecasting, underestimating demand leads to stockouts and lost sales. In credit scoring, underestimating creditworthiness excludes viable customers. This metric helps identify when the model is too pessimistic, allowing teams to capture opportunities they would otherwise miss and optimize for growth rather than pure risk avoidance.

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
- Threshold parameter (float) - defines "extreme" undervaluation (e.g., 0.20 = 20%)

### SQL Complexity (Optional - for guidance only)
- [ ] Simple (single table, basic aggregation)
- [ ] Medium (CTEs, multiple aggregations)
- [ ] Complex (window functions, multiple CTEs, advanced logic)
- [x] Let Claude Code determine based on metric requirements

### Additional Context
- Formula: `(ground_truth - prediction) / ground_truth > threshold`
- Common thresholds: 20% (moderate), 50% (severe), 100% (critical)
- Must handle division by zero when ground_truth = 0
- Related metrics: Extreme Overvaluation Rate, MAPE, percentage error
- Useful for asymmetric loss functions where underestimation is costlier than overestimation
- Complement to Extreme Overvaluation Rate - both should be monitored together

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
