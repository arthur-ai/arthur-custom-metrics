# Loan Amount Prediction Dataset Generator

This directory contains a dataset generator for creating synthetic loan amount prediction data optimized for computing regression metrics. The dataset simulates a loan approval model that predicts the approved loan amount based on applicant features.

## Overview

The dataset generator creates a parquet dataset with:
- **1,000 samples** of loan applications with model predictions
- **Ground truth loan amounts** and **model predicted loan amounts** for regression
- **Continuous numeric values** for both predictions and actual values (compatible with Absolute Error metric)
- **Geographic regions** for potential segmentation analysis
- **Loan underwriting features** (credit score, income, age, employment, debt-to-income ratio, etc.)
- **Date partitioning** (DATE type) for efficient querying across ±90 days from today

## Use Case

This dataset simulates a **loan amount prediction system** where:
- **Actual Loan Amount**: Ground truth approved loan amount (continuous numeric, $5,000-$500,000)
- **Predicted Loan Amount**: ML model's predicted loan amount (continuous numeric, $5,000-$500,000)
- **Features**: Credit score, income, age, employment status, debt-to-income ratio, loan purpose, etc.
- **Regions**: Geographic regions with different loan amount patterns

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

This will create a partitioned parquet dataset in the `output/` directory with data spanning ±90 days from today.

### Customize Generation

You can also import and use the generator function programmatically:

```python
from generate_dataset import generate_dataset
from pathlib import Path

# Generate dataset with default ±90 days from today
df = generate_dataset(
    n_samples=1000,           # Number of loan applications
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
| `loan_id` | int64 | Unique identifier for each loan application |
| `region` | string | Geographic region (Region_North, Region_South, Region_East, Region_West) |
| `actual_loan_amount` | float64 | Ground truth approved loan amount ($5K-$500K) |
| `predicted_loan_amount` | float64 | Model's predicted loan amount ($5K-$500K) |
| `is_valid_application` | int64 | Valid application indicator (1=valid, 0=invalid) |
| `credit_score` | int64 | Applicant's credit score (300-850) |
| `annual_income` | int64 | Applicant's annual income in USD (20,000-200,000) |
| `age` | int64 | Applicant's age (18-75) |
| `employment_status` | string | Employment status (Employed, Self-employed, Unemployed, Retired) |
| `years_at_job` | int64 | Years at current job (0-40) |
| `debt_to_income_ratio` | float64 | Debt-to-income ratio (0-0.8) |
| `loan_purpose` | string | Purpose of the loan (Home Purchase, Debt Consolidation, Business, Education, Other) |
| `loan_term_months` | int64 | Loan term in months (12, 24, 36, 48, 60) |
| `years_credit_history` | int64 | Years of credit history (0-50) |
| `num_existing_loans` | int64 | Number of existing loans (0-5) |

## Output Format

The dataset is saved as a **partitioned parquet** file structure with strftime format:

```
output/
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
df = pd.read_parquet('output')

# Read specific date partition
df = pd.read_parquet('output/2025-10-29')
```

## Data Types

The dataset uses proper data types for compatibility:

- **partition_date**: DATE type (date32 in parquet) - stored as Python date objects
- **All numeric features**: Proper int64/float64 types
- **String features**: Stored as strings
- **timestamp**: Timestamp with UTC timezone

## JSON Serialization

The dataset is designed to be **fully JSON serializable** to avoid issues with systems like DuckDB:

- Dates are stored as **date objects** (converted to strings for JSON)
- All numpy types are converted to native Python types
- No pandas Timestamp objects remain in the data

## Metrics Supported

This dataset is optimized for computing the following regression metrics:

### Regression Metrics
- **Absolute Error**: Mean absolute error between predicted and actual loan amounts
- **Mean Squared Error (MSE)**: Average squared difference between predictions and actuals
- **Root Mean Squared Error (RMSE)**: Square root of MSE
- **Mean Absolute Percentage Error (MAPE)**: Average percentage error
- **R-squared (R²)**: Coefficient of determination

### Use with Absolute Error Custom Metric

This dataset is **fully compatible** with the Absolute Error custom metric:

- **Required columns:**
  - `timestamp`: Timestamp column for time bucketing
  - `predicted_loan_amount`: Continuous numeric prediction column
  - `actual_loan_amount`: Continuous numeric ground truth column

- **Configuration for Absolute Error metric:**
  - `timestamp_col`: `timestamp`
  - `prediction_col`: `predicted_loan_amount`
  - `actual_col`: `actual_loan_amount`

## Dataset Characteristics

- **Loan amount range**: $5,000 to $500,000
- **Realistic correlations**: Loan amounts correlate with income, credit score, employment status, etc.
- **Model error**: Predictions have 75-90% correlation with actual values, simulating realistic model performance
- **Regional differences**: Different regions may have slightly different loan amount patterns
- **Time span**: ±90 days from today (181 days total)
- **Partitioning**: Partitioned by date in strftime format (%Y-%m-%d/) for efficient querying
- **Feature correlations**: Features are realistically correlated (e.g., credit score with income, age with credit history)

## Testing

Run the unit tests to verify dataset generation and data integrity:

```bash
# Run all tests
python test_dataset.py
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
- ✅ Data structure matches loan amount prediction schema
- ✅ All feature ranges are valid (credit score, income, age, etc.)
- ✅ Business logic constraints (unemployed/retired have 0 years at job)
- ✅ Loan amounts are within realistic bounds ($5K-$500K)
- ✅ Both actual and predicted loan amounts are continuous numeric values
