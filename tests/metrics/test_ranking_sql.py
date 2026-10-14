"""Run the Base Metric SQL of every doc in examples/metrics/ranking/ and check the numbers.

Two kinds of checks:

* Generated data: the ranking-recsys-ads generator produces a few days of
  impressions and the SQL output is compared to the pandas implementations in
  ``references.py`` to 1e-6.
* Hand-computed slates: tiny fixtures whose expected values were worked out by
  hand (see ``conftest.py`` for the cases) so an error shared by the SQL and the
  pandas reference would still be caught.
"""
import numpy as np
import pandas as pd
import pytest

import references as ref
from helpers import METRICS_DIR, assert_frames_match, extract_base_metric_sql, metric_sql, render

K = 3
N_BINS = 10
TOP_N = 50
CATALOG_SIZE = 2000

IMPRESSION_ARGS = dict(dataset='ds', timestamp_col='timestamp', request_id_col='request_id',
                       position_col='position', k=K)
SLATE_ARRAY_ARGS = dict(dataset='ds_slates', timestamp_col='timestamp', request_id_col='request_id',
                        recommended_items_col='recommended_items', engaged_items_col='engaged_items', k=K)
CALIBRATION_ARGS = dict(dataset='ds', timestamp_col='timestamp', score_col='predicted_score',
                        label_col='clicked', n_bins=N_BINS)
COVERAGE_ARGS = dict(dataset='ds', timestamp_col='timestamp', item_id_col='item_id', top_n=TOP_N)
DIVERSITY_ARGS = dict(dataset='ds', timestamp_col='timestamp', request_id_col='request_id',
                      item_category_col='item_category')

RANKING_DOCS = {
    'top-k-ranking-quality', 'top-k-ranking-quality-slate-arrays', 'calibration-profile',
    'reliability-diagram-bins', 'catalog-coverage-and-exposure', 'slate-diversity',
}

LOG2_3 = np.log2(3)


# --- generated data -----------------------------------------------------------

@pytest.mark.parametrize('relevance_col', ['relevance_grade', 'clicked'])
def test_top_k_ranking_quality(engine, ranking_df, relevance_col):
    got = engine.run(metric_sql('ranking/top-k-ranking-quality', {**IMPRESSION_ARGS, 'relevance_col': relevance_col}))
    assert_frames_match(got, ref.top_k_ranking_quality(ranking_df, relevance_col, K))


def test_slate_array_layout_matches_impression_layout(engine, ranking_df):
    """Arrays built from clicks must give exactly the binary-relevance impression result."""
    got = engine.run(metric_sql('ranking/top-k-ranking-quality-slate-arrays', SLATE_ARRAY_ARGS))
    assert_frames_match(got, ref.top_k_ranking_quality(ranking_df, 'clicked', K))


def test_calibration_profile(engine, ranking_df):
    got = engine.run(metric_sql('ranking/calibration-profile', CALIBRATION_ARGS))
    assert_frames_match(got, ref.calibration_profile(ranking_df, 'predicted_score', 'clicked', N_BINS))


def test_reliability_diagram_bins(engine, ranking_df):
    got = engine.run(metric_sql('ranking/reliability-diagram-bins', CALIBRATION_ARGS))
    # The SQL labels bins like '0.1-0.2'; map the lower edge back to the bin index.
    got['bin'] = got['score_bin'].str.split('-').str[0].astype(float).mul(N_BINS).round().astype(int)
    assert_frames_match(got, ref.reliability_diagram_bins(ranking_df, 'predicted_score', 'clicked', N_BINS),
                        keys=('ts', 'bin'))


@pytest.mark.parametrize('catalog_size', [CATALOG_SIZE, 0], ids=['explicit-catalog', 'auto-detect'])
def test_catalog_coverage_and_exposure(engine, ranking_df, catalog_size):
    got = engine.run(metric_sql('ranking/catalog-coverage-and-exposure', {**COVERAGE_ARGS, 'catalog_size': catalog_size}))
    assert_frames_match(got, ref.catalog_coverage_and_exposure(ranking_df, 'item_id', catalog_size, TOP_N))


def test_slate_diversity(engine, ranking_df):
    got = engine.run(metric_sql('ranking/slate-diversity', DIVERSITY_ARGS))
    assert_frames_match(got, ref.slate_diversity(ranking_df, 'item_category'))


# --- hand-computed slates (K = 3) ----------------------------------------------
#
# Request A: gains [0, 1, 0, 2, 0]. DCG@3 = 1/log2(3). IDCG@3 = 2/log2(2) + 1/log2(3).
#            AP@3 = (precision at rank 2 = 1/2) / min(3, 2 relevant) = 0.25. RR = 1/2.
#            P@3 = 1/3, R@3 = 1/2, hit = 1.
# Request B: nothing relevant -> excluded from the averages, counted in request_count.
# Request C: gains [3, 0, 0, 0, 1]. DCG@3 = 3. IDCG@3 = 3 + 1/log2(3). AP@3 = 1/2.
#            RR = 1, P@3 = 1/3, R@3 = 1/2, hit = 1.
# Request D: gain only at position 4 -> NDCG, AP, RR, P, R, hit all 0 but still evaluable.

def test_top_k_ranking_quality_hand_computed(engine):
    got = engine.run(metric_sql('ranking/top-k-ranking-quality',
                                {**IMPRESSION_ARGS, 'dataset': 'mini_long', 'relevance_col': 'relevance'}))
    ndcg_a = (1 / LOG2_3) / (2 + 1 / LOG2_3)
    ndcg_c = 3 / (3 + 1 / LOG2_3)
    expected = pd.DataFrame([dict(
        ts='2026-01-01', ndcg_at_k=(ndcg_a + ndcg_c + 0) / 3, map_at_k=(0.25 + 0.5 + 0) / 3,
        mrr_at_k=(0.5 + 1 + 0) / 3, precision_at_k=(1 / 3 + 1 / 3 + 0) / 3, recall_at_k=(0.5 + 0.5 + 0) / 3,
        hit_rate_at_k=2 / 3, evaluable_request_ratio=3 / 4, request_count=4.0,
    )])
    assert_frames_match(got, expected)


# Same slates with binary relevance from the engaged arrays. Differences from above:
# A's gains become [0, 1, 0, 1, 0] so IDCG@3 = 1 + 1/log2(3).
# C engaged 'a' (position 1) and 'z' (never shown): 2 relevant, DCG@3 = 1, IDCG@3 = 1 + 1/log2(3).
# E has NULL arrays: not evaluable, so the ratio is 3/5 and request_count is 5.

def test_slate_array_hand_computed(engine):
    got = engine.run(metric_sql('ranking/top-k-ranking-quality-slate-arrays',
                                {**SLATE_ARRAY_ARGS, 'dataset': 'mini_slates'}))
    ndcg_a = (1 / LOG2_3) / (1 + 1 / LOG2_3)
    ndcg_c = 1 / (1 + 1 / LOG2_3)
    expected = pd.DataFrame([dict(
        ts='2026-01-01', ndcg_at_k=(ndcg_a + ndcg_c + 0) / 3, map_at_k=0.25, mrr_at_k=0.5,
        precision_at_k=2 / 9, recall_at_k=1 / 3, hit_rate_at_k=2 / 3,
        evaluable_request_ratio=3 / 5, request_count=5.0,
    )])
    assert_frames_match(got, expected)


# --- doc hygiene ----------------------------------------------------------------

def test_every_ranking_doc_is_covered():
    """A new metric doc must be added to this suite, and every doc must have a SQL block."""
    docs = {p.stem for p in (METRICS_DIR / 'ranking').glob('*.md')}
    assert docs == RANKING_DOCS, f'ranking docs changed; update the tests. Diff: {docs ^ RANKING_DOCS}'
    for name in docs:
        extract_base_metric_sql(METRICS_DIR / 'ranking' / f'{name}.md')


def test_render_rejects_leftover_placeholders():
    with pytest.raises(AssertionError, match='unreplaced'):
        render('SELECT {{a}}, {{b}}', {'a': 1})
