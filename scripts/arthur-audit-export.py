"""
Arthur Audit Evidence Export Script

PURPOSE: Export historical metric values, thresholds, and alert events from Arthur
         for governance/audit evidence to be attached in Archer.

USAGE:
    python arthur-audit-export.py \\
        --model-id <MODEL_ID> \\
        --metric-name <METRIC_NAME> \\
        --start-date 2025-01-01 \\
        --end-date   2025-01-31 \\
        --output     evidence.csv

    # Or with specific days, service account auth, and alerts included:
    python arthur-audit-export.py \\
        --model-id <MODEL_ID> \\
        --metric-name <METRIC_NAME> \\
        --days 2025-01-15 2025-01-16 2025-01-22 \\
        --include-alerts \\
        --auth service-account \\
        --output evidence.csv

AUTHENTICATION:
    Device (default)  - browser-based OAuth, suitable for interactive use
    Service account   - client_id + client_secret via env vars or flags,
                        suitable for automation / CI-CD

    For service account, set either:
      ARTHUR_CLIENT_ID and ARTHUR_CLIENT_SECRET environment variables
    or pass --client-id / --client-secret flags.

OUTPUT COLUMNS:
    date, metric_name, metric_value, threshold, threshold_operator,
    control_pass, alert_expected, alert_fired, alert_id, alert_timestamp,
    model_id, evidence_generated_at

NOTES:
    - Read-only: does not mutate any Arthur state.
    - Metric values are retrieved from stored historical data (no recomputation).
    - Thresholds are taken from the alert rule associated with the metric at
      query time (point-in-time history not available via this API).
    - Deterministic CSV ordering: date ASC, then metric_name ASC.
"""

import argparse
import csv
import os
import sys
from datetime import datetime, date, timedelta, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
try:
    from arthur_client.api_bindings import (
        AlertRulesV1Api,
        AlertsV1Api,
        MetricsV1Api,
        ModelsV1Api,
    )
    from arthur_client.api_bindings.api_client import ApiClient
    from arthur_client.api_bindings.models import (
        AlertBound,
        PostMetricsQuery,
        PostMetricsQueryTimeRange,
    )
    from arthur_client.auth import (
        ArthurClientCredentialsAPISession,
        ArthurOAuthSessionAPIConfiguration,
        ArthurOIDCMetadata,
        DeviceAuthorizer,
    )
