import uuid
import hashlib
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


# ---------------------------------------------------------------------------
# Class vocabulary — mutually exclusive spending categories
# ---------------------------------------------------------------------------
CATEGORIES = [
    'groceries',
    'dining',
    'travel',
    'entertainment',
    'utilities',
    'healthcare',
    'shopping',
    'automotive',
]

# Population-level base rate for each category
CATEGORY_PRIORS = np.array([0.20, 0.15, 0.08, 0.10, 0.10, 0.08, 0.18, 0.11])
assert abs(CATEGORY_PRIORS.sum() - 1.0) < 1e-9

# ---------------------------------------------------------------------------
# Feature distributions per category
# ---------------------------------------------------------------------------

# Transaction amount: log-normal (mean_ln, sigma_ln) → median = exp(mean_ln)
AMOUNT_LOG_PARAMS = {
    'groceries':     (3.8, 0.6),   # median ~$45
    'dining':        (3.2, 0.7),   # median ~$25
    'travel':        (5.5, 1.2),   # median ~$245
    'entertainment': (3.5, 0.8),   # median ~$33
    'utilities':     (4.5, 0.5),   # median ~$90
    'healthcare':    (4.2, 0.9),   # median ~$67
    'shopping':      (4.0, 0.9),   # median ~$55
    'automotive':    (4.3, 0.8),   # median ~$74
}

# Channel: [in_store, online, mobile, contactless]
CHANNELS = ['in_store', 'online', 'mobile', 'contactless']
CHANNEL_PROBS = {
    'groceries':     [0.55, 0.15, 0.10, 0.20],
    'dining':        [0.65, 0.20, 0.10, 0.05],
    'travel':        [0.25, 0.55, 0.15, 0.05],
    'entertainment': [0.35, 0.40, 0.20, 0.05],
    'utilities':     [0.05, 0.70, 0.25, 0.00],
    'healthcare':    [0.65, 0.25, 0.10, 0.00],
    'shopping':      [0.30, 0.50, 0.15, 0.05],
    'automotive':    [0.80, 0.08, 0.05, 0.07],
}

# Peak hours (when the category is most likely to occur)
PEAK_HOURS = {
    'groceries':     list(range(9, 20)),
    'dining':        list(range(11, 14)) + list(range(18, 22)),
    'travel':        list(range(6, 22)),
    'entertainment': list(range(14, 23)),
    'utilities':     list(range(8, 18)),
    'healthcare':    list(range(8, 17)),
    'shopping':      list(range(10, 21)),
    'automotive':    list(range(7, 20)),
}

# Weekend boost — categories more likely on Sat/Sun (day_of_week 5 or 6)
WEEKEND_MULTIPLIER = {
    'groceries':     1.2,
    'dining':        1.5,
    'travel':        1.4,
    'entertainment': 1.6,
    'utilities':     0.8,
    'healthcare':    0.5,
    'shopping':      1.4,
    'automotive':    1.1,
}

# Coarse merchant type label per category (adds a categorical feature)
MERCHANT_TYPES = {
    'groceries':     ['supermarket', 'convenience_store', 'wholesale_club', 'specialty_food'],
    'dining':        ['restaurant', 'fast_food', 'cafe', 'food_delivery', 'bar'],
    'travel':        ['airline', 'hotel', 'car_rental', 'rideshare', 'vacation_rental'],
    'entertainment': ['cinema', 'streaming', 'gaming', 'event_venue', 'amusement'],
    'utilities':     ['electric', 'gas', 'water', 'internet', 'mobile_carrier'],
    'healthcare':    ['pharmacy', 'clinic', 'hospital', 'dental', 'vision'],
    'shopping':      ['department_store', 'online_retailer', 'electronics', 'clothing', 'home_goods'],
    'automotive':    ['gas_station', 'parking', 'auto_repair', 'car_wash', 'dealership'],
}

CUSTOMER_SEGMENTS = ['retail', 'premium', 'small_business']

# ---------------------------------------------------------------------------
# Model accuracy — realistic per-category accuracy and confusion targets
# ---------------------------------------------------------------------------

# How often the model predicts the correct category for each class
CATEGORY_ACCURACY = {
    'groceries':     0.82,  # sometimes confused with shopping
    'dining':        0.78,  # confused with entertainment
    'travel':        0.88,  # distinctive amounts and channels
    'entertainment': 0.74,  # confused with dining / shopping
    'utilities':     0.90,  # very distinctive (online, fixed amounts)
    'healthcare':    0.76,  # confused with utilities / shopping
    'shopping':      0.75,  # confused with groceries / entertainment
    'automotive':    0.85,  # gas stations are quite distinctive
}
# Overall expected accuracy ≈ sum(accuracy * prior) ≈ 0.80

