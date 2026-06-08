"""
Upsolve UCF Dashboard Sync Script

PURPOSE: Promote dashboards between on-prem Upsolve environments (e.g. staging → prod)
         using the three admin-API-key UCF endpoints.

FLOW:
    1. Mark dashboards as exportable  (set-exportable)
    2. Export them to an encrypted .ucf blob  (export)
    3. Import the blob into the target environment  (import)

USAGE:
    # Export from staging and import into prod:
    python upsolve-dashboard-sync.py \\
        --src  http://upsolve-staging:5001 \\
        --dst  http://upsolve-prod:5001 \\
        --src-key <SKELETON_KEY_STAGING> \\
        --dst-key <SKELETON_KEY_PROD> \\
        --dashboard-ids <UUID1> <UUID2>

    # Use friendly names from a dashboard map:
    python upsolve-dashboard-sync.py \\
        --src  http://upsolve-staging:5001 \\
        --dst  http://upsolve-prod:5001 \\
        --dashboard-map dashboard-ids.json \\
        --dashboard-ids fraud-overview risk-summary

    # Export only (save .ucf to disk):
    python upsolve-dashboard-sync.py \\
        --src  http://upsolve-staging:5001 \\
        --src-key <SKELETON_KEY> \\
        --dashboard-ids <UUID1> \\
        --export-file dashboards.ucf

    # Import only (load .ucf from disk):
    python upsolve-dashboard-sync.py \\
        --dst  http://upsolve-prod:5001 \\
        --dst-key <SKELETON_KEY> \\
        --import-file dashboards.ucf

ENVIRONMENT VARIABLES (alternative to flags; loaded from .env if present):
    UPSOLVE_SRC_HOST        Source Upsolve base URL
    UPSOLVE_DST_HOST        Destination Upsolve base URL
    UPSOLVE_SRC_API_KEY     SKELETON_KEY for source environment
    UPSOLVE_DST_API_KEY     SKELETON_KEY for destination environment
    UPSOLVE_DASHBOARD_MAP   Path to dashboard name→UUID JSON map (alternative to --dashboard-map)

.env EXAMPLE:
    UPSOLVE_SRC_HOST=http://upsolve-staging:5001
    UPSOLVE_DST_HOST=http://upsolve-prod:5001
    UPSOLVE_SRC_API_KEY=sk-staging-...
    UPSOLVE_DST_API_KEY=sk-prod-...
    UPSOLVE_DASHBOARD_MAP=dashboard-ids.json

DASHBOARD MAP (dashboard-ids.json):
    {
        "fraud-overview":  "11111111-aaaa-...",
        "risk-summary":    "22222222-bbbb-..."
    }
    To find a dashboard UUID: open the dashboard → Actions menu (top-right) → "Copy dashboard ID".
    Pass --dashboard-ids fraud-overview risk-summary and the names are resolved to UUIDs.
    Raw UUIDs are also accepted and pass through unchanged.

NOTES:
    - SKELETON_KEY must equal ARTHUR_UPSOLVE_API_KEY set on the app-plane.
    - FILES_KEY must be identical across environments for import decryption to work.
    - Dashboard display names are the stable tenant identifiers — do not rename them.
    - The import is a true upsert; re-running it is safe (idempotent).
"""

import argparse
import json
import os
import sys

import requests

try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------

def load_env_file(path: str = ".env") -> None:
    if not _DOTENV_AVAILABLE:
        if os.path.exists(path):
            print(f"warning: {path} found but python-dotenv is not installed — run: pip install python-dotenv")
        return
    load_dotenv(path, override=False)  # env vars already set in the shell take precedence


# ---------------------------------------------------------------------------
# Dashboard name → UUID resolution
# ---------------------------------------------------------------------------

def load_dashboard_map(path: str | None) -> dict[str, str]:
    """Return a name→UUID dict from a JSON file, or {} if no path given."""
    resolved = path or os.getenv("UPSOLVE_DASHBOARD_MAP")
    if not resolved:
        return {}
    with open(resolved) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        print(f"error: dashboard map {resolved} must be a JSON object")
        sys.exit(1)
    return data


def resolve_dashboard_ids(ids: list[str], name_map: dict[str, str]) -> list[str]:
    """Resolve each entry: if it's a key in name_map use the UUID, otherwise pass through."""
    resolved = []
    for entry in ids:
        if entry in name_map:
            resolved.append(name_map[entry])
        else:
            resolved.append(entry)
    return resolved


# ---------------------------------------------------------------------------
# Upsolve admin API client
# ---------------------------------------------------------------------------

