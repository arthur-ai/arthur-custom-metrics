# Upsolve Dashboard Sync

Promote dashboards between Upsolve environments using the UCF admin endpoints.

## How it works

1. **Mark exportable** — flags the target dashboard(s) as exportable in the source DB
2. **Export** — downloads an encrypted `.ucf` blob from the source
3. **Import** — upserts the blob into the destination (idempotent, safe to re-run)

## Prerequisites

```bash
pip install requests python-dotenv
```

The source Upsolve must be reachable. If it is on an internal AWS ALB, run from within the VPC via SSM:

```bash
aws ssm start-session --target <ec2-instance-id> --profile <aws-profile>
```

## Usage

```bash
# Full sync (export from src, import to dst)
python upsolve-dashboard-sync.py \
  --src  <src-host> \
  --dst  <dst-host> \
  --src-key <SKELETON_KEY_SRC> \
  --dst-key <SKELETON_KEY_DST> \
  --dashboard-ids <UUID1> [<UUID2> ...]

# Export only — save blob to disk
python upsolve-dashboard-sync.py \
  --src <src-host> --src-key <key> \
  --dashboard-ids <UUID> \
  --export-file dashboards.ucf

# Import only — load blob from disk
python upsolve-dashboard-sync.py \
  --dst <dst-host> --dst-key <key> \
  --import-file dashboards.ucf

# Use friendly names instead of raw UUIDs
python upsolve-dashboard-sync.py \
  --src <src-host> --dst <dst-host> \
  --src-key <key> --dst-key <key> \
  --dashboard-map dashboard-ids.json \
  --dashboard-ids fraud-overview
```

## Configuration

Copy `.env.example` to `.env` and fill in values. The script loads `.env` automatically.

| Env var | Flag | Description |
|---------|------|-------------|
| `UPSOLVE_SRC_HOST` | `--src` | Source Upsolve base URL |
| `UPSOLVE_DST_HOST` | `--dst` | Destination Upsolve base URL |
| `UPSOLVE_SRC_API_KEY` | `--src-key` | SKELETON_KEY for source |
| `UPSOLVE_DST_API_KEY` | `--dst-key` | SKELETON_KEY for destination |
| `UPSOLVE_DASHBOARD_MAP` | `--dashboard-map` | Path to name→UUID JSON map |

The SKELETON_KEY for each environment is stored in its secrets manager:
- **AWS**: Secrets Manager → `platform-v4-infra-upsolve-api-key-dev`
- **GCP**: Secret Manager → `uplsolve_skeleton_key` *(note: typo in secret name)*

## Dashboard map

To use friendly names instead of raw UUIDs, create a `dashboard-ids.json`:

```json
{
  "fraud-overview": "11111111-aaaa-...",
  "risk-summary":   "22222222-bbbb-..."
}
```

To find a dashboard UUID: open the dashboard → Actions menu → **Copy dashboard ID**.

## ⚠️ Export size limit for Cloud Run destinations

The export endpoint returns **all** dashboards with `is_exportable = true`, not just the ones passed via `--dashboard-ids`. If many dashboards are already marked exportable the blob can easily exceed **32 MB**, which Cloud Run will reject with a 413.

Before exporting, un-mark all other exportable dashboards in the source Postgres DB:

```sql
UPDATE dashboards
SET is_exportable = false
WHERE is_exportable = true AND id != '<your-dashboard-id>';

UPDATE dashboards_versioning
SET is_exportable = false
WHERE is_exportable = true AND id != '<your-dashboard-id>';
```

Keep the export blob under ~30 MB. If it still exceeds this, use the [GCS import workflow](gcs-import/README.md).

## ⚠️ GCP destination: Postgres REPLICATION privilege

The import runs `SET LOCAL session_replication_role = 'replica'` to preserve exact IDs during upsert. The Upsolve DB user must have the `REPLICATION` privilege. If the import returns a 500 with `permission denied to set parameter "session_replication_role"`, grant it via the postgres superuser:

```sql
ALTER ROLE <upsolve-db-user> REPLICATION;
```

For GCP Cloud SQL, connect via:
```bash
gcloud beta sql connect <instance-name> --user=postgres --project=<project-id>
```

## Large blobs (>30 MB)

Use the [GCS import workflow](gcs-import/README.md) which uploads the blob to GCS and runs a Cloud Run Job to import — bypassing the 32 MB HTTP request body limit.
