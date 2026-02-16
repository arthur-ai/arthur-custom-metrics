# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a documentation and automation repository for Arthur AI Platform custom metrics and charts. It contains:
- Production-ready custom metric implementations
- Custom chart visualizations
- Test dataset generators
- LLM prompt templates for metric development
- Python automation scripts for model onboarding

## Development Commands

### Dataset Generation

Generate synthetic test data (±90 days from current date):

```bash
# Navigate to specific dataset directory
cd data/<dataset-name>/datagen

# Install dependencies
pip install pandas numpy pyarrow

# Run generator
python generate_dataset.py

# Run tests
python run_tests.py
```

Available datasets:
- `binary-classifier-card-fraud` - Credit card fraud detection
- `binary-classifier-cc-application` - Credit approval
- `regression-loan-amount-prediction` - Loan amount prediction
- `regression-housing-price-prediction` - Housing price prediction

### Model Onboarding Scripts

Install Arthur SDK:
```bash
pip install arthur-client
```

Main onboarding workflow:
```bash
cd scripts/onboarding

# 1. Initial model setup (creates connector, dataset, model, schedule)
python model-onboarding.py

# 2. Add domain-specific metrics
python add-fraud-model-aggregations.py        # For fraud detection models
python add-regression-model-aggregations.py   # For regression models
python add-custom-aggregations.py            # For custom metrics
```

Utility scripts:
```bash
python service-account-creation.py           # Create service accounts
python add-column-to-schema.py              # Modify dataset schema
python remove-column-from-schema.py         # Remove columns
python duplicate-metrics-to-new-datasets.py # Copy metrics between datasets
```

## Architecture

### Metric Documentation Structure

All metrics in `/examples/metrics/` follow this standard structure:

1. **Overview** - What the metric tracks, when to use it
2. **Step 1: Write the SQL** - Complete SQL query with TimescaleDB `time_bucket()` aggregation
3. **Step 2: Fill Basic Information** - Name and description
4. **Step 3: Configure Aggregate Arguments** - Parameters (Dataset, Column, Literal types)
5. **Step 4: Configure Reported Metrics** - Output specification (value column, timestamp column, metric kind)
6. **Interpreting the Metric** - How to read values and identify issues
7. **Use Cases** - Real-world applications

Metrics are organized by model type:
- `binary-classification/` - Binary classification metrics (Gini, PSI, error profiles)
- `multi-classification/` - Multi-label metrics (Jaccard, coverage, confusion matrix)
- `regression/` - Regression metrics (RMSE, MAD, percentage errors)

### Chart Documentation Structure

Charts in `/examples/charts/` follow this structure:

1. **Chart Title**
2. **Metrics Used** - Which metrics and dimensions
3. **SQL Query** - Query to fetch data for visualization
4. **What this shows** - Visual description
5. **How to interpret it** - Reading patterns, action triggers

### Dev-Metrics Workflow (LLM-Assisted Development)

The `/dev-metrics/prompts/` directory contains prompt templates for generating new metrics with LLMs:

1. Copy `PROMPT_TEMPLATE.md` or use an existing prompt as a template
2. Fill in metric details (name, type, description, business use case)
3. Provide the prompt to Claude Code along with reference docs
4. Generated metric follows the standard documentation structure
5. Output goes to corresponding `.md` file in `/examples/metrics/`

All prompt files are located in `/dev-metrics/prompts/`:
- `PROMPT_TEMPLATE.md` - Master template for new metrics
- `absolute-error-prompt.md` - Example accuracy metric prompt
- `accuracy-prompt.md` - Example classification metric prompt
- Additional domain-specific prompts

Reference documents automatically included:
- `/references/how-to-create-a-custom-metric.md` - Metric creation guide
- `/references/overview-metrics-and-querying.md` - Querying overview
- `/references/configuration-options.md` - Valid configuration values
- `/references/platform-default-metrics.md` - Out-of-the-box metrics
- `/references/sql_schema_metrics_numeric_latest_version.md` - Numeric metrics table schema (for Dashboard Chart SQL)
- `/references/sql_schema_metrics_sketch_latest_version.md` - Sketch metrics table schema (for Dashboard Chart SQL)
- Examples from `/examples/metrics/` - Similar metric implementations

