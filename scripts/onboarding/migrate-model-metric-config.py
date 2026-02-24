"""
Migrate Model Metric Configuration Between Arthur Endpoints

PURPOSE: Copies all aggregation specs from a source model to a destination model,
         remapping dataset and column IDs by name. Handles both built-in aggregations
         (inference count, distributions, etc.) and custom SQL-based aggregations.

USAGE: python migrate-model-metric-config.py

PREREQUISITE:
  If your source model uses custom (SQL-based) aggregations, run
  migrate-custom-aggregation-definitions.py first to ensure those definitions
  exist in the destination workspace before running this script.

HOW IT WORKS:
  1. Connects to source, fetches the model's aggregation specs and dataset schemas
  2. For CUSTOM aggregations, fetches their definitions from the source workspace
     to resolve their names
  3. Connects to destination, fetches the dest model and datasets
  4. Looks up custom aggregation definitions in the dest workspace by name
     (does not create them - run migrate-custom-aggregation-definitions.py for that)
  5. Remaps all dataset and column IDs by matching source_name across datasets
  6. Deduplicates against specs already on the destination model
  7. Prompts for confirmation, then applies to the destination model

CONFIGURE:
  - SOURCE_ARTHUR_HOST, SOURCE_MODEL_ID
  - DEST_ARTHUR_HOST, DEST_MODEL_ID
  - SKIP_EXISTING (default True) - skip specs already present in destination

NOTES:
  - Datasets are matched between source and dest by dataset.name
  - Columns within datasets are matched by col.source_name
  - Custom aggregations are looked up in the dest workspace by name
  - Specs that reference unmapped datasets, columns, or missing custom aggregation
    definitions are skipped with a warning
  - Set DEST_ARTHUR_HOST = SOURCE_ARTHUR_HOST if migrating between models on the
    same platform (only one browser login will be required)
"""

import uuid

from arthur_client.api_bindings import (
    CustomAggregationsV1Api,
    DatasetsV1Api,
    ModelsV1Api,
    ProjectsV1Api,
)
from arthur_client.api_bindings.models import (
    AggregationSpec,
    MetricsArgSpec,
    PutModelMetricSpec,
)
from arthur_client.api_bindings.models.aggregation_kind import AggregationKind
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.auth import ArthurOAuthSessionAPIConfiguration, DeviceAuthorizer

# ============================================================
# CONFIGURATION - Update these before running
# ============================================================

# Source model (where metric config is copied FROM)
SOURCE_ARTHUR_HOST = "https://platform.arthur.ai"
SOURCE_MODEL_ID = "INSERT_SOURCE_MODEL_ID_HERE"

# Destination model (where metric config is copied TO)
# Set DEST_ARTHUR_HOST = SOURCE_ARTHUR_HOST if migrating between models on the same platform
DEST_ARTHUR_HOST = "https://platform.arthur.ai"
DEST_MODEL_ID = "INSERT_DEST_MODEL_ID_HERE"

# If True, skip specs that already exist in the destination model
# (matched by aggregation_id + argument values)
SKIP_EXISTING = True


# ============================================================
# HELPERS
# ============================================================

def is_uuid(value) -> bool:
    """Return True if value is a valid UUID string."""
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def make_api_client(host: str, label: str) -> ApiClient:
    """Authenticate via device flow and return an ApiClient for the given host."""
    print(f"\nAuthenticating with {label} ({host})...")
    sess = DeviceAuthorizer(arthur_host=host).authorize()
    return ApiClient(configuration=ArthurOAuthSessionAPIConfiguration(session=sess))


def get_workspace_id(model, projects_client) -> str:
    """Derive workspace ID from the model's project."""
    project = projects_client.get_project(project_id=model.project_id)
    return project.workspace_id


def fetch_model_and_datasets(models_client, datasets_client, model_id: str) -> tuple:
    """
    Fetch a model and all its associated datasets.
    Returns: (model, {dataset_id: Dataset})
    """
    model = models_client.get_model(model_id=model_id)
    if not model.datasets:
        raise ValueError(f"Model {model_id} has no associated datasets")

    datasets = {}
    for ds_ref in model.datasets:
        ds = datasets_client.get_dataset(dataset_id=ds_ref.dataset_id)
        datasets[ds.id] = ds

    return model, datasets


