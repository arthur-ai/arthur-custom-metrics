"""
Add Custom Aggregations to Any JPMC Model (General Purpose)

PURPOSE: Add custom metrics to any model - generic template
USAGE: python add-custom-aggregations.py
WHEN: Need specific metrics not covered by fraud model script

CUSTOMIZABLE: Edit gen_custom_aggregations() function for your columns

DEFAULT AGGREGATIONS:
  - Inference count
  - Nullable counts (all columns)
  - Prediction distribution (if prediction column exists)
  - Prediction sum (if prediction column exists)
  - Confidence distribution (if confidence_score exists)
  - Classification metrics (if binary classification)

REQUIRES:
  - Model ID
  - Dataset with timestamp column
  - Update column names in gen_custom_aggregations()

CONFIGURE:
  - MODEL_ID
  - Customize gen_custom_aggregations() for your schema

AGGREGATION IDS: See arthur-common/aggregations/functions/README.md
REFERENCE: AGGREGATIONS_REFERENCE.md for all 27 aggregation types

TIP: For card fraud models, use add-fraud-model-aggregations.py instead
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
MODEL_ID = "4487c615-5543-4569-b6b2-ed37b6ff63ac"  # Replace with your model ID


def column_id_from_col_name(dataset: Dataset, col_name: str) -> str:
    """Helper to get column ID from column name."""
    for col in dataset.dataset_schema.columns:
        if col.source_name == col_name:
            return col.id
    raise ValueError(f"Column '{col_name}' not found in dataset schema")


def gen_custom_aggregations(dataset: Dataset) -> list[AggregationSpec]:
    """
    Generate custom aggregation specs for your model.

    Customize this function based on your specific requirements.
    Available aggregation IDs and their purposes:

    Common Aggregations:
    - 00000000-0000-0000-0000-00000000000a: Inference count
    - 00000000-0000-0000-0000-00000000000b: Nullable column count
    - 00000000-0000-0000-0000-00000000000d: Numeric distribution (min/max/mean/std)
    - 00000000-0000-0000-0000-00000000000f: Numeric sum
    - 00000000-0000-0000-0000-000000000020: Inference count by class (binary classification)

    Args:
        dataset: The dataset to create aggregations for

    Returns:
        List of AggregationSpec objects
    """
    # Get column IDs for your specific columns
    # TODO: Update these column names to match your dataset schema
    timestamp_col_id = column_id_from_col_name(dataset, "timestamp")

    # Example: Get prediction-related columns (customize based on your schema)
    try:
        prediction_col_id = column_id_from_col_name(dataset, "prediction")
    except ValueError:
        prediction_col_id = None
        print("Warning: 'prediction' column not found, skipping prediction aggregations")

    try:
        confidence_col_id = column_id_from_col_name(dataset, "confidence_score")
    except ValueError:
        confidence_col_id = None
        print("Warning: 'confidence_score' column not found, skipping confidence aggregations")

    aggregation_specs = []

    # ========================================
    # 1. INFERENCE COUNT
    # ========================================
    # Tracks total number of inferences over time
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
    # 2. NULLABLE COUNTS (for all columns)
    # ========================================
    # Tracks missing/null values for each column
    for col in dataset.dataset_schema.columns:
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-00000000000b",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="nullable_col", arg_value=col.id),
                ],
            )
        )

    # ========================================
    # 3. PREDICTION DISTRIBUTION (if prediction column exists)
    # ========================================
    # Tracks min/max/mean/std of prediction values
    if prediction_col_id:
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-00000000000d",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="numeric_col", arg_value=prediction_col_id),
                ],
            )
        )

    # ========================================
    # 4. PREDICTION SUM (if prediction column exists)
    # ========================================
    # Tracks sum of prediction values over time
    if prediction_col_id:
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-00000000000f",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="numeric_col", arg_value=prediction_col_id),
                ],
            )
        )

    # ========================================
    # 5. CONFIDENCE SCORE DISTRIBUTION (if confidence column exists)
    # ========================================
    if confidence_col_id:
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-00000000000d",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="numeric_col", arg_value=confidence_col_id),
                ],
            )
        )

    # ========================================
    # 6. CLASSIFICATION METRICS (if applicable)
    # ========================================
    # For binary classification: tracks inference count per predicted class
    # TODO: Update threshold and labels based on your model
    if prediction_col_id:
        try:
            aggregation_specs.append(
                AggregationSpec(
                    aggregation_id="00000000-0000-0000-0000-000000000020",
                    aggregation_init_args=[],
                    aggregation_args=[
                        MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                        MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                        MetricsArgSpec(arg_key="prediction_col", arg_value=prediction_col_id),
                        MetricsArgSpec(arg_key="threshold", arg_value=0.5),  # TODO: Adjust threshold
                        MetricsArgSpec(arg_key="true_label", arg_value="POSITIVE"),  # TODO: Update labels
                        MetricsArgSpec(arg_key="false_label", arg_value="NEGATIVE"),
                    ],
                )
            )
        except Exception as e:
            print(f"Warning: Could not add classification metrics: {e}")

    # ========================================
    # ADD MORE CUSTOM AGGREGATIONS HERE
    # ========================================
    # Example: Track specific numeric columns
    # try:
    #     transaction_amount_col = column_id_from_col_name(dataset, "transaction_amount")
    #     aggregation_specs.append(
    #         AggregationSpec(
    #             aggregation_id="00000000-0000-0000-0000-00000000000d",
    #             aggregation_init_args=[],
    #             aggregation_args=[
    #                 MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
    #                 MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
    #                 MetricsArgSpec(arg_key="numeric_col", arg_value=transaction_amount_col),
    #             ],
    #         )
    #     )
    # except ValueError:
    #     print("Warning: 'transaction_amount' column not found")

    return aggregation_specs


def main():
    """Main execution function."""
    print(f"Connecting to Arthur at {ARTHUR_HOST}...")
    sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
    api_client = ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
    )

    models_client = ModelsV1Api(api_client)
    datasets_client = DatasetsV1Api(api_client)

    # Get the model
    print(f"\nFetching model {MODEL_ID}...")
    model = models_client.get_model(model_id=MODEL_ID)
    print(f"Model: {model.name}")
    print(f"Current aggregation count: {len(model.metric_config.aggregation_specs)}")

    # Get the primary dataset for the model
    print(f"\nFetching dataset...")
    if not model.datasets or len(model.datasets) == 0:
        raise ValueError(f"Model {MODEL_ID} has no associated datasets")
    dataset = datasets_client.get_dataset(dataset_id=model.datasets[0].dataset_id)
    print(f"Dataset: {dataset.name}")
    print(f"Dataset columns: {[col.source_name for col in dataset.dataset_schema.columns]}")

    # Generate custom aggregations
    print(f"\nGenerating custom aggregations...")
    new_aggregations = gen_custom_aggregations(dataset)
    print(f"Generated {len(new_aggregations)} new aggregations")

    # Get existing aggregation IDs to avoid duplicates
    existing_agg_ids = {
        agg.aggregation_id for agg in model.metric_config.aggregation_specs
    }

    # Filter out aggregations that already exist
    # Note: This checks by aggregation_id only, not by specific arguments
    aggregations_to_add = []
    skipped_count = 0

    for agg in new_aggregations:
        # Check if this exact aggregation already exists
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
        print("\nNo new aggregations to add. All specified aggregations already exist.")
        return

    # Combine existing and new aggregations
    all_aggregations = model.metric_config.aggregation_specs + aggregations_to_add

    # Show what will be added
    print(f"\nNew aggregations to be added:")
    for i, agg in enumerate(aggregations_to_add, 1):
        print(f"  {i}. Aggregation ID: {agg.aggregation_id}")
        for arg in agg.aggregation_args:
            if arg.arg_key != "dataset":  # Skip dataset ID for readability
                print(f"     - {arg.arg_key}: {arg.arg_value}")

    # Confirm before applying
    print(f"\nThis will update the model to have {len(all_aggregations)} total aggregations")
    response = input("Continue? (yes/no): ")

    if response.lower() != "yes":
        print("Cancelled. No changes made.")
        return

    # Apply the new metric configuration
    print(f"\nApplying new aggregations to model...")
    models_client.put_model_metric_config(
        model_id=MODEL_ID,
        put_model_metric_spec=PutModelMetricSpec(
            aggregation_specs=all_aggregations
        ),
    )

    print(f"✓ Successfully updated model metrics!")
    print(f"  Previous aggregation count: {len(model.metric_config.aggregation_specs)}")
    print(f"  New aggregation count: {len(all_aggregations)}")
    print(f"  Added: {len(aggregations_to_add)} aggregations")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you've updated:")
        print("  1. MODEL_ID with your actual model ID")
        print("  2. Column names in gen_custom_aggregations() to match your schema")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise
