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
# Country risk tiers — sorted for deterministic list ordering
# ---------------------------------------------------------------------------
LOW_RISK_COUNTRIES = sorted(['AU', 'CA', 'CH', 'DE', 'FR', 'GB', 'JP', 'NL', 'SG', 'US'])
MEDIUM_RISK_COUNTRIES = sorted(['AE', 'BR', 'CN', 'MX', 'PK', 'TH', 'TR', 'UA'])
HIGH_RISK_COUNTRIES = sorted(['BY', 'IR', 'KP', 'MM', 'NG', 'RU', 'SY', 'VE'])

LOW_RISK_SET = set(LOW_RISK_COUNTRIES)
MEDIUM_RISK_SET = set(MEDIUM_RISK_COUNTRIES)
HIGH_RISK_SET = set(HIGH_RISK_COUNTRIES)
SANCTIONS_SET = {'IR', 'KP', 'SY', 'BY'}  # Strictest sanctions targets

ALL_COUNTRIES = LOW_RISK_COUNTRIES + MEDIUM_RISK_COUNTRIES + HIGH_RISK_COUNTRIES

# ---------------------------------------------------------------------------
# Model label vocabulary
# ---------------------------------------------------------------------------
LABELS = ['AML', 'STRUCTURING', 'SANCTIONS', 'PEP', 'HIGH_RISK_COUNTRY', 'UNUSUAL_PATTERN']

# ---------------------------------------------------------------------------
# Customer segments and transaction channels
# ---------------------------------------------------------------------------
CUSTOMER_SEGMENTS = ['retail', 'corporate', 'private_banking', 'wealth_management']
CHANNELS = ['wire', 'ach', 'swift', 'internal', 'cash_deposit']

# Channel selection probabilities per segment (must sum to 1.0)
CHANNEL_PROBS = {
    'retail':            [0.10, 0.50, 0.05, 0.25, 0.10],
    'corporate':         [0.35, 0.35, 0.20, 0.10, 0.00],
    'private_banking':   [0.45, 0.15, 0.35, 0.05, 0.00],
    'wealth_management': [0.40, 0.10, 0.45, 0.05, 0.00],
}

# Fraction of country selections going to each risk tier, per segment
COUNTRY_WEIGHTS = {
    'retail':            (0.85, 0.12, 0.03),
    'corporate':         (0.75, 0.18, 0.07),
    'private_banking':   (0.65, 0.22, 0.13),
    'wealth_management': (0.60, 0.25, 0.15),
}

# Log-normal mean for transaction amount by segment (ln dollars)
AMOUNT_LOG_MEAN = {
    'retail':            6.5,   # ~$665 median
    'corporate':         9.0,   # ~$8,100 median
    'private_banking':   10.5,  # ~$36,000 median
    'wealth_management': 11.0,  # ~$60,000 median
}


# ---------------------------------------------------------------------------
# Helper: country selection probabilities
# ---------------------------------------------------------------------------
def _country_probs(segment):
    """
    Return a probability vector over ALL_COUNTRIES for the given customer segment.
    Countries are ordered: LOW_RISK | MEDIUM_RISK | HIGH_RISK.
    """
    w_low, w_med, w_high = COUNTRY_WEIGHTS[segment]
    return (
        [w_low  / len(LOW_RISK_COUNTRIES)]  * len(LOW_RISK_COUNTRIES)
        + [w_med  / len(MEDIUM_RISK_COUNTRIES)] * len(MEDIUM_RISK_COUNTRIES)
        + [w_high / len(HIGH_RISK_COUNTRIES)]  * len(HIGH_RISK_COUNTRIES)
    )


