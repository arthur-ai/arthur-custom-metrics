"""
Add standard aggregations for Card Fraud Model.

This script adds standard built-in aggregations for the card fraud detection use case.

Aggregations included:
- Numeric distributions: fraud_pred, is_fraud, distance_from_home_km, tenure_months
- Category counts: customer_segment, channel, region, risk_rank
- Binary classification: fraud vs not-fraud prediction counts
- Data quality: nullable counts for key columns

NOTE: For custom aggregations like positive-class error profile, use create-positive-class-error-profile.py
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
MODEL_ID = "INSERT_MODEL_ID_HERE"  # Replace with your model ID


def column_id_from_col_name(dataset: Dataset, col_name: str) -> str:
    """Helper to get column ID from column name."""
    for col in dataset.dataset_schema.columns:
        if col.source_name == col_name:
            return col.id
    raise ValueError(f"Column '{col_name}' not found in dataset schema")


def gen_fraud_model_aggregations(dataset: Dataset) -> list[AggregationSpec]:
    """
    Generate aggregations for card fraud model matching the reference configuration.

    Includes:
    - Inference count
    - Numeric distributions and sums
    - Category counts
    - Binary classification metrics with segmentation
    - Confusion matrix with segmentation
    - Data quality (nullable counts)
    """
    # Get required column IDs
    timestamp_col_id = column_id_from_col_name(dataset, "timestamp")

    # Primary columns
    fraud_pred_col_id = column_id_from_col_name(dataset, "fraud_pred")
    is_fraud_col_id = column_id_from_col_name(dataset, "is_fraud")

    # Additional numeric columns
    distance_col_id = column_id_from_col_name(dataset, "distance_from_home_km")
    tenure_col_id = column_id_from_col_name(dataset, "tenure_months")

    # Try to get additional numeric columns (optional)
    numeric_cols = [fraud_pred_col_id, is_fraud_col_id, distance_col_id, tenure_col_id]
    try:
        transaction_amount_col_id = column_id_from_col_name(dataset, "transaction_amount")
        numeric_cols.append(transaction_amount_col_id)
    except ValueError:
        transaction_amount_col_id = None

    try:
        merchant_risk_score_col_id = column_id_from_col_name(dataset, "merchant_risk_score")
        numeric_cols.append(merchant_risk_score_col_id)
    except ValueError:
        merchant_risk_score_col_id = None

    # Categorical columns
    customer_segment_col_id = column_id_from_col_name(dataset, "customer_segment")
    channel_col_id = column_id_from_col_name(dataset, "channel")
    region_col_id = column_id_from_col_name(dataset, "region")
    risk_rank_col_id = column_id_from_col_name(dataset, "risk_rank")

    categorical_cols = [customer_segment_col_id, channel_col_id, region_col_id, risk_rank_col_id]

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

    # 2-3. Sum of fraud predictions and is_fraud
    for col_id in [fraud_pred_col_id, is_fraud_col_id]:
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

    # 4-N. Distributions for all numeric columns
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
    # BINARY CLASSIFICATION METRICS
    # ========================================

    # Confusion Matrix with segmentation (region, risk_rank)
    aggregation_specs.append(
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000001e",
            aggregation_init_args=[],
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                MetricsArgSpec(arg_key="prediction_col", arg_value=fraud_pred_col_id),
                MetricsArgSpec(arg_key="gt_values_col", arg_value=is_fraud_col_id),
                MetricsArgSpec(arg_key="threshold", arg_value=0.5),
                MetricsArgSpec(arg_key="segmentation_cols", arg_value=[region_col_id, risk_rank_col_id]),
            ],
        )
    )

    # Inference count by class with segmentation (Fraud vs Authorized)
    aggregation_specs.append(
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-000000000020",
            aggregation_init_args=[],
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                MetricsArgSpec(arg_key="prediction_col", arg_value=fraud_pred_col_id),
                MetricsArgSpec(arg_key="threshold", arg_value=0.5),
                MetricsArgSpec(arg_key="true_label", arg_value="Fraud"),
                MetricsArgSpec(arg_key="false_label", arg_value="Authorized"),
                MetricsArgSpec(arg_key="segmentation_cols", arg_value=[risk_rank_col_id, region_col_id]),
            ],
        )
    )

    # ========================================
    # NULLABLE COUNTS (Data Quality)
    # ========================================

    # Nullable counts for all key columns (numeric + categorical)
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

    # Generate custom aggregations
    print(f"\n⚙️  Generating fraud model aggregations...")
    try:
        new_aggregations = gen_fraud_model_aggregations(dataset)
        print(f"✓ Generated {len(new_aggregations)} aggregations")
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nPlease verify that your dataset has these columns:")
        print("  - timestamp, fraud_pred, is_fraud, distance_from_home_km, tenure_months")
        print("  - customer_segment, channel, region, risk_rank")
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
    print(f"  • Numeric sums: fraud_pred, is_fraud totals")
    print(f"  • Numeric distributions: all numeric columns (min/max/mean/std)")
    print(f"  • Category counts: customer_segment, channel, region, risk_rank")
    print(f"  • Confusion matrix: with segmentation by region and risk_rank")
    print(f"  • Inference count by class: Fraud vs Authorized with segmentation")
    print(f"  • Data quality: nullable counts for all tracked columns")
    print(f"\n💡 To add custom error profile metrics, run: python create-positive-class-error-profile.py")

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
    print(f"  1. (Optional) Run create-positive-class-error-profile.py to add custom error metrics")
    print(f"  2. Wait for next scheduled metric calculation (hourly)")
    print(f"  3. View metrics in Arthur UI at {ARTHUR_HOST}")
    print(f"  4. Monitor for drift in fraud_pred and key features")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nMake sure you've updated MODEL_ID in the script.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
