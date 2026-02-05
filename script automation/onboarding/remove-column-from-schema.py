"""
Remove Column from Existing Dataset Schema

PURPOSE: Remove deprecated column from schema
USAGE: python remove-column-from-schema.py
WHEN: Data source removes field, column added by mistake, simplifying schema

REQUIRES:
  - Dataset ID
  - Column name to remove

CONFIGURE:
  - DATASET_ID
  - COLUMN_TO_REMOVE

WARNING:
  - Affects metrics that reference this column
  - Remove affected aggregations first
  - Cannot be easily undone

RECOMMENDED: Check which metrics use this column before removing
"""

import uuid

from arthur_client.api_bindings import (
    DatasetsV1Api,
)
from arthur_client.api_bindings.models import *
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.auth import ArthurOAuthSessionAPIConfiguration, DeviceAuthorizer

ARTHUR_HOST = "https://platform.arthur.ai"
DATASET_ID = "YOUR_DATASET_ID_HERE"  # Replace with your dataset ID
COLUMN_TO_REMOVE = "column_to_remove"  # Replace with the column name to remove


def main() -> None:
    sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
    api_client = ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
    )
    datasets_client = DatasetsV1Api(api_client)

    # get and print the inference dataset schema as a reference
    dataset = datasets_client.get_dataset(dataset_id=DATASET_ID)

    print("Current schema:")
    print(dataset.dataset_schema)
    print(dataset.dataset_schema.model_dump_json())

    # filter out the column to remove
    columns = []
    found = False
    for col in dataset.dataset_schema.columns:
        if col.source_name != COLUMN_TO_REMOVE:
            columns.append(col)
        else:
            found = True
            print(f"Found column {COLUMN_TO_REMOVE}, removing it...")

    if not found:
        raise Exception(f"Column {COLUMN_TO_REMOVE} not found in schema")

    # update dataset schema
    datasets_client.put_dataset_schema(
        dataset_id=dataset.id,
        put_dataset_schema=PutDatasetSchema(
            alias_mask=dataset.dataset_schema.alias_mask,
            columns=columns,
        ),
    )

    print(f"Successfully removed column {COLUMN_TO_REMOVE} from dataset {DATASET_ID}")


if __name__ == "__main__":
    main()
