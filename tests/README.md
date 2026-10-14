# Metric SQL Test Harness

Executable checks for the SQL in `examples/metrics/`. Each test pulls the
**Base Metric SQL** block straight out of a metric's markdown doc, fills in the
`{{template}}` variables, runs it in DuckDB (the engine Arthur uses for custom
metrics) and compares the output to an independent pandas implementation and to
hand-computed fixtures.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r tests/requirements.txt
pytest
```

The ranking suite generates a few days of the `ranking-recsys-ads` dataset into a
temporary directory on each run, so there is no committed test data.

### Optional: also run in PostgreSQL

Chart SQL runs in TimescaleDB, so it is useful to know the metric SQL is also
valid PostgreSQL. Set a DSN and install the driver:

```bash
pip install psycopg2-binary
ARTHUR_TEST_PG_DSN=postgresql://postgres:password@localhost:5432/postgres pytest
```

The harness creates a schema named `arthur_metric_tests` (dropped and recreated
on every run) with a `date_bin` based `time_bucket()` shim. Without the variable
the PostgreSQL parametrisation is skipped.

## Layout

| File | Purpose |
|------|---------|
| `metrics/helpers.py` | Extract SQL from a doc, render template variables, compare result frames |
| `metrics/references.py` | pandas/numpy implementations of each ranking metric, written from the definitions |
| `metrics/conftest.py` | Dataset generation, DuckDB and PostgreSQL engines, hand-built mini slates |
| `metrics/test_ranking_sql.py` | The tests for `examples/metrics/ranking/` |

## Adding a metric

1. Write the doc under `examples/metrics/<category>/` with a `## Base Metric SQL` section containing one ```` ```sql ```` block.
2. Add a reference implementation to `references.py` (or a new `references_<category>.py`).
3. Add a test that renders the doc's SQL with the argument keys from its
   **Aggregate Arguments** table and compares to the reference.
4. Add at least one hand-computed case covering the metric's edge conditions
   (empty groups, division by zero, items outside K, NULL inputs).
5. If the metric lives in `ranking/`, add its stem to `RANKING_DOCS` so the coverage test passes.
