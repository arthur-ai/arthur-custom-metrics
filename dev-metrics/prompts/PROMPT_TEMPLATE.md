# Arthur Platform Custom Metric Prompt Template

## Instructions for Claude Code

Create a custom model evaluation metric documentation called `[OUTPUT_FILENAME].md` for Arthur Platform following the structure outlined below.

**Requirements:**
- Produce the document in the same folder as this prompt file
- Include SQL to generate the metric (base metric query)
- Include SQL for dashboard chart visualization
- Follow the standard metric documentation structure from `/examples/metrics/`
- Conduct web research from reputable sources if needed for metric definitions

---

## Metric Specification

### Basic Information

**Metric Name:** [METRIC_NAME]
<!-- Example: "Extreme Undervaluation Rate" -->

**Output Filename:** `[output-filename].md`
<!-- Example: "extreme-undervaluation-rate.md" -->

**Metric Category:** [CATEGORY]
<!-- Examples:
- Model Performance - Prediction Accuracy & Error
- Model Performance - Extreme Value & Outlier
- Model Performance - Ranking & Discrimination
- Model Performance - Stability & Drift
- Data Quality & Distribution
- Business KPI & Custom
-->

**Description:**
[BRIEF_DESCRIPTION]
<!-- One-sentence explanation of what this metric measures -->

**Detailed Description:**
[DETAILED_DESCRIPTION]
<!-- 2-3 sentences explaining:
- What patterns or behaviors this metric captures
- How it differs from similar metrics
- What makes it unique or valuable
-->

**Business Use Case:**
[BUSINESS_USE_CASE]
<!-- Explain:
- When and why this metric is valuable
- What business decisions it informs
- What problems it helps identify
- Who typically uses this metric (data scientists, product owners, etc.)
-->

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
- **Binary Classification:** `/examples/metrics/binary-classification/` - For classification metrics
- **Multi-Classification:** `/examples/metrics/multi-classification/` - For multi-label metrics
- **Regression:** `/examples/metrics/regression/` - For continuous value metrics

Key patterns to review:
- SQL structure with TimescaleDB `time_bucket()` aggregation
- NULL handling and edge case management
- Aggregate argument configuration
- Reported metrics specification

### Dataset Compatibility
Examine the `/data` folder and identify:
- Which datasets are compatible with this metric
- What columns are required (e.g., predictions, ground truth, timestamps)
- Any data type requirements or constraints (int, float, str, etc.)
- Model types this metric applies to (binary classification, regression, etc.)

Available test datasets:
- `binary-classifier-card-fraud/` - Fraud detection with fraud_score, is_fraud
- `binary-classifier-cc-application/` - Credit approval with approval_score, is_approved
- `regression-loan-amount-prediction/` - Loan amount with predicted_amount, actual_amount
- `regression-housing-price-prediction/` - Housing prices with predicted_price, actual_price

---

## Metric-Specific Details

### Model Type Compatibility
[SELECT_ONE_OR_MORE]
- [ ] Binary Classification
- [ ] Multi-Class Classification
- [ ] Multi-Label Classification
- [ ] Regression
- [ ] Ranking/Scoring
- [ ] Generative AI/LLM
- [ ] Custom/Business KPI

### Required Data Columns
[LIST_REQUIRED_COLUMNS]
<!-- Example:
- Timestamp column (timestamp type)
- Prediction column (float)
- Ground truth column (float)
- Optional: Threshold value (literal parameter)
-->

### SQL Complexity (Optional - for guidance only)
If you have a preference for SQL complexity level, indicate it here. Otherwise, Claude Code will determine the appropriate complexity based on the metric requirements.

- [ ] Simple (single table, basic aggregation)
- [ ] Medium (CTEs, multiple aggregations)
- [ ] Complex (window functions, multiple CTEs, advanced logic)
- [x] Let Claude Code determine based on metric requirements (recommended)

### Additional Context
[ANY_ADDITIONAL_CONTEXT]
<!-- Examples:
- Industry-specific formulas or standards
- Mathematical definitions or research papers
- Relationship to other metrics
- Common thresholds or benchmarks
-->

---

## Output Requirements

The generated documentation must include these sections in order:

### 1. Overview
- What the metric tracks
- Key insights it provides
- When to use it
- Quick reference on interpretation

### 2. Step 1: Write the SQL
- Complete SQL query with CTEs if needed
- TimescaleDB `time_bucket()` for time-series aggregation
- Proper NULL handling with `COALESCE()` or `NULLIF()`
- Comments explaining complex logic
- Template variables using `{{variable}}` syntax

### 3. Step 2: Fill Basic Information
- Metric name for Arthur UI
- Description field content

### 4. Step 3: Configure Aggregate Arguments
For each parameter, specify:
- Parameter Key (variable name in SQL)
- Friendly Name (UI display name)
- Description
- Parameter Type (Dataset, Column, or Literal)
- For Column parameters:
  - Source Dataset Parameter Key
  - Allow Any Column Type (Yes/No)
  - Tag Hints (comma-separated)
  - Allowed Column Types (comma-separated)
- For Literal parameters:
  - Data Type (String, Integer, Float, Boolean, etc.)
  - Default value if applicable

### 5. Step 4: Configure Reported Metrics
For each output metric:
- Metric Name
- Description
- Value Column (column name in SQL SELECT)
- Timestamp Column (column name in SQL SELECT)
- Metric Kind (Numeric or Categorical)
- Dimension Column (if the metric has dimensions/labels)

### 6. Step 5: Dashboard Chart SQL (Optional but Recommended)
- SQL query for visualization
- Chart type suggestion (line chart, bar chart, heatmap, etc.)
- Time range filters
- Aggregation for chart display
- Explanation of what patterns the chart reveals

### 7. Interpreting the Metric
- What different values mean
- Typical value ranges
- Trends to watch for (increasing, decreasing, sudden changes)
- When to investigate or take action
- Common patterns and their implications

### 8. Use Cases
- Real-world applications
- Example scenarios
- Industry-specific applications
- When this metric is most valuable

### 9. Dataset Compatibility
- List compatible datasets from `/data/`
- Specify required columns for each dataset
- Provide example column mappings
- Note any limitations or special considerations

---

## Notes for Users

### How to Use This Template

1. **Copy this file:**
   ```bash
   cp dev-metrics/PROMPT_TEMPLATE.md dev-metrics/[category]/[your-metric-name]-prompt.md
   ```

2. **Fill in the placeholders:**
   - Replace all `[PLACEHOLDER]` sections with your metric details
   - Be specific about metric category and business use case
   - Check boxes for applicable model types

3. **Provide context to Claude Code:**
   - Share the completed prompt file
   - Claude Code will automatically reference the required documentation
   - Generated output will follow Arthur Platform standards

4. **Review and refine:**
   - Check the generated SQL for correctness
   - Verify parameter configurations
   - Test with compatible datasets

### Tips for Better Results

- **Be specific:** Provide clear metric descriptions and use cases
- **Cite references:** Mention similar metrics or industry standards
- **Specify thresholds:** If your metric uses thresholds, explain typical values
- **Consider edge cases:** Mention how to handle NULLs, zeros, or empty data
- **Think about visualization:** Describe how you'd want to see this metric displayed

### Folder Organization

Place prompt files in appropriate subdirectories under `/dev-metrics/`:
- `prediction-accuracy-error/` - Accuracy and error metrics
- `ranking-discrimination/` - Ranking and discrimination metrics
- `stability-drift/` - Population stability and drift metrics
- `business-kpi/` - Business-specific KPIs
- Create new subdirectories as needed for organization