except ImportError:
    sys.exit(
        "ERROR: arthur-client is not installed.\n"
        "Install it with:  pip install arthur-client"
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_ARTHUR_HOST = "https://platform.arthur.ai"
PAGE_SIZE = 1000  # maximum allowed by the API


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date '{s}'. Expected YYYY-MM-DD.")


def dates_in_range(start: date, end: date) -> list[date]:
    """Return every date from start through end inclusive."""
    delta = (end - start).days
    if delta < 0:
        raise ValueError("--start-date must be on or before --end-date")
    return [start + timedelta(days=i) for i in range(delta + 1)]


def day_window(d: date):
    """Return UTC-aware start/end datetimes covering the full calendar day."""
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def bound_to_operator(bound: AlertBound) -> str:
    """Map Arthur AlertBound to a human-readable comparison operator."""
    return ">" if bound == AlertBound.UPPER_BOUND else "<"


def threshold_violated(value: float, threshold: float, bound: AlertBound) -> bool:
    """Return True if value crosses the threshold in the direction of the bound."""
    if bound == AlertBound.UPPER_BOUND:
        return value > threshold
    return value < threshold


# ---------------------------------------------------------------------------
# Arthur API helpers
# ---------------------------------------------------------------------------

def build_api_client(args) -> ApiClient:
    host = args.arthur_host

    if args.auth == "service-account":
        client_id = args.client_id or os.environ.get("ARTHUR_CLIENT_ID")
        client_secret = args.client_secret or os.environ.get("ARTHUR_CLIENT_SECRET")
        if not client_id or not client_secret:
            sys.exit(
                "ERROR: Service account auth requires ARTHUR_CLIENT_ID and "
                "ARTHUR_CLIENT_SECRET (env vars or --client-id / --client-secret flags)."
            )
        sess = ArthurClientCredentialsAPISession(
            client_id=client_id,
            client_secret=client_secret,
            metadata=ArthurOIDCMetadata(arthur_host=host),
        )
    else:
        sess = DeviceAuthorizer(arthur_host=host).authorize()

    return ApiClient(configuration=ArthurOAuthSessionAPIConfiguration(session=sess))


def fetch_alert_rules(alert_rules_client: AlertRulesV1Api, model_id: str, metric_name: str):
    """Return all alert rules for the model that match metric_name."""
    rules = []
    page = 1
    while True:
        resp = alert_rules_client.get_model_alert_rules(
            model_id=model_id,
            metric_name=metric_name,
            page=page,
            page_size=PAGE_SIZE,
        )
        rules.extend(resp.records)
        if len(resp.records) < PAGE_SIZE:
            break
        page += 1
    return rules


def fetch_metric_value_for_day(
    metrics_client: MetricsV1Api,
    model_id: str,
    rule_query: str,
    d: date,
) -> Optional[float]:
    """
    Execute the alert rule query over a single calendar day and return the
    aggregate metric value. Returns None if no data is available for that day.
    """
    start, end = day_window(d)
    try:
        result = metrics_client.post_model_metrics_query(
            model_id=model_id,
            post_metrics_query=PostMetricsQuery(
                query=rule_query,
                time_range=PostMetricsQueryTimeRange(start=start, end=end),
                limit=1,
            ),
        )
    except Exception as exc:
        print(f"  WARNING: metrics query failed for {d}: {exc}", file=sys.stderr)
        return None

    if not result.results:
        return None

    # The query result is a list of dicts. We take the first row and look for
    # a numeric column that is not a timestamp column.
    row = result.results[0]
    if row is None:
        return None

    # Find the first numeric value in the row (skip timestamps / strings).
    for key, val in row.items():
        if isinstance(val, (int, float)):
            return float(val)
    return None


def fetch_alerts_for_day(
    alerts_client: AlertsV1Api,
    model_id: str,
    rule_id: str,
    d: date,
) -> list:
    """Return all alerts that fired for rule_id within the calendar day d."""
    start, end = day_window(d)
    fired = []
    page = 1
    while True:
        resp = alerts_client.get_model_alerts(
            model_id=model_id,
            alert_rule_ids=[rule_id],
            time_from=start,
            time_to=end,
            page=page,
            page_size=PAGE_SIZE,
        )
        fired.extend(resp.records)
        if len(resp.records) < PAGE_SIZE:
            break
        page += 1
    return fired


# ---------------------------------------------------------------------------
# Evidence assembly
# ---------------------------------------------------------------------------

def build_evidence_rows(
    days: list[date],
    metric_name: str,
    model_id: str,
    rules,
    metrics_client: MetricsV1Api,
    alerts_client: AlertsV1Api,
    include_alerts: bool,
) -> list[dict]:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []

    if not rules:
        print(
            f"WARNING: No alert rules found for metric '{metric_name}' "
            f"on model '{model_id}'. Threshold and alert columns will be empty.",
            file=sys.stderr,
        )

    for d in days:
        print(f"  Processing {d}...", file=sys.stderr)

        # Use the first matching rule for threshold data. If there are multiple
        # rules, each gets its own row so auditors can see all active controls.
        target_rules = rules if rules else [None]

        for rule in target_rules:
            threshold = rule.threshold if rule else None
            bound = rule.bound if rule else None
            operator = bound_to_operator(bound) if bound else None
            rule_query = rule.query if rule else None

            # --- Metric value ---
            if rule_query:
                metric_value = fetch_metric_value_for_day(
                    metrics_client, model_id, rule_query, d
                )
            else:
                metric_value = None

            # --- Derive pass/violation ---
            if metric_value is not None and threshold is not None and bound is not None:
                violated = threshold_violated(metric_value, threshold, bound)
                control_pass = not violated
                alert_expected = violated
            else:
                control_pass = None
                alert_expected = None

            # --- Alert lookup ---
            if include_alerts and rule:
                fired_alerts = fetch_alerts_for_day(alerts_client, model_id, rule.id, d)
                alert_fired = len(fired_alerts) > 0
                # Use the first (chronologically earliest) alert for identifiers.
                first_alert = (
                    min(fired_alerts, key=lambda a: a.timestamp)
                    if fired_alerts
                    else None
                )
                alert_id = first_alert.id if first_alert else None
                alert_timestamp = (
                    first_alert.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
                    if first_alert
                    else None
                )
            else:
                alert_fired = None
                alert_id = None
                alert_timestamp = None

            rows.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "metric_name": metric_name,
                    "metric_value": metric_value if metric_value is not None else "",
                    "threshold": threshold if threshold is not None else "",
                    "threshold_operator": operator if operator is not None else "",
                    "control_pass": (
                        str(control_pass).lower()
                        if control_pass is not None
                        else ""
                    ),
                    "alert_expected": (
                        str(alert_expected).lower()
                        if alert_expected is not None
                        else ""
                    ),
                    "alert_fired": (
                        str(alert_fired).lower()
                        if alert_fired is not None
                        else ""
                    ),
                    "alert_id": alert_id if alert_id else "",
                    "alert_timestamp": alert_timestamp if alert_timestamp else "",
                    "model_id": model_id,
                    "evidence_generated_at": generated_at,
                }
            )

    # Deterministic ordering: date ASC, metric_name ASC
    rows.sort(key=lambda r: (r["date"], r["metric_name"]))
    return rows


