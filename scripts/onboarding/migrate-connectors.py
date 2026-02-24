"""
Migrate Connectors Between Arthur Projects

PURPOSE: Copies all connectors from a source project to a destination project,
         stripping credential fields so they can be filled in manually via the
         Arthur UI afterward.

USAGE: python migrate-connectors.py

SUPPORTED CONNECTOR TYPES:
  - S3          (AWS Simple Storage Service)
  - GCS         (Google Cloud Storage)
  - BigQuery    (Google BigQuery)
  - ODBC        (Generic ODBC - PostgreSQL, MySQL, etc.)
  - Snowflake   (Snowflake Data Warehouse)
  - Shield      (Arthur Shield)

SKIPPED CONNECTOR TYPES:
  - ENGINE_INTERNAL  (no API-configurable fields, sourced from environment)

HOW IT WORKS:
  1. Lists all connectors in the source project
  2. For each connector, copies all structural (non-credential) fields
  3. Checks whether a same-named connector already exists in the destination
  4. Creates missing connectors in the destination project
  5. Prints a per-connector reminder of which credential fields to set in the UI

AFTER RUNNING:
  Go to the Arthur UI and update the credential fields for each created connector:
    S3         → access_key_id, secret_access_key  (or role_arn)
    GCS        → credentials  (service account JSON)
    BigQuery   → credentials  (service account JSON)
    ODBC       → password
    Snowflake  → password  (or private_key + private_key_passphrase)
    Shield     → shield_api_key  (or api_key)

CONFIGURE:
  - SOURCE_ARTHUR_HOST, SOURCE_PROJECT_ID
  - DEST_ARTHUR_HOST, DEST_PROJECT_ID, DEST_DATA_PLANE_ID

NOTES:
  - Connectors are matched by name; existing ones in destination are skipped
  - ODBC/Snowflake/BigQuery/Shield field names are sourced from SDK schema and
    may need adjustment if your Arthur version uses different key names
  - Set DEST_ARTHUR_HOST = SOURCE_ARTHUR_HOST if both projects are on the same
    platform (only one browser login required)
"""

from arthur_client.api_bindings import (
    ConnectorsV1Api,
    DataPlanesV1Api,
    ProjectsV1Api,
)
from arthur_client.api_bindings.models import (
    ConnectorSpecField,
    PostConnectorSpec,
)
from arthur_client.api_bindings.models.connector_type import ConnectorType
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.auth import ArthurOAuthSessionAPIConfiguration, DeviceAuthorizer

# ============================================================
# CONFIGURATION - Update these before running
# ============================================================

# Source project (connectors are copied FROM here)
SOURCE_ARTHUR_HOST = "https://platform.arthur.ai"
SOURCE_PROJECT_ID = "INSERT_SOURCE_PROJECT_ID_HERE"

# Destination project (connectors are created HERE)
# Set DEST_ARTHUR_HOST = SOURCE_ARTHUR_HOST if both projects are on the same platform
DEST_ARTHUR_HOST = "https://platform.arthur.ai"
DEST_PROJECT_ID = "INSERT_DEST_PROJECT_ID_HERE"

# Data plane to associate connectors with in the destination project
# Get this from the Arthur UI - required for connector creation
DEST_DATA_PLANE_ID = "INSERT_DEST_DATA_PLANE_ID_HERE"


# ============================================================
# CREDENTIAL FIELDS BY CONNECTOR TYPE
#
# These fields are stripped during migration - the user fills them
# in manually via the Arthur UI after the connector is created.
#
# NOTE: Field names reflect the Arthur API. If a connector creation
# fails with an "unknown field" error, check the Arthur UI network
# tab to confirm the exact key names your version uses.
# ============================================================

