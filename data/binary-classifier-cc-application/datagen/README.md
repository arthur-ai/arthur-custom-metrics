# Credit Card Application Dataset Generator

This directory contains a dataset generator for creating synthetic credit card application data optimized for computing classification and discrimination metrics. The dataset simulates a credit card application model that evaluates applicant risk and makes approval/rejection decisions.

## Overview

The dataset generator creates a parquet dataset with:
- **1,000 samples** of credit card applications with model predictions
- **Ground truth approval decisions** and **model predictions** for binary classification
- **Predicted probabilities** for threshold-based metrics (ROC, PR curves, KS, Gini)
- **Geographic regions** for discrimination/fairness metrics analysis
- **Credit risk features** (credit score, income, age, employment, etc.)
- **Date partitioning** (DATE type) for efficient querying across ±90 days from today

## Use Case

This dataset simulates a **credit card application approval system** where:
- **Actual Label (1=Approved, 0=Rejected)**: Ground truth approval decision based on applicant creditworthiness
- **Predicted Label**: ML model's approval/rejection prediction
- **Predicted Probability**: Model's confidence score for approval (0-1)
- **Features**: Credit score, income, age, employment status, debt-to-income ratio, credit history, etc.
- **Regions**: Geographic regions with different approval rates for discrimination analysis

## Requirements

- Python 3.8+
- pandas
- numpy
- pyarrow

Install dependencies:
```bash
pip install pandas numpy pyarrow
```

## Usage

### Generate Dataset

Run the dataset generator:

```bash
python generate_dataset.py
```

This will create a partitioned parquet dataset in the `model_predictions/` directory with data spanning ±90 days from today.

### Customize Generation

You can also import and use the generator function programmatically:

```python
from generate_dataset import generate_dataset
from pathlib import Path

# Generate dataset with default ±90 days from today
df = generate_dataset(
    n_samples=1000,           # Number of applications
    output_dir=Path("output"), # Output directory (None to skip saving)
    seed=42                   # Random seed for reproducibility
)

# Or specify custom date range
df = generate_dataset(
    n_samples=1000,
    output_dir=Path("output"),
    seed=42,
    past_days=30,      # 30 days in the past from today
    future_days=60     # 60 days in the future from today
)

# Use the DataFrame
print(df.head())
```

## Dataset Structure

The generated dataset contains the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `partition_date` | date | Partition date (DATE type in parquet) |
| `timestamp` | timestamp | Timestamp (timestamp[ns] with UTC timezone in parquet) |
| `application_id` | int64 | Unique identifier for each application |
| `region` | string | Geographic region (Region_North, Region_South, Region_East, Region_West) |
| `actual_label` | int64 | Ground truth approval decision (1=Approved, 0=Rejected) |
| `predicted_label` | int64 | Model's predicted approval decision (1=Approved, 0=Rejected) |
| `predicted_probability` | float64 | Model's approval probability score (0-1) |
| `is_valid_application` | int64 | Valid application indicator (1=valid, 0=invalid) |
| `credit_score` | int64 | Applicant's credit score (300-850) |
| `annual_income` | int64 | Applicant's annual income in USD (20,000-200,000) |
| `age` | int64 | Applicant's age (18-75) |
| `employment_status` | string | Employment status (Employed, Self-employed, Unemployed, Retired) |
| `years_at_job` | int64 | Years at current job (0-40) |
| `debt_to_income_ratio` | float64 | Debt-to-income ratio (0-0.8) |
| `num_credit_cards` | int64 | Number of existing credit cards (0-10) |
| `years_credit_history` | int64 | Years of credit history (0-50) |

## Output Format

The dataset is saved as a **partitioned parquet** file structure with strftime format:

```
model_predictions/
├── 2025-10-29/
│   └── data-2025-10-29.parquet
├── 2025-10-30/
│   └── data-2025-10-30.parquet
└── ...
```

### Reading the Dataset

```python
import pandas as pd

# Read entire dataset
df = pd.read_parquet('model_predictions')

# Read specific date partition
df = pd.read_parquet('model_predictions/2025-10-29')
```

## Data Types

The dataset uses proper data types for compatibility:

- **partition_date**: DATE type (date32 in parquet) - stored as Python date objects
- **All numeric features**: Proper int64/float64 types
- **String features**: Stored as strings
- **No timestamp column**: Removed to simplify the schema

## JSON Serialization

The dataset is designed to be **fully JSON serializable** to avoid issues with systems like DuckDB:

- Dates are stored as **date objects** (converted to strings for JSON)
- All numpy types are converted to native Python types
- No pandas Timestamp objects remain in the data

## Testing

Run the unit tests to verify dataset generation and data integrity:

```bash
pip install 

# Run all tests
python -m pytest test_dataset.py -v

# Or using unittest
python test_dataset.py

# Or using the test runner
python run_tests.py
```

### Test Coverage

The test suite verifies:
- ✅ JSON serialization of entire DataFrame
- ✅ JSON serialization of individual rows
- ✅ No pandas Timestamp objects
- ✅ Date objects only in partition_date column
- ✅ Partition date is DATE type
- ✅ Parquet read/write compatibility
- ✅ All numpy types converted to native Python types
- ✅ Data structure matches credit card application schema
- ✅ All feature ranges are valid (credit score, income, age, etc.)
- ✅ Business logic constraints (unemployed/retired have 0 years at job)
- ✅ Approval rates are reasonable

## Metrics Supported

This dataset is optimized for computing the following classification and discrimination metrics (see `metrics.MD`):

### Classification Metrics
- Adjusted False Positive Rate
- Agreement Rate
- Area Under Precision-Recall Curve (AUC-PR)
- Area Under the Curve (AUC-ROC)
- AUC Relative Decrease
- Capture Rate
- Classification Statistics
- Correct Acceptance Rate
- Correct Detection Rate
- F1 Score
- False Negative Percentage/Rate
- False Positive Rate/Ratio
- Gini Coefficient
- Kolmogorov-Smirnov Statistic (KS Score)
- Negative Predictive Value
- Overprediction Rate
- Precision
- Recall
- Receiver Operating Characteristic (ROC)
- Total False Positive Rate
- True Detection Rate
- True Positive Rate (Recall)
- Underprediction Rate
- Valid Detection Rate

### Discrimination/Fairness Metrics
- **Bad Case Rate**: Approval rate (proportion of applications approved)
- **Rate Difference**: Difference in approval rates between regions
- **Relative Bad Rate Difference**: Normalized difference in approval rates between regions

## Dataset Characteristics

- **Approval rate**: Varies by region (~10-25% approval rate)
- **Regional differences**: Different approval rates across regions for discrimination analysis
  - Region_North: ~25% approval rate
  - Region_South: ~15% approval rate
  - Region_East: ~20% approval rate
  - Region_West: ~18% approval rate
- **Realistic model behavior**: Model predictions correlated with actual approvals but include realistic error
- **Time span**: ±90 days from today (181 days total)
- **Partitioning**: Partitioned by date in strftime format (%Y-%m-%d/) for efficient querying
- **Feature correlations**: Features are realistically correlated (e.g., credit score with number of cards, age with credit history)