# When the model is wrong, these are the most probable misclassifications
# Probabilities within each dict must sum to 1.0
CONFUSION_TARGETS = {
    'groceries':     {'shopping': 0.50, 'dining': 0.30, 'automotive': 0.20},
    'dining':        {'entertainment': 0.45, 'groceries': 0.30, 'shopping': 0.25},
    'travel':        {'entertainment': 0.40, 'shopping': 0.35, 'automotive': 0.25},
    'entertainment': {'dining': 0.45, 'shopping': 0.30, 'travel': 0.25},
    'utilities':     {'healthcare': 0.40, 'shopping': 0.35, 'automotive': 0.25},
    'healthcare':    {'utilities': 0.45, 'shopping': 0.30, 'groceries': 0.25},
    'shopping':      {'groceries': 0.45, 'entertainment': 0.30, 'automotive': 0.25},
    'automotive':    {'shopping': 0.40, 'groceries': 0.35, 'utilities': 0.25},
}

# ---------------------------------------------------------------------------
# Parquet schema
# ---------------------------------------------------------------------------
_PARQUET_SCHEMA = pa.schema([
    pa.field('timestamp',              pa.timestamp('ns', tz='UTC')),
    pa.field('transaction_id',         pa.string()),
    pa.field('account_id',             pa.string()),
    pa.field('customer_segment',       pa.string()),
    pa.field('channel',                pa.string()),
    pa.field('merchant_type',          pa.string()),
    pa.field('transaction_amount',     pa.float64()),
    pa.field('hour_of_day',            pa.int64()),
    pa.field('day_of_week',            pa.int64()),
    pa.field('ground_truth_category',  pa.string()),
    pa.field('predicted_category',     pa.string()),
    pa.field('prediction_confidence',  pa.float64()),
    pa.field('pred_prob_groceries',    pa.float64()),
    pa.field('pred_prob_dining',       pa.float64()),
    pa.field('pred_prob_travel',       pa.float64()),
    pa.field('pred_prob_entertainment',pa.float64()),
    pa.field('pred_prob_utilities',    pa.float64()),
    pa.field('pred_prob_healthcare',   pa.float64()),
    pa.field('pred_prob_shopping',     pa.float64()),
    pa.field('pred_prob_automotive',   pa.float64()),
])


