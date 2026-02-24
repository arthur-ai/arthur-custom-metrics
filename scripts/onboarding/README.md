# Arthur Platform — Onboarding Scripts

Complete reference for all scripts that connect data sources to Arthur, configure model metrics, manage schemas, and migrate configurations between environments.

---

## All Scripts at a Glance

| Script | Category | Purpose |
|--------|----------|---------|
| [model-onboarding.py](#model-onboardingpy) | Onboarding | Full S3 → Arthur onboarding for binary classification models |
| [housing-price-onboarding.py](#housing-price-onboardingpy) | Onboarding | Full S3 → Arthur onboarding for regression models |
| [add-fraud-model-aggregations.py](#add-fraud-model-aggregationspy) | Metrics | Domain-specific metrics for card fraud binary classification |
| [add-regression-model-aggregations.py](#add-regression-model-aggregationspy) | Metrics | Domain-specific metrics for regression models |
| [add-custom-aggregations.py](#add-custom-aggregationspy) | Metrics | Generic template for adding built-in metrics to any model |
| [add-prediction-stats-metrics.py](#add-prediction-stats-metricspy) | Metrics | Add prediction sum and distribution to any model |
| [create-positive-class-error-profile.py](#create-positive-class-error-profilepy) | Custom SQL | Binary classification error analysis (7 metrics via custom SQL) |
| [create-regression-error-profile.py](#create-regression-error-profilepy) | Custom SQL | Regression error distribution analysis (3 metrics via custom SQL) |
| [migrate-connectors.py](#migrate-connectorspy) | Migration | Copy connectors between projects (all connector types) |
| [migrate-custom-aggregation-definitions.py](#migrate-custom-aggregation-definitionspy) | Migration | Copy custom SQL metric definitions between workspaces |
| [migrate-model-metric-config.py](#migrate-model-metric-configpy) | Migration | Copy a model's full metric configuration between endpoints |
| [duplicate-metrics-to-new-datasets.py](#duplicate-metrics-to-new-datasetspy) | Migration | Copy metrics from old datasets to new datasets within a model |
| [add-column-to-schema.py](#add-column-to-schemapy) | Schema | Add a new column to an existing dataset schema |
| [remove-column-from-schema.py](#remove-column-from-schemapy) | Schema | Remove a column from an existing dataset schema |
| [service-account-creation.py](#service-account-creationpy) | Auth | Create a service account for automation and CI/CD |
| [using-sdk-with-service-account-creds.py](#using-sdk-with-service-account-credspy) | Auth | Example of service account authentication |

### Reference Documents

| File | Contents |
|------|----------|
| [AGGREGATIONS_REFERENCE.md](AGGREGATIONS_REFERENCE.md) | All 27 built-in aggregation IDs, arguments, and examples |

---

## Prerequisites

- **Python 3.8+**
- **Arthur SDK**: `pip install arthur-client`
- **Arthur Project**: Created in the Arthur UI — note its project ID
- **Data source access**: S3 credentials, GCS service account, Snowflake creds, etc.

---

## Environment Variables

All scripts have credential values hardcoded as placeholder strings at the top of the file. **Do not commit real credentials into source control.** Use environment variables instead and load them at runtime.

### Recommended approach: `.env` file + `python-dotenv`

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file** in the `scripts/onboarding/` directory:

```bash
# Arthur
ARTHUR_HOST=https://platform.arthur.ai
ARTHUR_PROJECT_ID=your-project-id
ARTHUR_WORKSPACE_ID=your-workspace-id
ARTHUR_MODEL_ID=your-model-id
ARTHUR_DATA_PLANE_ID=your-data-plane-id

# Service account (for automation)
ARTHUR_CLIENT_ID=your-client-id
ARTHUR_CLIENT_SECRET=your-client-secret

# AWS S3
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/RoleName
AWS_EXTERNAL_ID=arthur-external-id
S3_BUCKET=your-bucket-name

# GCS / BigQuery
GCP_PROJECT_ID=your-gcp-project
GCP_CREDENTIALS={"type":"service_account","project_id":"..."}

# Snowflake
SNOWFLAKE_HOST=orgname-accountname
SNOWFLAKE_DATABASE=MY_DB
SNOWFLAKE_USERNAME=my_user
SNOWFLAKE_PASSWORD=...

# ODBC
ODBC_HOST=db.internal.company.com
ODBC_DATABASE=my_database
ODBC_USERNAME=my_user
ODBC_PASSWORD=...

# Migration
SOURCE_ARTHUR_HOST=https://source.arthur.ai
SOURCE_MODEL_ID=...
SOURCE_WORKSPACE_ID=...
SOURCE_PROJECT_ID=...
DEST_ARTHUR_HOST=https://dest.arthur.ai
DEST_MODEL_ID=...
DEST_WORKSPACE_ID=...
DEST_PROJECT_ID=...
DEST_DATA_PLANE_ID=...
```

**3. Add `.env` to `.gitignore`:**

```bash
echo ".env" >> .gitignore
```

**4. Load in any script** by adding these two lines at the top, before the configuration block:

```python
from dotenv import load_dotenv
import os
load_dotenv()
```

Then replace hardcoded values with `os.environ.get()`:

```python
# Before (hardcoded — do not commit)
ARTHUR_HOST       = "https://platform.arthur.ai"
AWS_ACCESS_KEY_ID = "AKIA..."

# After (loaded from environment)
ARTHUR_HOST       = os.environ.get("ARTHUR_HOST", "https://platform.arthur.ai")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
```

### Alternative: export directly in your shell

If you prefer not to use a `.env` file, export variables in your shell session before running any script:

```bash
export ARTHUR_HOST="https://platform.arthur.ai"
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."

python model-onboarding.py
```

### All credential variables by script

| Script | Credential variables to externalise |
|--------|-------------------------------------|
| `model-onboarding.py` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ROLE_ARN`, `AWS_EXTERNAL_ID` |
| `housing-price-onboarding.py` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ROLE_ARN`, `AWS_EXTERNAL_ID` |
| `create-positive-class-error-profile.py` | `ARTHUR_WORKSPACE_ID`, `ARTHUR_MODEL_ID` |
| `create-regression-error-profile.py` | `ARTHUR_WORKSPACE_ID`, `ARTHUR_MODEL_ID` |
| `migrate-connectors.py` | `SOURCE_PROJECT_ID`, `DEST_PROJECT_ID`, `DEST_DATA_PLANE_ID` |
| `migrate-custom-aggregation-definitions.py` | `SOURCE_WORKSPACE_ID`, `DEST_WORKSPACE_ID` |
| `migrate-model-metric-config.py` | `SOURCE_MODEL_ID`, `DEST_MODEL_ID` |
| `duplicate-metrics-to-new-datasets.py` | `ARTHUR_MODEL_ID`, dataset IDs in mapping dicts |
| `using-sdk-with-service-account-creds.py` | `ARTHUR_CLIENT_ID`, `ARTHUR_CLIENT_SECRET` |
| `service-account-creation.py` | None — outputs credentials, doesn't consume them |
| All others | `ARTHUR_MODEL_ID`, `ARTHUR_DATASET_ID` as applicable |

> **GCS/BigQuery credentials:** The `GCP_CREDENTIALS` value is a JSON string. If storing in a `.env` file, keep it on one line and wrap the entire JSON in single quotes to avoid shell interpretation issues. Alternatively, store the path to a credentials JSON file and load it with `json.load(open(os.environ.get("GCP_CREDENTIALS_FILE")))`.

---

## Authentication

All scripts use **device-based authentication** by default — a browser window opens and you log in with your Arthur credentials. This is suitable for interactive use.

```python
from arthur_client.auth import DeviceAuthorizer
sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
```

For automated systems (CI/CD, scheduled jobs), use **service account authentication** instead:

```python
from arthur_client.auth import ArthurClientCredentialsAPISession, ArthurOIDCMetadata
sess = ArthurClientCredentialsAPISession(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    metadata=ArthurOIDCMetadata(arthur_host=ARTHUR_HOST),
)
```

See [service-account-creation.py](#service-account-creationpy) to create a service account and [using-sdk-with-service-account-creds.py](#using-sdk-with-service-account-credspy) for a working example.

---

## Workflows

### 1. New Binary Classification Model

Use this path for fraud detection, credit approval, churn prediction, etc.

```bash
# Step 1: Create connector, dataset, model, and schedule
python model-onboarding.py

# Step 2: Add domain-specific metrics
python add-fraud-model-aggregations.py         # if this is a fraud model
# OR
python add-custom-aggregations.py              # for any other binary classifier

# Step 3 (optional): Add custom SQL error analysis
python create-positive-class-error-profile.py
```

### 2. New Regression Model

Use this path for price prediction, demand forecasting, scoring models, etc.

```bash
# Step 1: Create connector, dataset, model, and schedule
python housing-price-onboarding.py

# Step 2: Add regression metrics
python add-regression-model-aggregations.py

# Step 3 (optional): Add custom SQL error analysis
python create-regression-error-profile.py
```

### 3. Adding Custom SQL Metrics to an Existing Model

Use this when you need metrics beyond what the built-in aggregation IDs provide.

```bash
# Step 1: Create the custom aggregation definition (one-time, workspace-level)
python create-positive-class-error-profile.py   # binary classification
# OR
python create-regression-error-profile.py        # regression

# The script also attaches the new metric to the model automatically.
```

### 4. Migrating Between Arthur Environments

Use this path when copying a model configuration from one Arthur environment to another (e.g., staging → production, or between customers).

```bash
# Step 1 (if the model uses custom SQL metrics): copy their definitions
python migrate-custom-aggregation-definitions.py

# Step 2: copy the model's metric configuration
python migrate-model-metric-config.py

# Optional: also migrate connectors
python migrate-connectors.py
```

> **Note:** Run `migrate-custom-aggregation-definitions.py` before `migrate-model-metric-config.py`. The model migration script looks up custom aggregation definitions by name in the destination workspace — they must already exist.

### 5. Dataset Migration (Same Model, New Dataset)

Use this when the underlying data source changes (new S3 bucket, new schema version) but the model stays the same.

```bash
# Copy metrics from old datasets to new datasets, remapping column IDs by name
python duplicate-metrics-to-new-datasets.py
```

### 6. Schema Changes

```bash
# When your data source adds a new field
python add-column-to-schema.py

# When your data source removes a field
# First: remove any aggregations that reference the column from the model
# Then:
python remove-column-from-schema.py
```

---

## Script Reference

---

### model-onboarding.py

**Purpose:** Complete end-to-end onboarding of a binary classification model from an S3 data source.

**When to use:** First-time setup of any new model reading from S3.

**Creates:**
1. S3 connector (reuses an existing one if a connector with the same name exists)
2. Available dataset (registers the S3 path)
3. Schema inspection job (samples S3 files to infer column types)
4. Dataset with inferred + corrected schema
5. Model with basic metrics (inference count + nullable counts)
6. Hourly refresh schedule

**Configuration:**

```python
ARTHUR_HOST        = "https://platform.arthur.ai"
ARTHUR_PROJECT_ID  = "INSERT_ARTHUR_PROJECT_ID_HERE"   # From Arthur UI
DATA_PLANE_ID      = "INSERT_DATA_PLANE_ID_HERE"        # Optional; auto-detected if blank

# S3
AWS_ACCESS_KEY_ID      = "..."
AWS_SECRET_ACCESS_KEY  = "..."
AWS_REGION             = "us-east-1"
AWS_ROLE_ARN           = "..."          # Optional: use IAM role instead of keys
AWS_EXTERNAL_ID        = "..."          # Optional: role external ID
S3_BUCKET              = "your-bucket"
S3_FILE_PREFIX         = "inferences/%Y/%m/%d"   # strftime formatting supported
S3_FILE_SUFFIX         = ".*.json"               # regex pattern
S3_FILE_TYPE           = "json"                  # json | parquet | csv

# Model
MODEL_NAME             = "my-fraud-model"
MODEL_DESCRIPTION      = "..."
TIMESTAMP_COLUMN_NAME  = "timestamp"
```

**S3 authentication options:**

| Method | Fields to set |
|--------|--------------|
| Access keys | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| IAM role | `AWS_ROLE_ARN` (+ optional `AWS_EXTERNAL_ID`) |
| Custom endpoint | `S3_ENDPOINT` (for MinIO or on-premises S3) |

**File prefix patterns (strftime):**

| Pattern | Resolves to | Description |
|---------|-------------|-------------|
| `data/%Y%m%d/` | `data/20240101/` | Daily |
| `logs/%Y/%m/%d/` | `logs/2024/01/01/` | Nested daily |
| `inferences/%Y/%m/%d/%H/` | `inferences/2024/01/01/14/` | Hourly |

**Next step:** Run `add-fraud-model-aggregations.py` or `add-custom-aggregations.py`.

---

### housing-price-onboarding.py

**Purpose:** Complete end-to-end onboarding of a regression model from an S3 data source.

**When to use:** First-time setup for any regression model. This script is the regression equivalent of `model-onboarding.py` and includes CSV-specific configuration.

**Creates:** Same as `model-onboarding.py` but with `ModelProblemType.REGRESSION` and additional schema tagging for prediction and ground truth columns.

**Configuration:** Same structure as `model-onboarding.py` plus:

```python
TIMESTAMP_COLUMN_NAME      = "timestamp"
ROW_ID_COLUMN_NAME         = "house_id"
PREDICTION_COLUMN_NAME     = "predicted_house_value"
GROUND_TRUTH_COLUMN_NAME   = "actual_house_value"

# CSV-specific (when S3_FILE_TYPE = "csv")
CSV_DELIMITER   = ","
CSV_HAS_HEADER  = True
CSV_QUOTE_CHAR  = '"'
```

**What it does differently from model-onboarding.py:**
- Sets `ModelProblemType.REGRESSION` on the dataset and model
- Applies a `column_type_mapping` dict to explicitly set `DType` for each known column
- Tags prediction column with `ScopeSchemaTag.PREDICTION` and ground truth with `ScopeSchemaTag.GROUND_TRUTH`
- Adds distributions for both prediction and ground truth columns in the initial metric config

**Next step:** Run `add-regression-model-aggregations.py`.

---

### add-fraud-model-aggregations.py

**Purpose:** Add a comprehensive set of built-in aggregations tuned for card fraud detection.

**When to use:** After `model-onboarding.py`, when the model has columns for fraud score, ground truth fraud label, and categorical segmentation fields.

**Requires these columns in the dataset:**

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | Timestamp | Primary timestamp |
| `fraud_pred` | Float | Predicted fraud probability |
| `is_fraud` | Int/Bool | Ground truth fraud label |
| `distance_from_home_km` | Float | Feature |
| `tenure_months` | Float | Feature |
| `customer_segment` | String | Categorical |
| `channel` | String | Categorical |
| `region` | String | Categorical |
| `risk_rank` | String | Categorical |

**Adds:**
- Inference count
- Numeric sums: `fraud_pred`, `is_fraud`
- Numeric distributions (min/max/mean/std): all numeric columns
- Category counts: all categorical columns
- Confusion matrix with segmentation by `region` and `risk_rank`
- Inference count by class (Fraud vs Authorized) with segmentation
- Nullable counts for all tracked columns

**Configuration:**

```python
ARTHUR_HOST  = "https://platform.arthur.ai"
MODEL_ID     = "INSERT_MODEL_ID_HERE"
```

**Deduplication:** Automatically skips aggregations that already exist on the model (matched by aggregation ID + arguments).

---

### add-regression-model-aggregations.py

**Purpose:** Add a comprehensive set of built-in aggregations for regression models.

**When to use:** After `housing-price-onboarding.py`, or to add regression metrics to any existing regression model.

**Requires these columns in the dataset** (will skip with a warning if not found):

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | Timestamp | Primary timestamp |
| `predicted_house_value` | Float | Model prediction |
| `actual_house_value` | Float | Ground truth |
| `longitude`, `latitude` | Float | Geographic features |
| `housing_median_age`, `total_rooms`, etc. | Int | Numeric features |
| `ocean_proximity` | String | Categorical feature |

**Adds:**
- Inference count
- Numeric sums: prediction and ground truth columns
- Numeric distributions: all numeric columns
- Category counts: categorical columns
- **MAE** (Mean Absolute Error): aggregation ID `00000000-0000-0000-0000-00000000000e`
- **MSE** (Mean Squared Error): aggregation ID `00000000-0000-0000-0000-000000000010`
- Nullable counts for all tracked columns

**Configuration:**

```python
ARTHUR_HOST  = "https://platform.arthur.ai"
MODEL_ID     = "INSERT_MODEL_ID_HERE"
```

> MAE and MSE are only added if both `prediction_col` and `ground_truth_col` exist in the dataset.

---

### add-custom-aggregations.py

**Purpose:** Generic template for adding built-in aggregation specs to any model.

**When to use:** When `add-fraud-model-aggregations.py` and `add-regression-model-aggregations.py` don't match your model type, or when you want to add specific aggregations beyond what those scripts provide.

**How to use:**
1. Set `MODEL_ID`
2. Edit `gen_custom_aggregations()` to add the aggregations you need
3. Run the script

**Template includes examples for:**
- Inference count
- Nullable counts (all columns)
- Numeric distribution
- Numeric sum
- Binary classification count by class

**Configuration:**

```python
ARTHUR_HOST  = "https://platform.arthur.ai"
MODEL_ID     = "INSERT_MODEL_ID_HERE"
```

**Key function to customize:**

```python
def gen_custom_aggregations(dataset: Dataset) -> list[AggregationSpec]:
    # Get column IDs by name
    timestamp_col_id = column_id_from_col_name(dataset, "timestamp")
    # ... build and return your list of AggregationSpec objects
```

See [AGGREGATIONS_REFERENCE.md](AGGREGATIONS_REFERENCE.md) for all available aggregation IDs and their required arguments.

---

### add-prediction-stats-metrics.py

**Purpose:** Add prediction sum and numeric distribution metrics to an existing model.

**When to use:** Quick addition of the two most common prediction monitoring metrics to any model that has `prediction` and `timestamp` columns.

**Adds:**
- Numeric Sum of `prediction` column
- Numeric Distribution (min/max/mean/std) of `prediction` column

**Configuration:**

```python
ARTHUR_HOST  = "https://platform.arthur.ai"
MODEL_ID     = "YOUR_MODEL_ID_HERE"
```

**Note:** Column names default to `prediction` and `timestamp`. Edit `gen_aggregation_specs()` if your columns have different names.

---

### create-positive-class-error-profile.py

**Purpose:** Create a custom SQL-based aggregation for binary classification error analysis, then attach it to a model.

**When to use:** When you need per-inference confusion matrix decomposition beyond what built-in aggregations provide. Ideal for fraud detection and other binary classifiers where the cost of false positives has operational significance.

**Creates a custom aggregation with 7 reported metrics:**

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| `adjusted_false_positive_rate` | FP / (FP + TN) | False alarm rate among actual negatives |
| `bad_case_rate` | (TP + FN) / Total | Fraction of actual positives in the data |
| `false_positive_ratio` | FP / Total | False positives as share of all inferences |
| `valid_detection_rate` | (TP + TN) / Total | Overall accuracy |
| `overprediction_rate` | max(predicted_pos − actual_pos, 0) / Total | Model optimism |
| `underprediction_rate` | max(actual_pos − predicted_pos, 0) / Total | Model conservatism |
| `total_false_positive_rate` | SUM(FP) / SUM(Total) | Cumulative FPR across all time |

**Required dataset columns:**

| Column | Type | Tag |
|--------|------|-----|
| timestamp | Timestamp | `primary_timestamp` |
| Ground truth | Int or Bool | `ground_truth` |
| Prediction score | Float | `prediction` |

**Configuration:**

```python
ARTHUR_HOST                = "https://platform.arthur.ai"
WORKSPACE_ID               = "INSERT_WORKSPACE_ID_HERE"
MODEL_ID                   = "INSERT_MODEL_ID_HERE"
TIMESTAMP_COLUMN_NAME      = "timestamp"
GROUND_TRUTH_COLUMN_NAME   = "is_fraud"
PREDICTION_COLUMN_NAME     = "fraud_pred"
CLASSIFICATION_THRESHOLD   = 0.5
```

**How it works:**
1. Creates a `CustomAggregationsV1Api` definition in the workspace (reusable across models)
2. Attaches it to the specified model with the configured column mappings
3. Prints the new aggregation ID — save this if you need to reference it later

---

### create-regression-error-profile.py

**Purpose:** Create a custom SQL-based aggregation for regression error distribution analysis, then attach it to a model.

**When to use:** When you need per-inference error distributions for outlier detection or bias analysis, beyond what the built-in MAE/MSE aggregations provide.

**Creates a custom aggregation with 3 reported metrics:**

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| `absolute_error` | \|prediction − actual\| | Magnitude of error; use for outlier detection |
| `forecast_error` | prediction − actual | Signed error; positive = over-prediction, negative = under-prediction |
| `absolute_percentage_error` | \|prediction − actual\| / actual × 100 | Scale-independent error; NULL when actual = 0 |

**Required dataset columns:**

| Column | Type | Tag |
|--------|------|-----|
| timestamp | Timestamp | `primary_timestamp` |
| Prediction | Int or Float | `prediction` |
| Ground truth | Int or Float | `ground_truth` |

**Configuration:**

```python
ARTHUR_HOST                = "https://platform.arthur.ai"
WORKSPACE_ID               = "INSERT_WORKSPACE_ID_HERE"
MODEL_ID                   = "INSERT_MODEL_ID_HERE"
TIMESTAMP_COLUMN_NAME      = "timestamp"
PREDICTION_COLUMN_NAME     = "predicted_house_value"
GROUND_TRUTH_COLUMN_NAME   = "actual_house_value"
```

---

### migrate-connectors.py

**Purpose:** Copy connectors from a source project to a destination project, stripping credential fields so they can be safely updated in the Arthur UI afterward.

**When to use:** When setting up a new environment (staging → production, or a new customer environment) and you want to replicate connector configurations without manually recreating each one.

**Supported connector types:**

| Type | Structural fields copied | Credentials stripped |
|------|--------------------------|----------------------|
| S3 | `bucket`, `region`, `role_arn`, `external_id`, `endpoint` | `access_key_id`, `secret_access_key` |
| GCS | `bucket`, `project_id` | `credentials` |
| BigQuery | `project_id`, `location` | `credentials` |
| ODBC | `host`, `port`, `database`, `username`, `driver`, `dialect` | `password` |
| Snowflake | `host`, `database`, `username`, `schema`, `warehouse`, `role`, `authenticator` | `password`, `private_key`, `private_key_passphrase` |
| Shield | `shield_endpoint` | `shield_api_key` |

> `ENGINE_INTERNAL` connectors are skipped — they have no API-configurable fields.

**Configuration:**

```python
SOURCE_ARTHUR_HOST  = "https://source.arthur.ai"
SOURCE_PROJECT_ID   = "INSERT_SOURCE_PROJECT_ID_HERE"

DEST_ARTHUR_HOST    = "https://dest.arthur.ai"
DEST_PROJECT_ID     = "INSERT_DEST_PROJECT_ID_HERE"
DEST_DATA_PLANE_ID  = "INSERT_DEST_DATA_PLANE_ID_HERE"
```

**After running:** Go to the Arthur UI → Project settings → Connectors and fill in the credential fields for each created connector.

> **Field name note:** ODBC/Snowflake/BigQuery/Shield field names are sourced from the SDK schema. If a connector creation fails with an unknown field error, check the Arthur UI network tab to confirm the exact key names your platform version uses.

---

### migrate-custom-aggregation-definitions.py

**Purpose:** Copy custom SQL aggregation definitions from one Arthur workspace to another.

**When to use:** Before running `migrate-model-metric-config.py`, if the source model uses any custom (SQL-based) aggregations. Custom aggregation definitions live at the workspace level; they must exist in the destination workspace before a model can reference them.

**How it works:**
1. Lists all custom aggregation definitions in the source workspace
2. Lists existing definitions in the destination workspace
3. For each source definition not already present (matched by name), creates it in the destination

**Configuration:**

```python
SOURCE_ARTHUR_HOST   = "https://source.arthur.ai"
SOURCE_WORKSPACE_ID  = "INSERT_SOURCE_WORKSPACE_ID_HERE"

DEST_ARTHUR_HOST     = "https://dest.arthur.ai"
DEST_WORKSPACE_ID    = "INSERT_DEST_WORKSPACE_ID_HERE"
```

> Set `DEST_ARTHUR_HOST = SOURCE_ARTHUR_HOST` if both workspaces are on the same platform — only one browser login will be required.

**Matching:** Definitions are matched by name. Existing same-named definitions in the destination are never overwritten.

---

### migrate-model-metric-config.py

**Purpose:** Copy all aggregation specs from a source model to a destination model, remapping dataset and column IDs by name.

**When to use:** To replicate a model's complete metric configuration to another model — either on a different endpoint or on the same platform. Handles both built-in aggregations and custom SQL-based aggregations.

**Prerequisite:** If the source model uses custom SQL aggregations, run `migrate-custom-aggregation-definitions.py` first.

**How it works:**
1. Fetches the source model's aggregation specs and dataset schemas
2. For CUSTOM aggregations, resolves their names from the source workspace
3. Looks up those custom aggregation definitions in the destination workspace by name
4. Remaps all dataset IDs and column IDs by matching `source_name`
5. Deduplicates against specs already on the destination model
6. Prompts for confirmation, then applies

**Configuration:**

```python
SOURCE_ARTHUR_HOST  = "https://source.arthur.ai"
SOURCE_MODEL_ID     = "INSERT_SOURCE_MODEL_ID_HERE"

DEST_ARTHUR_HOST    = "https://dest.arthur.ai"
DEST_MODEL_ID       = "INSERT_DEST_MODEL_ID_HERE"

SKIP_EXISTING = True   # skip specs already present in destination
```

**Matching rules:**
- Datasets matched by `dataset.name`
- Columns matched by `col.source_name` within each matched dataset
- Custom aggregations matched by definition name in the destination workspace
- Specs with unmapped datasets, columns, or missing custom aggregations are skipped with a warning

---

### duplicate-metrics-to-new-datasets.py

**Purpose:** Copy aggregation specs from old datasets to new datasets within the same model, remapping column IDs by name.

**When to use:** When the underlying data source for a model changes — new S3 bucket, schema version bump, or connector swap — and the new dataset has the same column names but different column IDs.

**How it works:**
1. For each old dataset → new dataset pair in `DATASET_MAPPING`, finds all aggregation specs referencing the old dataset
2. Maps each column ID from old to new by `source_name`
3. Skips aggregations that reference columns removed in the new dataset
4. Replaces all aggregation specs for the new datasets (keeps old dataset specs unchanged)
5. Validates that old dataset aggregations are untouched before applying

**Configuration:**

```python
ARTHUR_HOST  = "https://platform.arthur.ai"
MODEL_ID     = "YOUR_MODEL_ID_HERE"

OLD_DATASETS = {
    "dataset-v1":         "OLD_DATASET_ID_1",
    "dataset-v1-metrics": "OLD_DATASET_ID_2",
}

DATASET_MAPPING = {
    "OLD_DATASET_ID_1": "NEW_DATASET_ID_1",
    "OLD_DATASET_ID_2": "NEW_DATASET_ID_2",
}
```

> **Warning:** This replaces all aggregation specs for the new datasets. It cannot be undone without re-running the script.

---

### add-column-to-schema.py

**Purpose:** Add a new column to an existing dataset schema.

**When to use:** When the upstream data source adds a new field and you want Arthur to track it. The column must already exist in the actual data files — this only updates the schema definition; it does not backfill historical data.

**Configuration:**

```python
ARTHUR_HOST     = "https://platform.arthur.ai"
DATASET_ID      = "YOUR_DATASET_ID_HERE"
COLUMN_TO_ADD   = "new_column_name"
```

**In the script, also set:**

```python
new_col = DatasetColumn(
    ...
    definition=Definition(
        DatasetScalarType(
            nullable=True,       # or False
            dtype=DType.FLOAT,   # DType.INT | DType.FLOAT | DType.STRING | DType.BOOL | DType.TIMESTAMP
        )
    ),
)
```

**Checks:** Raises an exception if the column already exists in the schema, preventing duplicate columns.

---

### remove-column-from-schema.py

**Purpose:** Remove a column from an existing dataset schema.

**When to use:** When the upstream data source removes a field, a column was added by mistake, or you want to simplify the schema.

**Configuration:**

```python
ARTHUR_HOST        = "https://platform.arthur.ai"
DATASET_ID         = "YOUR_DATASET_ID_HERE"
COLUMN_TO_REMOVE   = "column_to_remove"
```

> **Warning:** Removing a column that is referenced by an existing aggregation spec will break that metric. Remove or update the affected aggregation specs first, then remove the column.

---

### service-account-creation.py

**Purpose:** Create a service account with machine-to-machine credentials for use in automated systems.

**When to use:** Setting up CI/CD pipelines, scheduled automation jobs, or any system that needs to call the Arthur API without a human logging in.

**Creates:**
- A service account user
- Client ID and Client Secret (printed once — save them immediately)
- Assigns `Organization Super Admin` role
- Adds to a specified group

**Configuration:**

```python
ARTHUR_HOST  = "https://platform.arthur.ai"
GROUP_NAME   = "INSERT_GROUP_NAME_HERE"   # Group to add the service account to
```

> **Security:** Store the Client Secret in a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.). It is shown only once and cannot be retrieved again.

**Next step:** Test the credentials with `using-sdk-with-service-account-creds.py`.

---

### using-sdk-with-service-account-creds.py

**Purpose:** Demonstrate service account authentication and verify that credentials work.

**When to use:** After running `service-account-creation.py`, to confirm the Client ID and Client Secret are valid.

**Configuration:**

```python
ARTHUR_HOST    = "https://platform.arthur.ai"
CLIENT_ID      = "<service account client ID>"
CLIENT_SECRET  = "<service account client secret>"
```

**What it does:** Authenticates using client credentials, lists all workspaces, and prints the projects in the first workspace. If this runs without error, the credentials are valid.

**Using service account auth in your own scripts:**

```python
from arthur_client.auth import (
    ArthurClientCredentialsAPISession,
    ArthurOIDCMetadata,
)

sess = ArthurClientCredentialsAPISession(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    metadata=ArthurOIDCMetadata(arthur_host=ARTHUR_HOST),
)
api_client = ApiClient(configuration=ArthurOAuthSessionAPIConfiguration(session=sess))
```

Replace `DeviceAuthorizer(...).authorize()` with the above block in any script that needs to run without a browser.

---

## Configuration Reference

### Column Types (`DType`)

| Value | Use for |
|-------|---------|
| `DType.INT` | Integer columns |
| `DType.FLOAT` | Floating point columns |
| `DType.STR` | String / categorical columns |
| `DType.BOOL` | Boolean columns |
| `DType.TIMESTAMP` | Datetime columns |
| `DType.DATE` | Date-only columns |
| `DType.UUID` | UUID columns |
| `DType.JSON` | JSON blob columns |

### Column Tag Hints (`ScopeSchemaTag`)

| Tag | Purpose |
|-----|---------|
| `PRIMARY_TIMESTAMP` | The main time column used for bucketing — required |
| `PREDICTION` | Model output / prediction score |
| `GROUND_TRUTH` | Actual label / ground truth value |
| `CATEGORICAL` | Categorical feature |
| `CONTINUOUS` | Continuous numeric feature |
| `PIN_IN_DEEP_DIVE` | Always shown in deep dive |
| `POSSIBLE_SEGMENTATION` | Available as a segmentation dimension |

### Dataset Locator Fields

| Field | Required | Description |
|-------|----------|-------------|
| `file_prefix` | Yes | Path prefix with strftime tokens, e.g. `data/%Y/%m/%d` |
| `file_suffix` | Yes | Regex suffix pattern, e.g. `.*.json` |
| `data_file_type` | Yes | `json`, `parquet`, or `csv` |
| `timestamp_time_zone` | No | Timezone for prefix interpretation, e.g. `UTC` |
| `csv_delimiter` | CSV only | Delimiter character, e.g. `,` |
| `csv_has_header` | CSV only | `"true"` or `"false"` |
| `csv_quote_char` | CSV only | Quote character, e.g. `"` |

### Connector Fields by Type

**S3:**

| Field | Required | Description |
|-------|----------|-------------|
| `bucket` | Yes | S3 bucket name |
| `region` | Recommended | AWS region, e.g. `us-east-1` |
| `access_key_id` | Auth* | AWS access key ID |
| `secret_access_key` | Auth* | AWS secret access key |
| `role_arn` | Auth* | IAM role ARN for role assumption |
| `external_id` | No | External ID for role assumption |
| `endpoint` | No | Custom endpoint for S3-compatible storage |

\* Either (`access_key_id` + `secret_access_key`) or `role_arn` required.

**GCS:**

| Field | Required | Description |
|-------|----------|-------------|
| `bucket` | Yes | GCS bucket name |
| `project_id` | Yes | GCP project ID |
| `credentials` | Yes | Service account credentials JSON string |

**BigQuery:**

| Field | Required | Description |
|-------|----------|-------------|
| `project_id` | Yes | GCP project ID |
| `credentials` | Yes | Service account credentials JSON string |
| `location` | No | Dataset location, e.g. `US` |

**ODBC:**

| Field | Required | Description |
|-------|----------|-------------|
| `host` | Yes | Database host |
| `database` | Yes | Database name |
| `username` | Yes | Database user |
| `password` | Yes | Database password |
| `port` | No | Port number |
| `driver` | No | ODBC driver |
| `dialect` | No | SQL dialect |

**Snowflake:**

| Field | Required | Description |
|-------|----------|-------------|
| `host` | Yes | Account identifier, e.g. `orgname-accountname` |
| `database` | Yes | Snowflake database name |
| `username` | Yes | Snowflake user |
| `password` | Auth* | Password |
| `private_key` | Auth* | Private key for key-pair auth |
| `private_key_passphrase` | No | Passphrase for private key |
| `schema` | No | Schema name (default: `PUBLIC`) |
| `warehouse` | No | Warehouse name (default: `COMPUTE_WH`) |
| `role` | No | Snowflake role |
| `authenticator` | No | `snowflake_password` or `snowflake_key_pair` |

\* Either `password` or `private_key` required.

---

## Troubleshooting

### Schema inspection job fails

**Symptom:** Job state is `FAILED`; no schema returned.

**Checklist:**
- S3/GCS permissions include read and list access on the bucket
- `file_prefix` exactly matches the S3 key structure (check for trailing slashes)
- `file_suffix` regex matches actual file names
- `data_file_type` matches the actual file format
- Files exist in the date range Arthur is sampling (±90 days from today by default)

### "Data plane not associated with project"

**Cause:** Multiple data planes exist in the workspace and the auto-detected one doesn't belong to your project.

**Fix:** Log into the Arthur UI, find the data plane associated with your project, and set `DATA_PLANE_ID` explicitly at the top of the onboarding script.

### Column not found

**Symptom:** `ValueError: Column 'xyz' not found in dataset schema`

**Fix:** Print the actual column names before setting configuration values:
```python
dataset = datasets_client.get_dataset(dataset_id=MODEL_ID)
print([col.source_name for col in dataset.dataset_schema.columns])
```

### Metrics not appearing in the UI

**Checklist:**
- Wait for the next scheduled metric run (hourly by default)
- Check the Arthur activity log for calculation errors
- Verify data exists in the time window the schedule is querying
- Confirm the aggregation IDs are valid (see [AGGREGATIONS_REFERENCE.md](AGGREGATIONS_REFERENCE.md))

### Migration: datasets not matched

**Symptom:** `WARNING: Source dataset 'xyz' not found in destination by name`

**Cause:** The destination model has datasets with different names than the source.

**Fix:** Ensure dataset names match between source and destination, or use `duplicate-metrics-to-new-datasets.py` for same-model dataset swaps where you control the mapping explicitly.

### Migration: custom aggregation not found in destination

**Symptom:** `NOT FOUND: 'my_metric' — aggregation specs referencing this will be skipped`

**Fix:** Run `migrate-custom-aggregation-definitions.py` first to copy the custom SQL definition to the destination workspace, then re-run `migrate-model-metric-config.py`.

### Connector creation fails with unknown field

**Symptom:** API error mentioning an unknown field name during connector creation.

**Cause:** Field key names in `migrate-connectors.py` may differ slightly from your platform version.

**Fix:** Open the Arthur UI, manually edit the connector, open browser developer tools, and inspect the network request to see the exact field keys your version accepts. Update `CREDENTIAL_FIELDS` in `migrate-connectors.py` accordingly.

---

## See Also

- [AGGREGATIONS_REFERENCE.md](AGGREGATIONS_REFERENCE.md) — All 27 built-in aggregation IDs with arguments and code examples
- Arthur API docs: `https://<your-arthur-host>/api/v1/docs`
