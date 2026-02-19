# Arthur Platform Custom Metric Prompt Template

## Instructions for Claude Code

Create a custom model evaluation metric documentation called `percentage-accuracy.md` for Arthur Platform following the structure outlined below.

**Requirements:**
- Produce the document in the same folder as this prompt file
- Include SQL to generate the metric (base metric query)
- Include SQL for dashboard chart visualization
- Follow the standard metric documentation structure from `/examples/metrics/`
- Conduct web research from reputable sources if needed for metric definitions

---

## Metric Specification

### Basic Information

**Metric Name:** Percentage Accuracy

**Output Filename:** `percentage-accuracy.md`

**Metric Category:** Model Performance - Prediction Accuracy & Error

**Description:**
The proportion of correct predictions expressed as a percentage (0-100%).

**Detailed Description:**
Percentage Accuracy measures the overall correctness of a classification model by calculating what percentage of all predictions match the actual labels. It's the most intuitive and widely understood metric in machine learning: if a model has 85% accuracy, it means 85 out of every 100 predictions are correct. Unlike more complex metrics like log loss or AUC-ROC, accuracy provides a straightforward assessment that's easy to communicate to non-technical stakeholders. However, accuracy alone can be misleading for imbalanced datasets where a naive "always predict the majority class" model can achieve high accuracy. Therefore, percentage accuracy is best used alongside complementary metrics like precision, recall, F1-score, and class-specific accuracy for comprehensive model evaluation.

**Business Use Case:**
Essential for communicating model performance to executives, product managers, and business stakeholders who need simple, actionable metrics. In fraud detection, "95% accuracy" tells stakeholders the model correctly identifies 95 out of 100 transactions. In customer churn prediction, "82% accuracy" indicates how often churn predictions are correct. Percentage accuracy serves as a high-level quality indicator for SLA monitoring ("model must maintain ≥80% accuracy"), A/B testing comparisons ("Model B has 3% higher accuracy"), deployment gates ("only promote to production if accuracy >85%"), and performance tracking dashboards. However, it should be paired with cost-aware metrics when false positives and false negatives have different business impacts. Used by product managers for roadmap decisions, executives for ROI assessment, and ML engineers for quick model health checks.

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
- Review other accuracy-based metrics if available
- Examine SQL patterns for handling NULL values and binary comparisons
- Study core-accuracy-ppe-10pct.md for similar structure (though different calculation)

### Dataset Compatibility
Examine the `/data` folder and identify:
- Compatible datasets: `binary-classifier-card-fraud` and `binary-classifier-cc-application`
- Required columns:
  - Timestamp column (timestamp type)
  - Predicted label column (int or bool) - e.g., `fraud_pred`, binary prediction (0/1 or false/true)
  - Ground truth label column (int or bool) - e.g., `is_fraud`, `is_approved`
  - Works with binary and multi-class classification (label comparison)

---

## Metric-Specific Details

### Model Type Compatibility
- [x] Binary Classification (primary use case)
- [x] Multi-Class Classification
- [ ] Multi-Label Classification (would need different approach)
- [ ] Regression
- [ ] Ranking/Scoring
- [ ] Generative AI/LLM
- [ ] Custom/Business KPI

### Required Data Columns
- Timestamp column (timestamp type) - for time bucketing
- Predicted label column (int or bool) - model's predicted class (0/1, false/true, or multi-class integers)
- Ground truth label column (int or bool) - actual class label
- No additional parameters needed (threshold-free metric)

### SQL Complexity (Optional - for guidance only)
- [x] Simple (single table, basic aggregation)
- [ ] Medium (CTEs, multiple aggregations)
- [ ] Complex (window functions, multiple CTEs, advanced logic)
- [ ] Let Claude Code determine based on metric requirements

### Additional Context

**Percentage Accuracy Formula:**
```
Percentage Accuracy = (Number of Correct Predictions / Total Predictions) × 100

Or in confusion matrix terms:
Percentage Accuracy = (TP + TN) / (TP + TN + FP + FN) × 100

Where:
- TP = True Positives (predicted 1, actual 1)
- TN = True Negatives (predicted 0, actual 0)
- FP = False Positives (predicted 1, actual 0)
- FN = False Negatives (predicted 0, actual 1)
```

**Key Concepts:**
- **Simplicity**: Most intuitive metric; percentage format familiar to all audiences
- **Balanced view**: Treats all prediction types equally (correct positives and negatives both count)
- **Threshold-free**: Unlike probability-based metrics, uses hard predictions (no threshold tuning needed)
- **Higher is better**: 100% = perfect, 0% = always wrong
- **Baseline comparison**: Random guessing on balanced dataset = 50%

**Interpretation Guidelines:**
- **95-100%**: Excellent performance (near-perfect model)
- **85-95%**: Very good performance (production-ready for most use cases)
- **70-85%**: Good performance (acceptable for many applications)
- **50-70%**: Moderate performance (may need improvement depending on use case)
- **<50%**: Poor performance (worse than random for balanced data; investigate issues)

**Important Caveats:**
- **Imbalanced datasets**: Can be misleading
  - Example: 99% negative, 1% positive → always predicting negative = 99% accuracy but useless
  - Solution: Pair with precision, recall, F1-score, per-class accuracy
- **Class-specific errors**: Doesn't distinguish between false positives and false negatives
  - Example: In fraud detection, missing fraud (FN) is worse than false alarms (FP)
  - Solution: Use cost-sensitive metrics or separate FP/FN tracking
- **Probabilistic models**: Accuracy uses hard labels, ignoring confidence
  - Example: 51% fraud probability gets same credit as 99% fraud probability if both correct
  - Solution: Complement with log loss, Brier score, calibration metrics

**Comparison to Other Metrics:**
- **vs. Balanced Accuracy**: Accuracy treats classes equally; balanced accuracy averages per-class accuracy
- **vs. F1-Score**: F1 focuses on positive class (precision + recall), accuracy on overall correctness
- **vs. Log Loss**: Log loss evaluates probability calibration, accuracy only cares about final decision
- **vs. AUC-ROC**: AUC measures ranking ability across thresholds, accuracy at single threshold

**When to Use:**
- High-level model health monitoring (dashboard KPI)
- Executive and stakeholder communication (simple, intuitive)
- Balanced datasets where all classes equally important
- A/B testing for quick comparison (Model A: 83%, Model B: 87%)
- SLA compliance ("maintain ≥80% accuracy")

**When NOT to Use Alone:**
- Imbalanced datasets (complement with precision/recall)
- Asymmetric costs (false positives ≠ false negatives in business impact)
- Probabilistic decision-making (need log loss, Brier score)
- Class-specific performance needs (use per-class metrics)

**Related Metrics:**
- Balanced Accuracy (average of per-class recall)
- Top-K Accuracy (for multi-class: correct if true label in top K predictions)
- Per-Class Accuracy (accuracy calculated separately for each class)
- Confusion Matrix (detailed breakdown of prediction types)

**Multi-Class Extension:**
For multi-class classification (>2 classes), accuracy is calculated the same way:
```
Accuracy = (Number of predictions where predicted_class == actual_class) / Total predictions × 100
```
Works naturally without modification.

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