def _write_parquet(rows_by_date, output_dir, stats):
    output_path = Path(output_dir)
    for date_str in sorted(rows_by_date):
        rows = rows_by_date[date_str]
        partition_dir = output_path / date_str
        partition_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(rows)
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert('UTC')

        table = pa.Table.from_pandas(df, schema=_PARQUET_SCHEMA, preserve_index=False)
        pq.write_table(table, partition_dir / f'data-{date_str}.parquet')
        stats['files_created'] += 1


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------
def generate_dataset(
    start_date=None,
    end_date=None,
    past_days=90,
    future_days=90,
    transactions_per_hour=60,
    output_dir=None,
    seed=42,
):
    """
    Generate a synthetic financial transaction category classification dataset.

    Each transaction belongs to exactly one spending category (mutually exclusive),
    making this a standard multi-class classification problem.

    Categories (8 classes)
    ----------------------
    groceries      Supermarkets, food stores, wholesale clubs
    dining         Restaurants, cafes, fast food, food delivery
    travel         Airlines, hotels, car rentals, rideshare
    entertainment  Cinemas, streaming, gaming, event venues
    utilities      Electric, gas, water, internet, mobile
    healthcare     Pharmacies, clinics, hospitals, dental
    shopping       Department stores, online retail, electronics
    automotive     Gas stations, parking, auto repair

    Output columns
    --------------
    timestamp               UTC timestamp of the transaction
    transaction_id          Deterministic UUID (stable across re-runs with same seed)
    account_id              Account identifier (sampled from a fixed customer base)
    customer_segment        retail | premium | small_business
    channel                 in_store | online | mobile | contactless
    merchant_type           Granular merchant type within the category
    transaction_amount      Transaction value in USD
    hour_of_day             Hour of the transaction (0–23)
    day_of_week             Day of week (0=Monday … 6=Sunday)
    ground_truth_category   True spending category (one of 8 classes)
    predicted_category      Model's top-1 prediction (argmax of softmax)
    prediction_confidence   Model's confidence in its prediction (max softmax prob)
    pred_prob_<category>    Softmax probability for each class (8 columns, sum ≈ 1.0)

    Output format
    -------------
    Date-partitioned Parquet: <output_dir>/YYYY-MM-DD/data-YYYY-MM-DD.parquet

    Args:
        start_date:            Start date (YYYY-MM-DD). Derived from past_days if None.
        end_date:              End date inclusive (YYYY-MM-DD). Derived from future_days if None.
        past_days:             Days before today to start generating data (default: 90).
        future_days:           Days after today to generate data (default: 90).
        transactions_per_hour: Transactions generated per hour slot (default: 60).
        output_dir:            Directory to write Parquet files. If None, no files are written.
        seed:                  Random seed for reproducibility.

    Returns:
        dict: Statistics — total_transactions, category_counts, category_rate,
              accuracy, files_created, date_range.
    """
    np.random.seed(seed)
    random.seed(seed)

    if start_date is None or end_date is None:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date is None:
            start_date = (today - timedelta(days=past_days)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = (today + timedelta(days=future_days)).strftime('%Y-%m-%d')

    start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    end_dt   = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)

    # Stable customer base
    n_accounts = 800
    account_ids = [f'acct_{i:06d}' for i in random.sample(range(100_000, 999_999), n_accounts)]
    account_segment = {
        a: np.random.choice(CUSTOMER_SEGMENTS, p=[0.70, 0.20, 0.10])
        for a in account_ids
    }

    stats = {
        'total_transactions': 0,
        'correct_predictions': 0,
        'category_counts': {cat: 0 for cat in CATEGORIES},
        'files_created': 0,
        'date_range': f'{start_date} to {end_date}',
    }

    rows_by_date = {}
    current_dt = start_dt

    while current_dt <= end_dt:
        date_str    = current_dt.strftime('%Y-%m-%d')
        day_of_week = current_dt.weekday()   # 0=Monday … 6=Sunday
        is_weekend  = day_of_week >= 5

        if date_str not in rows_by_date:
            rows_by_date[date_str] = []

        # Adjust category priors for time-of-day and weekend effects
        hour = current_dt.hour
        adjusted_priors = CATEGORY_PRIORS.copy()
        for idx, cat in enumerate(CATEGORIES):
            if hour in PEAK_HOURS[cat]:
                adjusted_priors[idx] *= 1.3
            if is_weekend:
                adjusted_priors[idx] *= WEEKEND_MULTIPLIER[cat]
        adjusted_priors /= adjusted_priors.sum()

        for i in range(transactions_per_hour):
            # --- Ground truth category ---
            gt_idx      = np.random.choice(len(CATEGORIES), p=adjusted_priors)
            gt_category = CATEGORIES[gt_idx]

            # --- Features (generated conditional on ground truth) ---
            log_mean, log_sigma = AMOUNT_LOG_PARAMS[gt_category]
            amount       = round(min(np.random.lognormal(log_mean, log_sigma), 50_000.0), 2)
            channel      = np.random.choice(CHANNELS, p=CHANNEL_PROBS[gt_category])
            merchant_type = random.choice(MERCHANT_TYPES[gt_category])

            account_id = random.choice(account_ids)
            segment    = account_segment[account_id]

            # --- Model prediction ---
            # Step 1: decide whether the model is correct or confused.
            cat_accuracy = CATEGORY_ACCURACY[gt_category]
            if np.random.random() < cat_accuracy:
                pred_category = gt_category
            else:
                confusion = CONFUSION_TARGETS[gt_category]
                pred_category = np.random.choice(
                    list(confusion.keys()), p=list(confusion.values())
                )
            pred_idx = CATEGORIES.index(pred_category)

            # Step 2: build a Dirichlet-based softmax probability vector.
            # Concentrate mass on the predicted class; give moderate leakage to
            # the true class (if different) so the runner-up looks realistic.
            alpha = np.ones(len(CATEGORIES)) * 0.4   # low background for all classes
            alpha[pred_idx] = 8.0                     # strong peak on predicted class
            if pred_category != gt_category:
                alpha[gt_idx] = 2.5                   # visible runner-up on the true class
            raw_probs = np.random.dirichlet(alpha)

            pred_probs    = {cat: round(float(p), 6) for cat, p in zip(CATEGORIES, raw_probs)}
            confidence    = round(float(raw_probs[pred_idx]), 6)

            # Deterministic transaction ID
            txn_hash = hashlib.md5(f'{current_dt.isoformat()}_{i}'.encode()).hexdigest()
            txn_id   = str(uuid.UUID(txn_hash))

            rows_by_date[date_str].append({
                'timestamp':               current_dt,
                'transaction_id':          txn_id,
                'account_id':              account_id,
                'customer_segment':        segment,
                'channel':                 channel,
                'merchant_type':           merchant_type,
                'transaction_amount':      amount,
                'hour_of_day':             hour,
                'day_of_week':             day_of_week,
                'ground_truth_category':   gt_category,
                'predicted_category':      pred_category,
                'prediction_confidence':   confidence,
                'pred_prob_groceries':     pred_probs['groceries'],
                'pred_prob_dining':        pred_probs['dining'],
                'pred_prob_travel':        pred_probs['travel'],
                'pred_prob_entertainment': pred_probs['entertainment'],
                'pred_prob_utilities':     pred_probs['utilities'],
                'pred_prob_healthcare':    pred_probs['healthcare'],
                'pred_prob_shopping':      pred_probs['shopping'],
                'pred_prob_automotive':    pred_probs['automotive'],
            })

            stats['total_transactions'] += 1
            stats['category_counts'][gt_category] += 1
            if pred_category == gt_category:
                stats['correct_predictions'] += 1

        current_dt += timedelta(hours=1)

    if output_dir is not None:
        _write_parquet(rows_by_date, output_dir, stats)

    stats['category_rate'] = {
        cat: stats['category_counts'][cat] / stats['total_transactions']
        for cat in CATEGORIES
    }
    stats['accuracy'] = stats['correct_predictions'] / stats['total_transactions']

    return stats


