"""
Housing Price Regression Model Onboarding Script

PURPOSE: Complete end-to-end onboarding of a regression model from S3 to Arthur platform
USAGE: python housing-price-onboarding.py
WHEN: First-time setup for housing price prediction model

CREATES:
  1. S3 connector (reuses if exists)
  2. Available dataset with schema inspection
  3. Dataset with inferred schema
  4. Regression model with basic metrics
  5. Hourly refresh schedule

REQUIRES:
  - S3 bucket with inference data (JSON/Parquet/CSV)
  - AWS credentials or IAM role
  - Arthur project ID
  - Data with timestamp column

CONFIGURE BEFORE RUNNING:
  - ARTHUR_HOST
  - AWS credentials
  - S3_BUCKET, S3_FILE_PREFIX, S3_FILE_TYPE
  - ARTHUR_PROJECT_ID
  - TIMESTAMP_COLUMN_NAME
  - PREDICTION_COLUMN_NAME (if applicable)
  - GROUND_TRUTH_COLUMN_NAME (if applicable)

NEXT STEP: Run add-regression-model-aggregations.py to add custom metrics
"""

from time import sleep

from arthur_client.api_bindings import (
    ConnectorsV1Api,
    DatasetsV1Api,
    ModelsV1Api,
    DataPlanesV1Api,
    ProjectsV1Api,
    JobsV1Api,
)
from arthur_client.api_bindings.models import *
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.auth import ArthurOAuthSessionAPIConfiguration, DeviceAuthorizer

ARTHUR_HOST = "https://platform.arthur.ai"

# SET THESE VARIABLES FOR THE MODEL
TIMESTAMP_COLUMN_NAME = "timestamp"
ROW_ID_COLUMN_NAME = "house_id"
PREDICTION_COLUMN_NAME = "predicted_house_value"
GROUND_TRUTH_COLUMN_NAME = "actual_house_value"

# CONFIGURATION - Update these for your environment

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = "INSERT_AWS_ACCESS_KEY_ID_HERE"
AWS_SECRET_ACCESS_KEY = "INSERT_AWS_SECRET_ACCESS_KEY_HERE"
AWS_REGION = "INSERT_AWS_REGION_HERE"
S3_BUCKET = "INSERT_S3_BUCKET_NAME_HERE"
S3_FILE_PREFIX = "regression-housing-price-prediction/%Y-%m-%d"
S3_FILE_SUFFIX = ".*.csv"
S3_FILE_TYPE = "csv"  # Options: json, parquet, csv
S3_FILE_PREFIX_TIMEZONE = "UTC"

# CSV-specific configuration
CSV_DELIMITER = ","  # Delimiter character (comma, tab, pipe, etc.)
CSV_HAS_HEADER = True  # Whether the CSV file has a header row
CSV_QUOTE_CHAR = '"'  # Quote character for string fields

# Optional: For role-based authentication (recommended)
AWS_ROLE_ARN = "INSERT_AWS_ROLE_ARN_HERE"
AWS_EXTERNAL_ID = "INSERT_AWS_EXTERNAL_ID_HERE"

# Arthur Configuration
ARTHUR_PROJECT_ID = "INSERT_ARTHUR_PROJECT_ID_HERE"

# Optional: Specify data plane ID explicitly if you have multiple data planes
DATA_PLANE_ID = "INSERT_DATA_PLANE_ID_HERE"

# Model Configuration
CONNECTOR_NAME = f"{S3_BUCKET}"
MODEL_NAME = "INSERT_MODEL_NAME_HERE"
MODEL_DESCRIPTION = "INSERT_MODEL_DESCRIPTION_HERE"

# CONFIGURE THE DATASET LOCATOR

dataset_locator_fields = [
    DatasetLocatorField(key="file_prefix", value=S3_FILE_PREFIX),
    DatasetLocatorField(key="file_suffix", value=S3_FILE_SUFFIX),
    DatasetLocatorField(key="data_file_type", value=S3_FILE_TYPE),
    DatasetLocatorField(key="timestamp_time_zone", value=S3_FILE_PREFIX_TIMEZONE),
]

# Add CSV-specific fields if file type is CSV
if S3_FILE_TYPE.lower() == "csv":
    dataset_locator_fields.extend([
        DatasetLocatorField(key="csv_delimiter", value=CSV_DELIMITER),
        DatasetLocatorField(key="csv_has_header", value=str(CSV_HAS_HEADER).lower()),
        DatasetLocatorField(key="csv_quote_char", value=CSV_QUOTE_CHAR),
    ])

dataset_locator = DatasetLocator(fields=dataset_locator_fields)


