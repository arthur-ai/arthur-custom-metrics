# Housing Price Prediction Dataset Generator

This directory contains a dataset generator for creating synthetic housing price prediction inference data optimized for computing regression metrics. The dataset simulates a housing price prediction model that predicts median house values based on housing features from the California housing dataset.

## Overview

The dataset generator creates a CSV dataset with:
- **20,640+ samples** of housing records with model predictions
- **Ground truth house values** and **model predicted house values** for regression
- **Continuous numeric values** for both predictions and actual values (compatible with Absolute Error and PPE threshold metrics)
- **Geographic features** (longitude, latitude, ocean proximity) for potential segmentation analysis
- **Housing features** (age, rooms, bedrooms, population, households, income)
- **Timestamp columns** for time-series analysis across ±90 days from today

## Use Case

This dataset simulates a **housing price prediction system** where:
- **Actual House Value**: Ground truth median house value (continuous numeric, $14,999-$500,001)
- **Predicted House Value**: ML model's predicted house value (continuous numeric, $14,999-$500,001)
- **Features**: Longitude, latitude, housing median age, total rooms, total bedrooms, population, households, median income, ocean proximity
- **Geographic Regions**: California housing districts with different price patterns

## Requirements

- Python 3.8+
- pandas
- numpy

Install dependencies:
```bash
pip install pandas numpy
```

## Usage

### Generate Dataset

Run the dataset generator:

```bash
python generate_dataset.py
```

This will:
1. Read the `housing.csv` training file from the parent directory
2. Generate synthetic model predictions based on the features
3. Add timestamp columns for time-series analysis
4. Create partitioned CSV files in the `output/` directory with data spanning ±90 days from today
5. Partition data by date into folders: `output/YYYY-MM-DD/data-YYYY-MM-DD.csv`

### Customize Generation

You can also import and use the generator function programmatically:

```python
from generate_dataset import generate_dataset
from pathlib import Path

# Generate dataset with default settings (reads from ../housing.csv)
df = generate_dataset(
    input_csv_path=Path("../housing.csv"),  # Path to training CSV
    output_dir=Path("output"),              # Output directory (None to skip saving)
    seed=42,                                # Random seed for reproducibility
    past_days=30,                           # 30 days in the past from today
    future_days=60                          # 60 days in the future from today
)

# Use the DataFrame
print(df.head())
```

## Dataset Structure

The generated dataset contains the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `partition_date` | string | Partition date (YYYY-MM-DD format) |
| `timestamp` | string | Timestamp (ISO 8601 format with UTC timezone, e.g., 2026-01-15T10:30:00+00:00) |
| `house_id` | int64 | Unique identifier for each house |
| `actual_house_value` | float64 | Ground truth median house value ($14,999-$500,001) |
| `predicted_house_value` | float64 | Model's predicted house value ($14,999-$500,001) |
| `longitude` | float64 | Longitude coordinate (-124.35 to -114.31) |
| `latitude` | float64 | Latitude coordinate (32.54 to 41.95) |
| `housing_median_age` | int64 | Median age of houses in block (1-52) |
| `total_rooms` | int64 | Total number of rooms in block (2-39,320) |
| `total_bedrooms` | int64 | Total number of bedrooms in block (1-6,445) |
| `population` | int64 | Population in block (3-35,682) |
| `households` | int64 | Number of households in block (1-6,082) |
| `median_income` | float64 | Median income in block (tens of thousands, 0.4999-15.0001) |
| `ocean_proximity` | string | Proximity to ocean (NEAR BAY, INLAND, ISLAND, NEAR OCEAN, <1H OCEAN) |

## Output Format

The dataset is saved as partitioned CSV files by date:
- **Partition structure**: `output/YYYY-MM-DD/data-YYYY-MM-DD.csv`
- **Date range**: ±90 days from today (configurable, default: 90 past + 90 future = 181 days)
- **Timezone**: UTC for all timestamps (ISO 8601 format)
- **Format**: Standard CSV with header row
- **Encoding**: UTF-8
- **Example**: `output/2026-01-15/data-2026-01-15.csv`

Each partition folder contains one CSV file with all records for that date.

## Model Predictions

The generator creates realistic model predictions by:
1. Using housing features (income, age, rooms, population, ocean proximity) to create a base prediction
2. Adding realistic model error (5-15% noise) to simulate imperfect predictions
3. Correlating predictions with actual values (75-90% correlation) to create realistic model performance
4. Ensuring predictions are within reasonable bounds (50% to 200% of actual value)

This creates a realistic inference dataset where:
- Predictions are correlated with actual values (good model performance)
- Some predictions have errors (realistic model imperfection)
- Error distribution is realistic (not too perfect, not too random)

## Compatibility with Metrics

This dataset is optimized for computing the following regression metrics:

### Regression Metrics

1. **Absolute Error** (`/metrics/prediction-accuracy-error/absolute-error.md`)
   - ✅ **Fully Compatible**
   - Uses: `timestamp`, `predicted_house_value`, `actual_house_value`
   - Computes per-record absolute error: `|predicted - actual|`

2. **Core Accuracy at PPE 10% Threshold** (`/metrics/prediction-accuracy-error/core-accuracy-at-ppe-10-threshold.md`)
   - ✅ **Fully Compatible**
   - Uses: `timestamp`, `predicted_house_value`, `actual_house_value`
   - Computes proportion of predictions within 10% of actual value

### Configuration for Metrics

When configuring these metrics in Arthur:

**Absolute Error:**
- `timestamp_col`: `timestamp`
- `prediction_col`: `predicted_house_value`
- `actual_col`: `actual_house_value`

**Core Accuracy at PPE 10% Threshold:**
- `timestamp_col`: `timestamp`
- `prediction_col`: `predicted_house_value`
- `actual_col`: `actual_house_value`

## Example Queries

### Check Dataset Statistics

```python
import pandas as pd
from pathlib import Path

# Read all partitioned CSV files
output_dir = Path('output')
csv_files = list(output_dir.rglob('data-*.csv'))

# Combine all partitions
dfs = []
for csv_file in csv_files:
    df = pd.read_csv(csv_file)
    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)

# Convert timestamp back to datetime if needed
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"Shape: {df.shape}")
print(f"Mean actual: ${df['actual_house_value'].mean():,.2f}")
print(f"Mean predicted: ${df['predicted_house_value'].mean():,.2f}")
print(f"MAE: ${abs(df['actual_house_value'] - df['predicted_house_value']).mean():,.2f}")

# Or read a specific date partition
df_single = pd.read_csv('output/2026-01-15/data-2026-01-15.csv')
print(f"Single partition shape: {df_single.shape}")
```

## Notes

- The training dataset (`housing.csv`) contains 20,640 samples from the California housing dataset
- All samples are used to generate the inference dataset
- Predictions are generated synthetically but are based on realistic model behavior
- The dataset maintains the original feature distributions from the training data
- Timestamps are distributed evenly across the date range for consistent time-series analysis
