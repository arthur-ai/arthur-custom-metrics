"""
Create Regression Error Distribution Custom Aggregation and Add to Model

PURPOSE: Creates a custom aggregation for comprehensive regression error analysis
         and adds it to your model's metric configuration

USAGE: python create-regression-error-profile.py
WHEN: One-time setup to add the regression error profile to your model

CREATES:
  - Custom aggregation with 3 metrics analyzing regression errors
  - Metrics include: absolute_error, forecast_error, absolute_percentage_error
  - All metrics are stored as sketches for percentile analysis
  - Adds this aggregation to your model's metric configuration

REQUIRES:
  - Arthur workspace access
  - Model with dataset containing: ground truth, prediction, timestamp, columns

CONFIGURE BEFORE RUNNING:
  - ARTHUR_HOST
  - WORKSPACE_ID
  - MODEL_ID
  - Column names (TIMESTAMP_COLUMN_NAME, PREDICTION_COLUMN_NAME, GROUND_TRUTH_COLUMN_NAME)
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
MODEL_ID = "INSERT_MODEL_ID_HERE"  # Get from Arthur UI

# Column configuration - update these to match your dataset
TIMESTAMP_COLUMN_NAME = "timestamp"
ROW_ID_COLUMN_NAME = "house_id"
PREDICTION_COLUMN_NAME = "predicted_house_value"
GROUND_TRUTH_COLUMN_NAME = "actual_house_value"

# SQL Query for Regression Error Distribution
REGRESSION_ERROR_PROFILE_SQL = """
WITH
  base AS (
    SELECT
      time_bucket(INTERVAL '1 day', {{timestamp_col}}) AS ts,
      {{prediction_col}}::float AS prediction,
      {{ground_truth_col}}::float AS actual
    FROM {{dataset}}
  )
SELECT
  ts,
  ABS(prediction - actual) AS absolute_error,
  prediction - actual AS forecast_error,
  CASE
    WHEN actual != 0 THEN ABS((prediction - actual) / actual) * 100
    ELSE NULL
  END AS absolute_percentage_error
FROM base
ORDER BY ts;
"""


def column_id_from_col_name(dataset, col_name: str) -> str:
    """Helper to get column ID from column name."""
    for col in dataset.dataset_schema.columns:
        if col.source_name == col_name:
            return col.id
    raise ValueError(f"Column '{col_name}' not found in dataset schema")


if __name__ == "__main__":
    try:
        # Create the custom aggregation and get the result with version info
        print("🔐 Authenticating with Arthur...")
        sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
        api_client = ApiClient(
            configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
        )
        custom_agg_client = CustomAggregationsV1Api(api_client)

        print("\n📊 Creating Regression Error Profile custom aggregation...")

        # Define the 3 reported metrics (all sketches for distribution analysis)
        reported_aggregations = [
            ReportedCustomAggregation(
                metric_name="absolute_error",
                description="Magnitude of prediction error (unsigned)",
                value_column="absolute_error",
                timestamp_column="ts",
                metric_kind=AggregationMetricType.NUMERIC,
                dimension_columns=[]
            ),
            ReportedCustomAggregation(
                metric_name="forecast_error",
                description="Signed prediction error (positive = over-prediction)",
                value_column="forecast_error",
                timestamp_column="ts",
                metric_kind=AggregationMetricType.NUMERIC,
                dimension_columns=[]
            ),
            ReportedCustomAggregation(
                metric_name="absolute_percentage_error",
                description="Percentage error per inference (scale-independent)",
                value_column="absolute_percentage_error",
                timestamp_column="ts",
                metric_kind=AggregationMetricType.NUMERIC,
                dimension_columns=[]
            ),
        ]

        # Define aggregate arguments (parameters for the SQL query)
        aggregate_args = [
            # Timestamp column parameter
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
            # Prediction column parameter
            CustomAggregationVersionSpecSchemaAggregateArgsInner(
                actual_instance=BaseColumnParameterSchema(
                    parameter_key="prediction_col",
                    friendly_name="Prediction Column",
                    description="Predicted value column",
                    source_dataset_parameter_key="dataset",
                    tag_hints=[ScopeSchemaTag.PREDICTION],
                    allowed_column_types=[
                        BaseColumnParameterSchemaAllowedColumnTypesInner(
                            actual_instance=ScalarType(dtype=DType.INT)
                        ),
                        BaseColumnParameterSchemaAllowedColumnTypesInner(
                            actual_instance=ScalarType(dtype=DType.FLOAT)
                        )
                    ],
                )
            ),
            # Ground truth column parameter
            CustomAggregationVersionSpecSchemaAggregateArgsInner(
                actual_instance=BaseColumnParameterSchema(
                    parameter_key="ground_truth_col",
                    friendly_name="Ground Truth Column",
                    description="Actual/ground truth value column",
                    source_dataset_parameter_key="dataset",
                    tag_hints=[ScopeSchemaTag.GROUND_TRUTH],
                    allowed_column_types=[
                        BaseColumnParameterSchemaAllowedColumnTypesInner(
                            actual_instance=ScalarType(dtype=DType.INT)
                        ),
                        BaseColumnParameterSchemaAllowedColumnTypesInner(
                            actual_instance=ScalarType(dtype=DType.FLOAT)
                        )
                    ],
                )
            ),
            # Dataset parameter (last, with model_problem_type)
            CustomAggregationVersionSpecSchemaAggregateArgsInner(
                actual_instance=BaseDatasetParameterSchema(
                    parameter_key="dataset",
                    friendly_name="Dataset",
                    description="Dataset containing ground truth and predictions",
                    model_problem_type=ModelProblemType.REGRESSION
                )
            ),
        ]

        # Create the custom aggregation spec
        spec = PostCustomAggregationSpecSchema(
            name="regression_error_profile",
            description="Comprehensive regression error analysis with absolute error, forecast error, and percentage error distributions for outlier detection and bias analysis",
            sql=REGRESSION_ERROR_PROFILE_SQL,
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

        agg_id = result.id
        agg_version = result.latest_version

        # Now add it to the model
        print(f"\n📊 Adding custom aggregation to model {MODEL_ID}...")
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
        prediction_col_id = column_id_from_col_name(dataset, PREDICTION_COLUMN_NAME)
        ground_truth_col_id = column_id_from_col_name(dataset, GROUND_TRUTH_COLUMN_NAME)

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
                    MetricsArgSpec(arg_key="prediction_col", arg_value=prediction_col_id),
                    MetricsArgSpec(arg_key="ground_truth_col", arg_value=ground_truth_col_id),
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

            print(f"\n✅ Successfully added regression error profile to model!")
            print(f"   Previous aggregations: {len(model.metric_config.aggregation_specs)}")
            print(f"   New aggregations: {len(all_aggregations)}")

        print("\n🎉 Setup complete!")
        print(f"\n📈 Next steps:")
        print(f"  1. Wait for next scheduled metric calculation")
        print(f"  2. View metrics in Arthur UI at {ARTHUR_HOST}")
        print(f"  3. Monitor error distributions for outliers and bias")
        print(f"\n💡 Analysis capabilities:")
        print(f"  • Absolute Error: Magnitude-based outlier detection")
        print(f"  • Forecast Error: Bias detection (over/under-prediction)")
        print(f"  • Absolute Percentage Error: Scale-independent error analysis")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
