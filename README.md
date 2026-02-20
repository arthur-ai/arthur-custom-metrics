# Arthur Platform Custom Metrics

Comprehensive documentation and examples for building custom metrics and charts in the Arthur AI platform.

This repository provides the following:
* Example custom metrics in `/examples/metrics`
* Example custom charts in `/examples/charts`
* Test dataset for various model types in `/data`
* Example LLM prompts for developing new custom metrics and their generated outputs in `/dev-metrics`
* Automation scripts for model onboarding and metric configuration in `/scripts`

Read about Arthur Metrics:
* [Customize your Arthur dashboard](https://docs.arthur.ai/docs/customize-your-dashboard)
* [Metrics Querying Overview](https://docs.arthur.ai/docs/metrics-querying-overview-1)
* [Custom Metrics](https://docs.arthur.ai/docs/custom-metrics)

## Metric Documentation Structure

Each metric file follows this structure:

### 1. Overview
- What the metric tracks
- Key insights it provides
- When to use it

### 2. Data Requirements
- Required columns (timestamp, IDs, labels, scores)
- Data types and formats

### 3. Base Metric SQL
- Complete SQL query with CTEs
- TimescaleDB time_bucket aggregation
- Handles NULL values and edge cases

### 4. Aggregate Arguments
Detailed parameter configuration for each argument:
- Parameter Key (variable name in SQL)
- Friendly Name (UI display)
- Description
- Parameter Type (Column, Dataset, etc.)
- Source Dataset Parameter Key
- Allow Any Column Type (Yes/No)
- Tag Hints (e.g., primary_timestamp, prediction)
- Allowed Column Types (timestamp, int, str, uuid, etc.)

### 5. Reported Metrics
Specification for each output metric:
- Metric Name
- Description
- Value Column (column name in SQL output)
- Timestamp Column
- Metric Kind (Numeric, Categorical)
- Dimension Column (for per-label metrics)

### 6. Interpreting the Metric
- What different values mean
- Trends to watch for
- Common patterns
- When to investigate

### 7. Use Cases
- Real-world applications
- Example scenarios
- When this metric is most valuable

## Chart Documentation Structure

Each chart file follows this structure:

### 1. Chart Title
Clear, descriptive name

### 2. Metrics Used
- Which metrics this chart visualizes
- Column names and dimensions

### 3. SQL Query
- Query to fetch data for visualization
- Often aggregates or filters base metrics
- Includes time range filters

### 4. What this shows
- Visual description of the chart
- What patterns it reveals

### 5. How to interpret it
- How to read the visualization
- What different patterns mean
- When to take action
- Typical value ranges

### Creating a New Custom Metric

1. **Navigate to the `/dev-metrics/prompts/` folder** and find an existing prompt similar to what you want to build
2. **Copy `PROMPT_TEMPLATE.md` or a `-prompt.md` file** (e.g., `absolute-error-prompt.md`) and rename it for your new metric
3. **Fill out the prompt template** with details about your metric (name, category, description, business use case)
4. **Open the repository in your LLM tool** (e.g., Claude Code, Cursor IDE)
5. **Feed the `-prompt.md` file as the prompt to your LLM** along with the reference documentations
6. **Review and refine** the generated metric implementation in the corresponding `.md` file

**Note**: See examples in `/examples/metrics` for production-ready metric implementations organized by problem type (binary-classification, multi-classification, regression).

### How to Generate a Synthentic Data Set

1. **Navigate to the `/data` directory** and choose a dataset generator:
   - `binary-classifier-card-fraud/` - Binary classification (fraud detection)
   - `binary-classifier-cc-application/` - Binary classification (credit approval)
   - `regression-loan-amount-prediction/` - Regression (loan amount prediction)
   - `regression-housing-price-prediction/` - Regression (housing price prediction)

2. **Install dependencies** (if needed):
   ```bash
   pip install pandas numpy pyarrow
   ```

3. **Run the generator**:
   ```bash
   cd data/<dataset-name>/datagen
   python generate_dataset.py
   ```

4. **Verify the output** in the `output/` directory

Each synthetic dataset generator includes:
- Realistic synthetic data with proper schemas of +/- 90 days from the current date
- Ground truth labels and model predictions
- Time-series data partitioned by date
- README with dataset-specific documentation

## Automation Scripts

The `/scripts/onboarding` directory contains Python scripts for automating model onboarding and metric configuration in the Arthur platform. These scripts use the Arthur SDK to programmatically set up models, datasets, connectors, and custom metrics.

For detailed documentation, see [`/scripts/onboarding/README.md`](scripts/onboarding/README.md).