def build_id_mappings(source_datasets: dict, dest_datasets: dict) -> tuple[dict, dict]:
    """
    Build source-to-destination ID mappings by matching on name.

    Datasets are matched by dataset.name.
    Columns within matched datasets are matched by col.source_name.

    Returns:
        dataset_mapping: {source_dataset_id: dest_dataset_id}
        column_mapping:  {source_column_id: dest_column_id}
    """
    dataset_mapping = {}
    column_mapping = {}

    dest_by_name = {ds.name: ds for ds in dest_datasets.values()}

    for src_ds_id, src_ds in source_datasets.items():
        if src_ds.name not in dest_by_name:
            print(f"  WARNING: Source dataset '{src_ds.name}' not found in destination by name - its aggregations will be skipped")
            print(f"           Available destination datasets: {list(dest_by_name.keys())}")
            continue

        dest_ds = dest_by_name[src_ds.name]
        dataset_mapping[src_ds_id] = dest_ds.id

        dest_col_by_name = {
            col.source_name: col.id for col in dest_ds.dataset_schema.columns
        }

        for src_col in src_ds.dataset_schema.columns:
            if src_col.source_name in dest_col_by_name:
                column_mapping[src_col.id] = dest_col_by_name[src_col.source_name]
            else:
                print(f"  WARNING: Column '{src_col.source_name}' not found in destination dataset '{dest_ds.name}'")

    return dataset_mapping, column_mapping


def fetch_source_custom_agg_definitions(custom_agg_client, agg_specs: list, workspace_id: str) -> dict:
    """
    Fetch custom aggregation definitions for all CUSTOM kind specs in the source model.
    This is needed only to resolve their names for lookup in the destination workspace.

    Returns: {source_aggregation_id: custom_aggregation_object}
    """
    custom_defs = {}

    for agg_spec in agg_specs:
        if agg_spec.aggregation_kind != AggregationKind.CUSTOM:
            continue
        if agg_spec.aggregation_id in custom_defs:
            continue

        try:
            custom_agg = custom_agg_client.get_custom_aggregation(
                aggregation_id=agg_spec.aggregation_id,
                workspace_id=workspace_id,
            )
            custom_defs[agg_spec.aggregation_id] = custom_agg
            print(f"  Source custom aggregation: '{custom_agg.name}' (ID: {agg_spec.aggregation_id})")
        except Exception as e:
            print(f"  WARNING: Could not fetch source custom aggregation {agg_spec.aggregation_id}: {e}")

    return custom_defs


def lookup_custom_aggs_in_dest(custom_agg_client, dest_workspace_id: str, source_custom_defs: dict) -> dict:
    """
    Look up custom aggregation definitions in the destination workspace by name.
    Does NOT create any - run migrate-custom-aggregation-definitions.py for that.

    Returns: {source_agg_id: (dest_agg_id, dest_agg_version)}
    """
    if not source_custom_defs:
        return {}

    print(f"\nLooking up custom aggregation definitions in destination workspace...")
    try:
        dest_resp = custom_agg_client.get_custom_aggregations(workspace_id=dest_workspace_id)
        dest_by_name = {agg.name: agg for agg in dest_resp.records}
        print(f"  Found {len(dest_by_name)} definition(s) in destination workspace")
    except Exception as e:
        print(f"  WARNING: Could not list destination custom aggregations: {e}")
        dest_by_name = {}

    agg_id_mapping = {}
    missing = []

    for source_agg_id, source_agg in source_custom_defs.items():
        if source_agg.name in dest_by_name:
            dest_agg = dest_by_name[source_agg.name]
            agg_id_mapping[source_agg_id] = (dest_agg.id, dest_agg.latest_version)
            print(f"  Found '{source_agg.name}' in destination (ID: {dest_agg.id})")
        else:
            missing.append(source_agg.name)
            print(f"  NOT FOUND: '{source_agg.name}' - aggregation specs referencing this will be skipped")

    if missing:
        print(f"\n  To create missing definitions, run first:")
        print(f"    python migrate-custom-aggregation-definitions.py")

    return agg_id_mapping


def translate_arg_value(arg_key: str, arg_value, dataset_mapping: dict, column_mapping: dict) -> tuple:
    """
    Translate a single aggregation arg value from source IDs to destination IDs.

    Returns: (translated_value, ok)
      ok=False means a required mapping was missing; the caller should skip this spec.
    """
    # Dataset reference
    if arg_key == "dataset":
        if arg_value in dataset_mapping:
            return dataset_mapping[arg_value], True
        print(f"  SKIP: Aggregation references unmapped dataset {arg_value}")
        return None, False

    # List of column IDs (e.g. segmentation_cols)
    if isinstance(arg_value, list):
        new_list = []
        for item in arg_value:
            if is_uuid(item):
                if item in column_mapping:
                    new_list.append(column_mapping[item])
                else:
                    print(f"  SKIP: Aggregation references unmapped column {item} in list arg '{arg_key}'")
                    return None, False
            else:
                new_list.append(item)
        return new_list, True

    # Single column/UUID reference
    if is_uuid(arg_value):
        if arg_value in column_mapping:
            return column_mapping[arg_value], True
        if arg_value in dataset_mapping:
            return dataset_mapping[arg_value], True
        # Unknown UUID (e.g. literal UUID passed as a parameter) - keep with a warning
        print(f"  WARNING: UUID '{arg_value}' for arg '{arg_key}' not found in any mapping, keeping as-is")
        return arg_value, True

    # Non-UUID scalar (threshold, label string, etc.) - copy unchanged
    return arg_value, True