# ---------------------------------------------------------------------------
# Reference dataset helper
# ---------------------------------------------------------------------------
def generate_reference_dataset(
    start_date=None,
    end_date=None,
    past_days=90,
    future_days=90,
    reference_days=14,
    transactions_per_hour=60,
    output_dir=None,
    seed=42,
):
    """
    Generate a reference / baseline transaction category dataset for comparison.

    Writes to <output_dir>/multi-class-txn-category-reference/.

    Args:
        start_date:            Start date (YYYY-MM-DD). Derived from past_days if None.
        end_date:              End date (YYYY-MM-DD). Derived from start_date + reference_days if None.
        past_days:             Days before today to start the reference window (default: 90).
        future_days:           Unused; kept for API consistency.
        reference_days:        Length of the reference window in days (default: 14).
        transactions_per_hour: Transactions per hour.
        output_dir:            Base output directory.
        seed:                  Random seed.

    Returns:
        dict: Statistics about the generated reference dataset.
    """
    if start_date is None or end_date is None:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date is None:
            start_date = (today - timedelta(days=past_days)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = (
                datetime.fromisoformat(start_date) + timedelta(days=reference_days - 1)
            ).strftime('%Y-%m-%d')

    ref_output = Path(output_dir) / 'multi-class-txn-category-reference' if output_dir else None

    return generate_dataset(
        start_date=start_date,
        end_date=end_date,
        transactions_per_hour=transactions_per_hour,
        output_dir=ref_output,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    base_output_dir = Path(__file__).parent / '../output'

    # Main dataset: ±90 days from today
    print('Generating transaction category multi-class dataset...')
    main_output = base_output_dir / 'multi-class-txn-category'
    stats = generate_dataset(
        past_days=90,
        future_days=90,
        transactions_per_hour=60,
        output_dir=main_output,
        seed=42,
    )

    print(f'\nMain Dataset Statistics:')
    print(f'  Date range:         {stats["date_range"]}')
    print(f'  Total transactions: {stats["total_transactions"]:,}')
    print(f'  Overall accuracy:   {stats["accuracy"]:.2%}')
    print(f'  Files created:      {stats["files_created"]:,}')
    print(f'  Output directory:   {main_output}')
    print(f'\n  Category distribution:')
    for cat in CATEGORIES:
        count = stats['category_counts'][cat]
        rate  = stats['category_rate'][cat]
        print(f'    {cat:<16s}: {count:>8,}  ({rate:.2%})')

    # Reference dataset: first 14 days of the main range
    print('\nGenerating reference dataset...')
    ref_stats = generate_reference_dataset(
        past_days=90,
        reference_days=14,
        transactions_per_hour=60,
        output_dir=base_output_dir,
        seed=42,
    )

    print(f'\nReference Dataset Statistics:')
    print(f'  Date range:         {ref_stats["date_range"]}')
    print(f'  Total transactions: {ref_stats["total_transactions"]:,}')
    print(f'  Overall accuracy:   {ref_stats["accuracy"]:.2%}')
    print(f'  Files created:      {ref_stats["files_created"]:,}')
    print(f'  Output directory:   {base_output_dir / "multi-class-txn-category-reference"}')

    print('\n✅ Dataset generation complete!')
