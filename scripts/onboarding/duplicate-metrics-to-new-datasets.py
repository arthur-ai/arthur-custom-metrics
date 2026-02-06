"""
Duplicate Metrics from Old Datasets to New Datasets

PURPOSE: Copy metrics from old→new datasets, mapping columns by name
USAGE: python duplicate-metrics-to-new-datasets.py
WHEN: Dataset migration, schema changes, connector updates, S3 bucket changes

HOW IT WORKS:
  1. Maps columns old→new by source_name
  2. Creates new aggregations with updated IDs
  3. Validates old metrics unchanged
  4. Replaces metrics for new datasets

REQUIRES:
  - Model ID with multiple datasets
  - OLD_DATASETS and DATASET_MAPPING dictionaries

CONFIGURE:
  - MODEL_ID
  - OLD_DATASETS = {"name": "old-id"}
  - DATASET_MAPPING = {"old-id": "new-id"}

FEATURES:
  - Smart column mapping by name (not ID)
  - Handles removed columns gracefully
  - Validation before applying
  - Confirmation prompt

WARNING: REPLACES all metrics for new datasets; cannot undo
"""

import json
from arthur_client.api_bindings import (
    DatasetsV1Api,
    ModelsV1Api,
)
from arthur_client.api_bindings.models import *
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.auth import ArthurOAuthSessionAPIConfiguration, DeviceAuthorizer

# Script to duplicate aggregation specs from old datasets to new datasets
# Maps column IDs from old to new datasets based on column source_name

# CONFIGURATION - UPDATE THESE
ARTHUR_HOST = "https://platform.arthur.ai"
MODEL_ID = "YOUR_MODEL_ID_HERE"  # Set your model ID

# Old dataset IDs that have existing aggregation specs
# TODO: Update this mapping with your actual dataset names and IDs
OLD_DATASETS = {
    "dataset-v1": "OLD_DATASET_ID_1",
    "dataset-v1-metrics": "OLD_DATASET_ID_2",
}

# Mapping from old dataset IDs to new dataset IDs
# TODO: Update this mapping with your actual dataset migration
DATASET_MAPPING = {
    "OLD_DATASET_ID_1": "NEW_DATASET_ID_1",  # dataset-v1 -> dataset-v2
    "OLD_DATASET_ID_2": "NEW_DATASET_ID_2",  # dataset-v1-metrics -> dataset-v2-metrics
}


def count_aggs_per_dataset(
    agg_specs: list[AggregationSpec], dataset_map: dict[str, Dataset]
) -> dict[str, int]:
    """
    Counts the number of aggregation specs per dataset.
    Returns: {dataset_name: count}
    """
    counts = {}
    for agg in agg_specs:
        # Find the dataset arg
        dataset_id = None
        for arg in agg.aggregation_args:
            if arg.arg_key == "dataset":
                dataset_id = arg.arg_value
                break

        if dataset_id and dataset_id in dataset_map:
            dataset_name = dataset_map[dataset_id].name
            counts[dataset_name] = counts.get(dataset_name, 0) + 1

    return counts


def is_uuid(value: any) -> bool:
    """Check if a value is a UUID string."""
    if not isinstance(value, str):
        return False
    try:
        # UUIDs are 36 characters with dashes in specific positions
        import uuid
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def get_column_mapping(
    old_dataset: Dataset, new_dataset: Dataset
) -> tuple[dict[str, str], set[str]]:
    """
    Creates a mapping of column IDs from old dataset to new dataset based on source_name.
    Returns: (column_mapping, removed_columns)
        - column_mapping: {old_column_id: new_column_id}
        - removed_columns: set of old column IDs that don't exist in new dataset
    """
    # Build a map of source_name -> column_id for new dataset
    new_col_map = {
        col.source_name: col.id for col in new_dataset.dataset_schema.columns
    }

    # Build mapping from old column IDs to new column IDs
    column_mapping = {}
    removed_columns = set()

    for old_col in old_dataset.dataset_schema.columns:
        if old_col.source_name in new_col_map:
            column_mapping[old_col.id] = new_col_map[old_col.source_name]
        else:
            removed_columns.add(old_col.id)
            print(
                f"WARNING: Column '{old_col.source_name}' (ID: {old_col.id}) from old dataset not found in new dataset - will be tracked as removed"
            )

    return column_mapping, removed_columns


