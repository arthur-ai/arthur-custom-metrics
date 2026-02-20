# Compliance Alert Multi-Label Dataset Generator

This directory contains a dataset generator for creating synthetic financial transaction compliance data. The dataset simulates a transaction monitoring system that flags transactions for multiple compliance alert types simultaneously, making it a **multi-label classification** problem.

## Overview

The dataset generator creates date-partitioned Parquet files with:
- **~50 transactions per hour** across a configurable date range (default: ±90 days from today)
- **Ground truth alert labels** confirmed by compliance analysts (zero or more per transaction)
- **Model-predicted labels** and **per-label confidence scores** from an ML-based alert model
- **Transaction features** including amount, channel, countries, customer segment, and account history

## Use Case

This dataset simulates a **financial transaction compliance monitoring system** where:
- **Ground Truth**: `ground_truth_labels` — array of compliance alert labels confirmed by human analysts
- **Model Prediction**: `predicted_labels` — array of labels predicted by the ML model (threshold at 0.5)
- **Confidence Scores**: `pred_prob_<label>` — model probability (0–1) for each alert type
- **Features**: Transaction amount, channel, sender/receiver countries, customer segment, account age, transaction frequency

### Alert Labels (6 classes, non-exclusive)

| Label | Description |
|-------|-------------|
| `AML` | Anti-money laundering — large cross-border flows, high-risk jurisdictions, high frequency |
| `STRUCTURING` | Amounts just below the $10 k Currency Transaction Report threshold |
| `SANCTIONS` | Counterparty in a sanctions-designated jurisdiction (BY, IR, KP, SY) |
| `PEP` | Politically exposed person involvement — more prevalent in private banking / wealth management |
| `HIGH_RISK_COUNTRY` | Transaction touches a high-risk jurisdiction (NG, RU, MM, VE, etc.) |
| `UNUSUAL_PATTERN` | Activity inconsistent with the account's history (new account with high volume, frequency spike) |

## Requirements

- Python 3.8+
- numpy
- pandas
- pyarrow

Install dependencies:
```bash
pip install numpy pandas pyarrow
```

## Usage

### Generate Dataset

```bash
python generate_dataset.py
```

This will create:
- **Main dataset**: `output/multi-label-compliance/` (±90 days from today, ~216k transactions)
- **Reference dataset**: `output/multi-label-compliance-reference/` (first 14 days)

### Customize Generation

```python
from generate_dataset import generate_dataset, generate_reference_dataset
from pathlib import Path

# Generate with default ±90 days from today
stats = generate_dataset(
    transactions_per_hour=50,
    output_dir=Path("output/multi-label-compliance"),
    seed=42
)

# Specify custom date range
stats = generate_dataset(
    past_days=30,
    future_days=60,
    transactions_per_hour=50,
    output_dir=Path("output/multi-label-compliance"),
    seed=42
)

# Specify exact dates
stats = generate_dataset(
    start_date="2025-11-01",
    end_date="2026-01-14",
    transactions_per_hour=50,
    output_dir=Path("output/multi-label-compliance"),
    seed=42
)

print(f"Generated {stats['total_transactions']:,} transactions")
for label, rate in stats['label_rate'].items():
    print(f"  {label}: {rate:.2%}")
```

