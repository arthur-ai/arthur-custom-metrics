"""Shared helpers for the metric SQL harness.

The harness never stores its own copy of a metric's SQL. It pulls the
``Base Metric SQL`` block straight out of the metric's markdown doc, fills in
the ``{{template}}`` variables the same way the Arthur UI does, runs the result
in DuckDB (the engine Arthur uses for custom metrics) and compares the output
to an independent pandas implementation.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
METRICS_DIR = REPO_ROOT / 'examples' / 'metrics'
DATAGEN_DIR = REPO_ROOT / 'data'

_SQL_BLOCK = re.compile(r'## Base Metric SQL.*?```sql\n(.*?)```', re.S)
_TEMPLATE_VAR = re.compile(r'\{\{(.*?)\}\}')


def extract_base_metric_sql(doc_path):
    """Return the SQL inside the first ```sql fence under '## Base Metric SQL'."""
    text = Path(doc_path).read_text()
    match = _SQL_BLOCK.search(text)
    if not match:
        raise AssertionError(f'no "## Base Metric SQL" code block found in {doc_path}')
    return match.group(1)


def render(sql, params):
    """Substitute {{key}} placeholders. Fails if any placeholder is left over."""
    for key, value in params.items():
        sql = sql.replace('{{' + key + '}}', str(value))
    leftover = _TEMPLATE_VAR.findall(sql)
    if leftover:
        raise AssertionError(f'unreplaced template variables: {sorted(set(leftover))}')
    return sql


def metric_sql(doc_name, params):
    """Load examples/metrics/<doc_name>.md and render its Base Metric SQL."""
    return render(extract_base_metric_sql(METRICS_DIR / f'{doc_name}.md'), params)


def assert_frames_match(got, expected, keys=('ts',), atol=1e-6, rtol=1e-6):
    """Compare two result frames row by row on every non-key column of ``expected``.

    Both frames are sorted by ``keys`` first. ``ts`` is normalised to UTC so a
    naive DuckDB timestamp and a tz-aware pandas timestamp compare equal.
    Every mismatch is collected so a failure shows the whole picture.
    """
    got = got.copy()
    expected = expected.copy()
    for frame in (got, expected):
        if 'ts' in frame.columns:
            frame['ts'] = pd.to_datetime(frame['ts'], utc=True)
    keys = list(keys)
    got = got.sort_values(keys).reset_index(drop=True)
    expected = expected.sort_values(keys).reset_index(drop=True)

    problems = []
    if len(got) != len(expected):
        problems.append(f'row count: got {len(got)}, expected {len(expected)}')
    else:
        for key in keys:
            if not got[key].astype(str).equals(expected[key].astype(str)):
                problems.append(f'key column {key!r} differs after sorting')
        for col in [c for c in expected.columns if c not in keys]:
            if col not in got.columns:
                problems.append(f'missing output column {col!r}')
                continue
            g = got[col].astype(float).to_numpy()
            e = expected[col].astype(float).to_numpy()
            bad = ~np.isclose(g, e, atol=atol, rtol=rtol, equal_nan=True)
            if bad.any():
                i = int(np.argmax(bad))
                problems.append(
                    f'{col}: {int(bad.sum())} mismatching rows; first at row {i} '
                    f'({[got[k].iloc[i] for k in keys]}): got {g[i]!r}, expected {e[i]!r}'
                )
    if problems:
        raise AssertionError('\n'.join(problems))
