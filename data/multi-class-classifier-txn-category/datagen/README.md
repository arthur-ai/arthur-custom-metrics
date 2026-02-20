# Transaction Category Multi-Class Dataset Generator

This directory contains a dataset generator for creating synthetic bank transaction categorization data. The dataset simulates a personal finance management (PFM) model that classifies each transaction into exactly one spending category, making it a **multi-class classification** problem.

## Overview

The dataset generator creates date-partitioned Parquet files with:
- **60 transactions per hour** across a configurable date range (default: ±90 days from today)
- **Ground truth spending category** (one of 8 mutually exclusive classes)
- **Model-predicted category** and **softmax probability scores** across all classes
- **Transaction features** including amount, channel, merchant type, and time-of-day

## Use Case

This dataset simulates a **bank transaction categorization system** where:
- **Ground Truth**: `ground_truth_category` — the true spending category of the transaction
- **Model Prediction**: `predicted_category` — the model's top-1 predicted category (argmax of softmax)
- **Confidence**: `prediction_confidence` — the model's probability for its top prediction
- **Softmax Scores**: `pred_prob_<category>` — probability for each class (8 columns, sum = 1.0)
- **Features**: Transaction amount, channel, merchant type, hour of day, day of week, customer segment

### Categories (8 mutually exclusive classes)

| Category | Base Rate | Model Accuracy | Common Confusions |
|----------|-----------|----------------|-------------------|
| `groceries` | 20% | 82% | shopping, dining |
| `shopping` | 19% | 75% | groceries, entertainment |
| `dining` | 15% | 78% | entertainment, groceries |
| `automotive` | 11% | 85% | shopping, groceries |
| `entertainment` | 11% | 74% | dining, shopping |
| `utilities` | 9% | 90% | healthcare, shopping |
| `travel` | 9% | 88% | entertainment, shopping |
| `healthcare` | 7% | 76% | utilities, shopping |

**Overall model accuracy: ~80%**

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
- **Main dataset**: `output/multi-class-txn-category/` (±90 days from today, ~259k transactions)
- **Reference dataset**: `output/multi-class-txn-category-reference/` (first 14 days)

### Customize Generation

```python
from generate_dataset import generate_dataset, generate_reference_dataset
from pathlib import Path

# Generate with default ±90 days from today
stats = generate_dataset(
    transactions_per_hour=60,
    output_dir=Path("output/multi-class-txn-category"),
    seed=42
)

# Specify custom date range
stats = generate_dataset(
    past_days=30,
    future_days=60,
    transactions_per_hour=60,
    output_dir=Path("output/multi-class-txn-category"),
    seed=42
)

# Specify exact dates
stats = generate_dataset(
    start_date="2025-11-01",
    end_date="2026-01-14",
    transactions_per_hour=60,
    output_dir=Path("output/multi-class-txn-category"),
    seed=42
)

print(f"Generated {stats['total_transactions']:,} transactions")
print(f"Overall accuracy: {stats['accuracy']:.2%}")
for cat, rate in stats['category_rate'].items():
    print(f"  {cat}: {rate:.2%}")
```

## Dataset Structure

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | timestamp (UTC) | Transaction timestamp |
| `transaction_id` | string (UUID) | Deterministic unique transaction identifier |
| `account_id` | string | Account identifier (format: `acct_XXXXXX`) |
| `customer_segment` | string | `retail`, `premium`, `small_business` |
| `channel` | string | `in_store`, `online`, `mobile`, `contactless` |
| `merchant_type` | string | Granular merchant type within the category (e.g., `supermarket`, `restaurant`) |
| `transaction_amount` | float64 | Transaction value in USD |
| `hour_of_day` | int64 | Hour of the transaction (0–23) |
| `day_of_week` | int64 | Day of week (0=Monday … 6=Sunday) |
| `ground_truth_category` | string | True spending category (one of 8 classes) |
| `predicted_category` | string | Model's top-1 predicted category |
| `prediction_confidence` | float64 | Model's confidence in its prediction (max softmax prob) |
| `pred_prob_groceries` | float64 | Softmax probability for `groceries` |
| `pred_prob_dining` | float64 | Softmax probability for `dining` |
| `pred_prob_travel` | float64 | Softmax probability for `travel` |
| `pred_prob_entertainment` | float64 | Softmax probability for `entertainment` |
| `pred_prob_utilities` | float64 | Softmax probability for `utilities` |
| `pred_prob_healthcare` | float64 | Softmax probability for `healthcare` |
| `pred_prob_shopping` | float64 | Softmax probability for `shopping` |
| `pred_prob_automotive` | float64 | Softmax probability for `automotive` |

> The 8 `pred_prob_*` columns always sum to 1.0 (softmax-normalized).

## Output Format

The dataset is saved as **date-partitioned Parquet files**:

```
output/
└── multi-class-txn-category/
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
df = pd.read_parquet("output/multi-class-txn-category")

# Read a single date partition
df = pd.read_parquet("output/multi-class-txn-category/2025-11-22")

# Compute per-category accuracy
accuracy_by_cat = df.groupby("ground_truth_category").apply(
    lambda g: (g["predicted_category"] == g["ground_truth_category"]).mean()
)
print(accuracy_by_cat)
```

## Dataset Characteristics

- **Transaction volume**: 60 transactions/hour (1,440/day)
- **Time span**: Configurable (default: ±90 days from today, 181 days total)
- **Customer base**: 800 accounts across 3 segments (retail 70%, premium 20%, small_business 10%)
- **Model accuracy**: ~80% overall; varies by category (utilities easiest at 90%, entertainment hardest at 74%)
- **Confusion patterns**: Errors are semantically realistic (shopping ↔ groceries, dining ↔ entertainment)
- **Temporal patterns**: Category priors shift by time-of-day and weekend/weekday
  - Dining peaks at lunch (11–14) and dinner (18–22)
  - Entertainment peaks on weekends (+60% multiplier)
  - Utilities/Healthcare suppressed on weekends

## Metrics Supported

See [`metrics.md`](metrics.md) for the full list. Note that array-based multi-label metrics (Jaccard, exact match, label density, co-occurrence, prediction volume) do not apply to single-label classification and are excluded.

| Metric | Description |
|--------|-------------|
| Multi-Label Precision, Recall, and F1 per Label | Per-category precision, recall, and F1 tracked over time |
| Multi-Label Confusion Matrix per Class | TP, FP, FN per spending category; reveals which categories are confused with each other |
| Multi-Label Classification Count by Class Label | Predicted category frequency over time; detects drift in category distribution |
| Label Coverage Ratio | Proportion of transactions predicted as each category |
| Average Confidence Score per Label | Mean softmax probability per category; identifies where the model is uncertain |

## Reference Dataset

The generator also creates a **reference dataset** (`multi-class-txn-category-reference`):
- Covers the first 14 days of the main date range
- Same statistical properties and category distributions as the main dataset
- Used as a baseline for drift detection and model monitoring
