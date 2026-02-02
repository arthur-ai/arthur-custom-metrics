# Card Fraud Dataset Generator

This directory contains a dataset generator for creating synthetic card fraud transaction data. The dataset simulates credit card transactions with fraud detection features and is organized in a hierarchical JSON structure.

## Overview

The dataset generator creates JSON files organized by:
- **Year** (`year=YYYY/`)
- **Month** (`month=MM/`)
- **Day** (`day=DD/`)
- **Hour** (`inferences_hour=HH.json`)

Each JSON file contains an array of transaction records with fraud detection features.

## Use Case

This dataset simulates a **credit card fraud detection system** where:
- **Transactions**: Credit card transactions with various features
- **Ground Truth**: `is_fraud` (binary: 0=legitimate, 1=fraud)
- **Model Prediction**: `fraud_score` (continuous 0-1 probability) and `fraud_pred` (binary prediction)
- **Features**: Transaction amount, distance from home, merchant risk, customer segment, channel, region, etc.

## Requirements

- Python 3.8+
- numpy

Install dependencies:
```bash
pip install numpy
```

## Usage

### Generate Dataset

Run the dataset generator:

```bash
python generate_dataset.py
```

This will create:
- **Main dataset**: `ccb-card-fraud/` (±90 days from today, default)
- **Reference dataset**: `ccb-card-fraud-reference/` (first 14 days of the main dataset range)

### Customize Generation

You can also import and use the generator function programmatically:

```python
from generate_dataset import generate_dataset
from pathlib import Path

# Generate main dataset with default ±90 days from today
stats = generate_dataset(
    transactions_per_hour=60,
    output_dir=Path("output/ccb-card-fraud"),
    seed=42
)

# Or specify custom date range using past_days and future_days
stats = generate_dataset(
    past_days=30,        # 30 days in the past
    future_days=60,      # 60 days in the future
    transactions_per_hour=60,
    output_dir=Path("output/ccb-card-fraud"),
    seed=42
)

# Or specify exact dates
stats = generate_dataset(
    start_date="2025-11-01",
    end_date="2026-01-14",
    transactions_per_hour=60,
    output_dir=Path("output/ccb-card-fraud"),
    seed=42
)

print(f"Generated {stats['total_transactions']} transactions")
print(f"Fraud rate: {stats['fraud_rate']:.2%}")
```

## Dataset Structure

Each transaction record contains the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string (ISO 8601) | Transaction timestamp with UTC timezone |
| `txn_id` | string (UUID) | Unique transaction identifier |
| `account_id` | string | Account identifier (format: `acct_XXXXX`) |
| `customer_id` | string | Customer identifier (format: `cust_XXXXX`) |
| `is_fraud` | int (0 or 1) | Ground truth fraud label (1=fraud, 0=legitimate) |
| `fraud_score` | float (0-1) | Model's fraud probability score |
| `fraud_pred` | int (0 or 1) | Model's binary fraud prediction (threshold at 0.5) |
| `rules_engine_flag` | int (0 or 1) | Rule-based system flag (1=flagged, 0=not flagged) |
| `risk_rank` | int (1-5) | Risk ranking based on fraud_score (1=lowest, 5=highest) |
| `customer_segment` | string | Customer segment: `new_to_bank`, `established`, `small_business` |
| `channel` | string | Transaction channel: `ecom`, `in_store`, `atm` |
| `region` | string | Geographic region: `W`, `NE`, `MW`, `S` |
| `txn_amount` | float | Transaction amount in USD ($1-$10,000) |
| `distance_from_home_km` | float | Distance from customer's home location in kilometers |
| `merchant_risk_score` | float (0-1) | Merchant risk score (0=low risk, 1=high risk) |
| `digital_engagement` | float | Digital engagement score (0-10) |
| `tenure_months` | int | Customer tenure with bank in months |

## Output Format

The dataset is saved as **JSON files** in a hierarchical directory structure:

```
output/
└── ccb-card-fraud/
    └── year=2025/
        └── month=11/
            └── day=01/
                ├── inferences_hour=00.json
                ├── inferences_hour=01.json
                ├── inferences_hour=02.json
                └── ...
    └── year=2026/
        └── month=01/
            └── day=01/
                └── ...
```

