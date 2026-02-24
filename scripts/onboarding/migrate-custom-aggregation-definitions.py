"""
Migrate Custom Aggregation Definitions Between Arthur Workspaces

PURPOSE: Copies custom (SQL-based) aggregation definitions from a source workspace
         to a destination workspace. These are the reusable metric templates created
         via CustomAggregationsV1Api - they live at the workspace level, not on
         individual models.

USAGE: python migrate-custom-aggregation-definitions.py

WHEN TO RUN THIS:
  Run this BEFORE migrate-model-metric-config.py when your source model uses
  custom (SQL-based) aggregations. The model migration script expects these
  definitions to already exist in the destination workspace.

HOW IT WORKS:
  1. Lists all custom aggregation definitions in the source workspace
  2. Lists existing custom aggregation definitions in the destination workspace
  3. For each source definition not found in destination (matched by name),
     creates it in the destination workspace
  4. Reports which were created, which already existed, and which failed

CONFIGURE:
  - SOURCE_ARTHUR_HOST, SOURCE_WORKSPACE_ID
  - DEST_ARTHUR_HOST, DEST_WORKSPACE_ID

NOTES:
  - Matching is done by aggregation name - if a same-named definition already
    exists in the destination it will be reused, not overwritten
  - Workspace IDs can be found in the Arthur UI under workspace settings
  - Set DEST_ARTHUR_HOST = SOURCE_ARTHUR_HOST if both workspaces are on the
    same platform (only one browser login will be required)
"""

from arthur_client.api_bindings import CustomAggregationsV1Api
from arthur_client.api_bindings.models import PostCustomAggregationSpecSchema
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.auth import ArthurOAuthSessionAPIConfiguration, DeviceAuthorizer

# ============================================================
# CONFIGURATION - Update these before running
# ============================================================

# Source workspace (where custom aggregation definitions are copied FROM)
SOURCE_ARTHUR_HOST = "https://platform.arthur.ai"
SOURCE_WORKSPACE_ID = "INSERT_SOURCE_WORKSPACE_ID_HERE"  # Get from Arthur UI

# Destination workspace (where custom aggregation definitions are copied TO)
# Set DEST_ARTHUR_HOST = SOURCE_ARTHUR_HOST if both workspaces are on the same platform
DEST_ARTHUR_HOST = "https://platform.arthur.ai"
DEST_WORKSPACE_ID = "INSERT_DEST_WORKSPACE_ID_HERE"  # Get from Arthur UI


# ============================================================
# HELPERS
# ============================================================

def make_api_client(host: str, label: str) -> ApiClient:
    """Authenticate via device flow and return an ApiClient for the given host."""
    print(f"\nAuthenticating with {label} ({host})...")
    sess = DeviceAuthorizer(arthur_host=host).authorize()
    return ApiClient(configuration=ArthurOAuthSessionAPIConfiguration(session=sess))


# ============================================================
# MAIN
# ============================================================

def main():
    # --------------------------------------------------------
    # Step 1: Connect to source and list all custom aggregations
    # --------------------------------------------------------
    source_api = make_api_client(SOURCE_ARTHUR_HOST, "source")
    src_custom_agg_client = CustomAggregationsV1Api(source_api)

    print(f"\nFetching custom aggregation definitions from source workspace {SOURCE_WORKSPACE_ID}...")
    src_resp = src_custom_agg_client.get_custom_aggregations(workspace_id=SOURCE_WORKSPACE_ID)
    source_aggs = src_resp.records
    print(f"  Found {len(source_aggs)} custom aggregation definition(s)")

    if not source_aggs:
        print("\nNo custom aggregation definitions found in source workspace. Nothing to migrate.")
        return

    for agg in source_aggs:
        print(f"  - '{agg.name}' (ID: {agg.id}, versions: {len(agg.versions)})")

    # --------------------------------------------------------
    # Step 2: Connect to destination and list existing definitions
    # --------------------------------------------------------
    if DEST_ARTHUR_HOST == SOURCE_ARTHUR_HOST:
        print(f"\nSource and destination share the same host - reusing authentication")
        dest_api = source_api
    else:
        dest_api = make_api_client(DEST_ARTHUR_HOST, "destination")

    dest_custom_agg_client = CustomAggregationsV1Api(dest_api)

    print(f"\nFetching existing custom aggregation definitions from destination workspace {DEST_WORKSPACE_ID}...")
    dest_resp = dest_custom_agg_client.get_custom_aggregations(workspace_id=DEST_WORKSPACE_ID)
    dest_existing_by_name = {agg.name: agg for agg in dest_resp.records}
    print(f"  Found {len(dest_existing_by_name)} existing definition(s)")

    # --------------------------------------------------------
    # Step 3: Determine what needs to be created
    # --------------------------------------------------------
    to_create = [agg for agg in source_aggs if agg.name not in dest_existing_by_name]
    already_exist = [agg for agg in source_aggs if agg.name in dest_existing_by_name]

    print(f"\nSummary:")
    print(f"  Already in destination (will skip): {len(already_exist)}")
    print(f"  Will be created:                    {len(to_create)}")

    if not to_create:
        print("\nAll source custom aggregation definitions already exist in the destination.")
        return

    print(f"\nDefinitions to create:")
    for agg in to_create:
        print(f"  - '{agg.name}'")

    response = input("\nCreate these definitions in the destination workspace? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled. No changes made.")
        return

    # --------------------------------------------------------
    # Step 4: Create missing definitions in destination
    # --------------------------------------------------------
    created = []
    failed = []

    for source_agg in to_create:
        if not source_agg.versions:
            print(f"  WARNING: '{source_agg.name}' has no versions, skipping")
            failed.append(source_agg.name)
            continue

        version = source_agg.versions[0]
        print(f"\n  Creating '{source_agg.name}'...")

        try:
            spec = PostCustomAggregationSpecSchema(
                name=source_agg.name,
                description=source_agg.description,
                sql=version.sql,
                reported_aggregations=version.reported_aggregations,
                aggregate_args=version.aggregate_args,
            )
            result = dest_custom_agg_client.post_custom_aggregation(
                workspace_id=DEST_WORKSPACE_ID,
                post_custom_aggregation_spec_schema=spec,
            )
            print(f"    Created (ID: {result.id}, version: {result.latest_version})")
            created.append(source_agg.name)
        except Exception as e:
            print(f"    ERROR: {e}")
            failed.append(source_agg.name)

    # --------------------------------------------------------
    # Step 5: Final summary
    # --------------------------------------------------------
    print(f"\n{'='*60}")
    print("MIGRATION COMPLETE")
    print(f"{'='*60}")
    print(f"  Already existed (skipped): {len(already_exist)}")
    print(f"  Successfully created:      {len(created)}")
    print(f"  Failed:                    {len(failed)}")

    if failed:
        print(f"\n  Failed definitions: {failed}")

    if created or already_exist:
        print(f"\nNext step: Run migrate-model-metric-config.py to copy model metric configurations.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
