# Recommendation / Ads Ranking Dataset Generator

This directory contains a dataset generator for a synthetic **recommendation and ad-ranking engine**. Each request (a home-feed view, a search, a product page, or an email send) produces a ranked slate of 10 items, and the generator logs **one row per (request, position)**: the item served, the ranker's predicted click probability, and what the user did with it.

This impression-level layout is the natural logging format for recommender systems and ads engines, and it is what the ranking, calibration, coverage and diversity metrics in [`/examples/metrics/ranking/`](../../../examples/metrics/ranking/) expect.

## Overview

The generator creates date-partitioned Parquet files with:
- **20 requests per hour**, 10 impressions per request (configurable), across ±90 days from today
- A **2,000-item catalog** with Zipf-like popularity and 12 product categories
- A **ranker score** (`predicted_score`) that is a calibrated-but-noisy estimate of click probability
- **Clicks and conversions** generated from an examination model (true item appeal x position bias x placement x user segment)
- A **graded relevance label** (`relevance_grade`: 0 none, 1 click, 2 conversion) for NDCG
- **Built-in drift** halfway through the range so monitoring metrics have something to detect

## Use Case

This dataset simulates a **ranked recommendation or ad placement system** where:
- **Model Prediction**: `predicted_score` — probability of click for this item at this position (pCTR)
- **Binary Ground Truth**: `clicked` — whether the impression was clicked
- **Graded Ground Truth**: `relevance_grade` — 0 / 1 / 2 for none / click / conversion
- **Ranking context**: `request_id` groups the slate, `position` is the 1-indexed rank
- **Catalog context**: `item_id`, `item_category`
- **Segmentation**: `placement`, `device`, `user_segment`, `model_version`

### Built-in drift

`drift_start_offset_days` (default 45) after the start date the serving stack switches from `ranker_v1` to `ranker_v2`:

| Change | Effect on metrics |
|--------|-------------------|
| Scores inflated by a logit shift | `calibration_ratio` rises from ~1.0 to ~1.4; `expected_calibration_error` rises |
| Retriever becomes more popularity-biased | `catalog_coverage` drops, `top_n_exposure_share` and `exposure_gini` rise, `effective_catalog_size` falls |
| Ranker noise increases | `ndcg_at_k`, `mrr_at_k` dip slightly |

The reference dataset never drifts, so it is a clean baseline.

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
- **Main dataset**: `output/ranking-recsys-ads/` (±90 days from today, ~870k impressions)
- **Reference dataset**: `output/ranking-recsys-ads-reference/` (first 14 days, no drift)

### Run Tests

```bash
python -m unittest test_dataset
```

### Customize Generation

```python
from generate_dataset import generate_dataset, generate_reference_dataset
from pathlib import Path

# Default ±90 days from today
stats = generate_dataset(
    requests_per_hour=20,
    output_dir=Path("output/ranking-recsys-ads"),
    seed=42,
)

# Exact dates, drift after 10 days
stats = generate_dataset(
    start_date="2026-01-01",
    end_date="2026-02-28",
    requests_per_hour=20,
    drift_start_offset_days=10,
    output_dir=Path("output/ranking-recsys-ads"),
    seed=42,
)

print(f"Requests: {stats['total_requests']:,}  Impressions: {stats['total_impressions']:,}")
print(f"CTR: {stats['click_rate']:.2%}  CVR: {stats['conversion_rate']:.2%}")
```

## Dataset Structure

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | timestamp (UTC) | Request timestamp (shared by every row of the slate) |
| `request_id` | string (UUID) | Deterministic request identifier; groups the slate |
| `impression_id` | string (UUID) | Deterministic unique row identifier |
| `user_id` | string | User identifier (`user_XXXXXX`) |
| `user_segment` | string | `new`, `casual`, `loyal` |
| `placement` | string | `home_feed`, `search`, `product_page`, `email` |
| `device` | string | `ios`, `android`, `web` |
| `model_version` | string | `ranker_v1` before the drift point, `ranker_v2` after |
| `slate_size` | int64 | Number of items in the request (10) |
| `position` | int64 | 1-indexed rank of the item within the slate |
| `item_id` | string | Catalog item identifier (`item_XXXXX`) |
| `item_category` | string | One of 12 product categories |
| `predicted_score` | float64 | Ranker's predicted click probability (0–1) |
| `clicked` | int64 | 1 if clicked, else 0 |
| `converted` | int64 | 1 if the click converted, else 0 |
| `relevance_grade` | int64 | 0 = none, 1 = click, 2 = conversion |
| `revenue` | float64 | Revenue attributed to the impression (0 without a conversion) |

## Output Format

```
output/
└── ranking-recsys-ads/
    ├── 2026-07-15/
    │   └── data-2026-07-15.parquet
    ├── 2026-07-16/
    │   └── data-2026-07-16.parquet
    └── ...
```

### Reading the Dataset

```python
import pandas as pd

df = pd.read_parquet("output/ranking-recsys-ads")

# Rebuild a slate-level (array) view if your metrics expect one row per request
slates = (
    df.sort_values(["request_id", "position"])
      .groupby("request_id")
      .agg(timestamp=("timestamp", "min"),
           recommended_items=("item_id", list),
           engaged_items=("item_id", lambda s: list(s[df.loc[s.index, "clicked"] == 1])))
      .reset_index()
)
```

## Dataset Characteristics

- **Volume**: 20 requests/hour, 200 impressions/hour, 4,800 impressions/day
- **Time span**: configurable (default ±90 days from today)
- **Catalog**: 2,000 items, 12 categories, Zipf-like popularity (exponent 0.9)
- **Click rate**: ~9% of impressions overall; ~19% at position 1 falling to ~3% at position 10
- **Conversion rate**: ~12% of clicks (~1% of impressions)
- **Requests with at least one click**: ~60%
- **Calibration**: `ranker_v1` calibration ratio ~1.0; `ranker_v2` ~1.4

## Metrics Supported

See [`metrics.md`](metrics.md) for the full list. This dataset supports every metric in `/examples/metrics/ranking/`:

| Metric | Columns used |
|--------|--------------|
| Top-K Ranking Quality (NDCG, MAP, MRR, Precision, Recall, Hit Rate @K) | `request_id`, `position`, `relevance_grade` or `clicked` |
| Top-K Ranking Quality — Slate Arrays | derived `recommended_items`, `engaged_items` arrays |
| Calibration Profile | `predicted_score`, `clicked` |
| Reliability Diagram Bins | `predicted_score`, `clicked` |
| Catalog Coverage and Exposure | `item_id` |
| Slate Diversity | `request_id`, `item_category` |

It also works with the generic binary-classification metrics (AUC/Gini, AUPRC, Log Loss, PSI) using `predicted_score` and `clicked`, and with Subgroup Rate Comparison using `placement`, `device` or `user_segment`.

## Reference Dataset

The generator also creates a **reference dataset** (`ranking-recsys-ads-reference`):
- Covers the first 14 days of the main date range
- Always served by `ranker_v1` (no drift)
- Use it as the baseline for PSI, drift and calibration comparisons
