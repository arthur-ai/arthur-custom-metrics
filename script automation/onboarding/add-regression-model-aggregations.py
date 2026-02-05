"""
Add Standard Aggregations for Housing Price Regression Model

This script adds standard built-in aggregations for regression models.

Aggregations included:
- Inference count
- Numeric distributions: all numeric feature columns, predictions, ground truth
- Numeric sums: predictions, ground truth (if applicable)
- Category counts: any categorical features
- Regression metrics: MAE (Mean Absolute Error) and MSE (Mean Squared Error)
- Data quality: nullable counts for all columns

CONFIGURE:
  - MODEL_ID: Your model ID from the onboarding script output
  - Update column names to match your schema

USAGE: python add-regression-model-aggregations.py
"""

from arthur_client.api_bindings import (
    DatasetsV1Api,
    ModelsV1Api,
)
from arthur_client.api_bindings.models import *
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.auth import ArthurOAuthSessionAPIConfiguration, DeviceAuthorizer

# CONFIGURATION
ARTHUR_HOST = "https://platform.arthur.ai"
MODEL_ID = "INSERT_MODEL_ID_HERE"  # Get from Arthur UI


def column_id_from_col_name(dataset: Dataset, col_name: str) -> str:
    """Helper to get column ID from column name."""
    for col in dataset.dataset_schema.columns:
        if col.source_name == col_name:
            return col.id
    raise ValueError(f"Column '{col_name}' not found in dataset schema")


def gen_regression_model_aggregations(dataset: Dataset) -> list[AggregationSpec]:
    """
    Generate aggregations for regression model.

    Includes:
    - Inference count
    - Numeric distributions for all numeric columns
    - Numeric sums for predictions and ground truth
    - Category counts for categorical features
    - Data quality (nullable counts)

    Customize the column lists below based on your specific schema.
    """
    # Get required column IDs
    timestamp_col_id = column_id_from_col_name(dataset, "timestamp")

    # Prediction and ground truth columns
    prediction_col_id = column_id_from_col_name(dataset, "predicted_house_value")
    ground_truth_col_id = column_id_from_col_name(dataset, "actual_house_value")

    # Numeric feature columns for housing price prediction
    numeric_feature_columns = [
        "longitude",             # Geographic coordinate
        "latitude",              # Geographic coordinate
        "housing_median_age",    # Property age
        "total_rooms",           # Property size metric
        "total_bedrooms",        # Property size metric
        "population",            # Area demographic
        "households",            # Area demographic
        "median_income",         # Economic indicator
    ]

    # Categorical feature columns
    categorical_feature_columns = [
        "ocean_proximity",
    ]

    # Collect all numeric column IDs
    numeric_cols = []
    if prediction_col_id:
        numeric_cols.append(prediction_col_id)
    if ground_truth_col_id:
        numeric_cols.append(ground_truth_col_id)

    # Try to add feature columns (optional - will skip if not found)
    for col_name in numeric_feature_columns:
        try:
            col_id = column_id_from_col_name(dataset, col_name)
            numeric_cols.append(col_id)
        except ValueError:
            print(f"Info: Numeric column '{col_name}' not found, skipping")

    # Collect categorical column IDs
    categorical_cols = []
    for col_name in categorical_feature_columns:
        try:
            col_id = column_id_from_col_name(dataset, col_name)
            categorical_cols.append(col_id)
        except ValueError:
            print(f"Info: Categorical column '{col_name}' not found, skipping")

    aggregation_specs = []

    # ========================================
    # BASIC METRICS
    # ========================================

    # 1. Total inference count
    aggregation_specs.append(
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000a",
            aggregation_init_args=[],
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
            ],
        )
    )

    # ========================================
    # NUMERIC SUMS
    # ========================================

    # 2-3. Sum of predictions and ground truth
    for col_id in [prediction_col_id, ground_truth_col_id]:
        if col_id:
            aggregation_specs.append(
                AggregationSpec(
                    aggregation_id="00000000-0000-0000-0000-00000000000f",
                    aggregation_init_args=[],
                    aggregation_args=[
                        MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                        MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                        MetricsArgSpec(arg_key="numeric_col", arg_value=col_id),
                    ],
                )
            )

    # ========================================
    # NUMERIC DISTRIBUTIONS (Min/Max/Mean/Std)
    # ========================================

    # Distributions for all numeric columns
    for col_id in numeric_cols:
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-00000000000d",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="numeric_col", arg_value=col_id),
                ],
            )
        )

    # ========================================
    # CATEGORY COUNTS
    # ========================================

    # Category counts for all categorical columns
    for col_id in categorical_cols:
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-00000000000c",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="categorical_col", arg_value=col_id),
                ],
            )
        )

    # ========================================
    # REGRESSION METRICS (if both prediction and ground truth exist)
    # ========================================

    if prediction_col_id and ground_truth_col_id:
        # Mean Absolute Error (MAE)
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-00000000000e",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="prediction_col", arg_value=prediction_col_id),
                    MetricsArgSpec(arg_key="ground_truth_col", arg_value=ground_truth_col_id),
                ],
            )
        )

        # Mean Squared Error (MSE)
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-000000000010",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="prediction_col", arg_value=prediction_col_id),
                    MetricsArgSpec(arg_key="ground_truth_col", arg_value=ground_truth_col_id),
                ],
            )
        )
        print("Added regression metrics: MAE and MSE")

    # ========================================
    # NULLABLE COUNTS (Data Quality)
    # ========================================

    # Nullable counts for all tracked columns (numeric + categorical)
    all_tracked_cols = numeric_cols + categorical_cols
    for col_id in all_tracked_cols:
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-00000000000b",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="nullable_col", arg_value=col_id),
                ],
            )
        )

    return aggregation_specs


