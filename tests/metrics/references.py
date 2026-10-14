"""Independent pandas/numpy implementations of the ranking metrics.

These are deliberately written from the metric definitions, not from the SQL,
so that a mistake in one is unlikely to be mirrored in the other. Each function
takes an impression-level frame (one row per request and position) that already
has a ``ts`` column holding the UTC day bucket.
"""
import math

import numpy as np
import pandas as pd


def top_k_ranking_quality(df, relevance_col, k):
    """NDCG / MAP / MRR / Precision / Recall / Hit Rate @K averaged per day.

    Only requests with at least one relevant item (relevance > 0) count towards
    the ranking metrics. ``evaluable_request_ratio`` reports that share and
    ``request_count`` counts every request.
    """
    rows = []
    for (ts, _request_id), g in df.groupby(['ts', 'request_id'], sort=False):
        g = g.sort_values('position')
        gain = np.maximum(g[relevance_col].astype(float).to_numpy(), 0.0)
        pos = g['position'].to_numpy()
        is_rel = (gain > 0).astype(int)
        in_k = pos <= k

        dcg = np.sum(gain[in_k] / np.log2(pos[in_k] + 1))
        ideal = np.sort(gain)[::-1][:k]
        idcg = np.sum(ideal / np.log2(np.arange(1, len(ideal) + 1) + 1))

        rel_total = int(is_rel.sum())
        rel_in_k = int(is_rel[in_k].sum())
        precision_at_rank = np.cumsum(is_rel) / pos
        ap_numerator = np.sum(precision_at_rank[in_k & (is_rel == 1)])
        first_rel = pos[is_rel == 1].min() if rel_total else None

        rows.append(dict(
            ts=ts,
            evaluable=int(rel_total > 0),
            ndcg=dcg / idcg if idcg > 0 else np.nan,
            ap=ap_numerator / min(k, rel_total) if rel_total else np.nan,
            rr=1.0 / first_rel if first_rel is not None and first_rel <= k else 0.0,
            precision=rel_in_k / k,
            recall=rel_in_k / rel_total if rel_total else np.nan,
            hit=int(rel_in_k > 0),
        ))
    per_request = pd.DataFrame(rows)
    evaluable = per_request[per_request.evaluable == 1]
    out = evaluable.groupby('ts').agg(
        ndcg_at_k=('ndcg', 'mean'), map_at_k=('ap', 'mean'), mrr_at_k=('rr', 'mean'),
        precision_at_k=('precision', 'mean'), recall_at_k=('recall', 'mean'),
        hit_rate_at_k=('hit', 'mean'),
    )
    out['evaluable_request_ratio'] = per_request.groupby('ts')['evaluable'].mean()
    out['request_count'] = per_request.groupby('ts').size().astype(float)
    return out.reset_index()


def _binned(df, score_col, label_col, n_bins):
    d = df[['ts', score_col, label_col]].copy()
    d['bin'] = np.minimum(np.floor(d[score_col] * n_bins), n_bins - 1).astype(int)
    d[label_col] = d[label_col].astype(float)
    return d.groupby(['ts', 'bin']).agg(
        n=(label_col, 'size'), avg_score=(score_col, 'mean'), obs=(label_col, 'mean'),
    ).reset_index()


def calibration_profile(df, score_col, label_col, n_bins):
    """Calibration ratio, ECE, MCE and the underlying averages per day."""
    per_bin = _binned(df, score_col, label_col, n_bins)
    rows = []
    for ts, g in per_bin.groupby('ts'):
        n = g.n.sum()
        gap = (g.avg_score - g.obs).abs()
        rows.append(dict(
            ts=ts,
            calibration_ratio=(g.n * g.avg_score).sum() / (g.n * g.obs).sum(),
            expected_calibration_error=(g.n * gap).sum() / n,
            max_calibration_error=gap.max(),
            avg_predicted_probability=(g.n * g.avg_score).sum() / n,
            observed_positive_rate=(g.n * g.obs).sum() / n,
            prediction_count=float(n),
        ))
    return pd.DataFrame(rows)


def reliability_diagram_bins(df, score_col, label_col, n_bins):
    """Per-bin predicted rate, observed rate, gap, share and count per day."""
    per_bin = _binned(df, score_col, label_col, n_bins)
    per_bin['predicted_rate'] = per_bin.avg_score
    per_bin['observed_rate'] = per_bin.obs
    per_bin['calibration_gap'] = per_bin.avg_score - per_bin.obs
    per_bin['bin_share'] = per_bin.n / per_bin.groupby('ts').n.transform('sum')
    per_bin['bin_count'] = per_bin.n.astype(float)
    return per_bin.drop(columns=['n', 'avg_score', 'obs'])


def catalog_coverage_and_exposure(df, item_col, catalog_size, top_n):
    """Coverage, top-N share, Gini over the full catalog, effective catalog size."""
    n_catalog = catalog_size if catalog_size > 0 else df[item_col].nunique()
    rows = []
    for ts, g in df.groupby('ts'):
        counts = g[item_col].value_counts().to_numpy().astype(float)
        served = len(counts)
        total = counts.sum()
        # Gini over every catalog item; unserved items contribute zero exposure.
        x = np.sort(np.concatenate([np.zeros(n_catalog - served), counts]))
        i = np.arange(1, n_catalog + 1)
        gini = 2 * np.sum(i * x) / (n_catalog * total) - (n_catalog + 1) / n_catalog
        p = counts / total
        rows.append(dict(
            ts=ts,
            catalog_coverage=served / n_catalog,
            top_n_exposure_share=np.sort(counts)[::-1][:top_n].sum() / total,
            exposure_gini=gini,
            effective_catalog_size=math.exp(-np.sum(p * np.log(p))),
            items_served=float(served),
            impression_count=total,
        ))
    return pd.DataFrame(rows)


def slate_diversity(df, category_col):
    """Intra-list diversity, normalised category entropy, single-category share."""
    rows = []
    for (ts, _request_id), g in df.groupby(['ts', 'request_id'], sort=False):
        counts = g[category_col].value_counts().to_numpy().astype(float)
        n = counts.sum()
        same_pairs = np.sum(counts * (counts - 1)) / 2
        all_pairs = n * (n - 1) / 2
        p = counts / n
        rows.append(dict(
            ts=ts,
            slate=n,
            distinct=len(counts),
            ild=(1 - same_pairs / all_pairs) if all_pairs > 0 else np.nan,
            ent=(-np.sum(p * np.log(p)) / math.log(n)) if n > 1 else np.nan,
            single=int(len(counts) == 1),
        ))
    per_request = pd.DataFrame(rows)
    out = per_request.groupby('ts').agg(
        avg_slate_size=('slate', 'mean'), avg_distinct_categories=('distinct', 'mean'),
        intra_list_diversity=('ild', 'mean'), normalized_category_entropy=('ent', 'mean'),
        single_category_slate_ratio=('single', 'mean'), request_count=('slate', 'size'),
    )
    out['request_count'] = out['request_count'].astype(float)
    return out.reset_index()
