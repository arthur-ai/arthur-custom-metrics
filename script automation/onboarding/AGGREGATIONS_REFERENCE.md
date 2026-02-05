# Aggregations Reference Guide

Complete reference for all available aggregation types in Arthur (from `arthur-common/src/arthur_common/aggregations/functions/`).

Use with the `add-custom-aggregations.py` script.

## Complete List of Aggregations

Source: `/Users/ibrahim/Documents/GitLab/arthur-common/src/arthur_common/aggregations/functions/README.md`

### Basic Metrics

| ID | Name | Purpose |
|----|------|---------|
| `00000000-0000-0000-0000-00000000000a` | **Inference Count** | Total number of inferences |
| `00000000-0000-0000-0000-00000000000b` | **Null Value Count** | Count missing/null values |
| `00000000-0000-0000-0000-00000000000c` | **Category Count** | Count categorical values |
| `00000000-0000-0000-0000-00000000000d` | **Numeric Distribution** | Min/max/mean/std of numeric column |
| `00000000-0000-0000-0000-00000000000f` | **Numeric Sum** | Sum of numeric column |

### Binary Classification

| ID | Name | Purpose |
|----|------|---------|
| `00000000-0000-0000-0000-00000000001c` | **Confusion Matrix - Int/Bool** | Confusion matrix for int/bool ground truth |
| `00000000-0000-0000-0000-00000000001d` | **Confusion Matrix - String** | Confusion matrix for string ground truth |
| `00000000-0000-0000-0000-00000000001e` | **Confusion Matrix - Probability** | Confusion matrix with probability threshold |
| `00000000-0000-0000-0000-00000000001f` | **Count by Class - Class Label** | Count by actual class label |
| `00000000-0000-0000-0000-000000000020` | **Count by Class - Probability** | Count by probability threshold |

### Regression

| ID | Name | Purpose |
|----|------|---------|
| `00000000-0000-0000-0000-00000000000e` | **Mean Absolute Error** | MAE between prediction and ground truth |
| `00000000-0000-0000-0000-000000000010` | **Mean Squared Error** | MSE between prediction and ground truth |

### GenAI / Shield Metrics

| ID | Name | Purpose |
|----|------|---------|
| `00000000-0000-0000-0000-000000000001` | **Pass/Fail Count** | Shield inference pass/fail counts |
| `00000000-0000-0000-0000-000000000002` | **Rule Result Count** | Count of rule evaluation results |
| `00000000-0000-0000-0000-000000000003` | **Hallucination Count** | Count of detected hallucinations |
| `00000000-0000-0000-0000-000000000004` | **Toxicity Distribution** | Toxicity score distribution |
| `00000000-0000-0000-0000-000000000005` | **PII Score Distribution** | PII detection score distribution |
| `00000000-0000-0000-0000-000000000006` | **Claim Count** | Total claim count distribution |
| `00000000-0000-0000-0000-000000000007` | **Valid Claim Count** | Valid (passing) claim count |
| `00000000-0000-0000-0000-000000000008` | **Invalid Claim Count** | Invalid (failing) claim count |
| `00000000-0000-0000-0000-000000000009` | **Rule Latency** | Rule execution latency distribution |
| `00000000-0000-0000-0000-000000000021` | **Token Count** | Token usage count |

### Multiclass Classification

| ID | Name | Purpose |
|----|------|---------|
| `64a338fb-6c99-4c40-ba39-81ab8baa8687` | **Count by Class** | Multiclass count by class label |
| `dc728927-6928-4a3b-b174-8c1ec8b58d62` | **Confusion Matrix Single Class** | Single class confusion matrix |

---

## Most Commonly Used

---

## Detailed Aggregation Examples

### 1. Inference Count (`00000000-0000-0000-0000-00000000000a`)

**Purpose**: Track total number of inferences over time

**Required Args**:
- `dataset`: Dataset ID
- `timestamp_col`: Timestamp column ID

**Example**:
```python
AggregationSpec(
    aggregation_id="00000000-0000-0000-0000-00000000000a",
    aggregation_init_args=[],
    aggregation_args=[
        MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
        MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
    ],
)
```

**Use Cases**:
- Monitor inference volume
- Detect traffic anomalies
- Capacity planning

---

### 2. Nullable Count (`00000000-0000-0000-0000-00000000000b`)

**Purpose**: Track missing/null values for a specific column

**Required Args**:
- `dataset`: Dataset ID
- `timestamp_col`: Timestamp column ID
- `nullable_col`: Column ID to check for nulls

**Example**:
```python
AggregationSpec(
    aggregation_id="00000000-0000-0000-0000-00000000000b",
    aggregation_init_args=[],
    aggregation_args=[
        MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
        MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
        MetricsArgSpec(arg_key="nullable_col", arg_value=feature_col_id),
    ],
)
```