CREDENTIAL_FIELDS = {
    ConnectorType.S3: {
        "access_key_id",
        "secret_access_key",
    },
    ConnectorType.GCS: {
        "credentials",
    },
    ConnectorType.BIGQUERY: {
        "credentials",
    },
    ConnectorType.ODBC: {
        "password",
        "odbc_password",        # alternate key name in some versions
    },
    ConnectorType.SNOWFLAKE: {
        "password",
        "odbc_password",        # alternate key name in some versions
        "private_key",
        "snowflake_private_key",
        "private_key_passphrase",
        "snowflake_private_key_passphrase",
    },
    ConnectorType.SHIELD: {
        "api_key",
        "shield_api_key",       # alternate key name in some versions
    },
    ConnectorType.ENGINE_INTERNAL: set(),
}

# Human-readable reminder of what to fill in after migration
CREDENTIAL_REMINDER = {
    ConnectorType.S3: (
        "access_key_id + secret_access_key  "
        "(or leave blank and use role_arn for IAM role auth)"
    ),
    ConnectorType.GCS: (
        "credentials  (paste service account JSON)"
    ),
    ConnectorType.BIGQUERY: (
        "credentials  (paste service account JSON)"
    ),
    ConnectorType.ODBC: (
        "password"
    ),
    ConnectorType.SNOWFLAKE: (
        "password  "
        "(or private_key + private_key_passphrase for key-pair auth)"
    ),
    ConnectorType.SHIELD: (
        "shield_api_key  (or api_key)"
    ),
}


# ============================================================
# HELPERS
# ============================================================

def make_api_client(host: str, label: str) -> ApiClient:
    """Authenticate via device flow and return an ApiClient for the given host."""
    print(f"\nAuthenticating with {label} ({host})...")
    sess = DeviceAuthorizer(arthur_host=host).authorize()
    return ApiClient(configuration=ArthurOAuthSessionAPIConfiguration(session=sess))


def get_all_connectors(connectors_client, project_id: str) -> list:
    """
    Fetch all connectors for a project across all connector types.
    Returns a flat list of connector objects.
    """
    all_connectors = []

    for connector_type in ConnectorType:
        if connector_type == ConnectorType.ENGINE_INTERNAL:
            continue  # not user-managed, skip
        try:
            resp = connectors_client.get_connectors(
                project_id=project_id,
                connector_type=connector_type,
            )
            all_connectors.extend(resp.records)
        except Exception as e:
            # Some connector types may not be enabled on all platforms
            print(f"  Note: Could not list {connector_type.value} connectors: {e}")

    return all_connectors


def strip_credentials(connector) -> list[ConnectorSpecField]:
    """
    Return a copy of the connector's fields with credential fields removed.
    """
    credential_keys = CREDENTIAL_FIELDS.get(connector.connector_type, set())
    return [
        ConnectorSpecField(key=f.key, value=f.value)
        for f in connector.fields
        if f.key not in credential_keys
    ]


# ============================================================
# MAIN
# ============================================================