def main():
    """Main execution function."""
    print(f"🔗 Connecting to Arthur at {ARTHUR_HOST}...")
    sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
    api_client = ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
    )

    models_client = ModelsV1Api(api_client)
    datasets_client = DatasetsV1Api(api_client)

    # Get the model
    print(f"\n📊 Fetching model {MODEL_ID}...")
    model = models_client.get_model(model_id=MODEL_ID)
    print(f"Model: {model.name}")
    print(f"Current aggregation count: {len(model.metric_config.aggregation_specs)}")

    # Get the primary dataset for the model
    print(f"\n📁 Fetching dataset...")
    if not model.datasets or len(model.datasets) == 0:
        raise ValueError(f"Model {MODEL_ID} has no associated datasets")
    dataset = datasets_client.get_dataset(dataset_id=model.datasets[0].dataset_id)
    print(f"Dataset: {dataset.name}")

    # Show available columns
    print(f"\n📋 Available columns in dataset:")
    for col in dataset.dataset_schema.columns:
        print(f"  - {col.source_name}")

    # Generate aggregations
    print(f"\n⚙️  Generating regression model aggregations...")
    try:
        new_aggregations = gen_regression_model_aggregations(dataset)
        print(f"✓ Generated {len(new_aggregations)} aggregations")
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nPlease verify that your dataset has the required columns.")
        print("Update the column names in gen_regression_model_aggregations() to match your schema.")
        return

    # Filter out duplicates
    aggregations_to_add = []
    skipped_count = 0

    for agg in new_aggregations:
        exists = False
        for existing_agg in model.metric_config.aggregation_specs:
            if (existing_agg.aggregation_id == agg.aggregation_id and
                existing_agg.aggregation_args == agg.aggregation_args):
                exists = True
                break

        if not exists:
            aggregations_to_add.append(agg)
        else:
            skipped_count += 1

    print(f"Skipping {skipped_count} aggregations that already exist")
    print(f"Adding {len(aggregations_to_add)} new aggregations")

    if len(aggregations_to_add) == 0:
        print("\n✓ No new aggregations to add. All specified aggregations already exist.")
        return

    # Show summary
    print(f"\n📊 Aggregations Summary:")
    print(f"  • Inference count: total predictions over time")
    print(f"  • Numeric sums: predictions and ground truth totals")
    print(f"  • Numeric distributions: all numeric columns (min/max/mean/std)")
    print(f"  • Category counts: categorical features")
    print(f"  • Regression metrics: MAE and MSE (if ground truth available)")
    print(f"  • Data quality: nullable counts for all tracked columns")

    # Combine existing and new aggregations
    all_aggregations = model.metric_config.aggregation_specs + aggregations_to_add

    print(f"\n🔢 Metrics:")
    print(f"  Previous: {len(model.metric_config.aggregation_specs)} aggregations")
    print(f"  New:      {len(all_aggregations)} aggregations")
    print(f"  Added:    {len(aggregations_to_add)} aggregations")

    # Confirm before applying
    response = input("\n❓ Continue? (yes/no): ")

    if response.lower() != "yes":
        print("❌ Cancelled. No changes made.")
        return

    # Apply the new metric configuration
    print(f"\n⏳ Applying aggregations to model...")
    models_client.put_model_metric_config(
        model_id=MODEL_ID,
        put_model_metric_spec=PutModelMetricSpec(
            aggregation_specs=all_aggregations
        ),
    )

    print(f"\n✅ Successfully updated model metrics!")
    print(f"\n📈 Next steps:")
    print(f"  1. Wait for next scheduled metric calculation (hourly)")
    print(f"  2. View metrics in Arthur UI at {ARTHUR_HOST}")
    print(f"  3. Monitor for drift in predictions and key features")
    print(f"  4. Set up alerts for regression performance degradation")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nMake sure you've updated:")
        print("  1. MODEL_ID with your actual model ID from onboarding output")
        print("  2. Column names in gen_regression_model_aggregations() to match your schema")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
