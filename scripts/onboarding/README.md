# Model Onboarding Package

Complete set of scripts and documentation for onboarding models to Arthur platform using AWS S3.

## Quick Start

```bash
# 1. Install dependencies
pip install arthur-client

# 2. Configure model-onboarding.py with your AWS and Arthur credentials

# 3. Run onboarding
python model-onboarding.py

# 4. Add fraud-specific metrics (for card fraud models)
python add-fraud-model-aggregations.py
```

## 📁 Package Contents

### Main Scripts
- **[model-onboarding.py](model-onboarding.py)** - Complete S3-to-Arthur onboarding (connector, dataset, model, schedule)
- **[add-fraud-model-aggregations.py](../add-fraud-model-aggregations.py)** - 15 fraud-specific metrics including positive-class error profile
- **[add-custom-aggregations.py](../add-custom-aggregations.py)** - Template for adding custom metrics to any model

### Utility Scripts
- **[service-account-creation.py](service-account-creation.py)** - Create service accounts for automation
- **[using-sdk-with-service-account-creds.py](using-sdk-with-service-account-creds.py)** - Service account authentication example
- **[add-column-to-schema.py](add-column-to-schema.py)** - Add columns to dataset schema
- **[remove-column-from-schema.py](remove-column-from-schema.py)** - Remove columns from dataset schema
- **[add-prediction-stats-metrics.py](add-prediction-stats-metrics.py)** - Add prediction sum/distribution metrics
- **[duplicate-metrics-to-new-datasets.py](duplicate-metrics-to-new-datasets.py)** - Copy metrics between datasets

### Documentation
- **[AGGREGATIONS_REFERENCE.md](AGGREGATIONS_REFERENCE.md)** - Complete reference for all 27 aggregation types

---

## Prerequisites

1. **Arthur Project**: Create a project in the Arthur UI and note its ID
2. **AWS S3 Access**: One of:
   - AWS Access Key ID and Secret Access Key
   - IAM Role ARN for role assumption (recommended for production)
3. **S3 Bucket**: Model inference data in JSON, Parquet, or CSV format
4. **Python**: Python 3.8+ with `arthur-client` installed

---

## Configuration Guide

### 1. Basic Setup (model-onboarding.py)

```python
# Arthur Configuration
ARTHUR_HOST = "https://platform.arthur.ai"
ARTHUR_PROJECT_ID = "YOUR_PROJECT_ID_HERE"  # From Arthur UI
DATA_PLANE_ID = None  # Optional: Set explicitly if you have multiple data planes

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = "YOUR_AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "YOUR_AWS_SECRET_ACCESS_KEY"
AWS_REGION = "us-east-1"
S3_BUCKET = "your-ml-data-bucket"
S3_FILE_PREFIX = "model-inferences/%Y%m%d/"  # Daily partitions
S3_FILE_SUFFIX = ".*.json"  # Match all .json files
S3_FILE_TYPE = "json"  # Options: json, parquet, csv

# Model Configuration
MODEL_NAME = "your-model-name"
TIMESTAMP_COLUMN_NAME = "timestamp"
```

### 2. File Format Configuration

**JSON** (human-readable, flexible):
```python
S3_FILE_TYPE = "json"
S3_FILE_SUFFIX = ".*.json"
```

**Parquet** (efficient, 10x compression):
```python
S3_FILE_TYPE = "parquet"
S3_FILE_SUFFIX = ".*\\.parquet$"
```

**CSV** (legacy systems, Excel-compatible):
```python
S3_FILE_TYPE = "csv"
S3_FILE_SUFFIX = ".*\\.csv$"

# Add to dataset_locator if needed:
DatasetLocatorField(key="delimiter", value=","),  # or "|", "\\t"
DatasetLocatorField(key="has_header", value="true"),
DatasetLocatorField(key="encoding", value="utf-8"),
```

### 3. S3 Authentication Options

**Option A: Access Keys** (simpler, less secure):
```python
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/..."
```

**Option B: IAM Role** (recommended for production):
```python
AWS_ROLE_ARN = "arn:aws:iam::123456789012:role/ArthurDataAccessRole"
AWS_EXTERNAL_ID = "arthur-external-id"  # Optional security
AWS_ROLE_DURATION_SECONDS = 3600
```

**Option C: Custom S3 Endpoint** (MinIO, on-premises):
```python
S3_ENDPOINT = "https://s3.company.internal"
```

### 4. S3 Connector Fields Reference

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `bucket` | ✓ | S3 bucket name | `"your-ml-data-bucket"` |
| `access_key_id` | * | AWS access key | `"AKIAIOSFODNN7..."` |
| `secret_access_key` | * | AWS secret | `"wJalrXUtnFEMI..."` |
| `role_arn` | * | IAM role ARN | `"arn:aws:iam::..."` |
| `region` |  | AWS region | `"us-east-1"` |
| `external_id` |  | Role external ID | `"arthur-123"` |
| `endpoint` |  | Custom S3 endpoint | `"https://s3.company.com"` |