# ---------------------------------------------------------------------------
# Helper: ground-truth label probabilities from transaction features
# ---------------------------------------------------------------------------
def _gt_probs(amount, sender_country, receiver_country, segment, channel,
              account_age, txn_freq_7d, base_freq):
    """
    Compute the probability that each compliance label applies to this transaction.
    Returns a dict {label: float}.
    """
    involves_high_risk = sender_country in HIGH_RISK_SET or receiver_country in HIGH_RISK_SET
    involves_medium_risk = sender_country in MEDIUM_RISK_SET or receiver_country in MEDIUM_RISK_SET
    involves_sanctions = sender_country in SANCTIONS_SET or receiver_country in SANCTIONS_SET

    # AML — large cross-border volumes, high-risk jurisdictions, high frequency
    aml = 0.03
    if amount > 50_000:
        aml *= 1.8
    if involves_high_risk:
        aml *= 2.5
    if txn_freq_7d > 10:
        aml *= 1.5
    if segment in ('private_banking', 'wealth_management'):
        aml *= 1.3

    # STRUCTURING — amounts just below the $10 k CTR reporting threshold
    structuring = 0.02
    if 8_000 <= amount <= 9_999:
        structuring *= 8.0
    if txn_freq_7d > 5:
        structuring *= 2.0
    if channel in ('cash_deposit', 'ach'):
        structuring *= 1.5

    # SANCTIONS — specific designated countries
    sanctions = 0.01
    if involves_sanctions:
        sanctions *= 20.0
    elif involves_high_risk:
        sanctions *= 3.0

    # PEP — segment-driven; amplified by very large amounts
    pep_base = {
        'retail': 0.01, 'corporate': 0.03,
        'private_banking': 0.08, 'wealth_management': 0.12,
    }
    pep = pep_base[segment]
    if amount > 100_000:
        pep *= 1.5

    # HIGH_RISK_COUNTRY — driven by country risk tier
    if involves_high_risk:
        hrisk = 0.80
    elif involves_medium_risk:
        hrisk = 0.30
    else:
        hrisk = 0.04

    # UNUSUAL_PATTERN — new account with high activity, or frequency spike
    unusual = 0.04
    if account_age < 3 and txn_freq_7d > 3:
        unusual *= 4.0
    elif txn_freq_7d > base_freq * 3 + 1:
        unusual *= 3.0
    if account_age < 12 and amount > 20_000:
        unusual *= 1.8

    return {
        'AML':               min(aml, 0.40),
        'STRUCTURING':       min(structuring, 0.35),
        'SANCTIONS':         min(sanctions, 0.55),
        'PEP':               min(pep, 0.30),
        'HIGH_RISK_COUNTRY': min(hrisk, 0.90),
        'UNUSUAL_PATTERN':   min(unusual, 0.50),
    }


# ---------------------------------------------------------------------------
# Parquet writer
# ---------------------------------------------------------------------------
_PARQUET_SCHEMA = pa.schema([
    pa.field('timestamp',                pa.timestamp('ns', tz='UTC')),
    pa.field('transaction_id',           pa.string()),
    pa.field('account_id',               pa.string()),
    pa.field('customer_segment',         pa.string()),
    pa.field('channel',                  pa.string()),
    pa.field('sender_country',           pa.string()),
    pa.field('receiver_country',         pa.string()),
    pa.field('transaction_amount',       pa.float64()),
    pa.field('account_age_months',       pa.int64()),
    pa.field('transaction_frequency_7d', pa.int64()),
    pa.field('ground_truth_labels',      pa.list_(pa.string())),
    pa.field('predicted_labels',         pa.list_(pa.string())),
    pa.field('pred_prob_AML',            pa.float64()),
    pa.field('pred_prob_STRUCTURING',    pa.float64()),
    pa.field('pred_prob_SANCTIONS',      pa.float64()),
    pa.field('pred_prob_PEP',            pa.float64()),
    pa.field('pred_prob_HIGH_RISK_COUNTRY', pa.float64()),
    pa.field('pred_prob_UNUSUAL_PATTERN',   pa.float64()),
])