def main():
    # --------------------------------------------------------
    # Step 1: Connect to source and list all connectors
    # --------------------------------------------------------
    source_api = make_api_client(SOURCE_ARTHUR_HOST, "source")
    src_connectors_client = ConnectorsV1Api(source_api)

    print(f"\nFetching connectors from source project {SOURCE_PROJECT_ID}...")
    source_connectors = get_all_connectors(src_connectors_client, SOURCE_PROJECT_ID)
    print(f"  Found {len(source_connectors)} connector(s)")

    if not source_connectors:
        print("\nNo connectors found in source project. Nothing to migrate.")
        return

    for c in source_connectors:
        print(f"  - '{c.name}'  [{c.connector_type.value}]  (ID: {c.id})")

    # --------------------------------------------------------
    # Step 2: Connect to destination
    # --------------------------------------------------------
    if DEST_ARTHUR_HOST == SOURCE_ARTHUR_HOST:
        print(f"\nSource and destination share the same host - reusing authentication")
        dest_api = source_api
    else:
        dest_api = make_api_client(DEST_ARTHUR_HOST, "destination")

    dest_connectors_client = ConnectorsV1Api(dest_api)
    dest_data_planes_client = DataPlanesV1Api(dest_api)

    # Validate the destination data plane
    print(f"\nValidating destination data plane {DEST_DATA_PLANE_ID}...")
    try:
        data_plane = dest_data_planes_client.get_data_plane(data_plane_id=DEST_DATA_PLANE_ID)
        print(f"  Data plane: {data_plane.name}")
    except Exception as e:
        raise ValueError(
            f"Could not find data plane {DEST_DATA_PLANE_ID} on {DEST_ARTHUR_HOST}.\n"
            f"Get the correct data plane ID from the Arthur UI.\nError: {e}"
        )

    # --------------------------------------------------------
    # Step 3: List existing connectors in destination
    # --------------------------------------------------------
    print(f"\nFetching existing connectors in destination project {DEST_PROJECT_ID}...")
    dest_connectors = get_all_connectors(dest_connectors_client, DEST_PROJECT_ID)
    dest_names = {c.name for c in dest_connectors}
    print(f"  Found {len(dest_connectors)} existing connector(s)")

    # --------------------------------------------------------
    # Step 4: Determine what to create
    # --------------------------------------------------------
    to_create = [c for c in source_connectors if c.name not in dest_names]
    already_exist = [c for c in source_connectors if c.name in dest_names]

    print(f"\nMigration plan:")
    print(f"  Already in destination (will skip): {len(already_exist)}")
    for c in already_exist:
        print(f"    - '{c.name}'  [{c.connector_type.value}]")
    print(f"  Will be created:                    {len(to_create)}")
    for c in to_create:
        stripped = strip_credentials(c)
        cred_fields = [f.key for f in c.fields if f.key not in {sf.key for sf in stripped}]
        print(f"    - '{c.name}'  [{c.connector_type.value}]  (stripping: {cred_fields or 'none'})")

    if not to_create:
        print("\nAll source connectors already exist in the destination. Nothing to do.")
        return

    response = input("\nCreate these connectors in the destination project? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled. No changes made.")
        return

    # --------------------------------------------------------
    # Step 5: Create connectors in destination
    # --------------------------------------------------------
    created = []
    failed = []

    for connector in to_create:
        print(f"\n  Creating '{connector.name}'  [{connector.connector_type.value}]...")
        structural_fields = strip_credentials(connector)

        try:
            result = dest_connectors_client.post_connector(
                project_id=DEST_PROJECT_ID,
                post_connector_spec=PostConnectorSpec(
                    name=connector.name,
                    connector_type=connector.connector_type,
                    temporary=False,
                    data_plane_id=DEST_DATA_PLANE_ID,
                    fields=structural_fields,
                ),
            )
            print(f"    Created (ID: {result.id})")
            created.append(connector)
        except Exception as e:
            print(f"    ERROR: {e}")
            failed.append(connector)

    # --------------------------------------------------------
    # Step 6: Summary + credential update reminders
    # --------------------------------------------------------
    print(f"\n{'='*60}")
    print("MIGRATION COMPLETE")
    print(f"{'='*60}")
    print(f"  Already existed (skipped): {len(already_exist)}")
    print(f"  Successfully created:      {len(created)}")
    print(f"  Failed:                    {len(failed)}")

    if failed:
        print(f"\n  Failed connectors:")
        for c in failed:
            print(f"    - '{c.name}'  [{c.connector_type.value}]")

    if created:
        print(f"\n{'='*60}")
        print("ACTION REQUIRED: Update credentials in the Arthur UI")
        print(f"{'='*60}")
        print(f"  Go to: {DEST_ARTHUR_HOST} → Project settings → Connectors\n")
        for connector in created:
            reminder = CREDENTIAL_REMINDER.get(connector.connector_type)
            if reminder:
                print(f"  '{connector.name}'  [{connector.connector_type.value}]")
                print(f"    Set: {reminder}\n")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
