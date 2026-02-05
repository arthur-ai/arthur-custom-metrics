"""
Create Positive-Class Error Profile Custom Aggregation and Add to Model

PURPOSE: Creates a custom aggregation for comprehensive binary classification error analysis
         and adds it to your model's metric configuration

USAGE: python create-positive-class-error-profile.py
WHEN: One-time setup to add the positive-class error profile to your model

CREATES:
  - Custom aggregation with 7 metrics analyzing classification errors
  - Metrics include: adjusted_false_positive_rate, bad_case_rate, false_positive_ratio,
    valid_detection_rate, overprediction_rate, underprediction_rate, total_false_positive_rate
  - Adds this aggregation to your model's metric configuration

REQUIRES:
  - Arthur workspace access
  - Model with dataset containing: ground truth label, prediction score, timestamp columns

CONFIGURE BEFORE RUNNING:
  - ARTHUR_HOST
  - WORKSPACE_ID
  - MODEL_ID
  - Column names (TIMESTAMP_COLUMN_NAME, GROUND_TRUTH_COLUMN_NAME, PREDICTION_COLUMN_NAME)
  - CLASSIFICATION_THRESHOLD
"""

from arthur_client.auth import DeviceAuthorizer
from arthur_client.api_bindings import CustomAggregationsV1Api, ModelsV1Api, DatasetsV1Api
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.api_bindings.models.aggregation_kind import AggregationKind
from arthur_client.api_bindings.models import (
    PostCustomAggregationSpecSchema,
    ReportedCustomAggregation,
    AggregationMetricType,
    BaseDatasetParameterSchema,
    BaseColumnParameterSchema,
    BaseLiteralParameterSchema,
    CustomAggregationVersionSpecSchemaAggregateArgsInner,
    AggregationSpec,
    MetricsArgSpec,
    PutModelMetricSpec,
    DType,
    ScopeSchemaTag,
    ScalarType,
    BaseColumnParameterSchemaAllowedColumnTypesInner,
    ModelProblemType,
)
from arthur_client.auth import ArthurOAuthSessionAPIConfiguration

# CONFIGURATION
ARTHUR_HOST = "https://platform.arthur.ai"
WORKSPACE_ID = "INSERT_WORKSPACE_ID_HERE"  # Get from Arthur UI
MODEL_ID = "INSERT_MODEL_ID_HERE"  # Replace with your model ID

# Column configuration - update these to match your dataset
TIMESTAMP_COLUMN_NAME = "timestamp"
GROUND_TRUTH_COLUMN_NAME = "is_fraud"
PREDICTION_COLUMN_NAME = "fraud_pred"
CLASSIFICATION_THRESHOLD = 0.5

# SQL Query for Positive-Class Error Profile
POSITIVE_CLASS_ERROR_PROFILE_SQL = """
WITH counts AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS bucket,
    SUM(CASE WHEN {{ground_truth}} = 1 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END) AS tp,
    SUM(CASE WHEN {{ground_truth}} = 0 AND {{prediction}} >= {{threshold}} THEN 1 ELSE 0 END) AS fp,
    SUM(CASE WHEN {{ground_truth}} = 0 AND {{prediction}} <  {{threshold}} THEN 1 ELSE 0 END) AS tn,
    SUM(CASE WHEN {{ground_truth}} = 1 AND {{prediction}} <  {{threshold}} THEN 1 ELSE 0 END) AS fn
  FROM {{dataset}}
  GROUP BY 1
),
prepared AS (
  SELECT
    bucket,
    tp::float AS tp,
    fp::float AS fp,
    tn::float AS tn,
    fn::float AS fn,
    (tp + fp + tn + fn)::float AS total,
    (tp + fp)::float          AS predicted_pos,
    (tp + fn)::float          AS actual_pos,
    (fp + tn)::float          AS negatives
  FROM counts
)
SELECT
  bucket AS bucket,

  -- Adjusted False Positive Rate: FP / negatives
  CASE WHEN negatives > 0 THEN fp / negatives ELSE 0 END
    AS adjusted_false_positive_rate,

  -- Bad Case Rate: actual "bad" cases / total
  CASE WHEN total > 0 THEN (tp + fn) / total ELSE 0 END
    AS bad_case_rate,

  -- False Positive Ratio: FP / total
  CASE WHEN total > 0 THEN fp / total ELSE 0 END
    AS false_positive_ratio,

  -- Valid Detection Rate: (TP + TN) / total
  CASE WHEN total > 0 THEN (tp + tn) / total ELSE 0 END
    AS valid_detection_rate,

  -- Overprediction: (predicted_pos - actual_pos) / total, floored at 0
  CASE WHEN total > 0 THEN GREATEST((predicted_pos - actual_pos) / total, 0)
       ELSE 0 END
    AS overprediction_rate,

  -- Underprediction: (actual_pos - predicted_pos) / total, floored at 0
  CASE WHEN total > 0 THEN GREATEST((actual_pos - predicted_pos) / total, 0)
       ELSE 0 END
    AS underprediction_rate,

  -- Total False Positive Rate: global FP / global total
  CASE WHEN SUM(total) OVER () > 0
       THEN SUM(fp) OVER () / SUM(total) OVER ()
       ELSE 0 END
    AS total_false_positive_rate

FROM prepared
ORDER BY bucket;
"""