def map_aggregation_spec(
    agg_spec: AggregationSpec,
    old_dataset_id: str,
    new_dataset_id: str,
    column_mapping: dict[str, str],
    removed_columns: set[str],
) -> AggregationSpec | None:
    """
    Creates a new aggregation spec with updated dataset ID and column IDs.
    For any arg whose value is a UUID that exists in the column mapping, swap it.
    Special handling for 'segmentation' arg which contains a list of column IDs.
    Returns None if the aggregation references any removed columns.
    """
    new_args = []

    for arg in agg_spec.aggregation_args:
        new_arg_value = arg.arg_value

        # Update dataset reference
        if arg.arg_key == "dataset" and arg.arg_value == old_dataset_id:
            new_arg_value = new_dataset_id
        # Special handling for segmentation - it's a list of column IDs
        elif arg.arg_key == "segmentation" and isinstance(arg.arg_value, list):
            new_arg_value = []
            for col_id in arg.arg_value:
                if is_uuid(col_id) and col_id in removed_columns:
                    # Skip this aggregation if it references a removed column
                    print(
                        f"  SKIP: Aggregation references removed column {col_id} in segmentation"
                    )
                    return None
                elif is_uuid(col_id) and col_id in column_mapping:
                    new_col_id = column_mapping[col_id]
                    new_arg_value.append(new_col_id)
                    print(f"  Mapping segmentation column: {col_id} -> {new_col_id}")
                elif is_uuid(col_id):
                    print(
                        f"  WARNING: Segmentation column {col_id} not found in column mapping, keeping as-is"
                    )
                    new_arg_value.append(col_id)
                else:
                    # Not a UUID, keep as-is
                    new_arg_value.append(col_id)
        # Check if this is a removed column
        elif is_uuid(arg.arg_value) and arg.arg_value in removed_columns:
            # Skip this aggregation if it references a removed column
            print(
                f"  SKIP: Aggregation references removed column {arg.arg_value} for {arg.arg_key}"
            )
            return None
        # Update any column references (check if value is a UUID in the column mapping)
        elif is_uuid(arg.arg_value) and arg.arg_value in column_mapping:
            new_arg_value = column_mapping[arg.arg_value]
            print(f"  Mapping column {arg.arg_key}: {arg.arg_value} -> {new_arg_value}")
        # If it's a UUID but not in the mapping, warn but keep the value
        elif is_uuid(arg.arg_value) and arg.arg_value not in column_mapping:
            print(
                f"  WARNING: UUID {arg.arg_value} for {arg.arg_key} not found in column mapping, keeping as-is"
            )
        # All other values (thresholds, labels, etc.) are copied as-is

        new_args.append(
            MetricsArgSpec(
                arg_key=arg.arg_key,
                arg_value=new_arg_value,
            )
        )

    # Preserve aggregation_kind and aggregation_version from source
    spec_dict = {
        "aggregation_id": agg_spec.aggregation_id,
        "aggregation_init_args": agg_spec.aggregation_init_args,
        "aggregation_args": new_args,
    }

    # Copy aggregation_kind if present
    if agg_spec.aggregation_kind:
        spec_dict["aggregation_kind"] = agg_spec.aggregation_kind

    # Copy aggregation_version if present (required for custom aggregations)
    if hasattr(agg_spec, 'aggregation_version') and agg_spec.aggregation_version:
        spec_dict["aggregation_version"] = agg_spec.aggregation_version

    return AggregationSpec(**spec_dict)




