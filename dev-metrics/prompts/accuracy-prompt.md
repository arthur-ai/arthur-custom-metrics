# Arthur Platform Custom Metric Prompt Template

## Instructions for Claude Code

Create a custom model evaluation metric documentation called `accuracy.md` for Arthur Platform following the structure outlined below.

**Requirements:**
- Produce the document in the same folder as this prompt file
- Include SQL to generate the metric (base metric query)
- Include SQL for dashboard chart visualization
- Follow the standard metric documentation structure from `/examples/metrics/`
- Conduct web research from reputable sources if needed for metric definitions

---

## Metric Specification

### Basic Information

**Metric Name:** Accuracy

**Output Filename:** `accuracy.md`

**Metric Category:** Model Performance - Prediction Accuracy & Error

**Description:**
The proportion of correct predictions (true positives and true negatives) among all predictions.

**Detailed Description:**
Accuracy is a fundamental classification metric that measures overall model correctness. It is calculated as (TP + TN) / (TP + TN + FP + FN), where TP = true positives, TN = true negatives, FP = false positives, and FN = false negatives. While simple and intuitive, accuracy can be misleading for imbalanced datasets where one class dominates.

**Business Use Case:**
Monitor overall model performance for balanced classification problems. Best used when the cost of false positives and false negatives is roughly equal, and when class distribution is relatively balanced. Useful as a high-level performance indicator, but should be complemented with precision, recall, and F1 score for comprehensive evaluation. Common in credit approval, fraud detection (when balanced), and binary decision systems.

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
- Look at confusion matrix based metrics
- Review threshold-based classification logic
- Examine SQL patterns for binary outcomes

### Dataset Compatibility
Examine the `/data` folder and identify:
- Compatible datasets: `binary-classifier-card-fraud` and `binary-classifier-cc-application`
- Required columns:
  - Timestamp column (timestamp type)
  - Prediction column (int/bool or float with threshold) - e.g., `fraud_pred`, `is_approved`
  - Ground truth column (int/bool) - e.g., `is_fraud`, `actual_approval`

---

## Metric-Specific Details

### Model Type Compatibility
- [x] Binary Classification
- [x] Multi-Class Classification
- [ ] Multi-Label Classification
- [ ] Regression
- [ ] Ranking/Scoring
- [ ] Generative AI/LLM
- [ ] Custom/Business KPI

### Required Data Columns
- Timestamp column (timestamp type) - for time bucketing
- Prediction column (int/bool or float) - model's predicted class or probability
- Ground truth column (int/bool) - actual class label
- Optional: Threshold parameter (float) - if using probability scores

### SQL Complexity (Optional - for guidance only)
- [ ] Simple (single table, basic aggregation)
- [ ] Medium (CTEs, multiple aggregations)
- [ ] Complex (window functions, multiple CTEs, advanced logic)
- [x] Let Claude Code determine based on metric requirements

### Additional Context
- Formula: Accuracy = (TP + TN) / (TP + TN + FP + FN)
- Range: 0.0 to 1.0 (or 0% to 100%)
- Baseline: For imbalanced datasets, compare against majority class baseline
- Limitations: Can be misleading with class imbalance (e.g., 99% accuracy on 99% negative class)
- Best practices: Use with precision, recall, and F1 score for complete picture

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