def _write_parquet(rows_by_date, output_dir, stats):
    """Write date-partitioned Parquet files from the accumulated row dict."""
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
    transactions_per_hour=50,
    output_dir=None,
    seed=42,
):
    """
    Generate a synthetic financial transaction compliance multi-label dataset.

    Each transaction can trigger zero or more compliance alert labels simultaneously,
    making this a multi-label classification problem. The dataset is intended for
    evaluating models that predict which alert types apply to each transaction.

    Labels
    ------
    AML               Anti-money laundering alert (large cross-border flows)
    STRUCTURING       Amounts just below $10 k CTR reporting threshold
    SANCTIONS         Counterparty in a sanctions-designated jurisdiction
    PEP               Politically exposed person involvement
    HIGH_RISK_COUNTRY Transaction touches a high-risk jurisdiction
    UNUSUAL_PATTERN   Activity inconsistent with the account's history

    Output columns
    --------------
    timestamp                  UTC timestamp of the transaction
    transaction_id             Deterministic UUID (stable across re-runs with same seed)
    account_id                 Account identifier (sampled from a fixed customer base)
    customer_segment           retail | corporate | private_banking | wealth_management
    channel                    wire | ach | swift | internal | cash_deposit
    sender_country             ISO-2 sender country code
    receiver_country           ISO-2 receiver country code
    transaction_amount         Transaction value in USD
    account_age_months         Age of the account at transaction time
    transaction_frequency_7d   Number of transactions in the prior 7 days
    ground_truth_labels        Array of analyst-confirmed alert labels
    predicted_labels           Array of model-predicted labels (threshold = 0.5)
    pred_prob_<LABEL>          Model confidence score (0-1) for each label

    Output format
    -------------
    Date-partitioned Parquet files: <output_dir>/YYYY-MM-DD/data-YYYY-MM-DD.parquet

    Args:
        start_date: Start date (YYYY-MM-DD). Derived from past_days if None.
        end_date:   End date inclusive (YYYY-MM-DD). Derived from future_days if None.
        past_days:  Days before today to start generating data (default: 90).
        future_days: Days after today to generate data (default: 90).
        transactions_per_hour: Transactions generated per hour slot.
        output_dir: Directory to write Parquet files. If None, no files are written.
        seed:       Random seed for reproducibility.

    Returns:
        dict: Statistics — total_transactions, label_counts, label_rate,
              files_created, date_range.
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

    # Stable customer base — properties fixed for the entire dataset
    n_accounts = 500
    account_ids = [f'acct_{i:06d}' for i in random.sample(range(100_000, 999_999), n_accounts)]
    account_segment  = {a: np.random.choice(CUSTOMER_SEGMENTS, p=[0.60, 0.25, 0.10, 0.05])
                        for a in account_ids}
    account_age      = {a: int(np.random.randint(1, 241)) for a in account_ids}   # months
    account_base_freq = {a: int(np.random.poisson(5))     for a in account_ids}   # 7-day baseline

    stats = {
        'total_transactions': 0,
        'label_counts': {label: 0 for label in LABELS},
        'files_created': 0,
        'date_range': f'{start_date} to {end_date}',
    }

    rows_by_date = {}
    current_dt = start_dt

    while current_dt <= end_dt:
        date_str = current_dt.strftime('%Y-%m-%d')
        if date_str not in rows_by_date:
            rows_by_date[date_str] = []

        for i in range(transactions_per_hour):
            # --- Account & transaction properties ---
            account_id = random.choice(account_ids)
            segment    = account_segment[account_id]
            age        = account_age[account_id]
            base_freq  = account_base_freq[account_id]

            channel          = np.random.choice(CHANNELS, p=CHANNEL_PROBS[segment])
            sender_country   = np.random.choice(ALL_COUNTRIES, p=_country_probs(segment))
            receiver_country = np.random.choice(ALL_COUNTRIES, p=_country_probs(segment))
            amount           = round(
                min(np.random.lognormal(mean=AMOUNT_LOG_MEAN[segment], sigma=1.2), 10_000_000.0),
                2,
            )
            txn_freq_7d = max(0, int(np.random.normal(base_freq, 2)))

            # --- Ground truth ---
            gt_prob = _gt_probs(
                amount, sender_country, receiver_country,
                segment, channel, age, txn_freq_7d, base_freq,
            )
            ground_truth_labels = sorted([
                label for label, prob in gt_prob.items()
                if np.random.random() < prob
            ])

            # --- Model predictions ---
            # Confidence scores are correlated with ground truth but imperfect.
            # Positive labels get higher scores (Beta(5,3) ~ 0.63 mean);
            # negative labels get lower scores (Beta(2,8) ~ 0.20 mean).
            pred_scores = {}
            for label in LABELS:
                if label in ground_truth_labels:
                    score = gt_prob[label] * 0.4 + np.random.beta(5, 3) * 0.6
                else:
                    score = gt_prob[label] * 0.4 + np.random.beta(2, 8) * 0.6
                pred_scores[label] = round(float(np.clip(score, 0.0, 1.0)), 6)

            predicted_labels = sorted([lbl for lbl, s in pred_scores.items() if s >= 0.5])

            # Deterministic transaction ID based on timestamp + position
            txn_hash = hashlib.md5(f'{current_dt.isoformat()}_{i}'.encode()).hexdigest()
            txn_id   = str(uuid.UUID(txn_hash))

            rows_by_date[date_str].append({
                'timestamp':                current_dt,
                'transaction_id':           txn_id,
                'account_id':               account_id,
                'customer_segment':         segment,
                'channel':                  channel,
                'sender_country':           sender_country,
                'receiver_country':         receiver_country,
                'transaction_amount':       amount,
                'account_age_months':       age,
                'transaction_frequency_7d': txn_freq_7d,
                'ground_truth_labels':      ground_truth_labels,
                'predicted_labels':         predicted_labels,
                'pred_prob_AML':            pred_scores['AML'],
                'pred_prob_STRUCTURING':    pred_scores['STRUCTURING'],
                'pred_prob_SANCTIONS':      pred_scores['SANCTIONS'],
                'pred_prob_PEP':            pred_scores['PEP'],
                'pred_prob_HIGH_RISK_COUNTRY': pred_scores['HIGH_RISK_COUNTRY'],
                'pred_prob_UNUSUAL_PATTERN':   pred_scores['UNUSUAL_PATTERN'],
            })

            stats['total_transactions'] += 1
            for label in ground_truth_labels:
                stats['label_counts'][label] += 1

        current_dt += timedelta(hours=1)

    if output_dir is not None:
        _write_parquet(rows_by_date, output_dir, stats)

    stats['label_rate'] = {
        label: stats['label_counts'][label] / stats['total_transactions']
        for label in LABELS
    }

    return stats


# ---------------------------------------------------------------------------
# Reference dataset helper (mirrors card-fraud API)
# ---------------------------------------------------------------------------
def generate_reference_dataset(
    start_date=None,
    end_date=None,
    past_days=90,
    future_days=90,
    reference_days=14,
    transactions_per_hour=50,
    output_dir=None,
    seed=42,
):
    """
    Generate a reference / baseline compliance dataset for comparison.

    Writes to <output_dir>/multi-label-compliance-reference/.

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

    ref_output = Path(output_dir) / 'multi-label-compliance-reference' if output_dir else None

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
    print('Generating compliance alert multi-label dataset...')
    main_output = base_output_dir / 'multi-label-compliance'
    stats = generate_dataset(
        past_days=90,
        future_days=90,
        transactions_per_hour=50,
        output_dir=main_output,
        seed=42,
    )

    print(f'\nMain Dataset Statistics:')
    print(f'  Date range:         {stats["date_range"]}')
    print(f'  Total transactions: {stats["total_transactions"]:,}')
    print(f'  Files created:      {stats["files_created"]:,}')
    print(f'  Output directory:   {main_output}')
    print(f'\n  Label prevalence:')
    for label in LABELS:
        count = stats['label_counts'][label]
        rate  = stats['label_rate'][label]
        print(f'    {label:<22s}: {count:>7,}  ({rate:.2%})')

    # Reference dataset: first 14 days of the main range
    print('\nGenerating reference dataset...')
    ref_stats = generate_reference_dataset(
        past_days=90,
        reference_days=14,
        transactions_per_hour=50,
        output_dir=base_output_dir,
        seed=42,
    )

    print(f'\nReference Dataset Statistics:')
    print(f'  Date range:         {ref_stats["date_range"]}')
    print(f'  Total transactions: {ref_stats["total_transactions"]:,}')
    print(f'  Files created:      {ref_stats["files_created"]:,}')
    print(f'  Output directory:   {base_output_dir / "multi-label-compliance-reference"}')
    print(f'\n  Label prevalence:')
    for label in LABELS:
        count = ref_stats['label_counts'][label]
        rate  = ref_stats['label_rate'][label]
        print(f'    {label:<22s}: {count:>7,}  ({rate:.2%})')

    print('\n✅ Dataset generation complete!')
