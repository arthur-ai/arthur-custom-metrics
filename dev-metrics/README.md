# Dev-Metrics: LLM-Assisted Metric Development

This directory contains prompt templates for generating Arthur Platform custom metric documentation using LLMs like Claude Code.

## Quick Start
1. Ask Calude Code to prepare a new prompt to develop a new custom metric

Example:
```
Create a new /dev-metrics prompt, "Gini Coefficient" as "gini-coefficient-prompt.md" file. The category of the metric is "Model Performance - Classification and Discrimination". The metric is a measure of the discriminatory power of a model; higher values indicate better separation.
```

2. Ask Claude Code to generate the new metrics documentation with the `ultrathink` keyword

Example:
```
Ultrathink and generate the "Gini Coefficient" metric documentation from @dev-metrics/prompts/gini-coefficient-prompt.md
```

## The More Prescriptive Way

### Option 1: Use Existing Prompt

If a similar metric prompt already exists:

```bash
# 1. Navigate to the prompts folder
cd dev-metrics/prompts/

# 2. Review the existing prompt files
ls -la
cat absolute-error-prompt.md

# 3. Open this repository in Claude Code and provide the prompt file
# Claude Code will generate the complete metric documentation
```

### Option 2: Create New Metric from Template

For a brand new metric:

```bash
# 1. Copy the template
cp dev-metrics/prompts/PROMPT_TEMPLATE.md dev-metrics/prompts/[your-metric-name]-prompt.md

# 2. Edit the prompt file and fill in all [PLACEHOLDER] sections
# - Metric name and description
# - Business use case
# - Model type compatibility
# - Required columns
# - Any additional context

# 3. Provide the completed prompt to Claude Code
# Claude Code will generate the full metric documentation
```

## How It Works

### Workflow

```
1. Create/Customize Prompt File
   └─> [your-metric-name]-prompt.md

2. Provide to Claude Code
   └─> Claude Code reads prompt + references automatically

3. Claude Code Generates Documentation
   └─> [your-metric-name].md with complete Arthur Platform structure

4. Review and Deploy
   └─> Test SQL, validate parameters, deploy to Arthur
```

### What Claude Code Generates

The LLM will automatically create a complete metric documentation file with:

- ✅ **Overview** - Business context and use cases
- ✅ **SQL Query** - TimescaleDB-compatible base metric query
- ✅ **Aggregate Arguments** - Complete parameter configuration
- ✅ **Reported Metrics** - Output specification
- ✅ **Chart SQL** - Dashboard visualization query
- ✅ **Interpretation Guide** - How to read and act on the metric
- ✅ **Dataset Compatibility** - Which test datasets work with the metric

### References Included Automatically

Claude Code will automatically reference:
- `/references/how-to-create-a-custom-metric.md` - Metric creation guide
- `/references/overview-metrics-and-querying.md` - Querying patterns
- `/references/configuration-options.md` - Valid configuration values
- `/examples/metrics/` - Example implementations to follow

## Directory Structure

```
dev-metrics/
├── README.md                                    # This file
└── prompts/                                     # All prompt templates
    ├── PROMPT_TEMPLATE.md                       # Master template for new metrics
    ├── absolute-error-prompt.md                 # Example: absolute error
    ├── accuracy-prompt.md                       # Example: accuracy
    ├── extreme-overvaluation-rate-prompt.md     # Example: extreme overvaluation
    └── extreme-undervaluation-rate-prompt.md    # Example: extreme undervaluation
```

### Organizing Your Prompts

All prompt files are stored in `/dev-metrics/prompts/`. You can optionally organize them with prefixes:

- **accuracy-*** - Error and accuracy metrics
- **ranking-*** - Ranking, AUC, Gini metrics
- **stability-*** - PSI, drift detection
- **fairness-*** - Demographic parity, equalized odds
- **business-*** - Custom business metrics
- **quality-*** - Completeness, consistency checks

Example naming:
- `accuracy-absolute-error-prompt.md`
- `ranking-gini-coefficient-prompt.md`
- `stability-psi-prompt.md`

