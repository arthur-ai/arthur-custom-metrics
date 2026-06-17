"""Upsolve UCF dashboard sync — see README.md for full usage and operational notes."""

from __future__ import annotations

import argparse
import binascii
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
# UCF encryption / decryption (AES-256-CBC, FILES_KEY hex-decoded)
# ---------------------------------------------------------------------------

def _aes_key(files_key: str) -> bytes:
    return bytes.fromhex(files_key)


def decrypt_ucf(blob: str, files_key: str) -> dict:
    """Decrypt a UCF blob (iv_hex:ciphertext_hex) and return the parsed JSON payload."""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        print("error: cryptography package required for merge mode — run: pip install cryptography")
        sys.exit(1)

    iv_hex, enc_hex = blob.strip().split(":", 1)
    key = _aes_key(files_key)
    cipher = Cipher(algorithms.AES(key), modes.CBC(binascii.unhexlify(iv_hex)),
                    backend=default_backend())
    padded = cipher.decryptor().update(binascii.unhexlify(enc_hex))
    padded += Cipher(algorithms.AES(key), modes.CBC(binascii.unhexlify(iv_hex)),
                     backend=default_backend()).decryptor().finalize()
    # Redo cleanly in one pass
    dec = Cipher(algorithms.AES(key), modes.CBC(binascii.unhexlify(iv_hex)),
                 backend=default_backend()).decryptor()
    padded = dec.update(binascii.unhexlify(enc_hex)) + dec.finalize()
    return json.loads(padded[:-padded[-1]].decode("utf-8"))


def encrypt_ucf(payload: dict, files_key: str) -> str:
    """Encrypt a payload dict into a UCF blob (iv_hex:ciphertext_hex)."""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import padding as crypto_padding
    except ImportError:
        print("error: cryptography package required for merge mode — run: pip install cryptography")
        sys.exit(1)

    key = _aes_key(files_key)
    plaintext = json.dumps(payload).encode("utf-8")
    new_iv = os.urandom(16)
    padder = crypto_padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    enc = Cipher(algorithms.AES(key), modes.CBC(new_iv), backend=default_backend()).encryptor()
    ciphertext = enc.update(padded) + enc.finalize()
    return new_iv.hex() + ":" + ciphertext.hex()


# ---------------------------------------------------------------------------
# Cross-environment merge logic
# ---------------------------------------------------------------------------

# GCP identity fields that must be preserved from the destination blob.
_IDENTITY_FIELDS = (
    "id", "name", "author", "tenant_id", "owner_project_user_id",
    "parent_template_dashboard", "workspace_id", "visibility",
    "organization_id", "created_at",
)


def _find_dashboard(tables: dict, dashboard_id: str) -> dict | None:
    for d in tables.get("dashboards", []):
        if d.get("id") == dashboard_id:
            return d
    return None


