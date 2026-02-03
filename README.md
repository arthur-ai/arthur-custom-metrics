# Arthur Platform Custom Metrics

A development kit for creating, testing, and deploying custom metrics for the Arthur AI Platform. This repository provides a prompt engineering framework and synthetic dataset generators to streamline the development of custom metrics.

## Overview

Arthur **Custom Metrics** allow you to define model- or business-specific metrics using SQL. Custom metrics are evaluated during metrics calculation jobs and appear alongside Arthur's built-in metrics in dashboards and alerts.

This repository includes:

- **Custom Metric Templates**: Pre-built metric definitions with SQL queries, configuration instructions, and visualization examples
- **Prompt Engineering Framework**: Structured prompts (`-prompt.md` files) that guide LLM tools to generate complete custom metric implementations
- **Test Data Generators**: Synthetic dataset generators for common ML use cases (fraud detection, credit applications, loan prediction)
- **Reference Documentation**: Comprehensive guides on creating custom metrics, querying metrics, and configuration options (for the prompt engineering tasks)

## Quick Start

### Creating a New Custom Metric

1. **Navigate to the `/metrics` folder** and find an existing metric similar to what you want to build
2. **Copy a `-prompt.md` file** (e.g., `accuracy-prompt.md`) and rename it for your new metric
3. **Fill out the prompt template** with details about your metric
4. **Open the repository in your LLM tool** (e.g., Cursor IDE) to give it access to the `/references` folder
5. **Feed the `-prompt.md` file to the LLM** along with the reference documentation
6. **Review and refine** the generated metric implementation in the corresponding `.md` file

The generated metric will include:
- SQL query for computing the metric
- Aggregate argument configurations
- Reported metric configurations
- Example visualization queries
- Dataset compatibility information

### Generating Test Data

1. **Navigate to the `/data` directory** and choose a dataset generator:
   - `card-fraud/` - Binary classification (fraud detection)
   - `cc-application/` - Binary classification (credit approval)
   - `loan-amount-prediction/` - Regression (loan amount prediction)

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

Each dataset generator includes:
- Realistic synthetic data with proper schemas
- Ground truth labels and model predictions
- Time-series data partitioned by date
- README with dataset-specific documentation