def column_id_from_col_name(dataset, col_name: str) -> str:
    """Helper to get column ID from column name."""
    for col in dataset.dataset_schema.columns:
        if col.source_name == col_name:
            return col.id
    raise ValueError(f"Column '{col_name}' not found in dataset schema")


def create_positive_class_error_profile_aggregation():
    """
    Creates the positive-class error profile custom aggregation.

    Returns:
        str: The ID of the created custom aggregation
    """
    print("🔐 Authenticating with Arthur...")
    sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
    api_client = ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
    )
    custom_agg_client = CustomAggregationsV1Api(api_client)

    print("\n📊 Creating Positive-Class Error Profile custom aggregation...")

    # Define the 7 reported metrics
    reported_aggregations = [
        ReportedCustomAggregation(
            metric_name="adjusted_false_positive_rate",
            description="False positive rate among negative cases: FP / (FP + TN)",
            value_column="adjusted_false_positive_rate",
            timestamp_column="bucket",
            metric_kind=AggregationMetricType.NUMERIC,
            dimension_columns=[]
        ),
        ReportedCustomAggregation(
            metric_name="bad_case_rate",
            description="Fraction of cases classified as bad: (TP + FN) / Total",
            value_column="bad_case_rate",
            timestamp_column="bucket",
            metric_kind=AggregationMetricType.NUMERIC,
            dimension_columns=[]
        ),
        ReportedCustomAggregation(
            metric_name="false_positive_ratio",
            description="False positives as fraction of all cases: FP / Total",
            value_column="false_positive_ratio",
            timestamp_column="bucket",
            metric_kind=AggregationMetricType.NUMERIC,
            dimension_columns=[]
        ),
        ReportedCustomAggregation(
            metric_name="valid_detection_rate",
            description="Overall accuracy: (TP + TN) / Total",
            value_column="valid_detection_rate",
            timestamp_column="bucket",
            metric_kind=AggregationMetricType.NUMERIC,
            dimension_columns=[]
        ),
        ReportedCustomAggregation(
            metric_name="overprediction_rate",
            description="Rate of over-predicting positives: (predicted_pos - actual_pos) / Total",
            value_column="overprediction_rate",
            timestamp_column="bucket",
            metric_kind=AggregationMetricType.NUMERIC,
            dimension_columns=[]
        ),
        ReportedCustomAggregation(
            metric_name="underprediction_rate",
            description="Rate of under-predicting positives: (actual_pos - predicted_pos) / Total",
            value_column="underprediction_rate",
            timestamp_column="bucket",
            metric_kind=AggregationMetricType.NUMERIC,
            dimension_columns=[]
        ),
        ReportedCustomAggregation(
            metric_name="total_false_positive_rate",
            description="Global false positive rate across all time: SUM(FP) / SUM(Total)",
            value_column="total_false_positive_rate",
            timestamp_column="bucket",
            metric_kind=AggregationMetricType.NUMERIC,
            dimension_columns=[]
        ),
    ]

    # Define aggregate arguments (parameters for the SQL query)
    # Note: Order matters - dataset parameter should be last
    aggregate_args = [
        # Timestamp column parameter (marked with PRIMARY_TIMESTAMP tag)
        CustomAggregationVersionSpecSchemaAggregateArgsInner(
            actual_instance=BaseColumnParameterSchema(
                parameter_key="timestamp_col",
                friendly_name="Timestamp Column",
                description="Timestamp column for bucketing",
                source_dataset_parameter_key="dataset",
                tag_hints=[ScopeSchemaTag.PRIMARY_TIMESTAMP],
                allowed_column_types=[
                    BaseColumnParameterSchemaAllowedColumnTypesInner(
                        actual_instance=ScalarType(dtype=DType.TIMESTAMP)
                    )
                ]
            )
        ),
        # Ground truth column parameter
        CustomAggregationVersionSpecSchemaAggregateArgsInner(
            actual_instance=BaseColumnParameterSchema(
                parameter_key="ground_truth",
                friendly_name="Ground Truth",
                description="Ground truth label column (0 or 1)",
                source_dataset_parameter_key="dataset",
                tag_hints=[ScopeSchemaTag.GROUND_TRUTH],
                allowed_column_types=[
                    BaseColumnParameterSchemaAllowedColumnTypesInner(
                        actual_instance=ScalarType(dtype=DType.BOOL)
                    ),
                    BaseColumnParameterSchemaAllowedColumnTypesInner(
                        actual_instance=ScalarType(dtype=DType.INT)
                    )
                ],
            )
        ),
        # Prediction column parameter
        CustomAggregationVersionSpecSchemaAggregateArgsInner(
            actual_instance=BaseColumnParameterSchema(
                parameter_key="prediction",
                friendly_name="Prediction",
                description="Prediction score column (probability or score)",
                source_dataset_parameter_key="dataset",
                tag_hints=[ScopeSchemaTag.PREDICTION],
                allowed_column_types=[
                    BaseColumnParameterSchemaAllowedColumnTypesInner(
                        actual_instance=ScalarType(dtype=DType.FLOAT)
                    )
                ],
            )
        ),
        # Threshold literal parameter
        CustomAggregationVersionSpecSchemaAggregateArgsInner(
            actual_instance=BaseLiteralParameterSchema(
                parameter_key="threshold",
                friendly_name="Threshold",
                description="Classification threshold (default 0.5)",
                parameter_dtype=DType.FLOAT
            )
        ),
        # Dataset parameter (last, with model_problem_type)
        CustomAggregationVersionSpecSchemaAggregateArgsInner(
            actual_instance=BaseDatasetParameterSchema(
                parameter_key="dataset",
                friendly_name="Dataset",
                description="Dataset containing ground truth and predictions",
                model_problem_type=ModelProblemType.BINARY_CLASSIFICATION
            )
        ),
    ]

    # Create the custom aggregation spec
    spec = PostCustomAggregationSpecSchema(
        name="positive_class_error_profile",
        description="Comprehensive binary classification error analysis showing FP/FN rates, accuracy, and over/under-prediction across time buckets",
        sql=POSITIVE_CLASS_ERROR_PROFILE_SQL,
        reported_aggregations=reported_aggregations,
        aggregate_args=aggregate_args
    )

    # Create the custom aggregation
    result = custom_agg_client.post_custom_aggregation(
        workspace_id=WORKSPACE_ID,
        post_custom_aggregation_spec_schema=spec
    )

    print(f"\n✅ Successfully created custom aggregation!")
    print(f"   ID: {result.id}")
    print(f"   Name: {result.name}")
    print(f"   Version: {result.latest_version}")
    if result.versions and len(result.versions) > 0:
        print(f"   Metrics: {len(result.versions[0].reported_aggregations)}")
        print("\nReported Metrics:")
        for agg in result.versions[0].reported_aggregations:
            print(f"  - {agg.metric_name}: {agg.description}")

    print(f"\n📝 Custom aggregation ID: {result.id}")
    print(f"   Version: {result.latest_version}")

    return result.id, result.latest_version