class UpsolveAdminClient:
    def __init__(self, host: str, api_key: str, verify_ssl: bool = True):
        self.base = host.rstrip("/")
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "x-api-key": api_key,
        })

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def set_exportable(self, dashboard_ids: list[str], exportable: bool = True) -> dict:
        """Mark dashboards as exportable (or un-mark them)."""
        payload = {"dashboardIds": dashboard_ids, "isExportable": exportable}
        resp = self.session.post(
            self._url("/v1/api/ucf/dashboards/set-exportable"),
            json=payload,
            verify=self.verify_ssl,
        )
        resp.raise_for_status()
        return resp.json()

    def export_dashboards(self) -> str:
        """Export all exportable dashboards. Returns the encrypted .ucf blob (string)."""
        resp = self.session.post(
            self._url("/v1/api/ucf/dashboards/export"),
            json={},
            verify=self.verify_ssl,
        )
        resp.raise_for_status()
        body = resp.json()
        return body.get("data") or body  # blob is in `data` field

    def import_dashboards(self, ucf_data: str) -> dict:
        """Import an encrypted .ucf blob into this environment."""
        resp = self.session.post(
            self._url("/v1/api/ucf/dashboards/import"),
            json={"data": ucf_data},
            verify=self.verify_ssl,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Promote Upsolve dashboards between environments via UCF admin endpoints.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    p.add_argument("--env-file", default=".env", metavar="PATH",
                   help="Path to .env file to load (default: .env in cwd)")

    src = p.add_argument_group("source environment")
    src.add_argument("--src", default=None, metavar="URL",
                     help="Base URL of source Upsolve (e.g. http://upsolve-staging:5001)")
    src.add_argument("--src-key", default=None, metavar="KEY",
                     help="SKELETON_KEY / ARTHUR_UPSOLVE_API_KEY for source env")

    dst = p.add_argument_group("destination environment")
    dst.add_argument("--dst", default=None, metavar="URL",
                     help="Base URL of destination Upsolve (e.g. http://upsolve-prod:5001)")
    dst.add_argument("--dst-key", default=None, metavar="KEY",
                     help="SKELETON_KEY / ARTHUR_UPSOLVE_API_KEY for destination env")

    io = p.add_argument_group("dashboards / files")
    io.add_argument("--dashboard-ids", nargs="+", metavar="UUID_OR_NAME",
                    help="Dashboard UUIDs (or names from --dashboard-map) to mark exportable")
    io.add_argument("--dashboard-map", default=None, metavar="PATH",
                    help="JSON file mapping friendly names → UUIDs (also: UPSOLVE_DASHBOARD_MAP env var)")
    io.add_argument("--export-file", metavar="PATH",
                    help="Save the exported .ucf blob to this file (skips import)")
    io.add_argument("--import-file", metavar="PATH",
                    help="Load a .ucf blob from this file (skips export)")

    p.add_argument("--no-verify-ssl", action="store_true",
                   help="Disable SSL certificate verification (useful for self-signed certs)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would happen without making any API calls")

    return p.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    doing_export = args.src or args.dashboard_ids
    doing_import = args.dst

    if not doing_export and not args.import_file:
        print("error: provide --src / --dashboard-ids for export, or --import-file to import from disk")
        sys.exit(1)

    if doing_export and not args.src:
        print("error: --src is required when exporting")
        sys.exit(1)

    if doing_export and not args.src_key:
        print("error: --src-key (or UPSOLVE_SRC_API_KEY) is required for the source environment")
        sys.exit(1)

    if doing_import and not args.dst_key:
        print("error: --dst-key (or UPSOLVE_DST_API_KEY) is required for the destination environment")
        sys.exit(1)

    if not doing_import and not args.export_file:
        print("error: provide --dst for live import, or --export-file to save the blob to disk")
        sys.exit(1)


def main() -> None:
    args = parse_args()

    # Load .env first so env vars are available for the fallbacks below
    load_env_file(args.env_file)

    # Apply env var fallbacks (flags take priority; env vars fill gaps)
    args.src = args.src or os.getenv("UPSOLVE_SRC_HOST")
    args.src_key = args.src_key or os.getenv("UPSOLVE_SRC_API_KEY")
    args.dst = args.dst or os.getenv("UPSOLVE_DST_HOST")
    args.dst_key = args.dst_key or os.getenv("UPSOLVE_DST_API_KEY")

    validate_args(args)

    # Resolve friendly names → UUIDs if a map was provided
    if args.dashboard_ids:
        name_map = load_dashboard_map(args.dashboard_map)
        args.dashboard_ids = resolve_dashboard_ids(args.dashboard_ids, name_map)

    verify_ssl = not args.no_verify_ssl
    ucf_data: str | None = None

    # ------------------------------------------------------------------
    # Step 1 & 2: Export from source
    # ------------------------------------------------------------------
    if args.import_file:
        print(f"Loading .ucf blob from {args.import_file}")
        if not args.dry_run:
            with open(args.import_file) as f:
                ucf_data = f.read().strip()
    else:
        src_client = UpsolveAdminClient(args.src, args.src_key, verify_ssl)

        if args.dashboard_ids:
            print(f"Marking {len(args.dashboard_ids)} dashboard(s) as exportable on {args.src}")
            if not args.dry_run:
                result = src_client.set_exportable(args.dashboard_ids)
                print(f"  set-exportable response: {json.dumps(result, indent=2)}")

        print(f"Exporting dashboards from {args.src}")
        if not args.dry_run:
            ucf_data = src_client.export_dashboards()
            print(f"  export succeeded — blob length: {len(str(ucf_data))} chars")

        if args.export_file:
            print(f"Saving .ucf blob to {args.export_file}")
            if not args.dry_run:
                with open(args.export_file, "w") as f:
                    f.write(str(ucf_data))
            print("Done — skipping import (no --dst provided).")
            return

    # ------------------------------------------------------------------
    # Step 3: Import into destination
    # ------------------------------------------------------------------
    if args.dst:
        dst_client = UpsolveAdminClient(args.dst, args.dst_key, verify_ssl)
        print(f"Importing dashboards into {args.dst}")
        if not args.dry_run:
            result = dst_client.import_dashboards(ucf_data)
            print(f"  import response: {json.dumps(result, indent=2)}")
        print("Done.")
    elif args.dry_run:
        print("[dry-run] would import blob into destination — re-run without --dry-run")


if __name__ == "__main__":
    main()