Each JSON file contains an array of transaction objects:

```json
[
  {
    "timestamp": "2025-11-01T00:00:00+00:00",
    "txn_id": "6382e493-c04a-411d-a35b-ef7f644b77a3",
    "account_id": "acct_16068",
    "customer_id": "cust_5367",
    "is_fraud": 0,
    "fraud_score": 0.056296,
    "fraud_pred": 0,
    "rules_engine_flag": 0,
    "risk_rank": 1,
    "customer_segment": "new_to_bank",
    "channel": "ecom",
    "region": "W",
    "txn_amount": 16.58,
    "distance_from_home_km": 4.37,
    "merchant_risk_score": 0.4352,
    "digital_engagement": 4.05,
    "tenure_months": 5
  },
  ...
]
```

### Reading the Dataset

```python
import json
from pathlib import Path

# Read a specific hour file
file_path = Path("output/ccb-card-fraud/year=2025/month=11/day=01/inferences_hour=00.json")
with open(file_path, 'r') as f:
    transactions = json.load(f)

# Process transactions
for txn in transactions:
    print(f"Transaction {txn['txn_id']}: ${txn['txn_amount']}, Fraud: {txn['is_fraud']}")
```

## Dataset Characteristics

- **Transaction volume**: 60 transactions per hour (1,440 per day)
- **Fraud rate**: ~5-7% (varies based on transaction characteristics)
- **Time span**: Configurable (default: Nov 2025 - Jan 2026)
- **Customer segments**:
  - `new_to_bank`: 15% of transactions
  - `established`: 70% of transactions
  - `small_business`: 15% of transactions
- **Channels**:
  - `ecom`: 60% of transactions
  - `in_store`: 35% of transactions
  - `atm`: 5% of transactions
- **Regions**: W, NE, MW, S (equal distribution)

## Fraud Patterns

The generator creates realistic fraud patterns:

- **Higher fraud risk** for:
  - New customers (`new_to_bank` segment)
  - Large transactions (>$500)
  - Transactions far from home (>50km)
  - High merchant risk scores (>0.5)
  - ATM transactions

- **Model performance**:
  - `fraud_score` is correlated with actual fraud (~75-85% correlation)
  - Model has realistic false positives and false negatives
  - Binary prediction (`fraud_pred`) uses 0.5 threshold

## Metrics Supported

This dataset is optimized for computing classification metrics:

- **Binary Classification Metrics**:
  - Precision, Recall, F1 Score
  - True Positive Rate, False Positive Rate
  - ROC-AUC, PR-AUC
  - Confusion Matrix metrics

- **Fraud Detection Specific**:
  - Fraud Detection Rate
  - False Positive Rate
  - Alert Rate
  - Rules Engine Performance

## Reference Dataset

The generator also creates a **reference dataset** (`ccb-card-fraud-reference`) which is typically:
- Smaller time range (e.g., 2 weeks)
- Used as a baseline for comparison
- Useful for drift detection and model monitoring

## Customization

You can customize the generation by modifying:

- **Date range**: `start_date` and `end_date` parameters
- **Transaction volume**: `transactions_per_hour` parameter
- **Fraud rate**: Adjust `fraud_base_prob` in the code
- **Customer segment distribution**: Modify probabilities in `np.random.choice()`
- **Channel distribution**: Modify probabilities in `np.random.choice()`
- **Fraud patterns**: Adjust fraud risk factors in the code

## Testing

To verify the generated dataset:

```python
import json
from pathlib import Path

# Load a sample file
file_path = Path("output/ccb-card-fraud/year=2025/month=11/day=01/inferences_hour=00.json")
with open(file_path, 'r') as f:
    transactions = json.load(f)

# Verify structure
assert len(transactions) == 60  # 60 transactions per hour
assert all('is_fraud' in txn for txn in transactions)
assert all('fraud_score' in txn for txn in transactions)
assert all(0 <= txn['fraud_score'] <= 1 for txn in transactions)

# Check fraud rate
fraud_count = sum(1 for txn in transactions if txn['is_fraud'] == 1)
fraud_rate = fraud_count / len(transactions)
print(f"Fraud rate: {fraud_rate:.2%}")
```