### Python Automation Scripts

Scripts in `/scripts/onboarding/` use the Arthur SDK to automate:

1. **S3 Connector Setup** - Configure AWS S3 data sources (access keys or IAM roles)
2. **Dataset Creation** - Schema inspection and dataset configuration
3. **Model Onboarding** - Create models with metrics and refresh schedules
4. **Custom Metrics** - Add aggregations (distributions, counts, error profiles)
5. **Schema Management** - Add/remove columns from datasets

All scripts use device-based authentication by default:
```python
from arthur_client.auth import DeviceAuthorizer
sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
```

For automation/CI-CD, use service account authentication (see `using-sdk-with-service-account-creds.py`).

## Key SQL Patterns

### TimescaleDB Time Bucketing

All time-series metrics use TimescaleDB's `time_bucket()`:
```sql
time_bucket(INTERVAL '1 day', {{timestampColumnName}}) AS ts
```

### Parameterized Queries

Metrics use double-brace template variables:
- `{{dataset}}` - Dataset reference
- `{{columnName}}` - Column parameters
- `{{literalValue}}` - Literal parameters (thresholds, labels)

### NULL Handling

Always handle NULLs in aggregations:
```sql
COALESCE(column_name, 0)  -- For numeric columns
NULLIF(COUNT(*), 0)       -- Prevent division by zero
```

## Dashboard Chart SQL Patterns

Chart SQL queries read from stored metrics tables, not the raw dataset.

### Metrics Tables

**metrics_numeric_latest_version** - For numeric metrics
- Columns: model_id, project_id, workspace_id, organization_id, metric_name, timestamp, metric_version, value (double precision), dimensions (jsonb)

**metrics_sketch_latest_version** - For sketch/distribution metrics
- Columns: Same as numeric, but value is user-defined type

### Chart SQL Pattern

```sql
SELECT
    time_bucket_gapfill(
        '1 day',                           -- Time bucket size
        timestamp,                          -- Timestamp column
        '{{dateStart}}'::timestamptz,      -- Start of time range
        '{{dateEnd}}'::timestamptz         -- End of time range
    ) AS time_bucket_1d,

    metric_name,

    CASE                                    -- Optional: friendly names
        WHEN metric_name = 'my_metric' THEN 'My Metric'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version        -- Or metrics_sketch_latest_version
WHERE metric_name IN ('metric1', 'metric2')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]  -- Optional filter syntax

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**Key elements:**
- `time_bucket_gapfill()` - Creates continuous time series with no gaps
- `{{dateStart}}` and `{{dateEnd}}` - Template variables for time range
- `[[AND ...]]` - Optional filter syntax
- Filter by `metric_name` - Must match names from "Reported Metrics" section
- `COALESCE(AVG(value), 0)` - Handle missing values gracefully

## Configuration Reference

### Aggregate Argument Types

- **Dataset** - Reference to the data source
- **Column** - Column selection with optional type filtering
- **Literal** - Fixed values (strings, numbers, booleans)

### Allowed Column Types

Use comma-separated values: `int, float, bool, str, uuid, timestamp, date, json, image`

**Important**: Use `int` and/or `float`, not `numeric`

### Tag Hints

Use comma-separated values: `primary_timestamp, categorical, continuous, prediction, ground_truth, pin_in_deep_dive, possible_segmentation`

**Important**: Use `ground_truth`, not `label`

### Data Types

String, Integer, Float, Boolean, UUID, Timestamp, Date, JSON

## Important Notes

- Metric SQL queries must use TimescaleDB/PostgreSQL syntax
- Test datasets generate data ±90 days from current date by default
- Model onboarding requires Arthur project ID from the UI
- S3 file patterns support strftime formatting (`%Y%m%d`) for date partitioning
- Custom metrics support versioning - models continue using previous versions until explicitly updated
- Dataset generators require Python 3.8+ with numpy, pandas, pyarrow
- Arthur SDK scripts require `arthur-client` package