if __name__ == "__main__":
    # Authenticate
    sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
    api_client = ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
    )
    models_client = ModelsV1Api(api_client)
    datasets_client = DatasetsV1Api(api_client)

    # Get model and its metric config
    print(f"Fetching model {MODEL_ID}...")
    model = models_client.get_model(model_id=MODEL_ID)
    print(f"Model: {model.name}")
    print(f"Current aggregation specs: {len(model.metric_config.aggregation_specs)}")

    # Get all datasets for the model
    print(f"\nFetching datasets for model...")
    datasets = datasets_client.get_datasets(
        project_id=model.project_id, model_ids=[model.id]
    ).records
    print(f"Found {len(datasets)} datasets")

    # Create a map of dataset ID to dataset object
    dataset_map = {ds.id: ds for ds in datasets}

    # Display all datasets
    print("\nDatasets:")
    for ds in datasets:
        print(f"  - {ds.name} (ID: {ds.id})")

    # Count and display current aggregations per dataset
    print(f"\n{'='*80}")
    print("CURRENT AGGREGATION COUNTS BY DATASET")
    print(f"{'='*80}")
    current_counts = count_aggs_per_dataset(
        model.metric_config.aggregation_specs, dataset_map
    )
    for dataset_name in sorted(current_counts.keys()):
        count = current_counts[dataset_name]
        print(f"  {dataset_name}: {count} aggregation specs")
    print(f"Total: {sum(current_counts.values())} aggregation specs")

    # Process each old dataset and find its corresponding new dataset
    new_aggregation_specs = []

    for old_dataset_suffix, old_dataset_id in OLD_DATASETS.items():
        print(f"\n{'='*80}")
        print(f"Processing old dataset: {old_dataset_suffix} ({old_dataset_id})")

        # Get the old dataset
        if old_dataset_id not in dataset_map:
            print(f"ERROR: Old dataset {old_dataset_id} not found in model datasets")
            continue

        old_dataset = dataset_map[old_dataset_id]
        print(f"Old dataset name: {old_dataset.name}")

        # Get new dataset ID from mapping
        if old_dataset_id not in DATASET_MAPPING:
            print(f"ERROR: No mapping found for old dataset {old_dataset_id}")
            continue

        new_dataset_id = DATASET_MAPPING[old_dataset_id]

        # Get the new dataset object
        if new_dataset_id not in dataset_map:
            print(f"ERROR: New dataset {new_dataset_id} not found in model datasets")
            continue

        new_dataset = dataset_map[new_dataset_id]
        print(f"New dataset name: {new_dataset.name}")
        print(f"New dataset ID: {new_dataset.id}")

        # Create column mapping
        column_mapping, removed_columns = get_column_mapping(old_dataset, new_dataset)
        print(f"Mapped {len(column_mapping)} columns")
        if removed_columns:
            print(f"Found {len(removed_columns)} removed columns")

        # Find all agg specs for this old dataset
        old_agg_specs = [
            agg
            for agg in model.metric_config.aggregation_specs
            if any(
                arg.arg_key == "dataset" and arg.arg_value == old_dataset_id
                for arg in agg.aggregation_args
            )
        ]

        print(f"Found {len(old_agg_specs)} aggregation specs for old dataset")

        # Create new agg specs for the new dataset
        skipped_count = 0
        for agg_spec in old_agg_specs:
            new_agg_spec = map_aggregation_spec(
                agg_spec, old_dataset_id, new_dataset.id, column_mapping, removed_columns
            )
            if new_agg_spec is not None:
                new_aggregation_specs.append(new_agg_spec)
            else:
                skipped_count += 1

        created_count = len(old_agg_specs) - skipped_count
        print(f"Created {created_count} new aggregation specs for new dataset")
        if skipped_count > 0:
            print(f"Skipped {skipped_count} aggregation specs due to removed columns")

    # Combine specs: Keep old dataset aggregations, REPLACE new dataset aggregations
    # Get IDs of new datasets
    new_dataset_ids = set(DATASET_MAPPING.values())

    # Keep all aggregations that DON'T reference the new datasets
    retained_aggregation_specs = [
        agg
        for agg in model.metric_config.aggregation_specs
        if not any(
            arg.arg_key == "dataset" and arg.arg_value in new_dataset_ids
            for arg in agg.aggregation_args
        )
    ]

    print(f"\nRetained {len(retained_aggregation_specs)} aggregations (excluding new datasets)")
    print(f"Adding {len(new_aggregation_specs)} new aggregations for new datasets")

    # Combine: retained (old) + new
    all_aggregation_specs = retained_aggregation_specs + new_aggregation_specs

    # Count and display final aggregations per dataset
    print(f"\n{'='*80}")
    print("FINAL AGGREGATION COUNTS BY DATASET")
    print(f"{'='*80}")
    final_counts = count_aggs_per_dataset(all_aggregation_specs, dataset_map)
    for dataset_name in sorted(final_counts.keys()):
        count = final_counts[dataset_name]
        print(f"  {dataset_name}: {count} aggregation specs")
    print(f"Total: {sum(final_counts.values())} aggregation specs")

    # Show changes
    print(f"\n{'='*80}")
    print("CHANGES")
    print(f"{'='*80}")
    all_dataset_names = set(current_counts.keys()) | set(final_counts.keys())
    for dataset_name in sorted(all_dataset_names):
        old_count = current_counts.get(dataset_name, 0)
        new_count = final_counts.get(dataset_name, 0)
        if old_count != new_count:
            change = new_count - old_count
            change_str = f"+{change}" if change > 0 else str(change)
            print(f"  {dataset_name}: {old_count} -> {new_count} ({change_str})")

    # Validation: Ensure old dataset aggregations are unchanged
    print(f"\n{'='*80}")
    print("VALIDATION: Checking old dataset aggregations are unchanged")
    print(f"{'='*80}")

    old_dataset_ids = set(OLD_DATASETS.values())

    # Extract aggregations for old datasets from original specs
    original_old_aggs = [
        agg
        for agg in model.metric_config.aggregation_specs
        if any(
            arg.arg_key == "dataset" and arg.arg_value in old_dataset_ids
            for arg in agg.aggregation_args
        )
    ]

    # Extract aggregations for old datasets from final specs
    final_old_aggs = [
        agg
        for agg in all_aggregation_specs
        if any(
            arg.arg_key == "dataset" and arg.arg_value in old_dataset_ids
            for arg in agg.aggregation_args
        )
    ]

    # Compare counts
    if len(original_old_aggs) != len(final_old_aggs):
        print(f"❌ ERROR: Count mismatch for old dataset aggregations!")
        print(f"  Original: {len(original_old_aggs)}")
        print(f"  Final: {len(final_old_aggs)}")
    else:
        print(f"✓ Count match: {len(original_old_aggs)} aggregations for old datasets")

    # Compare JSON representations
    original_json = json.dumps([agg.model_dump() for agg in original_old_aggs], sort_keys=True)
    final_json = json.dumps([agg.model_dump() for agg in final_old_aggs], sort_keys=True)

    if original_json == final_json:
        print(f"✓ VALIDATION PASSED: Old dataset aggregations are identical")
    else:
        print(f"❌ VALIDATION FAILED: Old dataset aggregations have changed!")
        print(f"  This should not happen. Please review the changes.")
        # Show which datasets have differences
        for old_dataset_suffix, old_dataset_id in OLD_DATASETS.items():
            orig_aggs_for_ds = [
                agg for agg in original_old_aggs
                if any(arg.arg_key == "dataset" and arg.arg_value == old_dataset_id
                       for arg in agg.aggregation_args)
            ]
            final_aggs_for_ds = [
                agg for agg in final_old_aggs
                if any(arg.arg_key == "dataset" and arg.arg_value == old_dataset_id
                       for arg in agg.aggregation_args)
            ]
            if json.dumps([a.model_dump() for a in orig_aggs_for_ds], sort_keys=True) != \
               json.dumps([a.model_dump() for a in final_aggs_for_ds], sort_keys=True):
                print(f"    - {old_dataset_suffix} ({old_dataset_id}): DIFFERENT")

    # Output the final JSON
    print(f"\n{'='*80}")
    print(f"FINAL RESULT")
    print(f"{'='*80}")
    print(f"Original aggregation specs: {len(model.metric_config.aggregation_specs)}")
    print(f"Retained aggregation specs (old datasets): {len(retained_aggregation_specs)}")
    print(f"New aggregation specs (new datasets): {len(new_aggregation_specs)}")
    print(f"Total aggregation specs: {len(all_aggregation_specs)}")

    # Ask for confirmation before applying
    print(f"\n{'='*80}")
    print("CONFIRMATION")
    print(f"{'='*80}")
    response = input("Do you want to apply these metrics to the model? (yes/no): ")

    if response.lower() == "yes":
        # Create the PutModelMetricSpec object with combined specs
        put_metric_spec = PutModelMetricSpec(aggregation_specs=all_aggregation_specs)

        # Apply the new metrics
        models_client.put_model_metric_config(
            model_id=MODEL_ID,
            put_model_metric_spec=put_metric_spec,
        )
        print("✓ Metrics successfully applied to model!")
    else:
        print("Skipped applying metrics. No changes made.")
        print(f"\nTo manually apply these metrics later, use:")
        print(f"PUT /models/{MODEL_ID}/metric-config")