def merge_blobs(
    src_blob: str,
    src_dashboard_id: str,
    dst_blob: str,
    dst_dashboard_id: str,
    files_key: str,
) -> str:
    """
    Merge chart configs from src_dashboard_id (AWS) into dst_dashboard_id (GCP),
    preserving all GCP identity fields.  Returns the re-encrypted merged UCF blob.

    Matching strategy: charts are paired by name.  Charts present in the source
    but absent from the destination are imported as new charts (keeping their
    source IDs).  Charts present only in the destination are left untouched in
    the existing GCP dashboard — they are not included in the import blob.
    """
    src = decrypt_ucf(src_blob, files_key)
    dst = decrypt_ucf(dst_blob, files_key)

    src_dash = _find_dashboard(src["tables"], src_dashboard_id)
    dst_dash = _find_dashboard(dst["tables"], dst_dashboard_id)
    if not src_dash:
        print(f"error: dashboard {src_dashboard_id} not found in source blob")
        sys.exit(1)
    if not dst_dash:
        print(f"error: dashboard {dst_dashboard_id} not found in destination blob")
        sys.exit(1)

    src_chart_ids = set(src_dash["config"].get("charts", {}).keys())
    dst_chart_ids = set(dst_dash["config"].get("charts", {}).keys())

    # Build name → chart row maps
    src_charts_by_name = {c["name"]: c for c in src["tables"]["charts"]
                          if c["id"] in src_chart_ids}
    dst_charts_by_name = {c["name"]: c for c in dst["tables"]["charts"]
                          if c["id"] in dst_chart_ids}

    # Compute src→dst chart ID mapping for matched names
    src_to_dst: dict[str, str] = {}
    for name, sc in src_charts_by_name.items():
        if name in dst_charts_by_name:
            src_to_dst[sc["id"]] = dst_charts_by_name[name]["id"]
            print(f"  match  {name}: {sc['id'][:8]}… → {dst_charts_by_name[name]['id'][:8]}…")
        else:
            print(f"  new    {name}: {sc['id'][:8]}… (new chart in destination)")

    full_remap = {src_dashboard_id: dst_dashboard_id, **src_to_dst}

    def remap(obj):
        if isinstance(obj, str):
            return full_remap.get(obj, obj)
        if isinstance(obj, dict):
            return {remap(k): remap(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [remap(i) for i in obj]
        return obj

    # Filter source tables to only this dashboard's rows
    src_dv_sample = next(
        (r for r in src["tables"].get("dashboards_versioning", [])
         if r.get("id") == src_dashboard_id), {}
    )

    def build_dashes(rows):
        out = remap([r for r in rows if r.get("id") == src_dashboard_id])
        for row in out:
            for f in _IDENTITY_FIELDS:
                v = dst_dash.get(f)
                if v is not None:
                    row[f] = v
        return out

    def build_versioning(rows):
        out = remap([r for r in rows if r.get("id") == src_dashboard_id])
        dst_dv_sample = dst["tables"].get("dashboards_versioning", [{}])[0]
        for row in out:
            for f in _IDENTITY_FIELDS:
                if f == "id":
                    continue
                v = dst_dv_sample.get(f) or dst_dash.get(f)
                if v is not None:
                    row[f] = v
        return out

    merged_chart_ids_after_remap = {full_remap.get(i, i) for i in src_chart_ids}

    merged_tables = {
        "dashboards": build_dashes(src["tables"].get("dashboards", [])),
        "dashboards_versioning": build_versioning(src["tables"].get("dashboards_versioning", [])),
        "charts": remap([c for c in src["tables"].get("charts", [])
                         if c["id"] in src_chart_ids]),
        "charts_versioning": remap([c for c in src["tables"].get("charts_versioning", [])
                                    if c["id"] in src_chart_ids]),
        "chart_filters": remap([f for f in src["tables"].get("chart_filters", [])
                                 if f.get("parent_chart_id") in src_chart_ids]),
        "dashboard_filters": remap([f for f in src["tables"].get("dashboard_filters", [])
                                     if f.get("parent_dashboard_id") == src_dashboard_id]),
        # Preserve destination theme — avoids overwriting GCP visual customisations
        "dashboard_themes": dst["tables"].get("dashboard_themes", []),
    }

    merged = {
        "formatVersion": src["formatVersion"],
        "organizationId": src["organizationId"],
        "generatedAt":    src["generatedAt"],
        "tables":         merged_tables,
    }

    print(f"\nMerged payload:")
    for k, v in merged_tables.items():
        print(f"  {k}: {len(v)} rows")
    print(f"  dashboard id:               {merged_tables['dashboards'][0]['id']}")
    print(f"  parent_template_dashboard:  {merged_tables['dashboards'][0].get('parent_template_dashboard')}")
    print(f"  tenant_id:                  {merged_tables['dashboards'][0].get('tenant_id')}")

    return encrypt_ucf(merged, files_key)


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
        })

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def set_exportable(self, dashboard_ids: list[str], exportable: bool = True) -> dict:
        """Mark dashboards as exportable (or un-mark them)."""
        payload = {"dashboardIds": dashboard_ids, "isExportable": exportable, "apiKey": self.api_key}
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
            json={"apiKey": self.api_key},
            verify=self.verify_ssl,
        )
        resp.raise_for_status()
        try:
            body = resp.json()
            return body.get("data") or body
        except Exception:
            return resp.text  # UCF blob returned as raw text

    def import_dashboards(self, ucf_data: str) -> dict:
        """Import an encrypted .ucf blob into this environment."""
        resp = self.session.post(
            self._url("/v1/api/ucf/dashboards/import"),
            json={"data": ucf_data, "apiKey": self.api_key},
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

    merge = p.add_argument_group(
        "merge mode",
        "Export one dashboard from each environment, merge chart configs from source "
        "into destination (preserving all destination identity fields), then import back. "
        "Requires --src, --src-key, --dst, --dst-key, --src-dashboard-id, "
        "--dst-dashboard-id, and --files-key.",
    )
    merge.add_argument("--merge", action="store_true",
                       help="Enable merge mode")
    merge.add_argument("--src-dashboard-id", metavar="UUID",
                       help="Dashboard UUID to export from the source environment")
    merge.add_argument("--dst-dashboard-id", metavar="UUID",
                       help="Personal-workspace dashboard UUID in the destination (must already exist)")
    merge.add_argument("--files-key", default=None, metavar="HEX",
                       help="64-char hex FILES_KEY used by Upsolve for UCF encryption "
                            "(also: UPSOLVE_FILES_KEY env var)")
    merge.add_argument("--merged-file", metavar="PATH",
                       help="Save the merged .ucf blob to this file instead of importing")

    p.add_argument("--no-verify-ssl", action="store_true",
                   help="Disable SSL certificate verification (useful for self-signed certs)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would happen without making any API calls")

    return p.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.merge:
        missing = [f for f, v in [
            ("--src",              args.src),
            ("--src-key",         args.src_key),
            ("--src-dashboard-id", args.src_dashboard_id),
            ("--dst",              args.dst),
            ("--dst-key",         args.dst_key),
            ("--dst-dashboard-id", args.dst_dashboard_id),
            ("--files-key",       args.files_key),
        ] if not v]
        if missing:
            print(f"error: merge mode requires: {', '.join(missing)}")
            sys.exit(1)
        return

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
    args.files_key = args.files_key or os.getenv("UPSOLVE_FILES_KEY")

    validate_args(args)

    verify_ssl = not args.no_verify_ssl

    # ------------------------------------------------------------------
    # Merge mode: export src + dst, merge chart configs, import merged
    # ------------------------------------------------------------------
    if args.merge:
        src_client = UpsolveAdminClient(args.src, args.src_key, verify_ssl)
        dst_client = UpsolveAdminClient(args.dst, args.dst_key, verify_ssl)

        # 1. Export source dashboard
        print(f"Marking source dashboard {args.src_dashboard_id} as exportable on {args.src}")
        if not args.dry_run:
            src_client.set_exportable([args.src_dashboard_id])
        print(f"Exporting from {args.src}")
        if not args.dry_run:
            src_blob = src_client.export_dashboards()
            print(f"  source export succeeded — {len(str(src_blob))} chars")
            # Clear exportable flag on source to avoid accumulation
            src_client.set_exportable([args.src_dashboard_id], exportable=False)

        # 2. Export destination dashboard (clear all others first to avoid 500 on large orgs)
        print(f"\nClearing all exportable flags on {args.dst} to avoid payload-size errors")
        if not args.dry_run:
            # Mark only the target, then export, then clear
            dst_client.set_exportable([args.dst_dashboard_id])
        print(f"Exporting from {args.dst}")
        if not args.dry_run:
            dst_blob = dst_client.export_dashboards()
            print(f"  destination export succeeded — {len(str(dst_blob))} chars")
            dst_client.set_exportable([args.dst_dashboard_id], exportable=False)

        if args.dry_run:
            print("[dry-run] would merge blobs and import — re-run without --dry-run")
            return

        # 3. Merge
        print(f"\nMerging chart configs from {args.src_dashboard_id} → {args.dst_dashboard_id}")
        merged_blob = merge_blobs(
            src_blob=str(src_blob),
            src_dashboard_id=args.src_dashboard_id,
            dst_blob=str(dst_blob),
            dst_dashboard_id=args.dst_dashboard_id,
            files_key=args.files_key,
        )

        if args.merged_file:
            with open(args.merged_file, "w") as f:
                f.write(merged_blob)
            print(f"\nSaved merged blob to {args.merged_file} — skipping import.")
            return

        # 4. Import merged blob into destination
        print(f"\nImporting merged blob into {args.dst}")
        result = dst_client.import_dashboards(merged_blob)
        print(f"  import response: {json.dumps(result, indent=2)}")
        print("Done.")
        return

    # Resolve friendly names → UUIDs if a map was provided
    if args.dashboard_ids:
        name_map = load_dashboard_map(args.dashboard_map)
        args.dashboard_ids = resolve_dashboard_ids(args.dashboard_ids, name_map)

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
