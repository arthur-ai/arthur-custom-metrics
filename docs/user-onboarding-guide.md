# Arthur Platform — User Onboarding Guide

A step-by-step guide for setting up, configuring, and monitoring ML models on the Arthur Platform. Follow the sections in order for a first-time setup, or jump to a specific section when you need a reference.

---

## Prerequisites

Confirm each item below before starting. Steps that depend on a missing prerequisite are noted in parentheses.

### Platform Access

| Requirement | Details | Needed For |
|-------------|---------|------------|
| **Arthur account** | Login credentials for your organization's Arthur instance (e.g., `platform.arthur.ai`) | Everything |
| **Model Owner role or higher** | Required to create datasets, onboard models, and add metrics. Administrators can also create projects and manage users. Contact your Arthur admin if you are not sure of your role. | §1–§5 |
| **Arthur Engine deployed** | At least one engine must be running and associated with your workspace. Engines execute metric calculation jobs inside your infrastructure. If none exists, follow the [Evals Engine Quickstart](https://docs.arthur.ai/docs/quickstart) before proceeding. | §1, §5 |

### Data

| Requirement | Details | Needed For |
|-------------|---------|------------|
| **Data in a supported connector** | Inference data must be accessible via S3, GCS, Snowflake, BigQuery, or ODBC. See [§2](#2-building-a-data-connector) for the full connector list. | §2–§3 |
| **Supported file format** | Files must be JSON, Parquet, or CSV. The schema inspection job (§3) samples files from approximately ±90 days of the current date — ensure files exist in that window. | §3 |
| **Connector credentials** | AWS access keys or IAM role ARN (S3); username and password (Snowflake/ODBC). For GCS/BigQuery, a service account JSON is only required if your DevOps/Admin has **not** already configured ambient credentials on the Arthur Engine (e.g., Workload Identity or a pre-attached service account) — check with them first. See the credential field tables in [§2](#2-building-a-data-connector). | §2 |

### Python SDK (optional — only needed for script-based automation)

| Requirement | Details | Needed For |
|-------------|---------|------------|
| **Python 3.8+** | Required to run any script in [`scripts/onboarding/`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/). | SDK steps throughout |
| **Arthur client SDK** | `pip install arthur-client` | SDK steps throughout |
| **`python-dotenv`** (recommended) | `pip install python-dotenv` — used to load credentials from a `.env` file rather than hardcoding them. See the [scripts README](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md#environment-variables) for the full `.env` template. | SDK steps throughout |
| **Arthur Project ID** | The UUID of the project you create in §1. Visible in the Arthur UI URL when viewing the project. Required at the top of every onboarding script. | SDK steps in §2–§5 |

---

## Table of Contents

1. [Creating a Project](#1-creating-a-project)
2. [Building a Data Connector](#2-building-a-data-connector)
3. [Adding a Dataset](#3-adding-a-dataset)
4. [Creating Custom Metrics](#4-creating-custom-metrics)
5. [Onboarding a Model with Metrics](#5-onboarding-a-model-with-metrics)
6. [Building Dashboards](#6-building-dashboards)
7. [Creating New Charts](#7-creating-new-charts)
8. [Creating Webhooks](#8-creating-webhooks)
9. [Creating Alerts](#9-creating-alerts)
10. [Updating Your Setup](#10-updating-your-setup)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Creating a Project

### What is a Project and Why Does It Exist?

A **Project** is the top-level organizational container in Arthur. Everything you monitor — models, datasets, connectors, dashboards, and alerts — lives inside a project.

Projects matter for three reasons:

- **Access control**: Permissions (RBAC) are enforced at the project level. Users only see models and data for projects they belong to.
- **Logical grouping**: Group related models together (e.g., all fraud detection models, or all models for a specific business unit).
- **Engine association**: Each project is linked to one or more Arthur Engines, which determines where evaluation jobs actually run. This keeps inference data inside your infrastructure.

### How to Create a Project

1. Log in at [platform.arthur.ai](https://platform.arthur.ai).
2. From the top navigation, click **+ ADD** in the top right corner, or navigate to the **Projects** section.
3. Click **New Project**.
4. Enter a descriptive **Project Name** (e.g., `Fraud Detection - Production`).
5. Click **Create**.

> **Tip:** Use a naming convention that reflects team ownership and environment — for example, `[Team]-[Use Case]-[Env]` like `Risk-FraudScore-Prod`.

### Associate an Engine with Your Project

After creating the project, link it to an Arthur Engine so metric calculation jobs can run:

1. Navigate to **Workspace Settings → Engines Management**.
2. Click the engine you want to associate.
3. Under **Associated Projects**, click **Manage** and add your new project.
4. Click **Save**.

---

## 2. Building a Data Connector

### What is a Connector?

A **Connector** is the authenticated link between Arthur and your data source (S3, GCS, Snowflake, etc.). It stores the credentials and configuration Arthur needs to read your inference files.

Connectors are project-scoped — the same S3 bucket can have separate connectors in different projects, each with their own credentials.

### Supported Connector Types

| Connector | Use When |
|-----------|----------|
| **Amazon S3** | Inference data stored in S3 as JSON, Parquet, or CSV |
| **Google Cloud Storage (GCS)** | Inference data stored in GCS |
| **Snowflake** | Inference data in Snowflake tables |
| **BigQuery** | Inference data in Google BigQuery |
| **ODBC** | Generic database via ODBC driver |

### How to Create a Connector (UI)

1. Open your **Project** and click **Add Data Connector** (or go to **Project Settings → Connectors → + Add**).
2. Select your connector type (e.g., **Amazon S3**).
3. Fill in the required fields:

**For Amazon S3:**

| Field | Description |
|-------|-------------|
| Bucket | S3 bucket name |
| Region | AWS region (e.g., `us-east-1`) |
| Access Key ID | AWS access key (or leave blank to use IAM role) |
| Secret Access Key | AWS secret key |
| Role ARN | IAM role ARN (if using role-based auth instead of keys) |
| External ID | External ID for cross-account role assumption (optional) |

**For Google Cloud Storage (GCS) / BigQuery:**

| Field | Description |
|-------|-------------|
| Bucket / Project | GCS bucket name or BigQuery project ID |
| Credentials | Service account JSON — **leave blank** if your DevOps/Admin has already configured Workload Identity or a pre-attached service account on the Arthur Engine. Ask them before filling this in. |

> **Note for GCS/BigQuery users:** If the Arthur Engine runs inside GCP with Workload Identity or an attached service account that already has access to your bucket or dataset, you do not need to provide any credentials here. Only fill in the `Credentials` field if you are providing an explicit service account key.

4. Click **Test Connection** to verify credentials are valid.
5. Click **Save**.

### How to Create a Connector (Python SDK)

Use `model-onboarding.py` in [`scripts/onboarding/`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/) for automated connector creation:

```python
# Set your credentials at the top of model-onboarding.py
AWS_ACCESS_KEY_ID     = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION            = "us-east-1"
S3_BUCKET             = "your-bucket-name"
```

Then run:

```bash
cd scripts/onboarding
python model-onboarding.py
```

The script creates the connector automatically and reuses an existing one if a connector with the same name already exists.

> **Security:** Never commit credentials to source control. Store them in a `.env` file (listed in `.gitignore`) and load with `python-dotenv`. See the [scripts README](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md#environment-variables) for the full pattern.

---

## 3. Adding a Dataset

### What is a Dataset?

A **Dataset** is the schema definition that tells Arthur how to interpret your inference files — which columns exist, their types, and their roles (e.g., which column is the timestamp, which is the model prediction).

One connector can back multiple datasets (e.g., separate datasets per model version or per file prefix pattern).

### Key Concepts

| Field | Description |
|-------|-------------|
| **File Prefix** | Path pattern within the bucket, with `strftime` tokens for date partitioning (e.g., `inferences/%Y/%m/%d`) |
| **File Suffix** | Regex that matches file names (e.g., `.*.json`) |
| **File Type** | `json`, `parquet`, or `csv` |
| **Timestamp Column** | The column Arthur uses to bucket data into time windows |
| **Schema** | Column names, types, and tag hints (prediction, ground truth, etc.) |

### How to Add a Dataset (UI)

1. Inside your project, click **Add Dataset** (or **+ ADD → Dataset**).
2. Select the connector you created in step 2.
3. Fill in the file location details:
   - **File Prefix**: e.g., `inferences/%Y/%m/%d`
   - **File Suffix**: e.g., `.*.parquet`
   - **File Type**: select `parquet`, `json`, or `csv`
4. Click **Run Schema Inspection** — Arthur samples recent files to infer column names and types automatically.
5. Review the inferred schema:
   - Correct any column types that were misdetected.
   - Tag key columns using **Tag Hints**:
     - `primary_timestamp` → your timestamp column
     - `prediction` → model output column
     - `ground_truth` → actual label or value
     - `categorical` → categorical features for segmentation
6. Click **Save Dataset**.

> **Tip:** The schema inspection job samples files from approximately ±90 days of the current date. Ensure files exist in that range before running the inspection.

### Column Types Reference

| Type | Use For |
|------|---------|
| `int` | Integer columns |
| `float` | Continuous numeric columns |
| `str` | Categorical / text columns |
| `bool` | Boolean columns |
| `timestamp` | Datetime columns |
| `date` | Date-only columns |
| `uuid` | UUID identifier columns |
| `json` | JSON blob columns |

### How to Add a Dataset (Python SDK)

The onboarding scripts handle this automatically. After running `model-onboarding.py` or `housing-price-onboarding.py`, the dataset is created and the schema inspection job is submitted. The script waits for the job to complete and applies any type corrections you've configured in the script.

---

## 4. Creating Custom Metrics

Arthur ships with built-in metrics (inference counts, distributions, confusion matrix components, MAE, MSE, etc.). **Custom Metrics** let you define additional metrics using SQL — anything from business-specific KPIs to specialized statistical tests.

Custom metrics are **reusable** (define once, attach to many models), **versioned** (historical results are preserved when you edit), and **queryable** (appear alongside built-in metrics in dashboards and alerts).

> **Not on day one?** Many teams start with built-in metrics and add custom metrics later once they know what they need to measure. You can skip this section and return to it after completing §5.

### Start from a Pre-Built Example

The fastest path is to copy an existing metric definition from [`examples/metrics/`](../examples/metrics/):

| Category | Available Examples |
|----------|--------------------|
| Binary Classification | Positive-class error profile, Gini coefficient, PSI, AUC, detection/acceptance profile |
| Regression | Core accuracy (PPE), MAE, percentage error distribution, RMSE |
| Multi-classification | Jaccard similarity, label coverage, confusion matrix, F1 per label |
| Data Quality | Nullable counts, category distributions, drift scores |

Each file contains the complete SQL, argument configuration, and reported metric settings — ready to paste into the UI.

### Creating a Custom Metric in the UI (Overview)

Navigate to **Custom Metrics** in the left nav and click **+ New Custom Metric**. There are four things to fill in:

| Step | What You Do |
|------|-------------|
| **1. SQL Query** | Write or paste a DuckDB SQL query that outputs a time-series result using `time_bucket()` and `{{template_variables}}` |
| **2. Basic Information** | Name, description, and optional model problem type |
| **3. Aggregate Arguments** | Define one argument per `{{variable}}` — specifying whether it's a Dataset, Column, or Literal value |
| **4. Reported Metrics** | Map each output column of your SQL to a named time series stored in Arthur |

After saving the definition, attach it to a model via **Model Management → Metric Configuration → Add Custom Metric**, fill in the argument values, and it runs on the next scheduled job.

> **Need to write SQL from scratch?** See the [Custom Metrics Deep-Dive](./custom-metrics-deep-dive.md) for the full SQL authoring guide: template variable syntax, NULL handling patterns, dimension columns, multi-output queries, and advanced patterns (confusion matrix, array operations, Jaccard similarity).

### Automating Custom Metric Creation (Python SDK)

If you'd rather not use the UI, the SDK scripts create and attach custom metrics in one step:

```bash
# Binary classification — 7-metric error profile
python scripts/onboarding/create-positive-class-error-profile.py

# Regression — absolute error, forecast error, percentage error
python scripts/onboarding/create-regression-error-profile.py
```

---

## 5. Onboarding a Model with Metrics

### Overview

Model onboarding is the process of registering your model in Arthur and configuring which metrics to calculate. The full workflow:

```
Project → Connector → Dataset → Model → Metrics → Schedule
```

### How to Onboard a Model (UI)

1. Inside your project, click **+ ADD → ML Model**.
2. Enter a **Model Name** and click **Next**.
3. On the dataset step, select the dataset you created in step 3 (or create a new one).
4. On the metric configuration step (optional during setup), add built-in aggregations or skip to add later.
5. Click **Submit** — you are redirected to the model overview page.

### How to Add Built-in Metrics to a Model

After the model exists, navigate to **Model Management → Metric Configuration → + Add Metric** and choose from:

| Metric | Use For |
|--------|---------|
| **Inference Count** | Total predictions per time bucket |
| **Numeric Distribution** | Min/max/mean/stddev of any numeric column |
| **Numeric Sum** | Running total of a column |
| **Category Count** | Count per category value |
| **Nullable Count** | Track data quality / missing values |
| **MAE** | Mean Absolute Error (regression) |
| **MSE** | Mean Squared Error (regression) |
| **Confusion Matrix** | TP/FP/TN/FN counts (binary classification) |

### How to Onboard a Model (Python SDK)

**Binary classification model:**

```bash
# Step 1: Create connector, dataset, model, and schedule
python scripts/onboarding/model-onboarding.py

# Step 2: Add domain-specific metrics
python scripts/onboarding/add-fraud-model-aggregations.py

# Step 3 (optional): Add custom SQL error analysis
python scripts/onboarding/create-positive-class-error-profile.py
```

**Regression model:**

```bash
# Step 1: Create connector, dataset, model, and schedule
python scripts/onboarding/housing-price-onboarding.py

# Step 2: Add regression metrics
python scripts/onboarding/add-regression-model-aggregations.py

# Step 3 (optional): Add custom SQL error analysis
python scripts/onboarding/create-regression-error-profile.py
```

### Scheduling Data Refresh

After a model is set up, schedule automatic data refreshes:

1. Navigate to **Model Settings → Data Refresh Schedule**.
2. Choose a frequency — **Hourly** is the default and recommended for production models.
3. Click **Save**.

To trigger a one-time refresh immediately: **Model Overview → Refresh Data Now**.

---

## 6. Building Dashboards

### What Dashboards Do

Dashboards are the primary interface for monitoring your model over time. They display metric time series as interactive charts, allowing you to:

- Track model performance and data quality over days, weeks, or months
- Compare metric values across time periods or model versions
- Identify degradation trends, sudden drops, or anomalies

### Accessing Your Dashboard

1. Navigate to your project and open your model.
2. Click the **Dashboard** tab.
3. The default dashboard is pre-populated with built-in metric charts once data is available.

### Customizing the Dashboard

**To add a chart:**
1. Click **Customize Dashboard** (or the edit/pencil icon).
2. Click **+ Add Chart**.
3. Select a chart type and configure it (see [Section 7](#7-creating-new-charts)).

**To rearrange charts:**
- Drag and drop charts into the order you want.

**To set a time range:**
- Use the **date selector** at the top of the dashboard to zoom in or out.

**To filter by model version:**
- Use the **Version** selector to compare metrics from different model versions side by side.

### Dashboard Best Practices

- **Lead with volume**: Put inference count first — a spike or drop in volume is often the first sign of a data issue.
- **Group by theme**: Keep accuracy metrics together, data quality metrics together, and operational metrics together.
- **Use consistent time buckets**: Match the `time_bucket_gapfill` interval in your chart SQL to the refresh frequency of your data.
- **Pin critical metrics**: Keep your most important SLA metric (e.g., core accuracy) at the top.

---

## 7. Creating New Charts

### How Charts Work

Charts in Arthur are built on SQL queries against the **metrics tables** — not raw inference data. The two tables you query are:

| Table | Contents |
|-------|----------|
| `metrics_numeric_latest_version` | Scalar metrics (counts, rates, averages) |
| `metrics_sketch_latest_version` | Distribution metrics (histograms, percentile summaries) |

Both tables share the same schema:

| Column | Type | Description |
|--------|------|-------------|
| `model_id` | uuid | Model identifier |
| `metric_name` | varchar | Name of the reported metric (from custom metric Step 4) |
| `timestamp` | timestamptz | Time bucket timestamp |
| `metric_version` | integer | Metric version number |
| `value` | double precision | The metric value |
| `dimensions` | jsonb | Key-value dimension data |

### Step-by-Step: Creating a Chart

1. In the Dashboard editor, click **+ Add Chart**.
2. Give the chart a **title**.
3. Select the **chart type** (line, bar, area, etc.).
4. Enter the **SQL query** that fetches the metric data.

### Standard Chart SQL Template

```sql
SELECT
    time_bucket_gapfill(
        '1 day',                            -- Time bucket size (match your data frequency)
        timestamp,
        '{{dateStart}}'::timestamptz,       -- Dashboard date range start
        '{{dateEnd}}'::timestamptz          -- Dashboard date range end
    ) AS time_bucket_1d,

    metric_name,

    -- Optional: human-friendly display names
    CASE
        WHEN metric_name = 'my_metric_name' THEN 'My Friendly Name'
        ELSE metric_name
    END AS friendly_name,

    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN ('my_metric_name', 'another_metric')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

**Key elements:**

| Element | Purpose |
|---------|---------|
| `time_bucket_gapfill()` | Fills in missing time buckets so the chart has a continuous x-axis (no gaps) |
| `{{dateStart}}` / `{{dateEnd}}` | Template variables populated by the dashboard date picker |
| `[[AND ...]]` | Optional filter syntax — Arthur wraps these filters only when values are present |
| `metric_name IN (...)` | Filter to the specific metrics you want — must match names from **Reported Metrics** |
| `COALESCE(AVG(value), 0)` | Handles NULL gracefully; shows 0 for gaps |

### Example Charts

#### Inference Volume Over Time

```sql
SELECT
    time_bucket_gapfill('1 day', timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,
    COALESCE(SUM(value), 0) AS inference_count
FROM metrics_numeric_latest_version
WHERE metric_name = 'inference_count'
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
GROUP BY time_bucket_1d
ORDER BY time_bucket_1d;
```

#### Core Accuracy Rate (Regression)

```sql
SELECT
    time_bucket_gapfill('1 day', timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,
    metric_name,
    COALESCE(AVG(value), 0) * 100 AS metric_pct
FROM metrics_numeric_latest_version
WHERE metric_name IN ('core_accuracy_rate', 'avg_percentage_error')
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

#### False Positive Rates (Binary Classification)

```sql
SELECT
    time_bucket_gapfill('1 day', timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,
    metric_name,
    CASE
        WHEN metric_name = 'adjusted_false_positive_rate' THEN 'Adj FP Rate'
        WHEN metric_name = 'false_positive_ratio'         THEN 'FP Ratio'
        WHEN metric_name = 'bad_case_rate'                THEN 'Bad Case Rate'
        ELSE metric_name
    END AS friendly_name,
    COALESCE(AVG(value), 0) AS metric_value
FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'adjusted_false_positive_rate',
    'false_positive_ratio',
    'bad_case_rate'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]
GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

#### Filtering by Dimension

If your metric has dimension columns, filter on them using the `dimensions` JSONB field:

```sql
-- Show metrics for a specific region
WHERE metric_name = 'accuracy_rate'
  AND dimensions->>'region' = 'northeast'
```

### Chart Configuration Tips

- **Line charts**: Best for trends over time (accuracy, error rates, counts)
- **Bar charts**: Best for discrete comparisons (category counts, confusion matrix)
- **Dual Y-axis**: Use when overlaying metrics with different scales (e.g., accuracy % + prediction volume)
- **Target line**: Add a horizontal reference at your SLA threshold (e.g., 80% accuracy)
- **Color coding**: Green for healthy, yellow for warning, red for critical

---

## 8. Creating Webhooks

### What Webhooks Do

Webhooks send real-time HTTP POST notifications to external systems when events occur in Arthur — for example, when an alert fires. Use webhooks to integrate Arthur with Slack, Jira, PagerDuty, or any custom endpoint.

### How Webhooks Work in Arthur

1. An event occurs in Arthur (e.g., alert rule fires).
2. Arthur sends an HTTP POST request to your configured endpoint URL.
3. The payload contains event details in JSON format (timestamp, model ID, metric values, etc.).
4. Your receiving system processes the payload and takes action (posts to Slack, creates a Jira ticket, etc.).

### How to Create a Webhook

1. Navigate to **Settings → Webhooks** (or **Project Settings → Webhooks**).
2. Click **+ New Webhook**.
3. Configure the webhook:

| Field | Description |
|-------|-------------|
| **Name** | Human-readable label (e.g., `Slack - ML Alerts Channel`) |
| **Endpoint URL** | The HTTPS URL that will receive the POST payload |
| **Authentication** | Token passed in the URL query string or as a header |
| **Payload Template** | Customize the JSON body sent to the endpoint |

4. Click **Test Webhook** to send a test payload and verify the endpoint responds.
5. Click **Save**.

### Slack Integration

1. In Slack, create an **Incoming Webhook** for your alerts channel (Apps → Incoming Webhooks → Add New Webhook).
2. Copy the Webhook URL (format: `https://hooks.slack.com/services/...`).
3. In Arthur, create a new webhook with that URL.
4. Customize the payload template to format the Slack message:

```json
{
  "text": "Arthur Alert: {{alert_name}} fired on model {{model_name}}",
  "attachments": [{
    "color": "danger",
    "fields": [
      { "title": "Metric", "value": "{{metric_name}}", "short": true },
      { "title": "Value", "value": "{{metric_value}}", "short": true },
      { "title": "Threshold", "value": "{{threshold}}", "short": true },
      { "title": "Time", "value": "{{timestamp}}", "short": true }
    ]
  }]
}
```

### Jira Integration

1. In Jira, generate an API token for a service account.
2. Use the Jira REST API endpoint as your webhook URL:
   `https://your-org.atlassian.net/rest/api/3/issue`
3. Set the Authorization header to `Bearer <your-api-token>`.
4. Customize the payload to create a Jira issue:

```json
{
  "fields": {
    "project": { "key": "ML" },
    "summary": "Arthur Alert: {{alert_name}} on {{model_name}}",
    "description": "Metric {{metric_name}} = {{metric_value}} exceeded threshold {{threshold}}.",
    "issuetype": { "name": "Bug" },
    "priority": { "name": "High" }
  }
}
```

---

## 9. Creating Alerts

### What to Alert On

Effective alerts catch real problems without creating noise. Use the tables below as starting points, then see the [model-specific examples](#model-specific-alert-examples) further down for concrete thresholds grounded in the two reference datasets.

#### Critical Alerts (Immediate Response Required)

| Metric | Condition | Why |
|--------|-----------|-----|
| **Inference Count** | Drops to 0 for any 1-hour window | Data pipeline failure — model is not receiving data |
| **Inference Count** | Drops >50% versus prior 24-hour average | Major upstream disruption |
| **Core Accuracy Rate** | Falls below 70% (regression) | Model predictions are unreliable; SLA breach likely |
| **False Positive Rate** | Spikes >20 percentage points above baseline | Model regression or threshold shift — operational impact |
| **Null Count** | Any required column exceeds 10% null rate | Data quality failure upstream |

#### Warning Alerts (Investigate Within 24 Hours)

| Metric | Condition | Why |
|--------|-----------|-----|
| **Core Accuracy Rate** | Falls below 80% for 2+ consecutive days | Sustained performance degradation — begin investigation |
| **Prediction Distribution Mean** | Deviates >2 standard deviations from 30-day baseline | Possible input drift or model behavior shift |
| **False Positive Ratio** | Rising trend over 7 days | Gradual model degradation |
| **Bad Case Rate** | Exceeds 30% (binary classification) | Model over-predicting positives |
| **MAE / MSE** | Exceeds 1.5× rolling 30-day average (regression) | Error increasing — consider retraining |

#### Informational Alerts (Review Weekly)

| Metric | Condition | Why |
|--------|-----------|-----|
| **Inference Count** | 20% week-over-week change | Volume trend worth tracking for capacity planning |
| **Accuracy Rate** | 5+ percentage point improvement | Validate that a model update is working as expected |

### How to Create an Alert Rule

1. Navigate to **Alerts** in the left nav and click **+ New Alert Rule**.
2. Configure the alert:

| Field | Description |
|-------|-------------|
| **Name** | Descriptive name (e.g., `Fraud Model - Accuracy Below SLA`) |
| **Model** | Select the model to monitor |
| **SQL Query** | The query that computes the metric value to evaluate |
| **Condition** | The threshold check (e.g., `value < 0.80`) |
| **Evaluation Window** | How far back the query looks (e.g., last 24 hours) |
| **Frequency** | How often the rule is evaluated (e.g., every 1 hour) |
| **Notification** | Webhook(s) to fire when the alert triggers |

Alert queries follow the same SQL as dashboard charts, but without date template variables — Arthur injects the time window automatically:

```sql
SELECT AVG(value) AS alert_metric
FROM metrics_numeric_latest_version
WHERE metric_name = 'core_accuracy_rate'
  AND timestamp >= NOW() - INTERVAL '24 hours';
```

### Model-Specific Alert Examples

The thresholds below are grounded in the two reference datasets included in this repository. Adjust them based on your own model's observed baseline before going to production.

---

#### Card Fraud Model (Binary Classification)

**Data characteristics** (from [`data/binary-classifier-card-fraud/datagen/generate_dataset.py`](../data/binary-classifier-card-fraud/datagen/generate_dataset.py)):
- ~60 transactions/hour → ~1,440/day
- Base fraud rate ~5%, rising to ~15% for new customers, high-value transactions (>$500), or ATM channel
- Model prediction column: `fraud_score` (float 0–1); binary decision column: `fraud_pred` (0/1 at 0.5 threshold); ground truth: `is_fraud`

**Metrics produced by** [`create-positive-class-error-profile.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/create-positive-class-error-profile.py) and [`add-fraud-model-aggregations.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/add-fraud-model-aggregations.py):

| Alert Name | Metric | Condition | Severity | Rationale |
|------------|--------|-----------|----------|-----------|
| Pipeline down | `inference_count` | `SUM < 1` over 1 h | Critical | ~60 txn/h expected; zero means no data is arriving |
| Volume drop | `inference_count` | `SUM < 500` over 24 h | Critical | Normal ~1,440/day; <500 suggests >65% drop |
| Null fraud score | `nullable_count_fraud_score` | `AVG > 0.05` over 24 h | Critical | `fraud_score` must be populated; >5% nulls breaks downstream decisioning |
| FP spike | `adjusted_false_positive_rate` | `AVG > 0.25` over 24 h | Critical | FP/(FP+TN) — normal ~10–15% given base rates; >25% triggers excessive customer friction |
| Bad case rate high | `bad_case_rate` | `AVG > 0.20` over 24 h | Warning | Actual fraud fraction in data; >20% likely means a population shift or data issue |
| FP ratio rising | `false_positive_ratio` | `AVG > 0.15` over 24 h | Warning | FP/Total; baseline ~5–8%; sustained >15% means review threshold or retrain |
| Detection rate falling | `valid_detection_rate` | `AVG < 0.85` over 24 h | Warning | (TP+TN)/Total overall accuracy; <85% is a notable degradation from expected ~90%+ |

**Example SQL — FP spike alert:**

```sql
-- Metric produced by create-positive-class-error-profile.py
SELECT AVG(value) AS adj_fpr
FROM metrics_numeric_latest_version
WHERE metric_name = 'adjusted_false_positive_rate'
  AND timestamp >= NOW() - INTERVAL '24 hours';
```
**Condition**: `adj_fpr > 0.25`

**Example SQL — volume drop alert:**

```sql
-- Metric produced by add-fraud-model-aggregations.py
SELECT COALESCE(SUM(value), 0) AS daily_inferences
FROM metrics_numeric_latest_version
WHERE metric_name = 'inference_count'
  AND timestamp >= NOW() - INTERVAL '24 hours';
```
**Condition**: `daily_inferences < 500`

---

#### Housing Price Prediction Model (Regression)

**Data characteristics** (from [`data/regression-housing-price-prediction/datagen/generate_dataset.py`](../data/regression-housing-price-prediction/datagen/generate_dataset.py)):
- California housing dataset; median house values typically $50k–$500k
- Model error: ~8% standard deviation; predictions clipped to 50–200% of actual value
- Prediction column: `predicted_house_value`; ground truth: `actual_house_value`

**Metrics produced by** [`create-regression-error-profile.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/create-regression-error-profile.py) and [`add-regression-model-aggregations.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/add-regression-model-aggregations.py). Core accuracy metric from [`examples/metrics/regression/core-accuracy-ppe-10pct.md`](../examples/metrics/regression/core-accuracy-ppe-10pct.md):

| Alert Name | Metric | Condition | Severity | Rationale |
|------------|--------|-----------|----------|-----------|
| Pipeline down | `inference_count` | `SUM < 1` over 1 h | Critical | Zero inferences means no data is flowing |
| Accuracy SLA breach | `core_accuracy_rate` | `AVG < 0.70` over 24 h | Critical | At 8% std, ~80–85% of predictions should fall within 10%; <70% suggests a model or data issue |
| Avg error spike | `avg_percentage_error` | `AVG > 0.20` over 24 h | Critical | Normal ~8–12%; >20% average error means systematic mis-prediction — check for feature drift |
| Null predictions | `nullable_count_predicted_house_value` | `AVG > 0.05` over 24 h | Critical | >5% null predictions means the model or pipeline is failing |
| Accuracy degrading | `core_accuracy_rate` | `AVG < 0.80` for 2+ consecutive days | Warning | Below comfortable SLA; investigate data drift before it worsens |
| Systematic over/underprediction | `forecast_error` | Sketch P50 deviates >15% from 30-day median | Warning | Signed error (prediction − actual); a shifting median signals drift in a specific direction |

**Example SQL — accuracy SLA alert:**

```sql
-- Metric produced by the core-accuracy-ppe-10pct custom metric
-- (examples/metrics/regression/core-accuracy-ppe-10pct.md)
SELECT AVG(value) AS accuracy_rate
FROM metrics_numeric_latest_version
WHERE metric_name = 'core_accuracy_rate'
  AND timestamp >= NOW() - INTERVAL '24 hours';
```
**Condition**: `accuracy_rate < 0.70`

**Example SQL — average error spike alert:**

```sql
-- Metric produced by the core-accuracy-ppe-10pct custom metric
SELECT AVG(value) AS avg_pct_error
FROM metrics_numeric_latest_version
WHERE metric_name = 'avg_percentage_error'
  AND timestamp >= NOW() - INTERVAL '24 hours';
```
**Condition**: `avg_pct_error > 0.20`

---

### Attaching Webhooks to Alerts

After creating a webhook in step 8:

1. In the alert rule configuration, scroll to **Notifications**.
2. Click **+ Add Notification**.
3. Select the webhook you created.
4. Optionally add email addresses for additional notification paths.
5. Save the alert rule.

### Alert Management Tips

- **Start conservative**: Set initial thresholds wider than you think necessary. Tune based on false positive rate after 2–4 weeks.
- **Use layered severity**: Use separate Slack channels or Jira priorities for critical vs. warning alerts.
- **Document each alert**: Include a runbook link or investigation checklist in the alert description so on-call engineers know what to check.
- **Review alerts monthly**: Retire alerts that are never firing or always firing — both indicate misconfiguration.

---

## 10. Updating Your Setup

The sections above cover first-time setup. The notes below cover the three most common post-onboarding changes.

### Updating a Dataset Schema

**Adding a column** — when the upstream data source introduces a new field:

1. Confirm the column already exists in the actual data files (Arthur does not backfill).
2. Run [`add-column-to-schema.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/add-column-to-schema.py), setting `DATASET_ID` and `COLUMN_TO_ADD` at the top of the script. The script rejects the operation if the column already exists in the schema.
3. After the column is registered, add any metrics that reference it via **Model Management → Metric Configuration**.

**Removing a column** — when a field is dropped upstream:

1. First remove any aggregation specs that reference the column from the model's metric configuration. Removing a column that a metric still references will break that metric.
2. Run [`remove-column-from-schema.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/remove-column-from-schema.py), setting `DATASET_ID` and `COLUMN_TO_REMOVE`.

**Replacing a dataset entirely** — when the data source changes (new S3 bucket, schema version bump) but the model stays the same:

Run [`duplicate-metrics-to-new-datasets.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/duplicate-metrics-to-new-datasets.py). It copies all aggregation specs from the old dataset to the new one, remapping column IDs by `source_name`. Configure `DATASET_MAPPING` at the top of the script with the old-to-new dataset ID pairs. This replaces specs on the new dataset only — the old dataset specs are left untouched.

> **Note:** The schema inspection job samples files from approximately ±90 days of the current date. Ensure new files exist in that range before adding columns or registering a replacement dataset. See the [`scripts/onboarding/README.md` troubleshooting section](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md#schema-inspection-job-fails) if the inspection job fails.

### Changing a Custom Metric Definition

When you edit a custom metric's SQL or argument configuration and save it, Arthur creates a **new version** of that metric. Models already using it are not affected — they remain pinned to the previous version until you explicitly update their configuration.

To roll a model forward to the new version:

1. Navigate to **Model Management → Metric Configuration**.
2. Find the custom metric and click **Update to Latest Version**.
3. Review the argument mappings (column assignments carry over, but verify any new or renamed arguments).
4. Save — the updated metric runs on the next scheduled job.

To copy a custom metric definition to a different Arthur workspace (e.g., staging → production), run [`migrate-custom-aggregation-definitions.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/migrate-custom-aggregation-definitions.py). It matches definitions by name and skips any that already exist in the destination. Always run this before [`migrate-model-metric-config.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/migrate-model-metric-config.py) when migrating a model, since that script looks up custom definitions by name in the destination workspace.

> The versioning mechanism is described in detail in the [Custom Metric Creation Guide](../references/how-to-create-a-custom-metric.md#versioning) and the [Custom Metrics Deep-Dive](./custom-metrics-deep-dive.md#3-step-2--basic-information).

### Swapping a Connector

**Updating credentials on an existing connector** (e.g., rotating an AWS access key):

1. Navigate to **Project Settings → Connectors**.
2. Click the connector and edit the credential fields directly in the UI.
3. Click **Test Connection** to verify the new credentials, then **Save**.

No downstream objects (datasets, models, metrics) are affected — they reference the connector by ID, not by credential value.

**Migrating connectors to a new project or environment:**

Run [`migrate-connectors.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/migrate-connectors.py). It copies the structural configuration (bucket, region, host, etc.) of all connectors from a source project to a destination project, stripping credential fields so they are never transmitted. After the script runs, go to the destination project's connector list in the UI and fill in credentials for each connector.

The script supports S3, GCS, BigQuery, Snowflake, ODBC, and Shield connectors. `ENGINE_INTERNAL` connectors are skipped — they have no API-configurable fields. See the [script reference](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md#migrate-connectorspy) for the full field mapping per connector type.

### Deleting Resources

Not all deletions behave the same way. Before removing anything, check whether it is reversible:

| Resource | Delete type | What happens |
|----------|------------|--------------|
| Tasks | Soft | Archived (`archived=True`); not visible in the UI but recoverable via API |
| Metrics (aggregation specs) | Soft | Archived; historical metric values are retained in the metrics tables |
| Alert rules | Soft | Archived; alert history is preserved |
| Datasets | **Hard** | Permanent. All associated schema definitions and file pattern config are removed. Historical metric values stored in the metrics tables are **not** deleted, but you lose the ability to re-run metrics against this dataset. |
| Model providers | **Hard** | Permanent. |
| LLM Evaluations | **Hard** | Permanent. |
| Documents | **Hard** | Permanent. |

> **Before deleting a dataset**: export any schema configuration you may need later (connector type, file prefix/suffix, column list). There is no UI export — copy the values from the dataset settings page or retrieve them via the SDK before deleting.

Connectors and models are not listed above — deleting a connector will fail if any active dataset still references it; delete the datasets first. Model deletion behaviour follows platform version — confirm in the UI before proceeding.

---

## 11. Troubleshooting

The failures below account for the large majority of first-time setup issues. Each entry links to the source documentation where the fix originated.

---

### Where to find logs

Before diving into a specific failure, use the right diagnostic surface for the type of problem:

| Log surface | How to access | Best for |
|-------------|---------------|----------|
| **Activity Log** | Model Overview → Activity Log | Quick check: did the last metrics job succeed or fail? Shows per-job pass/fail and high-level error messages. |
| **Engine-level logs** | Arthur UI → Workspace Settings → Engines → select engine → Logs tab | Detailed error traces from the data-plane computation (SQL errors, connector read failures, memory/timeout errors). Use this when the activity log shows a failure but no useful message. |
| **Job Status API** | `GET /api/v1/jobs/{job_id}` — job IDs are returned by refresh and onboarding API calls, or listed via `GET /api/v1/models/{model_id}/jobs` | Programmatic status checks; useful in CI/CD pipelines or when running SDK scripts and you need the exact error payload. |
| **SDK script output** | stdout/stderr of your Python script | Script-level failures (auth errors, missing columns, API validation). Always run scripts with output visible — add `logging.basicConfig(level=logging.DEBUG)` at the top when debugging SDK calls. |

**Tip:** For most metric calculation failures, start with the Activity Log, then move to the Engine-level logs if the activity log message is generic (e.g., "Job failed"). The engine logs contain the actual SQL error or stack trace.

---

### Connector won't connect / test fails

**Symptom:** The "Test Connection" button returns an error or times out.

| Cause | Fix |
|-------|-----|
| Wrong credentials | Re-enter the access key, secret, or password. For S3, verify the key belongs to the correct AWS account. |
| Wrong region | S3 bucket region must match the `region` field — a `us-east-1` bucket configured as `us-west-2` will fail. |
| IAM role not assumed | If using a Role ARN, verify the role's trust policy allows Arthur's service account to assume it, and that `external_id` (if set) matches exactly. |
| GCS/BigQuery credentials format | If you **do** need to supply credentials: the `credentials` field expects a JSON string, not a file path. Keep it on one line in your `.env` file; see the [scripts README credentials section](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md#environment-variables). If your DevOps/Admin has set up Workload Identity or a pre-attached service account on the Engine, leave this field blank — no JSON needed. |
| Network / firewall | Arthur Engine must be able to reach the data source from your VPC. Check that egress rules allow traffic to the S3 endpoint or database host. |

---

### 403 / Permission Denied

**Symptom:** A UI action fails with a "403 Forbidden" or "Permission Denied" error; an SDK call raises an `AuthorizationError`; or a user can see a project but cannot perform a specific action (e.g., edit a model, add an aggregation, create an alert).

Arthur enforces role-based access control at the project level (see [Prerequisites — Platform Access](#prerequisites)). The four roles and their permissions are:

| Role | Can do |
|------|--------|
| User | View dashboards, run queries |
| Model Owner | All of the above + edit models, configure metrics, create alerts |
| Administrator | All of the above + manage connectors, datasets, webhooks, project settings |
| SuperAdmin | All of the above + manage users, create new projects |

**Fix steps:**

1. **Identify the required role.** Connector and dataset management require **Administrator**. Model/metric configuration requires **Model Owner**. Creating projects requires **SuperAdmin**.
2. **Check your current role.** Navigate to **Project Settings → Members** (Administrator access needed to see this page) or ask your project Administrator to check.
3. **Request a role upgrade.** A project Administrator or SuperAdmin can change your role from **Project Settings → Members → Edit**.
4. **For SDK 403 errors:** Verify the token or service account being used is a member of the correct project with the required role. Service accounts have their own membership — they must be added to the project separately from human users. See [`scripts/onboarding/service-account-creation.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/service-account-creation.py).
5. **For Engine-level 403:** If the Arthur Engine itself is getting a 403 when it tries to read from your data source (S3, GCS, etc.), that is a data-source permission issue, not an Arthur RBAC issue — see [Connector won't connect / test fails](#connector-wont-connect--test-fails) above.

---

### Schema inspection job fails

**Symptom:** Job state shows `FAILED`; no schema is returned and the dataset cannot be saved.

Source: [`scripts/onboarding/README.md`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md#schema-inspection-job-fails)

Work through this checklist in order:

1. The IAM role or service account used by the connector has **read and list** access on the bucket — list is required for the inspection job to enumerate files.
2. `file_prefix` exactly matches the key prefix in S3 (e.g., `inferences/%Y/%m/%d` not `inferences/%Y/%m/%d/` with a trailing slash).
3. `file_suffix` is a valid regex that matches at least some actual file names (test it locally: `import re; re.match(r'.*.parquet', 'your_file.parquet')`).
4. `data_file_type` matches the actual file format (`json`, `parquet`, or `csv` — not the file extension itself).
5. Files exist within approximately ±90 days of today. The dataset generators in [`data/*/datagen/`](../data/) default to this range; production files must also be present in this window.

---

### "Data plane not associated with project" (SDK)

**Symptom:** Script exits with an error containing "data plane not associated with project" or similar.

**Cause:** Multiple data planes exist in the workspace and the one that was auto-detected doesn't belong to your project.

**Fix:** Log into the Arthur UI, navigate to your project settings, and copy the data plane ID associated with that project. Set `DATA_PLANE_ID` explicitly at the top of the onboarding script instead of leaving it blank.

Source: [`scripts/onboarding/README.md`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md#data-plane-not-associated-with-project)

---

### Metrics not appearing after model onboarding

**Symptom:** Model overview page shows no data or charts are empty after running an onboarding script.

Source: [`scripts/onboarding/README.md`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md#metrics-not-appearing-in-the-ui)

1. **Wait for the next scheduled run.** Metrics jobs run hourly by default; it can take up to an hour after onboarding before data appears. Use **Refresh Data Now** on the model overview to trigger an immediate run.
2. **Check the Activity Log.** Navigate to **Model Overview → Activity Log** and look for calculation errors on the most recent job. If the error message is generic, escalate to the Engine-level logs (Workspace Settings → Engines → Logs) for the full SQL error or stack trace. See [Where to find logs](#where-to-find-logs) above.
3. **Verify data exists in the query window.** The schedule queries a rolling window around the current time. If your data is older than the window, no rows are processed.
4. **Confirm aggregation specs were attached.** Open **Model Management → Metric Configuration** and verify the expected aggregations are listed. If the list is empty, re-run the relevant aggregations script.

---

### Custom metric returns no values

**Symptom:** A custom metric is configured on the model but shows no data in dashboards or the Metrics Query UI.

Source: [`references/how-to-create-a-custom-metric.md`](../references/how-to-create-a-custom-metric.md#troubleshooting)

1. **Test the SQL directly.** Open the Metrics Query UI, paste the query with literal values substituted for all `{{variables}}`, and run it. If it returns zero rows, the SQL is the issue — not the configuration.
2. **Check aggregate arguments.** Navigate to the model's metric configuration, open the custom metric, and confirm every argument is filled in (none left blank).
3. **Verify the timestamp range.** The query window must overlap with data that exists in the dataset. NULL timestamps are filtered out by `WHERE {{timestamp_col}} IS NOT NULL` — if the timestamp column has high null rates, most rows are excluded.
4. **Check `{{variable}}` completeness.** Every `{{variable_name}}` in the SQL must have a matching Aggregate Argument defined. An undefined variable causes a silent substitution failure. See the [Custom Metrics Deep-Dive §4](./custom-metrics-deep-dive.md#4-step-3--configure-aggregate-arguments).

---

### Dashboard chart shows all zeros or has unexpected gaps

**Symptom:** A chart renders but shows a flat zero line, or has gaps where data should exist.

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Flat zero line | `COALESCE(AVG(value), 0)` converts missing buckets to 0 — the metric may not be running at all | Check the activity log; verify the metric is configured on the model |
| All zeros on a specific metric | `metric_name` in the WHERE clause doesn't match the name set in Reported Metrics (case-sensitive) | Open the custom metric definition and copy the exact Reported Metric name |
| Gaps in an otherwise populated chart | `time_bucket_gapfill()` requires `'{{dateStart}}'` and `'{{dateEnd}}'` — if either is missing or malformed, gap-fill doesn't run | Confirm both template variables are present in the `time_bucket_gapfill()` call |
| Chart shows data for wrong model | Dashboard-level model filter may be missing or overridden | Add `AND model_id = '{{model_id}}'` to the WHERE clause, or confirm the dashboard-wide filter is active |

The metrics table schema and query patterns are documented in [`references/overview-metrics-and-querying.md`](../references/overview-metrics-and-querying.md).

---

### Alert never fires or fires immediately on creation

**Symptom:** An alert rule exists but never triggers despite the condition appearing to be met; or it fires as soon as it's saved.

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Never fires | SQL query returns NULL (metric hasn't run yet or wrong `metric_name`) | Run the query manually in the Metrics Query UI and verify it returns a numeric value |
| Never fires | Condition direction is inverted (e.g., `< 0.8` when the metric is already 0.05) | Re-read the condition; rates are stored as decimals (0.0–1.0), not percentages |
| Fires immediately | Threshold is too tight relative to actual baseline | Widen the threshold; let the model run for 1–2 weeks before setting tight SLA alerts |
| Fires immediately | Metric hasn't accumulated enough history; first job produces a value that crosses the threshold | Set the evaluation window longer (e.g., 7-day average) to smooth early noise |

---

### Column not found (SDK)

**Symptom:** `ValueError: Column 'xyz' not found in dataset schema`

**Fix:** The column name in the script doesn't match the `source_name` stored in Arthur. Print the actual names before configuring:

```python
dataset = datasets_client.get_dataset(dataset_id=DATASET_ID)
print([col.source_name for col in dataset.dataset_schema.columns])
```

Source: [`scripts/onboarding/README.md`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md#column-not-found)

---

### Migration issues

For issues specific to migrating models, connectors, or metric definitions between environments, see [§10 — Updating Your Setup](#10-updating-your-setup) and the detailed fix steps in the [scripts README troubleshooting section](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md#troubleshooting), which covers:

- Dataset names not matched across environments → [`migrate-model-metric-config.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/migrate-model-metric-config.py) guidance
- Custom aggregation not found in destination → run [`migrate-custom-aggregation-definitions.py`](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/migrate-custom-aggregation-definitions.py) first
- Connector creation fails with unknown field → inspect browser network tab for exact field names

---

## Quick Reference: Full Onboarding Checklist

| Step | Action | Tool |
|------|--------|------|
| 1 | Create project | Arthur UI |
| 2 | Associate engine with project | Arthur UI → Workspace Settings |
| 3 | Create data connector | Arthur UI or `model-onboarding.py` |
| 4 | Add dataset with schema | Arthur UI or `model-onboarding.py` |
| 5 | Create model | Arthur UI or `model-onboarding.py` |
| 6 | Add built-in metrics | `add-fraud-model-aggregations.py` or `add-regression-model-aggregations.py` |
| 7 | Create custom metrics | Arthur UI (Custom Metrics) or `create-positive-class-error-profile.py` |
| 8 | Schedule data refresh | Arthur UI → Model Settings |
| 9 | Build dashboard | Arthur UI → Dashboard |
| 10 | Create charts | Arthur UI → Dashboard → Add Chart |
| 11 | Create webhooks | Arthur UI → Settings → Webhooks |
| 12 | Create alert rules | Arthur UI → Alerts |

---

## See Also

- [Onboarding Scripts Reference](https://github.com/arthur-ai/arthur-custom-metrics/tree/main/scripts/onboarding/README.md) — Full SDK automation guide
- [Custom Metric Examples](../examples/metrics/) — Production-ready SQL for binary classification, regression, and multi-classification
- [Dashboard Chart Examples](../examples/charts/) — Ready-to-paste chart SQL queries
- [Custom Metric Creation Guide](../references/how-to-create-a-custom-metric.md) — Detailed SQL patterns and advanced techniques
- [Metrics & Querying Overview](../references/overview-metrics-and-querying.md) — Metrics table schema and query language reference
- [Configuration Options](../references/configuration-options.md) — Valid values for all configuration fields