def translate_aggregation_spec(
    agg_spec: AggregationSpec,
    dataset_mapping: dict,
    column_mapping: dict,
    custom_agg_id_mapping: dict,
) -> AggregationSpec | None:
    """
    Produce a new AggregationSpec with all source IDs replaced by destination IDs.
    Returns None if any required mapping is missing (spec is skipped with a warning).
    """
    new_args = []
    for arg in agg_spec.aggregation_args:
        new_value, ok = translate_arg_value(arg.arg_key, arg.arg_value, dataset_mapping, column_mapping)
        if not ok:
            return None
        new_args.append(MetricsArgSpec(arg_key=arg.arg_key, arg_value=new_value))

    spec_kwargs = {
        "aggregation_init_args": agg_spec.aggregation_init_args or [],
        "aggregation_args": new_args,
    }

    if agg_spec.aggregation_kind == AggregationKind.CUSTOM:
        if agg_spec.aggregation_id not in custom_agg_id_mapping:
            print(f"  SKIP: Custom aggregation {agg_spec.aggregation_id} not found in destination workspace")
            return None
        dest_agg_id, dest_version = custom_agg_id_mapping[agg_spec.aggregation_id]
        spec_kwargs["aggregation_id"] = dest_agg_id
        spec_kwargs["aggregation_version"] = dest_version
        spec_kwargs["aggregation_kind"] = AggregationKind.CUSTOM
    else:
        spec_kwargs["aggregation_id"] = agg_spec.aggregation_id
        if agg_spec.aggregation_kind:
            spec_kwargs["aggregation_kind"] = agg_spec.aggregation_kind
        if hasattr(agg_spec, "aggregation_version") and agg_spec.aggregation_version:
            spec_kwargs["aggregation_version"] = agg_spec.aggregation_version

    return AggregationSpec(**spec_kwargs)


def agg_spec_fingerprint(agg: AggregationSpec) -> tuple:
    """Stable fingerprint for deduplication: (aggregation_id, sorted args)."""
    args = tuple(sorted((a.arg_key, str(a.arg_value)) for a in agg.aggregation_args))
    return (agg.aggregation_id, args)


# ============================================================
# MAIN
# ============================================================

