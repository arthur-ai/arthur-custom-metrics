"""
Add Column to Existing Dataset Schema

PURPOSE: Add new column when data source adds a field
USAGE: python add-column-to-schema.py
WHEN: Data source adds column, need to track new feature, schema initially wrong

REQUIRES:
  - Dataset ID
  - Column name (must match actual data)
  - Column type (INT, FLOAT, STRING, BOOL, TIMESTAMP)

CONFIGURE:
  - DATASET_ID
  - COLUMN_TO_ADD
  - dtype and nullable in code

TYPES: DType.INT, DType.FLOAT, DType.STRING, DType.BOOL, DType.TIMESTAMP

WARNING: Column must exist in actual data; doesn't backfill old data
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
COLUMN_TO_ADD = "new_column_name"  # Replace with your column name


def main() -> None:
    sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
    api_client = ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
    )
    datasets_client = DatasetsV1Api(api_client)

    # get and print the inference dataset schema as a reference
    dataset = datasets_client.get_dataset(dataset_id=DATASET_ID)

    print(dataset.dataset_schema)
    print(dataset.dataset_schema.model_dump_json())

    # check if column already exists
    for col in dataset.dataset_schema.columns:
        if col.source_name == COLUMN_TO_ADD:
            raise Exception(f"Column {COLUMN_TO_ADD} already exists")

    # Define the new column
    # Adjust the dtype and nullable based on your needs:
    # - DType.INT for integers
    # - DType.FLOAT for floating point numbers
    # - DType.STRING for text
    # - DType.BOOL for booleans
    # - DType.TIMESTAMP for timestamps
    new_col = DatasetColumn(
        id=str(uuid.uuid4()),
        source_name=COLUMN_TO_ADD,
        definition=Definition(
            DatasetScalarType(
                id=str(uuid.uuid4()),
                nullable=True,  # Set to False if the column should not allow nulls
                dtype=DType.INT,  # Change this to match your column type
            )
        ),
    )

    columns = dataset.dataset_schema.columns
    columns.append(new_col)

    # add column to dataset
    datasets_client.put_dataset_schema(
        dataset_id=dataset.id,
        put_dataset_schema=PutDatasetSchema(
            alias_mask=dataset.dataset_schema.alias_mask,
            columns=columns,
        ),
    )

    print(f"Successfully added column {COLUMN_TO_ADD} to dataset {DATASET_ID}")


if __name__ == "__main__":
    main()