## Template Sections Explained

### Metric Specification
The core information about your metric:
- **Metric Name** - Human-readable name
- **Category** - Classification for organization
- **Description** - What it measures
- **Business Use Case** - Why it matters

### Technical Requirements
Instructions for Claude Code:
- **Reference Documentation** - Files to read for context
- **Example Implementations** - Similar metrics to study
- **Dataset Compatibility** - Which test datasets apply

### Metric-Specific Details
Helps Claude Code generate accurate SQL:
- **Model Type** - Binary classification, regression, etc.
- **Required Columns** - What data is needed
- **SQL Complexity** - Sets expectations for query structure

### Output Requirements
Defines the structure of generated documentation:
- 9 standard sections following Arthur Platform conventions
- SQL requirements (time bucketing, NULL handling)
- Parameter specifications
- Interpretation guidance

## Best Practices

### Writing Effective Prompts

1. **Be Specific About Use Cases**
   - Don't: "Measures model performance"
   - Do: "Identifies cases where loan amount predictions underestimate by >20%, indicating potential revenue loss"

2. **Provide Context**
   - Cite similar metrics or industry standards
   - Explain mathematical formulas or thresholds
   - Mention edge cases to handle

3. **Specify Dataset Requirements**
   - Exact column names and types needed
   - Optional vs required columns
   - Example values or ranges

4. **Include Interpretation Guidance**
   - What values are "good" vs "bad"
   - When to take action
   - How it relates to business outcomes

### Reviewing Generated Metrics

After Claude Code generates the metric:

1. **Validate SQL**
   - Test query syntax (PostgreSQL/TimescaleDB compatible)
   - Verify NULL handling
   - Check time bucketing logic

2. **Verify Parameters**
   - Correct parameter types (Dataset, Column, Literal)
   - Appropriate tag hints and column types
   - Clear parameter descriptions

3. **Test with Data**
   - Run against test datasets in `/data/`
   - Verify output format matches specification
   - Check edge cases (empty data, NULLs, outliers)

4. **Review Documentation**
   - Clear interpretation guidance
   - Appropriate use cases
   - Correct dataset compatibility list

## Examples

### Simple Metric Prompt

For straightforward metrics like "count of predictions":
```markdown
**Metric Name:** Prediction Count
**Category:** Data Quality & Distribution
**Description:** Daily count of model predictions
**Required Columns:** timestamp (timestamp)
```

### Complex Metric Prompt

For advanced metrics like "rolling 30-day AUC by subgroup":
```markdown
**Metric Name:** Rolling AUC by Segment
**Category:** Model Performance - Ranking & Discrimination
**Description:** 30-day rolling AUC calculated separately for each customer segment
**Required Columns:**
  - timestamp (timestamp)
  - prediction_score (float)
  - ground_truth (int)
  - customer_segment (str)
**Additional Context:** Use window functions for 30-day rolling calculation
```

## Troubleshooting

### Issue: Generated SQL has syntax errors
**Solution:** Provide more specific column type information and SQL complexity level in the prompt

### Issue: Missing parameter configurations
**Solution:** Explicitly list all required columns in "Required Data Columns" section

### Issue: Unclear interpretation guidance
**Solution:** Add more context about "good" vs "bad" values and business impact

### Issue: Dataset compatibility is wrong
**Solution:** Review `/data/` folder structure first and specify exact column mappings

## Contributing

When creating new prompt templates:

1. Follow the structure in `prompts/PROMPT_TEMPLATE.md`
2. Place in `/dev-metrics/prompts/` directory
3. Use descriptive naming (e.g., `[category]-[metric-name]-prompt.md`)
4. Include clear business use case
5. Test generated output with real datasets
6. Document any special considerations

## Related Documentation

- **Main README:** `/README.md` - Repository overview
- **Metric Creation Guide:** `/references/how-to-create-a-custom-metric.md`
- **Example Metrics:** `/examples/metrics/` - Production-ready implementations
- **Configuration Reference:** `/references/configuration-options.md`
- **CLAUDE.md:** Repository guidance for Claude Code