CSV_FIELDNAMES = [
    "date",
    "metric_name",
    "metric_value",
    "threshold",
    "threshold_operator",
    "control_pass",
    "alert_expected",
    "alert_fired",
    "alert_id",
    "alert_timestamp",
    "model_id",
    "evidence_generated_at",
]


def write_csv(rows: list[dict], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} row(s) to {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Export Arthur metric evidence for governance/audit use in Archer. "
            "Read-only — does not mutate any Arthur state."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # --- Required ---
    parser.add_argument(
        "--model-id",
        required=True,
        metavar="UUID",
        help="Arthur model ID (find in the Arthur UI).",
    )
    parser.add_argument(
        "--metric-name",
        "--control-id",
        dest="metric_name",
        required=True,
        metavar="NAME",
        help="Arthur metric name / control ID to export (e.g. 'false_positive_rate').",
    )
    parser.add_argument(
        "--output",
        required=True,
        metavar="PATH",
        help="Output CSV file path (e.g. evidence.csv).",
    )

    # --- Date selection ---
    date_group = parser.add_argument_group(
        "Date selection (use --start/--end OR --days)"
    )
    date_group.add_argument(
        "--start-date",
        type=parse_date,
        metavar="YYYY-MM-DD",
        help="Start of date range (inclusive).",
    )
    date_group.add_argument(
        "--end-date",
        type=parse_date,
        metavar="YYYY-MM-DD",
        help="End of date range (inclusive).",
    )
    date_group.add_argument(
        "--days",
        nargs="+",
        type=parse_date,
        metavar="YYYY-MM-DD",
        help="Explicit list of dates (alternative to --start-date / --end-date).",
    )

    # --- Feature flags ---
    parser.add_argument(
        "--include-alerts",
        action="store_true",
        default=False,
        help="Include alert_fired, alert_id, and alert_timestamp columns.",
    )

    # --- Authentication ---
    auth_group = parser.add_argument_group("Authentication")
    auth_group.add_argument(
        "--auth",
        choices=["device", "service-account"],
        default="device",
        help=(
            "Authentication method. "
            "'device' opens a browser (default). "
            "'service-account' uses client_id + client_secret."
        ),
    )
    auth_group.add_argument(
        "--arthur-host",
        default=DEFAULT_ARTHUR_HOST,
        metavar="URL",
        help=f"Arthur platform host (default: {DEFAULT_ARTHUR_HOST}).",
    )
    auth_group.add_argument(
        "--client-id",
        default=None,
        help="Service account client ID (or set ARTHUR_CLIENT_ID env var).",
    )
    auth_group.add_argument(
        "--client-secret",
        default=None,
        help="Service account client secret (or set ARTHUR_CLIENT_SECRET env var).",
    )

    args = parser.parse_args(argv)

    # Validate date selection
    has_range = args.start_date is not None or args.end_date is not None
    has_days = args.days is not None

    if has_range and has_days:
        parser.error("Specify either --start-date/--end-date OR --days, not both.")
    if not has_range and not has_days:
        parser.error("Specify a date range with --start-date/--end-date or exact dates with --days.")
    if has_range:
        if args.start_date is None or args.end_date is None:
            parser.error("Both --start-date and --end-date are required when using a range.")
        if args.start_date > args.end_date:
            parser.error("--start-date must be on or before --end-date.")

    return args


def main(argv=None):
    args = parse_args(argv)

    # Resolve the set of dates to export
    if args.days:
        target_days = sorted(set(args.days))
    else:
        target_days = dates_in_range(args.start_date, args.end_date)

    print(
        f"Exporting evidence for metric '{args.metric_name}' "
        f"on model '{args.model_id}' "
        f"across {len(target_days)} day(s)...",
        file=sys.stderr,
    )

    # Authenticate and build API clients
    print("Authenticating...", file=sys.stderr)
    api_client = build_api_client(args)

    alert_rules_client = AlertRulesV1Api(api_client)
    alerts_client = AlertsV1Api(api_client)
    metrics_client = MetricsV1Api(api_client)

    # Fetch alert rules for this metric (provides threshold + query)
    print(f"Fetching alert rules for metric '{args.metric_name}'...", file=sys.stderr)
    rules = fetch_alert_rules(alert_rules_client, args.model_id, args.metric_name)
    print(f"  Found {len(rules)} alert rule(s).", file=sys.stderr)

    # Build evidence rows
    rows = build_evidence_rows(
        days=target_days,
        metric_name=args.metric_name,
        model_id=args.model_id,
        rules=rules,
        metrics_client=metrics_client,
        alerts_client=alerts_client,
        include_alerts=args.include_alerts,
    )

    # Write output
    write_csv(rows, args.output)


if __name__ == "__main__":
    main()
