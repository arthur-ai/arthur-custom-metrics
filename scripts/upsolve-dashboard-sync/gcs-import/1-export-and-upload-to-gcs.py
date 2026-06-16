"""
Step 1: Export UCF blob from source Upsolve and upload to GCS.

Run this from inside the AWS VPC (SSM session on EC2) because the source
Upsolve is on an internal ALB not reachable from the public internet.

Usage (from EC2 SSM session):
    pip3 install requests
    python3 1-export-and-upload-to-gcs.py

Required env vars (or edit the constants below):
    UPSOLVE_SRC_HOST       e.g. https://internal-platform-v4-scope-alb-dev-...amazonaws.com
    UPSOLVE_SRC_API_KEY    Upsolve SKELETON_KEY for the source environment
    UPSOLVE_DASHBOARD_IDS  Comma-separated dashboard UUIDs to mark exportable
    GCS_BUCKET             GCS bucket name
    GCS_BLOB               GCS object path (e.g. upsolve-sync/dashboard.ucf)
    GCS_UPLOAD_URL         Presigned GCS PUT URL (generate with: gsutil signurl ...)
                           OR leave blank and set GOOGLE_APPLICATION_CREDENTIALS
                           to use the ADC-based upload path.
"""

import os
import sys
import json
import urllib.request
import urllib.error

import requests

# ---------------------------------------------------------------------------
# Config — override via env vars or edit here
# ---------------------------------------------------------------------------

SRC_HOST    = os.getenv("UPSOLVE_SRC_HOST", "https://internal-platform-v4-scope-alb-dev-596696974.us-east-2.elb.amazonaws.com")
SRC_API_KEY = os.getenv("UPSOLVE_SRC_API_KEY", "bh7fIUvdbTFQbyM8")
DASHBOARD_IDS = [d.strip() for d in os.getenv("UPSOLVE_DASHBOARD_IDS", "11208a00-4557-44c3-9d79-cf3ffb95525d").split(",")]
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