## Dataset Structure

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | timestamp (UTC) | Transaction timestamp |
| `transaction_id` | string (UUID) | Deterministic unique transaction identifier |
| `account_id` | string | Account identifier (format: `acct_XXXXXX`) |
| `customer_segment` | string | `retail`, `corporate`, `private_banking`, `wealth_management` |
| `channel` | string | `wire`, `ach`, `swift`, `internal`, `cash_deposit` |
| `sender_country` | string | ISO-2 sender country code |
| `receiver_country` | string | ISO-2 receiver country code |
| `transaction_amount` | float64 | Transaction value in USD |
| `account_age_months` | int64 | Age of the account in months |
| `transaction_frequency_7d` | int64 | Number of transactions in the prior 7 days |
| `ground_truth_labels` | list\<string\> | Analyst-confirmed alert labels (zero or more) |
| `predicted_labels` | list\<string\> | Model-predicted labels at 0.5 threshold (zero or more) |
| `pred_prob_AML` | float64 | Model confidence score for AML (0–1) |
| `pred_prob_STRUCTURING` | float64 | Model confidence score for STRUCTURING (0–1) |
| `pred_prob_SANCTIONS` | float64 | Model confidence score for SANCTIONS (0–1) |
| `pred_prob_PEP` | float64 | Model confidence score for PEP (0–1) |
| `pred_prob_HIGH_RISK_COUNTRY` | float64 | Model confidence score for HIGH_RISK_COUNTRY (0–1) |
| `pred_prob_UNUSUAL_PATTERN` | float64 | Model confidence score for UNUSUAL_PATTERN (0–1) |

## Output Format

The dataset is saved as **date-partitioned Parquet files**:

```
output/
└── multi-label-compliance/
    ├── 2025-11-22/
    │   └── data-2025-11-22.parquet
    ├── 2025-11-23/
    │   └── data-2025-11-23.parquet
    └── ...
```

### Reading the Dataset

```python
import pandas as pd
import pyarrow.parquet as pq

# Read entire dataset
df = pd.read_parquet("output/multi-label-compliance")

# Read a single date partition
df = pd.read_parquet("output/multi-label-compliance/2025-11-22")

# Read with PyArrow
table = pq.read_table("output/multi-label-compliance")
```

## Dataset Characteristics

- **Transaction volume**: 50 transactions/hour (1,200/day)
- **Time span**: Configurable (default: ±90 days from today, 181 days total)
- **Customer base**: 500 accounts with stable segment/age/frequency properties
- **Label prevalence** (approximate):
  - `AML`: ~4%
  - `STRUCTURING`: ~4%
  - `SANCTIONS`: ~2%
  - `PEP`: ~3%
  - `HIGH_RISK_COUNTRY`: ~19%
  - `UNUSUAL_PATTERN`: ~4%
- **Multi-label**: ~15% of transactions have 2 or more simultaneous alerts
- **Country risk tiers**:
  - Low risk: AU, CA, CH, DE, FR, GB, JP, NL, SG, US
  - Medium risk: AE, BR, CN, MX, PK, TH, TR, UA
  - High risk: BY, IR, KP, MM, NG, RU, SY, VE

## Metrics Supported

See [`metrics.md`](metrics.md) for the full list. This dataset supports all multi-label classification metrics:

| Metric | Description |
|--------|-------------|
| Jaccard Similarity Score | Set similarity (IoU) between predicted and ground truth alert sets; rewards partial correctness |
| Exact Match Ratio | Proportion of inferences where predicted labels exactly match ground truth |
| Multi-Label Precision, Recall, and F1 per Label | Per-alert-type precision, recall, and F1 tracked over time |
| Multi-Label Confusion Matrix per Class | TP, FP, FN per alert label for identifying detection gaps |
| Multi-Label Classification Count by Class Label | Alert frequency per type over time; detects volume drift |
| Label Coverage Ratio | Proportion of transactions flagged per alert type |
| Label Density | Average number of alerts predicted per transaction (normalized 0–1) |
| Multi-Label Prediction Volume per Inference | Average alert count per transaction; detects alert inflation or suppression |
| Average Confidence Score per Label | Mean model probability per alert type; identifies uncertain or overconfident labels |
| Label Co-occurrence Matrix | How often alert pairs appear together (e.g. SANCTIONS + AML) |

## Reference Dataset

The generator also creates a **reference dataset** (`multi-label-compliance-reference`):
- Covers the first 14 days of the main date range
- Same statistical properties as the main dataset
- Used as a baseline for drift detection and model monitoring
