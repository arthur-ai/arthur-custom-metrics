# Upsolve Dashboard Sync — GCS Import Workflow

Use this workflow when the UCF blob is **larger than 32 MB** and cannot be
POSTed directly to a Cloud Run–hosted Upsolve instance (Cloud Run enforces a
32 MB HTTP request body limit).

The approach:
1. Export the UCF blob from the source Upsolve (inside the AWS VPC) and upload it to GCS.
2. A Cloud Run Job reads the blob from GCS and imports it into the destination Upsolve — avoiding the HTTP body size constraint entirely.

---

## Prerequisites

| Tool | Purpose |
|------|---------|
| Python 3.7+ + `requests` | Step 1 (EC2 SSM session) |
| Docker | Step 2 (local build) |
| `gcloud` CLI, authenticated | Step 2 (deploy + run) |
| AWS SSM session on `i-0848d9fab1987fb01` | Step 1 (VPC access to source Upsolve) |

---

## Step 1 — Export from source and upload to GCS

Run from inside an **AWS SSM session** (source Upsolve is on an internal ALB):

```bash
aws ssm start-session --target i-0848d9fab1987fb01 --profile dev
```

Inside the session:

```bash
cd /tmp
pip3 install requests

# Download script
curl -s https://raw.githubusercontent.com/arthur-ai/arthur-custom-metrics/main/scripts/upsolve-dashboard-sync/gcs-import/1-export-and-upload-to-gcs.py > 1-export-and-upload-to-gcs.py

# Generate a GCS presigned PUT URL locally (run this on your laptop):
#   python3 -c "
#   from google.cloud import storage
#   client = storage.Client(project='aa-cp-npr-01')
#   bucket = client.bucket('scope-artifacts-dev')
#   blob = bucket.blob('upsolve-sync/dashboard.ucf')
#   url = blob.generate_signed_url(expiration=3600, method='PUT')
#   print(url)
#   "
# Then paste the URL into the session:

export GCS_UPLOAD_URL='<presigned-PUT-url>'
export UPSOLVE_DASHBOARD_IDS='11208a00-4557-44c3-9d79-cf3ffb95525d'

python3 1-export-and-upload-to-gcs.py
```

The script will:
- Mark the dashboard(s) as exportable
- Export the UCF blob
- Save it to `/tmp/dashboard.ucf`
- Upload it to `gs://scope-artifacts-dev/upsolve-sync/dashboard.ucf`

---

## Step 2 — Deploy and run the Cloud Run import job

Run from your **local machine**:

```bash
cd scripts/upsolve-dashboard-sync/gcs-import

# Authenticate
gcloud auth login
gcloud config set project aa-cp-npr-01

# Run (builds image, pushes, deploys job, executes it, waits for completion)
./2-deploy-and-run-import-job.sh
```

### What the job does

1. Downloads `gs://scope-artifacts-dev/upsolve-sync/dashboard.ucf` to local disk inside the container.
2. Attempts to POST the blob to the Upsolve HTTP import endpoint.
3. If the blob exceeds 32 MB and the HTTP import returns 413, falls back to **direct PostgreSQL import** using `UPSOLVE_DST_CONN_URL`.

### Environment variable overrides

| Variable | Default | Description |
|----------|---------|-------------|
| `GCS_BUCKET` | `scope-artifacts-dev` | GCS bucket |
| `GCS_BLOB` | `upsolve-sync/dashboard.ucf` | GCS object path |
| `UPSOLVE_DST_HOST` | GCP Cloud Run URL | Destination Upsolve base URL |
| `UPSOLVE_DST_API_KEY` | fetched from Secret Manager | SKELETON_KEY for destination |
| `UPSOLVE_DST_CONN_URL` | fetched from Secret Manager | Postgres connection URL (fallback) |
| `UPSOLVE_FILES_KEY` | *(required for DB fallback)* | AES key used to encrypt the UCF blob |

---

## Getting UPSOLVE_FILES_KEY (DB import fallback only)

`FILES_KEY` is the AES encryption key Upsolve uses when writing `.ucf` blobs.
Both environments **must share the same key** for the import to succeed.

Since it is not stored as an environment variable in either deployment, it is
likely hardcoded in the Upsolve application. To retrieve it:

1. Pull the Upsolve image locally:
   ```bash
   docker pull us-central1-docker.pkg.dev/aa-cp-npr-01/arthur-docker-hub-enterprise-proxy/arthuraiplatform/upsolve:0.0.8-lts
   ```
2. Inspect the image config or run a shell:
   ```bash
   docker run --rm -it --entrypoint sh \
     us-central1-docker.pkg.dev/aa-cp-npr-01/arthur-docker-hub-enterprise-proxy/arthuraiplatform/upsolve:0.0.8-lts \
     -c 'grep -r FILES_KEY /app || env | grep FILES'
   ```
3. Set it as `UPSOLVE_FILES_KEY` before running step 2.

---

## Checking job logs

```bash
gcloud logging read \
  'resource.type=cloud_run_job AND resource.labels.job_name=upsolve-import-job' \
  --project=aa-cp-npr-01 --limit=50 --format='value(textPayload)'
```