def column_id_from_col_name(dataset: Dataset, col_name: str) -> str:
    """Helper to get column ID from column name."""
    for col in dataset.dataset_schema.columns:
        if col.source_name == col_name:
            return col.id
    raise ValueError(f"Column '{col_name}' not found in dataset schema")


def gen_aggregation_specs(dataset: Dataset) -> list[AggregationSpec]:
    """
    Generate aggregation specs for the regression model metrics.
    Includes basic metrics that work for any regression model:
    - Inference count
    - Nullable counts for all columns
    - Numeric distributions for prediction column (if exists)

    For more comprehensive metrics, run add-regression-model-aggregations.py after onboarding.
    """
    timestamp_col_id = column_id_from_col_name(dataset, TIMESTAMP_COLUMN_NAME)

    aggregation_specs = [
        # Inference count
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000a",
            aggregation_init_args=[],
            aggregation_args=[
                MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
            ],
        ),
    ]

    # Add nullable count aggregations for all columns
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

    # Add prediction distribution if prediction column exists
    try:
        pred_col_id = column_id_from_col_name(dataset, PREDICTION_COLUMN_NAME)
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-00000000000d",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="numeric_col", arg_value=pred_col_id),
                ],
            )
        )
        print(f"Added distribution aggregation for prediction column: {PREDICTION_COLUMN_NAME}")
    except ValueError:
        print(f"Warning: Prediction column '{PREDICTION_COLUMN_NAME}' not found, skipping prediction distribution")

    # Add ground truth distribution if ground truth column exists
    try:
        gt_col_id = column_id_from_col_name(dataset, GROUND_TRUTH_COLUMN_NAME)
        aggregation_specs.append(
            AggregationSpec(
                aggregation_id="00000000-0000-0000-0000-00000000000d",
                aggregation_init_args=[],
                aggregation_args=[
                    MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
                    MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
                    MetricsArgSpec(arg_key="numeric_col", arg_value=gt_col_id),
                ],
            )
        )
        print(f"Added distribution aggregation for ground truth column: {GROUND_TRUTH_COLUMN_NAME}")
    except ValueError:
        print(f"Warning: Ground truth column '{GROUND_TRUTH_COLUMN_NAME}' not found, skipping ground truth distribution")

    return aggregation_specs