def main():
    # --------------------------------------------------------
    # Step 1: Connect to source and fetch model + datasets
    # --------------------------------------------------------
    source_api = make_api_client(SOURCE_ARTHUR_HOST, "source")
    src_models_client = ModelsV1Api(source_api)
    src_datasets_client = DatasetsV1Api(source_api)
    src_custom_agg_client = CustomAggregationsV1Api(source_api)
    src_projects_client = ProjectsV1Api(source_api)

    print(f"\nFetching source model {SOURCE_MODEL_ID}...")
    src_model, src_datasets = fetch_model_and_datasets(src_models_client, src_datasets_client, SOURCE_MODEL_ID)
    print(f"  Name:            {src_model.name}")
    print(f"  Datasets:        {[ds.name for ds in src_datasets.values()]}")
    print(f"  Aggregation specs: {len(src_model.metric_config.aggregation_specs)}")

    src_workspace_id = get_workspace_id(src_model, src_projects_client)
    print(f"  Workspace:       {src_workspace_id}")

    # --------------------------------------------------------
    # Step 2: Resolve custom aggregation names from source workspace
    # --------------------------------------------------------
    custom_specs_count = sum(
        1 for a in src_model.metric_config.aggregation_specs
        if a.aggregation_kind == AggregationKind.CUSTOM
    )
    print(f"\nResolving custom aggregation definitions ({custom_specs_count} CUSTOM spec(s))...")
    source_custom_defs = fetch_source_custom_agg_definitions(
        src_custom_agg_client, src_model.metric_config.aggregation_specs, src_workspace_id
    )
    print(f"  Resolved {len(source_custom_defs)} unique custom aggregation definition(s)")

    # --------------------------------------------------------
    # Step 3: Connect to destination and fetch model + datasets
    # --------------------------------------------------------
    if DEST_ARTHUR_HOST == SOURCE_ARTHUR_HOST:
        print(f"\nSource and destination share the same host - reusing authentication")
        dest_api = source_api
    else:
        dest_api = make_api_client(DEST_ARTHUR_HOST, "destination")

    dest_models_client = ModelsV1Api(dest_api)
    dest_datasets_client = DatasetsV1Api(dest_api)
    dest_custom_agg_client = CustomAggregationsV1Api(dest_api)
    dest_projects_client = ProjectsV1Api(dest_api)

    print(f"\nFetching destination model {DEST_MODEL_ID}...")
    dest_model, dest_datasets = fetch_model_and_datasets(dest_models_client, dest_datasets_client, DEST_MODEL_ID)
    print(f"  Name:            {dest_model.name}")
    print(f"  Datasets:        {[ds.name for ds in dest_datasets.values()]}")
    print(f"  Aggregation specs: {len(dest_model.metric_config.aggregation_specs)}")

    dest_workspace_id = get_workspace_id(dest_model, dest_projects_client)
    print(f"  Workspace:       {dest_workspace_id}")

    # --------------------------------------------------------
    # Step 4: Look up custom aggregation definitions in destination workspace
    # --------------------------------------------------------
    custom_agg_id_mapping = lookup_custom_aggs_in_dest(
        dest_custom_agg_client, dest_workspace_id, source_custom_defs
    )

    # --------------------------------------------------------
    # Step 5: Build dataset and column ID mappings
    # --------------------------------------------------------
    print("\nBuilding dataset and column ID mappings (matched by name)...")
    dataset_mapping, column_mapping = build_id_mappings(src_datasets, dest_datasets)
    print(f"  Mapped {len(dataset_mapping)} dataset(s), {len(column_mapping)} column(s)")

    if not dataset_mapping:
        raise ValueError(
            "No datasets could be matched between source and destination by name. "
            "Ensure the destination model has datasets with the same names as the source."
        )

    # --------------------------------------------------------
    # Step 6: Translate all aggregation specs to destination IDs
    # --------------------------------------------------------
    print("\nTranslating aggregation specs...")
    translated_specs = []
    skipped_unmapped = 0

    for agg_spec in src_model.metric_config.aggregation_specs:
        translated = translate_aggregation_spec(
            agg_spec, dataset_mapping, column_mapping, custom_agg_id_mapping
        )
        if translated is not None:
            translated_specs.append(translated)
        else:
            skipped_unmapped += 1

    print(f"  Translated: {len(translated_specs)}")
    if skipped_unmapped:
        print(f"  Skipped (unmapped references): {skipped_unmapped}")

    # --------------------------------------------------------
    # Step 7: Deduplicate against existing destination specs
    # --------------------------------------------------------
    new_specs = translated_specs
    skipped_duplicates = 0

    if SKIP_EXISTING:
        existing_fingerprints = {agg_spec_fingerprint(a) for a in dest_model.metric_config.aggregation_specs}
        new_specs = []
        for spec in translated_specs:
            if agg_spec_fingerprint(spec) in existing_fingerprints:
                skipped_duplicates += 1
            else:
                new_specs.append(spec)
        if skipped_duplicates:
            print(f"  Skipping {skipped_duplicates} spec(s) already present in destination")

    all_dest_specs = dest_model.metric_config.aggregation_specs + new_specs

    # --------------------------------------------------------
    # Step 8: Summary and confirmation
    # --------------------------------------------------------
    print(f"\n{'='*60}")
    print("MIGRATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Source model:            {src_model.name}")
    print(f"  Source host:             {SOURCE_ARTHUR_HOST}")
    print(f"  Destination model:       {dest_model.name}")
    print(f"  Destination host:        {DEST_ARTHUR_HOST}")
    print(f"  Source agg specs:        {len(src_model.metric_config.aggregation_specs)}")
    print(f"  Successfully translated: {len(translated_specs)}")
    print(f"  Skipped (unmapped):      {skipped_unmapped}")
    print(f"  Skipped (duplicates):    {skipped_duplicates}")
    print(f"  New specs to add:        {len(new_specs)}")
    print(f"  Dest specs (before):     {len(dest_model.metric_config.aggregation_specs)}")
    print(f"  Dest specs (after):      {len(all_dest_specs)}")

    if not new_specs:
        print("\nNothing to do - destination already has all migrated metrics.")
        return

    response = input("\nApply these metrics to the destination model? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled. No changes made.")
        return

    # --------------------------------------------------------
    # Step 9: Apply to destination model
    # --------------------------------------------------------
    print("\nApplying metrics to destination model...")
    dest_models_client.put_model_metric_config(
        model_id=DEST_MODEL_ID,
        put_model_metric_spec=PutModelMetricSpec(aggregation_specs=all_dest_specs),
    )

    print(f"\nSuccessfully migrated model metric configuration!")
    print(f"  Added {len(new_specs)} new aggregation spec(s) to '{dest_model.name}'")
    print(f"  Destination now has {len(all_dest_specs)} total aggregation spec(s)")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