if __name__ == "__main__":
    try:
        # Create the custom aggregation and get the result with version info
        agg_id, agg_version = create_positive_class_error_profile_aggregation()

        # Now add it to the model
        print(f"\n📊 Adding custom aggregation to model {MODEL_ID}...")
        sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
        api_client = ApiClient(
            configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
        )
        models_client = ModelsV1Api(api_client)
        datasets_client = DatasetsV1Api(api_client)

        # Get the model
        model = models_client.get_model(model_id=MODEL_ID)
        print(f"   Model: {model.name}")

        # Get the dataset
        if not model.datasets or len(model.datasets) == 0:
            raise ValueError(f"Model {MODEL_ID} has no associated datasets")
        dataset = datasets_client.get_dataset(dataset_id=model.datasets[0].dataset_id)
        print(f"   Dataset: {dataset.name}")

        # Get column IDs
        timestamp_col_id = column_id_from_col_name(dataset, TIMESTAMP_COLUMN_NAME)
        ground_truth_col_id = column_id_from_col_name(dataset, GROUND_TRUTH_COLUMN_NAME)
        prediction_col_id = column_id_from_col_name(dataset, PREDICTION_COLUMN_NAME)

        # Check if this aggregation already exists in the model
        aggregation_exists = False
        for existing_agg in model.metric_config.aggregation_specs:
            if existing_agg.aggregation_id == agg_id:
                aggregation_exists = True
                break

        if aggregation_exists:
            print(f"\n⚠️  Aggregation already exists in model. Skipping addition.")
        else:
            # Create the aggregation spec to add to the model
            new_aggregation = AggregationSpec(
                aggregation_id=agg_id,
                aggregation_version=agg_version,  # Required for custom aggregations
                aggregation_init_args=[],
                aggregation_kind=AggregationKind.CUSTOM,
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="ground_truth", arg_value=ground_truth_col_id),
                    MetricsArgSpec(arg_key="prediction", arg_value=prediction_col_id),
                    MetricsArgSpec(arg_key="threshold", arg_value=str(CLASSIFICATION_THRESHOLD)),
                ],
            )

            # Add to existing aggregations
            all_aggregations = model.metric_config.aggregation_specs + [new_aggregation]

            # Update the model
            print(f"\n⏳ Updating model metric configuration...")
            models_client.put_model_metric_config(
                model_id=MODEL_ID,
                put_model_metric_spec=PutModelMetricSpec(
                    aggregation_specs=all_aggregations
                ),
            )

            print(f"\n✅ Successfully added positive-class error profile to model!")
            print(f"   Previous aggregations: {len(model.metric_config.aggregation_specs)}")
            print(f"   New aggregations: {len(all_aggregations)}")

        print("\n🎉 Setup complete!")
        print(f"\n📈 Next steps:")
        print(f"  1. Wait for next scheduled metric calculation")
        print(f"  2. View metrics in Arthur UI at {ARTHUR_HOST}")
        print(f"  3. Monitor positive-class error profile metrics for classification performance")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