\* Required: Either (`access_key_id` + `secret_access_key`) OR `role_arn`

### 5. File Path Patterns

The `S3_FILE_PREFIX` supports strftime formatting for date partitioning:

| Pattern | Result | Description |
|---------|--------|-------------|
| `"data/%Y%m%d/"` | `"data/20240101/"` | Daily partitions |
| `"logs/%Y/%m/%d/"` | `"logs/2024/01/01/"` | Nested daily |
| `"inferences/%Y/%m/%d/%H/"` | `"inferences/2024/01/01/14/"` | Hourly |
| `"model-v1/%Y-W%U/"` | `"model-v1/2024-W01/"` | Weekly |

The `S3_FILE_SUFFIX` is a regex pattern:

| Pattern | Matches | Description |
|---------|---------|-------------|
| `".*.json"` | Any `.json` file | Simple suffix |
| `".*\\.json$"` | Any `.json` file | Anchored (recommended) |
| `"predictions.*\\.json$"` | `predictions_001.json` | Prefix + suffix |
| `"data_[0-9]{8}\\.csv$"` | `data_20240101.csv` | Date in filename |

---

## S3 Data Structure

### Expected S3 Layout

```
s3://your-ml-data-bucket/
  model-inferences/
    20240101/
      predictions_000.json
      predictions_001.json
    20240102/
      predictions_000.json
```

### Required Data Schema

Your inference data must include:
- **Timestamp column** - For time-based filtering and metrics (ISO 8601 format recommended)
- **Model predictions** - Scores, classifications, or probability values
- **Ground truth** (optional) - For accuracy metrics
- **Input features** (optional) - For drift detection

**Example JSON:**
```json
[
  {
    "timestamp": "2024-01-01T00:00:00Z",
    "fraud_score": 0.95,
    "is_fraud": 1,
    "distance_from_home_km": 1250.5,
    "customer_segment": "premium"
  }
]
```

---

## Usage Instructions

### Initial Model Onboarding

```bash
# 1. Edit model-onboarding.py with your configuration
# 2. Run the script
python model-onboarding.py
```

The script will:
1. ✓ Create/retrieve S3 connector
2. ✓ Create available dataset
3. ✓ Run schema inspection (samples S3 files)
4. ✓ Create dataset with inferred schema
5. ✓ Create model with basic metrics
6. ✓ Set up hourly refresh schedule

### Adding Fraud Model Metrics

For card fraud models with columns like `fraud_score`, `is_fraud`, `distance_from_home_km`, etc:

```bash
# Edit add-fraud-model-aggregations.py with MODEL_ID
python add-fraud-model-aggregations.py
```

This adds 15 aggregations:
- Numeric distributions (fraud_score, is_fraud, distance_from_home_km, tenure_months)
- Category counts (customer_segment, channel, region, risk_rank)
- Binary classification metrics (fraud vs not-fraud)
- Positive-class error profile (TP/FP/TN/FN confusion matrix)
- Data quality checks (nullable counts)

### Adding Custom Metrics

For other model types:

```bash
# Edit add-custom-aggregations.py with MODEL_ID and column names
python add-custom-aggregations.py
```

Customize the `gen_custom_aggregations()` function with your specific columns and metrics.

### Creating Service Accounts

For automation and CI/CD:

```bash
python service-account-creation.py
```

**Important**: Save the client ID and secret - they're shown only once!

---

## Authentication

### Browser-Based (Interactive)

Default for all scripts:
```python
from arthur_client.auth import DeviceAuthorizer
sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
```

Opens browser for authentication.

### Service Account (Automation)

For scripts and CI/CD:
```python
from arthur_client.auth import ArthurClientCredentialsAPISession, ArthurOIDCMetadata
sess = ArthurClientCredentialsAPISession(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    metadata=ArthurOIDCMetadata(arthur_host=ARTHUR_HOST),
)
```

See [using-sdk-with-service-account-creds.py](using-sdk-with-service-account-creds.py) for example.

---

## Utility Scripts

### Schema Management

**Add Column to Dataset** ([add-column-to-schema.py](add-column-to-schema.py)):
```bash
# When data source adds a new field
python add-column-to-schema.py
```
Supports: `DType.INT`, `DType.FLOAT`, `DType.STRING`, `DType.BOOL`, `DType.TIMESTAMP`

**Remove Column from Dataset** ([remove-column-from-schema.py](remove-column-from-schema.py)):
```bash
# When field is deprecated
python remove-column-from-schema.py
```
⚠️ Warning: Remove affected metrics first!

### Metrics Management

**Add Prediction Stats** ([add-prediction-stats-metrics.py](add-prediction-stats-metrics.py)):
```bash
# Adds sum and distribution of predictions
python add-prediction-stats-metrics.py
```
Auto-skips duplicates, preserves existing metrics.