**Use Cases**:
- Data quality monitoring
- Detect missing feature values
- Pipeline health checks

---

### 3. Numeric Distribution (`00000000-0000-0000-0000-00000000000d`)

**Purpose**: Calculate min/max/mean/std deviation for numeric columns

**Required Args**:
- `dataset`: Dataset ID
- `timestamp_col`: Timestamp column ID
- `numeric_col`: Numeric column ID

**Example**:
```python
AggregationSpec(
    aggregation_id="00000000-0000-0000-0000-00000000000d",
    aggregation_init_args=[],
    aggregation_args=[
        MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
        MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
        MetricsArgSpec(arg_key="numeric_col", arg_value=prediction_col_id),
    ],
)
```

**Use Cases**:
- Monitor prediction score drift
- Track feature distributions
- Detect data distribution shifts

---

### 4. Numeric Sum (`00000000-0000-0000-0000-00000000000f`)

**Purpose**: Calculate sum of a numeric column over time

**Required Args**:
- `dataset`: Dataset ID
- `timestamp_col`: Timestamp column ID
- `numeric_col`: Numeric column ID

**Example**:
```python
AggregationSpec(
    aggregation_id="00000000-0000-0000-0000-00000000000f",
    aggregation_init_args=[],
    aggregation_args=[
        MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
        MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
        MetricsArgSpec(arg_key="numeric_col", arg_value=amount_col_id),
    ],
)
```

**Use Cases**:
- Total transaction amounts
- Cumulative predictions
- Volume tracking

---

### 5. Inference Count by Class (`00000000-0000-0000-0000-000000000020`)

**Purpose**: Track inference counts segmented by predicted class (binary classification)

**Required Args**:
- `dataset`: Dataset ID
- `timestamp_col`: Timestamp column ID
- `prediction_col`: Prediction score column ID
- `threshold`: Threshold value (e.g., 0.5)
- `true_label`: Label for values >= threshold
- `false_label`: Label for values < threshold

**Example**:
```python
AggregationSpec(
    aggregation_id="00000000-0000-0000-0000-000000000020",
    aggregation_init_args=[],
    aggregation_args=[
        MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
        MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
        MetricsArgSpec(arg_key="prediction_col", arg_value=prediction_col_id),
        MetricsArgSpec(arg_key="threshold", arg_value=0.5),
        MetricsArgSpec(arg_key="true_label", arg_value="FRAUD"),
        MetricsArgSpec(arg_key="false_label", arg_value="NOT_FRAUD"),
    ],
)
```

**Use Cases**:
- Class distribution monitoring
- Detect prediction bias
- Track positive rate

---

## Common Use Cases

### Financial Services / Fraud Detection

```python
def gen_fraud_detection_aggregations(dataset: Dataset) -> list[AggregationSpec]:
    timestamp_col = column_id_from_col_name(dataset, "timestamp")
    fraud_score_col = column_id_from_col_name(dataset, "fraud_score")
    transaction_amt_col = column_id_from_col_name(dataset, "transaction_amount")

    return [
        # Track fraud score distribution
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000d",
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col),
                MetricsArgSpec(arg_key="numeric_col", arg_value=fraud_score_col),
            ],
        ),
        # Track total transaction amounts
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000f",
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col),
                MetricsArgSpec(arg_key="numeric_col", arg_value=transaction_amt_col),
            ],
        ),
        # Track fraud vs not-fraud counts
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-000000000020",
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col),
                MetricsArgSpec(arg_key="prediction_col", arg_value=fraud_score_col),
                MetricsArgSpec(arg_key="threshold", arg_value=0.9),
                MetricsArgSpec(arg_key="true_label", arg_value="FRAUD"),
                MetricsArgSpec(arg_key="false_label", arg_value="NOT_FRAUD"),
            ],
        ),
    ]
```

### Credit Risk / Lending

```python
def gen_credit_risk_aggregations(dataset: Dataset) -> list[AggregationSpec]:
    timestamp_col = column_id_from_col_name(dataset, "timestamp")
    risk_score_col = column_id_from_col_name(dataset, "risk_score")
    loan_amount_col = column_id_from_col_name(dataset, "loan_amount")

    return [
        # Monitor risk score distribution
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000d",
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col),
                MetricsArgSpec(arg_key="numeric_col", arg_value=risk_score_col),
            ],
        ),
        # Track total loan amounts
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000f",
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col),
                MetricsArgSpec(arg_key="numeric_col", arg_value=loan_amount_col),
            ],
        ),
        # Track high-risk vs low-risk applications
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-000000000020",
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col),
                MetricsArgSpec(arg_key="prediction_col", arg_value=risk_score_col),
                MetricsArgSpec(arg_key="threshold", arg_value=0.7),
                MetricsArgSpec(arg_key="true_label", arg_value="HIGH_RISK"),
                MetricsArgSpec(arg_key="false_label", arg_value="LOW_RISK"),
            ],
        ),
    ]
```

