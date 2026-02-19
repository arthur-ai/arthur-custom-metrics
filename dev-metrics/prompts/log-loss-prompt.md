# Arthur Platform Custom Metric Prompt Template

## Instructions for Claude Code

Create a custom model evaluation metric documentation called `log-loss.md` for Arthur Platform following the structure outlined below.

**Requirements:**
- Produce the document in the same folder as this prompt file
- Include SQL to generate the metric (base metric query)
- Include SQL for dashboard chart visualization
- Follow the standard metric documentation structure from `/examples/metrics/`
- Conduct web research from reputable sources if needed for metric definitions

---

## Metric Specification

### Basic Information

**Metric Name:** Log Loss

**Output Filename:** `log-loss.md`

**Metric Category:** Model Performance - Prediction Accuracy & Error

**Description:**
A probabilistic metric that measures the uncertainty of predictions based on their probability estimates; lower values indicate better calibrated models.

**Detailed Description:**
Log Loss (also known as logarithmic loss or cross-entropy loss) quantifies the accuracy of probabilistic predictions by measuring how close predicted probabilities are to the actual outcomes. Unlike binary accuracy metrics that only consider whether a prediction is correct or incorrect, log loss evaluates the confidence of predictions—heavily penalizing confident wrong predictions while rewarding well-calibrated probability estimates. A perfectly calibrated model that predicts 0.8 probability for a positive class and is correct 80% of the time will have a low log loss. This metric is essential for models where prediction confidence matters, such as risk assessment, medical diagnosis, and fraud detection where knowing "how sure" the model is can be as important as the prediction itself.

**Business Use Case:**
Critical for applications where decision-making depends on prediction confidence, not just class labels. In fraud detection, a 95% fraud probability triggers immediate blocking while 55% triggers manual review—accurate probabilities drive operational workflows. In credit approval, probability scores determine interest rates and loan terms, making calibration directly impact revenue. In medical diagnosis, well-calibrated probabilities inform treatment decisions where false confidence can be dangerous. Log loss enables model comparison beyond accuracy ("Model B has 20% lower log loss, indicating better calibration"), probability recalibration decisions ("log loss increased 15%, probabilities no longer reliable"), and confidence-based automation ("only auto-approve predictions with log loss <0.1"). Used by ML engineers for model selection, risk managers for regulatory compliance, and product teams for threshold tuning.

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
- Look at probability-based metrics (if available)
- Review Gini coefficient and other scoring metrics for patterns
- Examine SQL patterns for handling NULL values, log functions, and edge cases

### Dataset Compatibility
Examine the `/data` folder and identify:
- Compatible datasets: `binary-classifier-card-fraud` and `binary-classifier-cc-application`
- Required columns:
  - Timestamp column (timestamp type)
  - Predicted probability column (float, 0-1 range) - e.g., `fraud_score`, `approval_score`
  - Ground truth label column (int or bool) - e.g., `is_fraud`, `is_approved`
  - Binary classification: single probability for positive class
  - Multi-class: would need probability array or multiple columns (advanced)

---

## Metric-Specific Details

### Model Type Compatibility
- [x] Binary Classification (primary use case)
- [x] Multi-Class Classification (can be extended)
- [ ] Multi-Label Classification
- [ ] Regression
- [ ] Ranking/Scoring
- [ ] Generative AI/LLM
- [ ] Custom/Business KPI

### Required Data Columns
- Timestamp column (timestamp type) - for time bucketing
- Predicted probability column (float, range 0-1) - model's probability estimate for positive class
- Ground truth label column (int or bool) - actual outcome (0/1, false/true)
- Epsilon parameter (float) - small value to prevent log(0) (default: 1e-15)

### SQL Complexity (Optional - for guidance only)
- [ ] Simple (single table, basic aggregation)
- [x] Medium (CTEs, logarithmic functions, multiple aggregations)
- [ ] Complex (window functions, multiple CTEs, advanced logic)
- [ ] Let Claude Code determine based on metric requirements

### Additional Context

**Log Loss Formula (Binary Classification):**
```
Log Loss = -1/N * Σ [y_i * log(p_i) + (1 - y_i) * log(1 - p_i)]

Where:
- N = number of predictions
- y_i = actual label (0 or 1)
- p_i = predicted probability for positive class (0 to 1)
- log = natural logarithm (ln)
```

**Key Concepts:**
- **Probabilistic scoring**: Evaluates quality of probability estimates, not just binary predictions
- **Calibration**: Well-calibrated models have log loss close to theoretical minimum
- **Confidence penalty**: Wrong confident predictions penalized more than wrong uncertain predictions
- **Lower is better**: 0 = perfect predictions, higher values indicate worse calibration
- **Unbounded above**: Extremely confident wrong predictions can produce very high log loss
- **Epsilon smoothing**: Add small ε to prevent log(0) = -∞ errors

**Interpretation Guidelines:**
- **Log Loss < 0.3**: Excellent calibration (very good model)
- **Log Loss 0.3 - 0.5**: Good calibration (acceptable model)
- **Log Loss 0.5 - 0.7**: Moderate calibration (needs improvement)
- **Log Loss > 0.7**: Poor calibration (major issues or random guessing ≈ 0.693)
- **Log Loss > 1.0**: Very poor calibration (worse than random)

**Comparison to Other Metrics:**
- **vs. Accuracy**: Accuracy only cares about correct/incorrect; log loss evaluates confidence
- **vs. AUC-ROC**: AUC measures ranking ability; log loss measures calibration
- **vs. Brier Score**: Similar goals but different penalties (Brier uses squared error, log loss uses logarithmic)
- **vs. Precision/Recall**: P/R focus on positive class performance; log loss evaluates probability quality

**Advantages:**
- Rewards well-calibrated probabilities (essential for decision-making)
- Differentiable (useful for model training optimization)
- Proper scoring rule (incentivizes honest probability estimates)
- Sensitive to probability shifts even when accuracy unchanged

**Edge Cases:**
- **Probability = 0 or 1**: Apply epsilon smoothing to prevent log(0) = -∞
- **Perfect predictions (p=1, y=1 or p=0, y=0)**: Log loss = 0 (perfect)
- **Wrong confident prediction (p=0.99, y=0)**: Log loss ≈ 4.6 (very high penalty)
- **Uncertain wrong prediction (p=0.55, y=0)**: Log loss ≈ 0.8 (moderate penalty)
- **NULL probabilities**: Exclude from calculation
- **Probabilities outside [0,1]**: Clip to valid range with warning

**Related Metrics:**
- Brier Score (mean squared error for probabilities)
- AUC-ROC (ranking performance)
- Calibration curves (visual assessment of calibration)
- Expected Calibration Error (ECE)

**When to Use:**
- Model selection: Compare calibration quality across candidates
- Production monitoring: Detect probability miscalibration over time
- Threshold optimization: Understand confidence levels for decision boundaries
- Regulatory compliance: Demonstrate probability reliability for risk models
- A/B testing: Compare calibration between model versions

**Multi-Class Extension:**
For multi-class classification, log loss becomes:
```
Log Loss = -1/N * Σ_i Σ_c [y_{i,c} * log(p_{i,c})]

Where:
- N = number of predictions
- C = number of classes
- y_{i,c} = 1 if sample i belongs to class c, 0 otherwise (one-hot)
- p_{i,c} = predicted probability for sample i, class c
```

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
