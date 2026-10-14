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
# Catalog and context vocabularies
# ---------------------------------------------------------------------------
CATEGORIES = sorted([
    'electronics', 'apparel', 'home', 'beauty', 'sports', 'toys',
    'books', 'grocery', 'automotive', 'garden', 'pets', 'office',
])

PLACEMENTS = ['home_feed', 'search', 'product_page', 'email']
PLACEMENT_PROBS = [0.45, 0.30, 0.15, 0.10]

# Placement-level multiplier on click propensity (search intent is strongest)
PLACEMENT_CTR_MULT = {
    'home_feed': 1.00,
    'search': 1.60,
    'product_page': 1.20,
    'email': 0.70,
}

DEVICES = ['ios', 'android', 'web']
DEVICE_PROBS = [0.40, 0.35, 0.25]

USER_SEGMENTS = ['new', 'casual', 'loyal']
USER_SEGMENT_PROBS = [0.25, 0.50, 0.25]
USER_SEGMENT_CTR_MULT = {'new': 0.80, 'casual': 1.00, 'loyal': 1.35}

# Position bias: probability a user examines the item at each slot (1-indexed)
POSITION_BIAS = [1.00, 0.85, 0.72, 0.62, 0.54, 0.47, 0.41, 0.36, 0.32, 0.28]

CATALOG_SIZE = 2000
SLATE_SIZE = 10
CANDIDATE_POOL = 40
CONVERSION_RATE_GIVEN_CLICK = 0.12


# ---------------------------------------------------------------------------
# Catalog construction
# ---------------------------------------------------------------------------
def _build_catalog(rng):
    """
    Build a fixed item catalog with:
      * a category per item
      * a hidden true click propensity (Beta distributed, heavy tail)
      * a popularity weight (Zipf-like) that drives how often the retriever
        surfaces the item as a candidate
    """
    item_ids = [f'item_{i:05d}' for i in range(CATALOG_SIZE)]
    categories = rng.choice(CATEGORIES, size=CATALOG_SIZE)
    true_ctr = np.clip(rng.beta(1.5, 20.0, size=CATALOG_SIZE), 0.002, 0.60)
    ranks = np.arange(1, CATALOG_SIZE + 1)
    popularity = 1.0 / np.power(ranks, 0.9)
    rng.shuffle(popularity)
    popularity = popularity / popularity.sum()
    return {
        'item_ids': item_ids,
        'categories': categories,
        'true_ctr': true_ctr,
        'popularity': popularity,
    }


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