**Duplicate Metrics to New Datasets** ([duplicate-metrics-to-new-datasets.py](duplicate-metrics-to-new-datasets.py)):
```bash
# Copy metrics when migrating datasets
python duplicate-metrics-to-new-datasets.py
```
Smart column mapping by name, handles removed columns gracefully.

---

## Troubleshooting

### Schema Inspection Fails

**Symptoms**: "No files found" or "Invalid schema"

**Solutions**:
- ✓ Check S3 permissions: `s3:ListBucket`, `s3:GetObject`
- ✓ Verify `S3_FILE_PREFIX` matches S3 structure exactly
- ✓ Ensure `S3_FILE_SUFFIX` regex matches your filenames
- ✓ Check `S3_FILE_TYPE` matches actual file format
- ✓ Verify files exist in the date range Arthur is sampling

### Connector Creation Fails

**Symptoms**: "Invalid credentials" or "Access denied"

**Solutions**:
- ✓ Verify AWS credentials are correct
- ✓ Check bucket exists and is in correct region
- ✓ Ensure IAM permissions include S3 read access
- ✓ For role assumption: verify trust relationship

### Data Plane Not Associated with Project

**Symptoms**: "Data plane ... is not associated with project ..."

**Cause**: The Arthur API doesn't expose the project-to-data-plane relationship, so the script cannot automatically select the correct data plane if multiple exist in your workspace.

**Solutions**:
1. ✓ Log into Arthur UI at `https://platform.arthur.ai`
2. ✓ Navigate to your project and find the associated data plane ID
3. ✓ Set `DATA_PLANE_ID` at the top of [model-onboarding.py](model-onboarding.py):
   ```python
   DATA_PLANE_ID = "12345678-1234-1234-1234-123456789012"  # Your data plane ID
   ```
4. ✓ Alternatively, ask your Arthur admin to associate your project with the data plane

### Timestamp Column Not Found

**Symptoms**: "Column 'timestamp' not found"

**Solutions**:
- ✓ Verify `TIMESTAMP_COLUMN_NAME` matches actual column name (case-sensitive)
- ✓ Use ISO 8601 format: `"2024-01-01T00:00:00Z"`
- ✓ Check timezone configuration matches your data

### Metrics Not Appearing

**Symptoms**: Metrics don't show up in Arthur UI

**Solutions**:
- ✓ Verify column IDs match dataset schema
- ✓ Check aggregation IDs are valid (see [AGGREGATIONS_REFERENCE.md](AGGREGATIONS_REFERENCE.md))
- ✓ Ensure data exists in the time range Arthur is querying
- ✓ Check Arthur activity log for detailed errors

### Performance Issues

**Symptoms**: Slow data loading or timeouts

**Solutions**:
- ✓ Switch from JSON/CSV to Parquet (10x compression)
- ✓ Increase file prefix granularity (daily → hourly)
- ✓ Use more specific `file_suffix` regex
- ✓ Enable gzip compression for JSON/CSV files

---

## Best Practices

### Security
- ✅ Use IAM roles instead of access keys in production
- ✅ Store credentials in AWS Secrets Manager or similar
- ✅ Use service accounts for automation, not personal credentials
- ✅ Rotate credentials regularly
- ✅ Use external ID for role assumption security

### Configuration
- ✅ Use environment variables for sensitive values
- ✅ Keep configuration in version control (without secrets)
- ✅ Document any custom aggregations in comments
- ✅ Test on staging environment first

### Data
- ✅ Use Parquet for large datasets (>1GB/day)
- ✅ Partition by day or hour for efficient queries
- ✅ Use ISO 8601 timestamps with timezone
- ✅ Include ground truth when available for accuracy metrics
- ✅ Validate schema changes before applying

### Metrics
- ✅ Start with basic metrics (inference count, distributions)
- ✅ Add fraud-specific metrics for fraud models
- ✅ Use named aggregations for important metrics
- ✅ Set up alerts for critical metrics (FPR, recall, accuracy)
- ✅ Review and clean up unused metrics periodically

---

## Support & Resources

- **Arthur Documentation**: https://docs.arthur.ai
- **API Reference**: Check your Arthur host + `/api/v1/docs`
- **Aggregations Reference**: [AGGREGATIONS_REFERENCE.md](AGGREGATIONS_REFERENCE.md)
- **Arthur Support**: Contact your Arthur representative

---

## Migration from GCS

Key differences when adapting from GCS:

| Aspect | GCS | S3 |
|--------|-----|-----|
| Connector Type | `ConnectorType.GCS` | `ConnectorType.S3` |
| Auth Field | `credentials` (JSON) | `access_key_id` + `secret_access_key` OR `role_arn` |
| Required Fields | `bucket`, `project_id` | `bucket`, `region` |
| Optional Fields | N/A | `endpoint`, `external_id`, `duration_seconds` |

All other aspects (dataset locators, schema inspection, metrics) work identically.
