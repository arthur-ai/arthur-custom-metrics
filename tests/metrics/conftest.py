"""Fixtures: a small generated ranking dataset and the SQL engines to run against.

DuckDB always runs. PostgreSQL runs only when ``ARTHUR_TEST_PG_DSN`` is set,
e.g. ``postgresql://postgres:secret@localhost:5432/postgres``; it is a
portability check, not the engine Arthur uses for custom metrics.
"""
import io
import os
import sys

import duckdb
import pandas as pd
import pytest

from helpers import DATAGEN_DIR

# Hand-built slates used by the hand-computed tests (K = 3). Positions are 1-based.
#   A: relevant at 2 (gain 1) and 4 (gain 2)   -> relevant inside and outside K
#   B: nothing relevant                        -> not evaluable
#   C: relevant at 1 (gain 3) and 5 (gain 1)   -> hit at the top, second item beyond K
#   D: relevant at 4 only                      -> evaluable but every @3 metric is zero
MINI_LONG_ROWS = [
    ('A', 1, 0.0), ('A', 2, 1.0), ('A', 3, 0.0), ('A', 4, 2.0), ('A', 5, 0.0),
    ('B', 1, 0.0), ('B', 2, 0.0), ('B', 3, 0.0),
    ('C', 1, 3.0), ('C', 2, 0.0), ('C', 3, 0.0), ('C', 4, 0.0), ('C', 5, 1.0),
    ('D', 1, 0.0), ('D', 2, 0.0), ('D', 3, 0.0), ('D', 4, 1.0), ('D', 5, 0.0),
]
MINI_HOUR = {'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14}
# Slate-array layout of the same cases. C engages 'z', which was never shown, so it
# counts as a relevant item that was missed. E has NULL arrays and is not evaluable.
MINI_SLATES = [
    ('A', ['a', 'b', 'c', 'd', 'e'], ['b', 'd']),
    ('B', ['a', 'b', 'c', 'd', 'e'], []),
    ('C', ['a', 'b', 'c', 'd', 'e'], ['a', 'z']),
    ('D', ['a', 'b', 'c', 'd', 'e'], ['d']),
    ('E', None, None),
]


def _mini_ts(request_id):
    return f'2026-01-01 {MINI_HOUR[request_id]:02d}:00:00+00'


@pytest.fixture(scope='session')
def ranking_df(tmp_path_factory):
    """Generate a few days of the ranking-recsys-ads dataset and load it."""
    sys.path.insert(0, str(DATAGEN_DIR / 'ranking-recsys-ads' / 'datagen'))
    from generate_dataset import generate_dataset  # noqa: E402

    out_dir = tmp_path_factory.mktemp('ranking-recsys-ads')
    # drift_start_offset_days=2 puts both ranker versions inside the 4-day window.
    generate_dataset(start_date='2026-01-01', end_date='2026-01-04', requests_per_hour=4,
                     output_dir=out_dir, seed=7, drift_start_offset_days=2)
    df = pd.read_parquet(out_dir)
    df['ts'] = df['timestamp'].dt.floor('D').dt.tz_convert('UTC')
    return df


class DuckDBEngine:
    name = 'duckdb'

    def __init__(self, df):
        self.con = duckdb.connect()
        self.con.execute("SET TimeZone='UTC'")
        self.con.register('df_src', df.drop(columns=['ts']))
        self.con.execute('CREATE TABLE ds AS SELECT * FROM df_src')
        self.con.execute("""
            CREATE TABLE ds_slates AS
            SELECT MIN(timestamp) AS timestamp, request_id,
                   list(item_id ORDER BY position) AS recommended_items,
                   list(item_id ORDER BY position) FILTER (WHERE clicked = 1) AS engaged_items
            FROM ds GROUP BY request_id
        """)
        long_values = ', '.join(
            f"(TIMESTAMPTZ '{_mini_ts(r)}', '{r}', {p}, {g})" for r, p, g in MINI_LONG_ROWS)
        self.con.execute(f'CREATE TABLE mini_long AS SELECT * FROM (VALUES {long_values}) '
                         't(timestamp, request_id, position, relevance)')

        def arr(items):
            return 'NULL::TEXT[]' if items is None else '[' + ', '.join(f"'{i}'" for i in items) + ']::TEXT[]'
        slate_values = ', '.join(
            f"(TIMESTAMPTZ '{_mini_ts(r)}', '{r}', {arr(rec)}, {arr(eng)})" for r, rec, eng in MINI_SLATES)
        self.con.execute(f'CREATE TABLE mini_slates AS SELECT * FROM (VALUES {slate_values}) '
                         't(timestamp, request_id, recommended_items, engaged_items)')

    def run(self, sql):
        return self.con.execute(sql).df()


class PostgresEngine:
    name = 'postgres'

    def __init__(self, dsn, df):
        import psycopg2

        self.conn = psycopg2.connect(dsn)
        self.conn.autocommit = True
        self.cur = self.conn.cursor()
        cur = self.cur
        cur.execute("DROP SCHEMA IF EXISTS arthur_metric_tests CASCADE; CREATE SCHEMA arthur_metric_tests; "
                    "SET search_path TO arthur_metric_tests; SET TimeZone='UTC';")
        # Plain PostgreSQL has no time_bucket(); emulate TimescaleDB's with date_bin().
        cur.execute("""
            CREATE FUNCTION arthur_metric_tests.time_bucket(bucket interval, ts timestamptz)
            RETURNS timestamptz AS $$ SELECT date_bin(bucket, ts, TIMESTAMPTZ '2000-01-03 00:00:00+00') $$
            LANGUAGE sql IMMUTABLE
        """)
        cur.execute("""
            CREATE TABLE ds (timestamp timestamptz, request_id text, impression_id text, user_id text,
                user_segment text, placement text, device text, model_version text, slate_size int,
                position int, item_id text, item_category text, predicted_score double precision,
                clicked int, converted int, relevance_grade int, revenue double precision)
        """)
        buf = io.StringIO()
        df.drop(columns=['ts']).to_csv(buf, index=False, header=False)
        buf.seek(0)
        cur.copy_expert('COPY ds FROM STDIN WITH (FORMAT csv)', buf)
        cur.execute("""
            CREATE TABLE ds_slates AS
            SELECT MIN(timestamp) AS timestamp, request_id,
                   array_agg(item_id ORDER BY position) AS recommended_items,
                   array_remove(array_agg(CASE WHEN clicked = 1 THEN item_id END ORDER BY position), NULL)
                       AS engaged_items
            FROM ds GROUP BY request_id
        """)
        cur.execute('CREATE TABLE mini_long (timestamp timestamptz, request_id text, position int, '
                    'relevance double precision)')
        cur.execute('INSERT INTO mini_long VALUES ' + ', '.join(
            f"('{_mini_ts(r)}', '{r}', {p}, {g})" for r, p, g in MINI_LONG_ROWS))

        def arr(items):
            return 'NULL' if items is None else 'ARRAY[' + ', '.join(f"'{i}'" for i in items) + ']::text[]'
        cur.execute('CREATE TABLE mini_slates (timestamp timestamptz, request_id text, '
                    'recommended_items text[], engaged_items text[])')
        cur.execute('INSERT INTO mini_slates VALUES ' + ', '.join(
            f"('{_mini_ts(r)}', '{r}', {arr(rec)}, {arr(eng)})" for r, rec, eng in MINI_SLATES))

    def run(self, sql):
        self.cur.execute(sql)
        return pd.DataFrame(self.cur.fetchall(), columns=[d[0] for d in self.cur.description])


@pytest.fixture(scope='session', params=['duckdb', 'postgres'])
def engine(request, ranking_df):
    if request.param == 'postgres':
        dsn = os.environ.get('ARTHUR_TEST_PG_DSN')
        if not dsn:
            pytest.skip('set ARTHUR_TEST_PG_DSN to also run the metric SQL in PostgreSQL')
        pytest.importorskip('psycopg2')
        return PostgresEngine(dsn, ranking_df)
    return DuckDBEngine(ranking_df)