# ---------------------------------------------------------------------------
# Parquet writer
# ---------------------------------------------------------------------------
_PARQUET_SCHEMA = pa.schema([
    pa.field('timestamp',        pa.timestamp('ns', tz='UTC')),
    pa.field('request_id',       pa.string()),
    pa.field('impression_id',    pa.string()),
    pa.field('user_id',          pa.string()),
    pa.field('user_segment',     pa.string()),
    pa.field('placement',        pa.string()),
    pa.field('device',           pa.string()),
    pa.field('model_version',    pa.string()),
    pa.field('slate_size',       pa.int64()),
    pa.field('position',         pa.int64()),
    pa.field('item_id',          pa.string()),
    pa.field('item_category',    pa.string()),
    pa.field('predicted_score',  pa.float64()),
    pa.field('clicked',          pa.int64()),
    pa.field('converted',        pa.int64()),
    pa.field('relevance_grade',  pa.int64()),
    pa.field('revenue',          pa.float64()),
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
    requests_per_hour=20,
    output_dir=None,
    seed=42,
    drift_start_offset_days=45,
):
    """
    Generate a synthetic impression-level dataset for a recommendation /
    ad-ranking engine.

    Each request (a page view, search, or email send) produces a ranked slate
    of SLATE_SIZE items. One row is emitted per (request, position). This
    long layout is the natural logging format for recommender and ads systems
    and is what the ranking, calibration, coverage and diversity custom
    metrics in /examples/metrics/ranking/ expect.

    Mechanics
    ---------
    * A retriever samples CANDIDATE_POOL candidates from a 2,000-item catalog
      with Zipf-like popularity weights.
    * A ranker scores each candidate with a noisy estimate of the item's true
      click propensity and serves the top SLATE_SIZE by score.
    * Clicks follow an examination model: P(click) = true_ctr x position_bias
      x placement multiplier x user segment multiplier.
    * Conversions occur for a fraction of clicks and carry revenue.
    * relevance_grade is a graded label: 0 = no engagement, 1 = click,
      2 = conversion. Use it as the gain for NDCG; use clicked for binary
      relevance.

    Built-in drift
    --------------
    From `drift_start_offset_days` after the start date the ranker is swapped
    to `model_version = 'ranker_v2'`, which inflates its scores (calibration
    ratio rises above 1) and the retriever becomes more popularity-biased
    (catalog coverage falls, exposure concentration rises). This gives the
    monitoring metrics something to detect.

    Output columns
    --------------
    timestamp         UTC timestamp of the request
    request_id        Deterministic UUID shared by every row in the slate
    impression_id     Deterministic UUID unique to the row
    user_id           User identifier
    user_segment      new | casual | loyal
    placement         home_feed | search | product_page | email
    device            ios | android | web
    model_version     ranker_v1 | ranker_v2
    slate_size        Number of items served in the request
    position          1-indexed rank of the item within the slate
    item_id           Catalog item identifier
    item_category     Catalog category of the item
    predicted_score   Ranker's predicted click probability (0-1)
    clicked           1 if the item was clicked, else 0
    converted         1 if the click led to a conversion, else 0
    relevance_grade   0 = none, 1 = click, 2 = conversion
    revenue           Revenue attributed to the impression (0 when no conversion)

    Output format
    -------------
    Date-partitioned Parquet files: <output_dir>/YYYY-MM-DD/data-YYYY-MM-DD.parquet

    Args:
        start_date: Start date (YYYY-MM-DD). Derived from past_days if None.
        end_date:   End date inclusive (YYYY-MM-DD). Derived from future_days if None.
        past_days:  Days before today to start generating data (default: 90).
        future_days: Days after today to generate data (default: 90).
        requests_per_hour: Ranked requests generated per hour slot.
        output_dir: Directory to write Parquet files. If None, no files are written.
        seed:       Random seed for reproducibility.
        drift_start_offset_days: Days after start_date at which ranker_v2 takes over.

    Returns:
        dict: Statistics — total_requests, total_impressions, total_clicks,
              total_conversions, click_rate, conversion_rate, distinct_items,
              files_created, date_range.
    """
    rng = np.random.default_rng(seed)
    random.seed(seed)

    if start_date is None or end_date is None:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date is None:
            start_date = (today - timedelta(days=past_days)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = (today + timedelta(days=future_days)).strftime('%Y-%m-%d')

    start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    # end_date is inclusive: generate every hour of that day
    end_dt   = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc) + timedelta(days=1)
    drift_dt = start_dt + timedelta(days=drift_start_offset_days)

    catalog = _build_catalog(rng)
    item_ids   = catalog['item_ids']
    categories = catalog['categories']
    true_ctr   = catalog['true_ctr']
    popularity = catalog['popularity']

    # Popularity-sharpened retriever used after the drift point
    popularity_v2 = np.power(popularity, 1.6)
    popularity_v2 = popularity_v2 / popularity_v2.sum()

    n_users = 5000
    user_ids = [f'user_{i:06d}' for i in range(n_users)]
    user_segment = {u: rng.choice(USER_SEGMENTS, p=USER_SEGMENT_PROBS) for u in user_ids}

    stats = {
        'total_requests': 0,
        'total_impressions': 0,
        'total_clicks': 0,
        'total_conversions': 0,
        'files_created': 0,
        'date_range': f'{start_date} to {end_date}',
    }
    seen_items = set()

    rows_by_date = {}
    current_dt = start_dt

    while current_dt < end_dt:
        date_str = current_dt.strftime('%Y-%m-%d')
        if date_str not in rows_by_date:
            rows_by_date[date_str] = []

        is_v2 = current_dt >= drift_dt
        model_version = 'ranker_v2' if is_v2 else 'ranker_v1'
        retrieval_weights = popularity_v2 if is_v2 else popularity
        rank_noise_sd = 0.9 if is_v2 else 0.7     # ranker gets noisier after the swap
        score_shift = 0.45 if is_v2 else 0.0      # logit-space inflation -> overconfidence

        for i in range(requests_per_hour):
            # Spread requests across the hour for realistic timestamps
            ts = current_dt + timedelta(seconds=int(rng.integers(0, 3600)))

            user_id   = random.choice(user_ids)
            segment   = user_segment[user_id]
            placement = rng.choice(PLACEMENTS, p=PLACEMENT_PROBS)
            device    = rng.choice(DEVICES, p=DEVICE_PROBS)

            # --- Retrieval: sample a candidate pool weighted by popularity ---
            cand_idx = rng.choice(CATALOG_SIZE, size=CANDIDATE_POOL, replace=False, p=retrieval_weights)

            # --- Ranking: noisy estimate of true CTR, top SLATE_SIZE by rank score ---
            rank_logits = _logit(true_ctr[cand_idx]) + rng.normal(0.0, rank_noise_sd, size=CANDIDATE_POOL)
            order     = np.argsort(-rank_logits)[:SLATE_SIZE]
            slate_idx = cand_idx[order]

            request_hash = hashlib.md5(f'{current_dt.isoformat()}_{i}'.encode()).hexdigest()
            request_id   = str(uuid.UUID(request_hash))

            ctr_mult = PLACEMENT_CTR_MULT[placement] * USER_SEGMENT_CTR_MULT[segment]

            for pos, idx in enumerate(slate_idx, start=1):
                p_click = min(0.95, true_ctr[idx] * POSITION_BIAS[pos - 1] * ctr_mult)

                # Logged pCTR: a calibrated-but-noisy estimate of P(click) at this
                # position. ranker_v2 adds a logit shift so it over-predicts.
                score = _sigmoid(_logit(p_click) + rng.normal(0.0, 0.35) + score_shift)
                score = float(np.clip(score, 0.001, 0.999))
                clicked = int(rng.random() < p_click)
                converted = int(clicked and rng.random() < CONVERSION_RATE_GIVEN_CLICK)
                revenue = round(float(rng.lognormal(3.4, 0.6)), 2) if converted else 0.0
                relevance_grade = 2 if converted else (1 if clicked else 0)

                impression_hash = hashlib.md5(f'{request_id}_{pos}'.encode()).hexdigest()

                rows_by_date[date_str].append({
                    'timestamp':       ts,
                    'request_id':      request_id,
                    'impression_id':   str(uuid.UUID(impression_hash)),
                    'user_id':         user_id,
                    'user_segment':    segment,
                    'placement':       placement,
                    'device':          device,
                    'model_version':   model_version,
                    'slate_size':      SLATE_SIZE,
                    'position':        pos,
                    'item_id':         item_ids[idx],
                    'item_category':   categories[idx],
                    'predicted_score': round(float(score), 6),
                    'clicked':         clicked,
                    'converted':       converted,
                    'relevance_grade': relevance_grade,
                    'revenue':         revenue,
                })

                seen_items.add(item_ids[idx])
                stats['total_impressions'] += 1
                stats['total_clicks'] += clicked
                stats['total_conversions'] += converted

            stats['total_requests'] += 1

        current_dt += timedelta(hours=1)

    if output_dir is not None:
        _write_parquet(rows_by_date, output_dir, stats)

    stats['click_rate'] = stats['total_clicks'] / max(stats['total_impressions'], 1)
    stats['conversion_rate'] = stats['total_conversions'] / max(stats['total_impressions'], 1)
    stats['distinct_items'] = len(seen_items)
    stats['catalog_size'] = CATALOG_SIZE

    return stats


# ---------------------------------------------------------------------------
# Reference dataset helper (mirrors other generators)
# ---------------------------------------------------------------------------
def generate_reference_dataset(
    start_date=None,
    end_date=None,
    past_days=90,
    future_days=90,
    reference_days=14,
    requests_per_hour=20,
    output_dir=None,
    seed=42,
):
    """
    Generate a reference / baseline ranking dataset for comparison.

    Writes to <output_dir>/ranking-recsys-ads-reference/. The reference window
    always uses ranker_v1 (no drift) so it serves as a clean baseline.

    Args:
        start_date:        Start date (YYYY-MM-DD). Derived from past_days if None.
        end_date:          End date (YYYY-MM-DD). Derived from start_date + reference_days if None.
        past_days:         Days before today to start the reference window (default: 90).
        future_days:       Unused; kept for API consistency.
        reference_days:    Length of the reference window in days (default: 14).
        requests_per_hour: Requests per hour.
        output_dir:        Base output directory.
        seed:              Random seed.

    Returns:
        dict: Statistics (same keys as generate_dataset).
    """
    if start_date is None:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = (today - timedelta(days=past_days)).strftime('%Y-%m-%d')
    if end_date is None:
        start_dt = datetime.fromisoformat(start_date)
        end_date = (start_dt + timedelta(days=reference_days - 1)).strftime('%Y-%m-%d')

    ref_output = Path(output_dir) / 'ranking-recsys-ads-reference' if output_dir else None
    return generate_dataset(
        start_date=start_date,
        end_date=end_date,
        requests_per_hour=requests_per_hour,
        output_dir=ref_output,
        seed=seed,
        drift_start_offset_days=10_000,   # never drift inside the reference window
    )


if __name__ == '__main__':
    base_output_dir = Path(__file__).parent / '../output'

    print('Generating ranking / ads dataset...')
    main_output = base_output_dir / 'ranking-recsys-ads'
    stats = generate_dataset(
        past_days=90,
        future_days=90,
        requests_per_hour=20,
        output_dir=main_output,
        seed=42,
    )

    print('\nMain Dataset Statistics:')
    print(f"  Date range: {stats['date_range']}")
    print(f"  Total requests: {stats['total_requests']:,}")
    print(f"  Total impressions: {stats['total_impressions']:,}")
    print(f"  Click rate: {stats['click_rate']:.2%}")
    print(f"  Conversion rate: {stats['conversion_rate']:.2%}")
    print(f"  Distinct items served: {stats['distinct_items']:,} of {stats['catalog_size']:,}")
    print(f"  Files created: {stats['files_created']:,}")
    print(f"  Output directory: {main_output}")

    print('\nGenerating reference dataset...')
    ref_stats = generate_reference_dataset(
        past_days=90,
        reference_days=14,
        requests_per_hour=20,
        output_dir=base_output_dir,
        seed=42,
    )

    print('\nReference Dataset Statistics:')
    print(f"  Date range: {ref_stats['date_range']}")
    print(f"  Total requests: {ref_stats['total_requests']:,}")
    print(f"  Total impressions: {ref_stats['total_impressions']:,}")
    print(f"  Click rate: {ref_stats['click_rate']:.2%}")
    print(f"  Files created: {ref_stats['files_created']:,}")
    print(f"  Output directory: {base_output_dir / 'ranking-recsys-ads-reference'}")