### Marketing / Customer Segmentation

```python
def gen_marketing_aggregations(dataset: Dataset) -> list[AggregationSpec]:
    timestamp_col = column_id_from_col_name(dataset, "timestamp")
    conversion_prob_col = column_id_from_col_name(dataset, "conversion_probability")
    customer_value_col = column_id_from_col_name(dataset, "predicted_lifetime_value")

    return [
        # Monitor conversion probability distribution
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000d",
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col),
                MetricsArgSpec(arg_key="numeric_col", arg_value=conversion_prob_col),
            ],
        ),
        # Track total predicted customer value
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000f",
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col),
                MetricsArgSpec(arg_key="numeric_col", arg_value=customer_value_col),
            ],
        ),
        # Track likely-to-convert vs unlikely
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-000000000020",
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col),
                MetricsArgSpec(arg_key="prediction_col", arg_value=conversion_prob_col),
                MetricsArgSpec(arg_key="threshold", arg_value=0.6),
                MetricsArgSpec(arg_key="true_label", arg_value="LIKELY_CONVERT"),
                MetricsArgSpec(arg_key="false_label", arg_value="UNLIKELY_CONVERT"),
            ],
        ),
    ]
```

---

## Usage with add-custom-aggregations.py

### Step 1: Configure the script

```python
# In add-custom-aggregations.py
ARTHUR_HOST = "https://platform.arthur.ai"
MODEL_ID = "your-model-id-here"
```

### Step 2: Customize gen_custom_aggregations()

Replace the function with your specific aggregations:

```python
def gen_custom_aggregations(dataset: Dataset) -> list[AggregationSpec]:
    # Get column IDs
    timestamp_col = column_id_from_col_name(dataset, "timestamp")
    prediction_col = column_id_from_col_name(dataset, "prediction_score")

    # Return your custom aggregations
    return [
        # Add your aggregations here
        AggregationSpec(...),
        AggregationSpec(...),
    ]
```

### Step 3: Run the script

```bash
python add-custom-aggregations.py
```

Output:
```
Connecting to Arthur at https://platform.arthur.ai...
Fetching model abc123...
Model: fraud-model
Current aggregation count: 5

Fetching dataset...
Dataset: fraud-inferences
Dataset columns: ['timestamp', 'fraud_score', 'transaction_amount', 'merchant_id']

Generating custom aggregations...
Generated 8 new aggregations
Skipping 3 aggregations that already exist
Adding 5 new aggregations

New aggregations to be added:
  1. Aggregation ID: 00000000-0000-0000-0000-00000000000d
     - timestamp_col: abc-123
     - numeric_col: def-456
  2. Aggregation ID: 00000000-0000-0000-0000-00000000000f
     - timestamp_col: abc-123
     - numeric_col: def-456

This will update the model to have 10 total aggregations
Continue? (yes/no): yes

Applying new aggregations to model...
✓ Successfully updated model metrics!
  Previous aggregation count: 5
  New aggregation count: 10
  Added: 5 aggregations
```

---

## Special Case: Positive-Class Error Profile

The **Positive-Class Error Profile** is a custom aggregation that provides comprehensive binary classification error analysis. It uses custom SQL to calculate 7 metrics from confusion matrix components (TP, FP, TN, FN) over time buckets.

### Creating the Custom Aggregation

**Step 1**: Run the creation script to register the custom aggregation:

```bash
python create-positive-class-error-profile.py
```

This creates a custom aggregation using `CustomAggregationsV1Api` with:
- 7 reported metrics (see below)
- Custom SQL query with time bucketing
- Configurable parameters (dataset, timestamp, ground truth, prediction, threshold)

**Step 2**: Save the returned custom aggregation ID for use in model configurations.

### The 7 Reported Metrics

**1. Adjusted False Positive Rate**: `FP / (FP + TN)`
- Among actual negatives, what fraction were incorrectly flagged?
- Use for: Understanding false alarm rate

**2. Bad Case Rate**: `(TP + FN) / Total`
- Fraction of cases classified as "bad" (actual positives)
- Use for: Understanding class distribution

**3. False Positive Ratio**: `FP / Total`
- False positives as fraction of all cases
- Use for: Overall system burden

**4. Valid Detection Rate**: `(TP + TN) / Total` = Accuracy
- Overall fraction of correct predictions
- Use for: High-level performance tracking

**5. Overprediction Rate**: `max((predicted_pos - actual_pos) / Total, 0)`
- Rate of over-predicting the positive class
- Use for: Understanding model optimism