if __name__ == "__main__":
    print(f"🔗 Connecting to Arthur at {ARTHUR_HOST}...")
    sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
    api_client = ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
    )
    projects_client = ProjectsV1Api(api_client)
    connectors_client = ConnectorsV1Api(api_client)
    datasets_client = DatasetsV1Api(api_client)
    models_client = ModelsV1Api(api_client)
    data_planes_client = DataPlanesV1Api(api_client)
    jobs_client = JobsV1Api(api_client)

    # Fetch project
    print(f"\n📁 Fetching project {ARTHUR_PROJECT_ID}...")
    project = projects_client.get_project(project_id=ARTHUR_PROJECT_ID)
    print(f"   Project: {project.name}")

    # Get data plane ID
    if DATA_PLANE_ID:
        data_plane = data_planes_client.get_data_plane(data_plane_id=DATA_PLANE_ID)
        print(f"\n🌐 Using explicitly configured data plane: {data_plane.name} (ID: {data_plane.id})")
    else:
        data_planes_response = data_planes_client.get_data_planes(
            workspace_id=project.workspace_id
        )

        if not data_planes_response.records:
            raise ValueError(
                f"No data planes found for workspace {project.workspace_id}. "
                f"Please create a data plane in the Arthur UI first."
            )

        data_plane = data_planes_response.records[0]
        print(f"\n🌐 Using first data plane from workspace: {data_plane.name} (ID: {data_plane.id})")
        print(f"   If this fails, check Arthur UI for correct data plane and set DATA_PLANE_ID")

    # Check for existing connector or create new one
    print(f"\n🔌 Checking for S3 connector with name {CONNECTOR_NAME}...")
    connectors = connectors_client.get_connectors(
        project_id=project.id,
        connector_type=ConnectorType.S3,
        data_plane_id=data_plane.id,
        name=CONNECTOR_NAME,
        page_size=1,
    )
    if len(connectors.records) > 0:
        connector = connectors.records[0]
        print(f"   ✓ Found existing S3 connector: {connector.name} (ID: {connector.id})")
    else:
        print(f"   Creating new S3 connector: {CONNECTOR_NAME}...")

        # Build connector fields
        connector_fields = [
            ConnectorSpecField(key="bucket", value=S3_BUCKET),
        ]

        if AWS_REGION:
            connector_fields.append(
                ConnectorSpecField(key="region", value=AWS_REGION)
            )

        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            connector_fields.extend([
                ConnectorSpecField(key="access_key_id", value=AWS_ACCESS_KEY_ID),
                ConnectorSpecField(key="secret_access_key", value=AWS_SECRET_ACCESS_KEY),
            ])

        if AWS_ROLE_ARN:
            connector_fields.append(
                ConnectorSpecField(key="role_arn", value=AWS_ROLE_ARN)
            )
        if AWS_EXTERNAL_ID:
            connector_fields.append(
                ConnectorSpecField(key="external_id", value=AWS_EXTERNAL_ID)
            )

        try:
            connector = connectors_client.post_connector(
                project_id=ARTHUR_PROJECT_ID,
                post_connector_spec=PostConnectorSpec(
                    name=CONNECTOR_NAME,
                    connector_type=ConnectorType.S3,
                    temporary=False,
                    data_plane_id=data_plane.id,
                    fields=connector_fields,
                ),
            )
            print(f"   ✓ Created S3 Connector: {connector.id}")
        except Exception as e:
            if "not associated with project" in str(e):
                print(f"\n❌ ERROR: Data plane {data_plane.id} is not associated with project {ARTHUR_PROJECT_ID}")
                print("\nTo fix this:")
                print("1. Log into Arthur UI at https://platform.arthur.ai")
                print(f"2. Navigate to your project (ID: {ARTHUR_PROJECT_ID})")
                print("3. Find the correct data plane ID for this project")
                print("4. Set DATA_PLANE_ID at the top of this script to that ID")
                raise
            else:
                raise

    # Create available dataset
    print(f"\n📊 Creating Available Dataset with prefix {S3_FILE_PREFIX}...")
    avail_dataset = datasets_client.post_available_dataset(
        connector_id=connector.id,
        put_available_dataset=PutAvailableDataset(
            name=MODEL_NAME,
            dataset_locator=dataset_locator,
        ),
    )
    print(f"   ✓ Created Available Dataset: {avail_dataset.id}")

    # Run schema inspection
    print(f"\n🔍 Running schema inspection job...")
    jobs_resp = jobs_client.post_submit_jobs_batch(
        project_id=ARTHUR_PROJECT_ID,
        post_job_batch=PostJobBatch(
            jobs=[
                PostJob(
                    kind=PostJobKind.SCHEMA_INSPECTION,
                    job_spec=PostJobSpec(
                        SchemaInspectionJobSpec(
                            connector_id=connector.id,
                            available_dataset_id=avail_dataset.id,
                        )
                    ),
                )
            ]
        ),
    )
    job = jobs_resp.jobs[0]

    # Poll for job completion
    while job.state == JobState.QUEUED or job.state == JobState.RUNNING:
        print(f"   Job state: {job.state}. Waiting...")
        sleep(1)
        job = jobs_client.get_job(job_id=job.id)

    print(f"   ✓ Schema inspection completed with state: {job.state}")
    if job.state != JobState.COMPLETED:
        raise Exception(
            f"Error completing schema inspection job. "
            f"Check the activity log in the project for more information."
        )

    # Fetch updated available dataset with inferred schema
    print(f"\n📋 Fetching inferred schema...")
    avail_dataset = datasets_client.get_available_dataset(
        available_dataset_id=avail_dataset.id
    )

    if avail_dataset.dataset_schema is None:
        raise Exception(
            "Error during schema inspection, schema came back None. "
            "See the activity log in the project for more information."
        )

    print(f"   ✓ Retrieved schema with {len(avail_dataset.dataset_schema.columns)} columns")
    print(f"\n   Available columns:")
    for col in avail_dataset.dataset_schema.columns:
        print(f"   - {col.source_name}")

    # Update schema - set timestamp column
    timestamp_found = False
    for column in avail_dataset.dataset_schema.columns:
        if column.source_name == TIMESTAMP_COLUMN_NAME:
            column.definition.actual_instance.tag_hints.append(
                ScopeSchemaTag.PRIMARY_TIMESTAMP
            )
            column.definition.actual_instance.dtype = DType.TIMESTAMP
            timestamp_found = True
            print(f"\n✓ Set {TIMESTAMP_COLUMN_NAME} as PRIMARY_TIMESTAMP")
            break

    if not timestamp_found:
        raise Exception(
            f"Timestamp column '{TIMESTAMP_COLUMN_NAME}' not found in schema. "
            f"Available columns: {[col.source_name for col in avail_dataset.dataset_schema.columns]}"
        )

    # Optionally tag prediction and ground truth columns
    for column in avail_dataset.dataset_schema.columns:
        if column.source_name == PREDICTION_COLUMN_NAME:
            if ScopeSchemaTag.PREDICTION not in column.definition.actual_instance.tag_hints:
                column.definition.actual_instance.tag_hints.append(
                    ScopeSchemaTag.PREDICTION
                )
            print(f"✓ Tagged {PREDICTION_COLUMN_NAME} as PREDICTION")
        elif column.source_name == GROUND_TRUTH_COLUMN_NAME:
            if ScopeSchemaTag.GROUND_TRUTH not in column.definition.actual_instance.tag_hints:
                column.definition.actual_instance.tag_hints.append(
                    ScopeSchemaTag.GROUND_TRUTH
                )
            print(f"✓ Tagged {GROUND_TRUTH_COLUMN_NAME} as GROUND_TRUTH")

    # Set explicit column types based on dataset structure
    print(f"\n🔧 Setting column types...")

    column_type_mapping = {
        # Date/Time columns
        "partition_date": DType.DATE,
        "timestamp": DType.TIMESTAMP,  # Already set above

        # Identifier
        "house_id": DType.INT,

        # Target and prediction (float values)
        "actual_house_value": DType.FLOAT,
        "predicted_house_value": DType.FLOAT,

        # Geographic coordinates (float)
        "longitude": DType.FLOAT,
        "latitude": DType.FLOAT,

        # Numeric features - integers
        "housing_median_age": DType.INT,
        "total_rooms": DType.INT,
        "total_bedrooms": DType.INT,
        "population": DType.INT,
        "households": DType.INT,

        # Numeric features - floats
        "median_income": DType.FLOAT,

        # Categorical
        "ocean_proximity": DType.STR,
    }

    # Apply column types
    for column in avail_dataset.dataset_schema.columns:
        if column.source_name in column_type_mapping:
            expected_dtype = column_type_mapping[column.source_name]
            # Only update if different from expected
            if column.definition.actual_instance.dtype != expected_dtype:
                column.definition.actual_instance.dtype = expected_dtype
                print(f"   ✓ Set {column.source_name} -> {expected_dtype.value}")
            else:
                print(f"   ✓ {column.source_name} already {expected_dtype.value}")

    # Create dataset
    print(f"\n💾 Creating dataset {MODEL_NAME}...")
    dataset = datasets_client.post_connector_dataset(
        connector_id=connector.id,
        post_dataset=PostDataset(
            name=MODEL_NAME,
            dataset_locator=dataset_locator,
            dataset_schema=PutDatasetSchema(
                alias_mask=avail_dataset.dataset_schema.alias_mask,
                columns=avail_dataset.dataset_schema.columns,
            ),
            model_problem_type=ModelProblemType.REGRESSION,
        ),
    )
    print(f"   ✓ Created dataset: {dataset.id}")

    # Generate aggregation specs
    print(f"\n⚙️  Generating aggregation specs...")
    aggregation_specs = gen_aggregation_specs(dataset)
    print(f"   ✓ Generated {len(aggregation_specs)} aggregation specs")

    # Create model
    print(f"\n🤖 Creating model {MODEL_NAME}...")
    model = models_client.post_model(
        project_id=ARTHUR_PROJECT_ID,
        post_model=PostModel(
            name=MODEL_NAME,
            description=MODEL_DESCRIPTION,
            dataset_ids=[dataset.id],
            metric_config=PutModelMetricSpec(
                aggregation_specs=aggregation_specs
            ),
        ),
    )
    print(f"   ✓ Created model: {model.id}")

    # Set refresh schedule
    print(f"\n⏰ Setting hourly refresh schedule...")
    models_client.put_model_metrics_schedule(
        model_id=model.id,
        put_model_metrics_schedule=PutModelMetricsSchedule(
            cron="0 */1 * * *",  # run every hour
            lookback_period_seconds=60 * 60 * 2,  # pull last 2 hours of data
            name="hourly",
        ),
    )
    print(f"   ✓ Refresh schedule set")

    print(f"\n🎉 Onboarding complete!")
    print(f"\n📋 Summary:")
    print(f"   Model ID: {model.id}")
    print(f"   Model Name: {model.name}")
    print(f"   Dataset ID: {dataset.id}")
    print(f"   Connector ID: {connector.id}")
    print(f"   Problem Type: REGRESSION")
    print(f"\n📈 Next steps:")
    print(f"  1. (Optional) Create add-regression-model-aggregations.py for additional metrics")
    print(f"  2. Wait for next scheduled metric calculation (hourly)")
    print(f"  3. View metrics in Arthur UI at {ARTHUR_HOST}")
    print(f"  4. Monitor model performance and data quality")
