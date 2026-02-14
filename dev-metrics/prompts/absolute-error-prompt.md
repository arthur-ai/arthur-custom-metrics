# Arthur Platform Custom Metric Prompt Template

## Instructions for Claude Code

Create a custom model evaluation metric documentation called `absolute-error.md` for Arthur Platform following the structure outlined below.

**Requirements:**
- Produce the document in the same folder as this prompt file
- Include SQL to generate the metric (base metric query)
- Include SQL for dashboard chart visualization
- Follow the standard metric documentation structure from `/examples/metrics/`
- Conduct web research from reputable sources if needed for metric definitions

---

## Metric Specification

### Basic Information

**Metric Name:** Absolute Error

**Output Filename:** `absolute-error.md`

**Metric Category:** Model Performance - Prediction Accuracy & Error

**Description:**
The absolute difference between a predicted value and the actual value for each prediction.

**Detailed Description:**
Absolute Error measures the magnitude of prediction error without considering direction. Unlike Mean Absolute Error (MAE) which aggregates errors across predictions, this metric reports the individual absolute error for each prediction, allowing you to track the distribution and patterns of prediction errors over time.

**Business Use Case:**
Track individual prediction errors to identify specific time periods or conditions where the model performs poorly. Useful for detecting sudden shifts in model performance, understanding error distribution patterns, and identifying outliers that may require investigation. Helps distinguish between systematic errors (consistent over/under prediction) versus random errors.

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
- Look at error-based metrics (RMSE, MAE, percentage errors)
- Review SQL patterns for NULL handling and aggregation

### Dataset Compatibility
Examine the `/data` folder and identify:
- Compatible datasets: `regression-loan-amount-prediction` and `regression-housing-price-prediction`
- Required columns:
  - Timestamp column (timestamp type)
  - Prediction column (float) - e.g., `predicted_amount`, `predicted_price`
  - Ground truth column (float) - e.g., `actual_amount`, `actual_price`

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

### SQL Complexity (Optional - for guidance only)
- [ ] Simple (single table, basic aggregation)
- [ ] Medium (CTEs, multiple aggregations)
- [ ] Complex (window functions, multiple CTEs, advanced logic)
- [x] Let Claude Code determine based on metric requirements

### Additional Context
- This is NOT Mean Absolute Error (MAE) - this metric reports individual errors
- Formula: `ABS(prediction - ground_truth)`
- Common with regression models for forecasting, pricing, demand prediction
- Useful for identifying error patterns and outliers over time

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