**6. Underprediction Rate**: `max((actual_pos - predicted_pos) / Total, 0)`
- Rate of under-predicting the positive class
- Use for: Understanding model conservatism

**7. Total False Positive Rate**: `SUM(FP) / SUM(Total)` (global)
- Cumulative false positive rate across all time
- Use for: Historical performance tracking

### Data Requirements

The custom aggregation requires these columns in your dataset:
- **Timestamp column**: For time bucketing (daily buckets)
- **Ground truth column**: Binary label (0 or 1)
- **Prediction column**: Probability score (0.0 to 1.0)

### Configuration in Model

After creating the custom aggregation, add it to your model:

```python
# Get the custom aggregation ID from create-positive-class-error-profile.py
CUSTOM_AGGREGATION_ID = "abc-123-def-456"  # Replace with actual ID

aggregation_specs.append(
    AggregationSpec(
        aggregation_id=CUSTOM_AGGREGATION_ID,
        aggregation_init_args=[],
        aggregation_args=[
            MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
            MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
            MetricsArgSpec(arg_key="ground_truth", arg_value=is_fraud_col_id),
            MetricsArgSpec(arg_key="prediction", arg_value=fraud_score_col_id),
            MetricsArgSpec(arg_key="threshold", arg_value="0.5"),  # Adjust as needed
        ],
    )
)
```

### SQL Query

The custom aggregation uses this SQL structure:

```sql
WITH counts AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    SUM(CASE WHEN {{ground_truth}} = 1 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END) AS tp,
    SUM(CASE WHEN {{ground_truth}} = 0 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END) AS fp,
    SUM(CASE WHEN {{ground_truth}} = 0 AND {{prediction}} <  {{threshold}} THEN 1 ELSE 0 END) AS tn,
    SUM(CASE WHEN {{ground_truth}} = 1 AND {{prediction}} <  {{threshold}} THEN 1 ELSE 0 END) AS fn
  FROM {{dataset}}
  GROUP BY 1
)
-- Additional CTEs calculate metrics from TP/FP/TN/FN
```

### When to Use

Perfect for:
- Fraud detection models
- Credit risk scoring
- Account takeover detection
- Any binary classification where false positives have operational cost

### Files

- [create-positive-class-error-profile.py](create-positive-class-error-profile.py) - Creates the custom aggregation
- [add-fraud-model-aggregations.py](add-fraud-model-aggregations.py) - Shows how to reference it in model configs

---

## Best Practices

### 1. Start with Essential Metrics

Always include:
- Inference count (volume monitoring)
- Nullable counts (data quality)
- Prediction distribution (drift detection)

### 2. Add Domain-Specific Metrics

Based on your use case:
- **Financial**: Transaction amounts, risk scores
- **Healthcare**: Patient risk scores, treatment probabilities
- **Retail**: Purchase probabilities, customer values

### 3. Monitor Key Features

Track distributions for:
- Top 5-10 most important features
- Features known to drift
- Business-critical features

### 4. Avoid Over-Aggregation

Too many aggregations can:
- Slow down metric calculation
- Make dashboards cluttered
- Increase storage costs

**Recommendation**: Start with 10-20 aggregations, add more as needed

### 5. Use Meaningful Thresholds

For classification aggregations:
- Use business-relevant thresholds (not just 0.5)
- Example: 0.9 for high-confidence fraud detection
- Document why you chose each threshold

---

## Troubleshooting

### Column Not Found Error

```
ValueError: Column 'prediction_score' not found in dataset schema
```

**Solution**: Check your dataset schema:
```python
dataset = datasets_client.get_dataset(dataset_id=model.dataset_id)
print([col.source_name for col in dataset.dataset_schema.columns])
```

### Aggregation Already Exists

The script automatically skips duplicate aggregations. If you see:
```
Skipping 5 aggregations that already exist
```

This is normal - it means those metrics are already configured.

### Wrong Aggregation ID

If metrics don't appear or show errors, verify you're using the correct aggregation ID:
- `00000000-0000-0000-0000-00000000000a` = Inference count
- `00000000-0000-0000-0000-00000000000b` = Nullable count
- `00000000-0000-0000-0000-00000000000d` = Numeric distribution
- `00000000-0000-0000-0000-00000000000f` = Numeric sum
- `00000000-0000-0000-0000-000000000020` = Inference count by class

---

## See Also

- [add-custom-aggregations.py](add-custom-aggregations.py) - General template for adding custom aggregations
- [add-fraud-model-aggregations.py](add-fraud-model-aggregations.py) - Fraud-specific aggregations with error profile
- [model-onboarding.py](model-onboarding.py) - Initial model setup
- [README.md](README.md) - Complete onboarding guide
