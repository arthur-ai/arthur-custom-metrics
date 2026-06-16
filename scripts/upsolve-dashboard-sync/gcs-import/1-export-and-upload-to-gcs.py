"""Step 1 of the GCS import workflow — see gcs-import/README.md."""

import os
import sys
import json
import urllib.request
import urllib.error

import requests

# ---------------------------------------------------------------------------
# Config — override via env vars or edit here
# ---------------------------------------------------------------------------

SRC_HOST    = os.getenv("UPSOLVE_SRC_HOST", "")
SRC_API_KEY = os.getenv("UPSOLVE_SRC_API_KEY", "")
DASHBOARD_IDS = [d.strip() for d in os.getenv("UPSOLVE_DASHBOARD_IDS", "").split(",") if d.strip()]
GCS_UPLOAD_URL = os.getenv("GCS_UPLOAD_URL", "")   # presigned PUT URL
GCS_BUCKET     = os.getenv("GCS_BUCKET", "scope-artifacts-dev")
GCS_BLOB       = os.getenv("GCS_BLOB", "upsolve-sync/dashboard.ucf")
VERIFY_SSL     = os.getenv("VERIFY_SSL", "false").lower() != "false"
LOCAL_UCF_PATH = os.getenv("LOCAL_UCF_PATH", "/tmp/dashboard.ucf")


def upsolve_post(path, payload):
    resp = requests.post(
        SRC_HOST.rstrip("/") + path,
        json=payload,
        verify=VERIFY_SSL,
    )
    resp.raise_for_status()
    return resp


def main():
    if not SRC_HOST or not SRC_API_KEY or not DASHBOARD_IDS:
        print("ERROR: UPSOLVE_SRC_HOST, UPSOLVE_SRC_API_KEY, and UPSOLVE_DASHBOARD_IDS must be set.")
        sys.exit(1)

    # 1. Mark dashboards as exportable
    print(f"Marking {len(DASHBOARD_IDS)} dashboard(s) as exportable on {SRC_HOST}")
    result = upsolve_post(
        "/v1/api/ucf/dashboards/set-exportable",
        {"dashboardIds": DASHBOARD_IDS, "isExportable": True, "apiKey": SRC_API_KEY},
    )
    print("  set-exportable:", result.json())

    # 2. Export
    print(f"Exporting dashboards from {SRC_HOST}")
    resp = upsolve_post(
        "/v1/api/ucf/dashboards/export",
        {"apiKey": SRC_API_KEY},
    )
    try:
        body = resp.json()
        ucf_data = body.get("data") or body
        if isinstance(ucf_data, dict):
            ucf_data = json.dumps(ucf_data)
    except Exception:
        ucf_data = resp.text

    if not ucf_data:
        print("ERROR: empty export response")
        sys.exit(1)

    print(f"  export succeeded — blob length: {len(str(ucf_data))} chars")

    # 3. Save locally
    blob_bytes = ucf_data.encode() if isinstance(ucf_data, str) else ucf_data
    with open(LOCAL_UCF_PATH, "wb") as f:
        f.write(blob_bytes)
    print(f"  saved to {LOCAL_UCF_PATH}")

    # 4. Upload to GCS
    if GCS_UPLOAD_URL:
        print(f"Uploading to GCS via presigned URL...")
        req = urllib.request.Request(GCS_UPLOAD_URL, data=blob_bytes, method="PUT")
        try:
            urllib.request.urlopen(req)
            print(f"  uploaded to gs://{GCS_BUCKET}/{GCS_BLOB}")
        except urllib.error.HTTPError as e:
            print(f"  upload failed: {e.code} {e.reason}")
            sys.exit(1)
    else:
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(GCS_BUCKET)
            blob = bucket.blob(GCS_BLOB)
            blob.upload_from_string(blob_bytes)
            print(f"  uploaded to gs://{GCS_BUCKET}/{GCS_BLOB}")
        except ImportError:
            print("  google-cloud-storage not installed and no GCS_UPLOAD_URL set.")
            print(f"  UCF saved locally to {LOCAL_UCF_PATH} — upload manually.")

    print("\nDone. Next step: run 2-deploy-and-run-import-job.sh")


if __name__ == "__main__":
    main()
