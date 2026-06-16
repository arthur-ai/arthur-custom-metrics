"""Cloud Run Job for the GCS import workflow — see gcs-import/README.md."""

import os
import sys
import json
import tempfile

import requests
from google.cloud import storage

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GCS_BUCKET      = os.environ["GCS_BUCKET"]
GCS_BLOB        = os.environ["GCS_BLOB"]
DST_HOST        = os.environ["UPSOLVE_DST_HOST"].rstrip("/")
DST_API_KEY     = os.environ["UPSOLVE_DST_API_KEY"]
DST_CONN_URL    = os.environ.get("UPSOLVE_DST_CONN_URL", "")
VERIFY_SSL      = os.environ.get("VERIFY_SSL", "true").lower() == "true"
LOCAL_UCF_PATH  = os.environ.get("LOCAL_UCF_PATH", "/tmp/dashboard.ucf")


def download_from_gcs():
    print(f"Downloading gs://{GCS_BUCKET}/{GCS_BLOB} ...")
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB)
    blob.download_to_filename(LOCAL_UCF_PATH)
    size = os.path.getsize(LOCAL_UCF_PATH)
    print(f"  downloaded {size / 1024 / 1024:.1f} MB to {LOCAL_UCF_PATH}")


def import_via_http(ucf_data: str) -> bool:
    """Try importing via Upsolve HTTP API. Returns True on success."""
    print(f"Importing into {DST_HOST} via HTTP ...")
    try:
        resp = requests.post(
            f"{DST_HOST}/v1/api/ucf/dashboards/import",
            json={"data": ucf_data, "apiKey": DST_API_KEY},
            verify=VERIFY_SSL,
            timeout=300,
        )
        if resp.status_code == 413:
            print(f"  HTTP 413 — payload too large for Cloud Run ({len(ucf_data)//1024//1024} MB). Falling back to direct DB import.")
            return False
        resp.raise_for_status()
        print(f"  import response: {resp.json()}")
        return True
    except requests.exceptions.HTTPError as e:
        if "413" in str(e):
            return False
        raise


def import_via_postgres(ucf_data: str):
    """
    Direct PostgreSQL import fallback.

    The Upsolve import endpoint performs an upsert transaction with
    session_replication_role = 'replica', which preserves exact IDs
    and skips version-reassign triggers. This function replicates that
    behaviour using psycopg2.

    Requires:
      - UPSOLVE_DST_CONN_URL env var with a valid Postgres connection string
      - The UCF blob to be decryptable (requires FILES_KEY — see README)
    """
    if not DST_CONN_URL:
        print("ERROR: UPSOLVE_DST_CONN_URL is not set. Cannot fall back to direct DB import.")
        print("       Set this env var to the Postgres connection URL for the destination Upsolve DB.")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed. Add it to requirements.txt and rebuild the image.")
        sys.exit(1)

    # The UCF blob is AES-encrypted with FILES_KEY. Decryption is required
    # before we can parse and upsert the dashboard rows.
    # See README for instructions on obtaining FILES_KEY.
    files_key = os.environ.get("UPSOLVE_FILES_KEY", "")
    if not files_key:
        print("ERROR: UPSOLVE_FILES_KEY is not set. Cannot decrypt the UCF blob.")
        print("       Obtain FILES_KEY from the Upsolve deployment config and set this env var.")
        sys.exit(1)

    print("Decrypting UCF blob ...")
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        import binascii

        iv_hex, encrypted_hex = ucf_data.strip().split(":", 1)
        iv = binascii.unhexlify(iv_hex)
        encrypted = binascii.unhexlify(encrypted_hex)
        key = files_key.encode()[:32].ljust(32, b"\0")

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()
        # Remove PKCS7 padding
        pad_len = padded[-1]
        decrypted = padded[:-pad_len]
        data = json.loads(decrypted.decode("utf-8"))
    except Exception as e:
        print(f"ERROR: decryption failed: {e}")
        print("       Check that UPSOLVE_FILES_KEY is correct.")
        sys.exit(1)

    print(f"  decrypted {len(json.dumps(data))} chars of JSON")
    print("Connecting to destination Postgres ...")

    conn = psycopg2.connect(DST_CONN_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SET session_replication_role = 'replica';")

                dashboards = data.get("dashboards", [])
                print(f"  upserting {len(dashboards)} dashboard(s) ...")

                for dashboard in dashboards:
                    cur.execute(
                        """
                        INSERT INTO dashboards (id, organization_id, display_name, is_exportable, created_at, updated_at)
                        VALUES (%(id)s, %(organization_id)s, %(display_name)s, %(is_exportable)s, %(created_at)s, %(updated_at)s)
                        ON CONFLICT (id) DO UPDATE SET
                            display_name = EXCLUDED.display_name,
                            is_exportable = EXCLUDED.is_exportable,
                            updated_at = EXCLUDED.updated_at
                        """,
                        dashboard,
                    )

                for table in ("dashboards_versioning", "dashboard_themes"):
                    rows = data.get(table, [])
                    print(f"  upserting {len(rows)} {table} row(s) ...")
                    for row in rows:
                        cols = ", ".join(row.keys())
                        vals = ", ".join(f"%({k})s" for k in row.keys())
                        updates = ", ".join(f"{k} = EXCLUDED.{k}" for k in row.keys() if k != "id")
                        cur.execute(
                            f"""
                            INSERT INTO {table} ({cols}) VALUES ({vals})
                            ON CONFLICT (id) DO UPDATE SET {updates}
                            """,
                            row,
                        )

                cur.execute("SET session_replication_role = 'origin';")
        print("  direct DB import complete.")
    finally:
        conn.close()


def main():
    download_from_gcs()

    with open(LOCAL_UCF_PATH) as f:
        ucf_data = f.read()

    success = import_via_http(ucf_data)
    if not success:
        import_via_postgres(ucf_data)

    print("\nDone.")


if __name__ == "__main__":
    main()
