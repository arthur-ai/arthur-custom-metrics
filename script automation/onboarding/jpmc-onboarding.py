"""
JPMC Model Onboarding Script

PURPOSE: Complete end-to-end onboarding of a new model from S3 to Arthur platform
USAGE: python jpmc-onboarding.py
WHEN: First-time setup, new S3 data source, initial project configuration

CREATES:
  1. S3 connector (reuses if exists)
  2. Available dataset with schema inspection
  3. Dataset with inferred schema
  4. Model with basic metrics
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

NEXT STEP: Run add-fraud-model-aggregations.py to add custom metrics
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

POS_PREDICTION_THRESHOLD = 0.95
POS_LABEL = "POSITIVE"
NEG_LABEL = "NEGATIVE"
TIMESTAMP_COLUMN_NAME = "timestamp"

# CONFIGURATION - Update these for your environment

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = "INSERT_AWS_ACCESS_KEY_ID_HERE"
AWS_SECRET_ACCESS_KEY = "INSERT_AWS_SECRET_ACCESS_KEY_HERE"
AWS_REGION = "INSERT_AWS_REGION_HERE"  # e.g., "us-east-1"
S3_BUCKET = "INSERT_S3_BUCKET_NAME_HERE"
S3_FILE_PREFIX = "INSERT_S3_FILE_PREFIX_HERE"  # e.g., "data/inferences/year=%Y/month=%m/day=%d"
S3_FILE_SUFFIX = ".*.json"
S3_FILE_TYPE = "json"  # Options: json, parquet, csv
S3_FILE_PREFIX_TIMEZONE = "UTC"

# Optional: For role-based authentication (recommended)
AWS_ROLE_ARN = "INSERT_AWS_ROLE_ARN_HERE"  # e.g., "arn:aws:iam::123456789012:role/RoleName"
AWS_EXTERNAL_ID = "INSERT_AWS_EXTERNAL_ID_HERE"
# AWS_ROLE_DURATION_SECONDS = 3600

# Optional: For custom S3 endpoint (e.g., on-premises S3-compatible storage)
# S3_ENDPOINT = "https://s3.custom-endpoint.com"

# Arthur Configuration
ARTHUR_PROJECT_ID = "INSERT_ARTHUR_PROJECT_ID_HERE"  # Get from Arthur UI

# Optional: Specify data plane ID explicitly if you have multiple data planes
# If not set, the script will use the first data plane from the workspace
# Get this from Arthur UI if you encounter "data plane not associated with project" errors
DATA_PLANE_ID = "INSERT_DATA_PLANE_ID_HERE"  # Get from Arthur UI (or leave as-is to auto-detect)

# Model Configuration
JPMC_CONNECTOR_NAME = f"{S3_BUCKET}"
JPMC_MODEL_NAME = "INSERT_MODEL_NAME_HERE"
JPMC_MODEL_DESCRIPTION = "INSERT_MODEL_DESCRIPTION_HERE"

# CONFIGURE THE DATASET LOCATOR AND METRICS CONFIGS FOR MODEL

jpmc_dataset_locator = DatasetLocator(
    fields=[
        DatasetLocatorField(
            key="file_prefix",
            value=S3_FILE_PREFIX,
        ),
        DatasetLocatorField(
            key="file_suffix",
            value=S3_FILE_SUFFIX,
        ),
        DatasetLocatorField(
            key="data_file_type",
            value=S3_FILE_TYPE,
        ),
        DatasetLocatorField(key="timestamp_time_zone", value=S3_FILE_PREFIX_TIMEZONE),
    ]
)


def column_id_from_col_name(dataset: Dataset, col_name: str) -> str:
    for col in dataset.dataset_schema.columns:
        if col.source_name == col_name:
            return col.id
    else:
        raise ValueError(f"Could not find column {col_name}")


def gen_aggregation_specs(dataset: Dataset) -> list[AggregationSpec]:
    """
    Generate aggregation specs for the model metrics.
    Customize this function based on your model's specific columns and requirements.
    """
    timestamp_col_id = column_id_from_col_name(dataset, "timestamp")

    aggregation_specs = [
        # aggregation for inference count
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000a",
            aggregation_init_args=[],
            aggregation_args=[
                MetricsArgSpec(
                    arg_key="dataset",
                    arg_value=dataset.id,
                ),
                MetricsArgSpec(
                    arg_key="timestamp_col",
                    arg_value=timestamp_col_id,
                ),
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
                    MetricsArgSpec(
                        arg_key="dataset",
                        arg_value=dataset.id,
                    ),
                    MetricsArgSpec(
                        arg_key="timestamp_col",
                        arg_value=timestamp_col_id,
                    ),
                    MetricsArgSpec(
                        arg_key="nullable_col",
                        arg_value=col.id,
                    ),
                ],
            )
        )

    # TODO: Add model-specific aggregations here
    # For example, if you have prediction columns:
    # pred_col_id = column_id_from_col_name(dataset, "prediction")
    # aggregation_specs.append(
    #     AggregationSpec(
    #         aggregation_id="00000000-0000-0000-0000-000000000020",
    #         aggregation_init_args=[],
    #         aggregation_args=[
    #             MetricsArgSpec(arg_key="dataset", arg_value=dataset.id),
    #             MetricsArgSpec(arg_key="timestamp_col", arg_value=timestamp_col_id),
    #             MetricsArgSpec(arg_key="prediction_col", arg_value=pred_col_id),
    #             MetricsArgSpec(arg_key="threshold", arg_value=JPMC_POS_PREDICTION_THRESHOLD),
    #             MetricsArgSpec(arg_key="true_label", arg_value=JPMC_POS_LABEL),
    #             MetricsArgSpec(arg_key="false_label", arg_value=JPMC_NEG_LABEL),
    #         ],
    #     ),
    # )

    return aggregation_specs


if __name__ == "__main__":
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

    # fetch project
    project = projects_client.get_project(project_id=ARTHUR_PROJECT_ID)

    # Get data plane ID
    # If DATA_PLANE_ID is explicitly set, use that. Otherwise, use first from workspace.
    if DATA_PLANE_ID:
        data_plane = data_planes_client.get_data_plane(data_plane_id=DATA_PLANE_ID)
        print(f"Using explicitly configured data plane: {data_plane.name} (ID: {data_plane.id})")
    else:
        # fetch data planes for project's workspace
        # NOTE: The Arthur API does not expose the project-to-data-plane relationship in the client,
        # so we cannot filter data planes by project. If you have multiple data planes and encounter
        # an error about the data plane not being associated with your project:
        # 1. Check the Arthur UI to find the correct data plane ID for your project
        # 2. Set DATA_PLANE_ID at the top of this file
        data_planes_response = data_planes_client.get_data_planes(
            workspace_id=project.workspace_id
        )

        if not data_planes_response.records:
            raise ValueError(
                f"No data planes found for workspace {project.workspace_id}. "
                f"Please create a data plane in the Arthur UI first."
            )

        # Use the first data plane from the workspace
        data_plane = data_planes_response.records[0]
        print(f"Using first data plane from workspace: {data_plane.name} (ID: {data_plane.id})")
        print(f"If this fails, check Arthur UI for correct data plane and set DATA_PLANE_ID")

    # NOTE - this script creates a connector (below) because one did not yet exist for
    # communicating with the JPMC S3 bucket. In general though,
    # connectors can, and should, be reused across models in the same project.
    # i.e. you only need to set up one connector per bucket in the Arthur project.
    # If you have multiple models using data from the same bucket,
    # they should all use the same connector.
    # It may make sense to create the connectors once manually in the UI, then reference them by ID
    # in the script. This process would be similar to what we've done here with the Project ID.
    # The projects were created manually in the UI, then their IDs were hardcoded here to be
    # used across multiple models.

    print(f"Check for S3 connector with name {JPMC_CONNECTOR_NAME}")
    connectors = connectors_client.get_connectors(
        project_id=project.id,
        connector_type=ConnectorType.S3,
        data_plane_id=data_plane.id,
        name=JPMC_CONNECTOR_NAME,
        page_size=1,
    )
    if len(connectors.records) > 0:
        connector = connectors.records[0]
        print(
            f"S3 connector found with name {JPMC_CONNECTOR_NAME}, ID {connector.id}"
        )
    else:
        print(
            f"Connector with name {JPMC_CONNECTOR_NAME} not found, creating a new one"
        )
        print(f"Creating S3 connector...")

        # Build connector fields based on authentication method
        connector_fields = [
            ConnectorSpecField(key="bucket", value=S3_BUCKET),
        ]

        # Add region if specified
        if AWS_REGION:
            connector_fields.append(
                ConnectorSpecField(key="region", value=AWS_REGION)
            )

        # Add access key credentials if provided
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            connector_fields.extend([
                ConnectorSpecField(key="access_key_id", value=AWS_ACCESS_KEY_ID),
                ConnectorSpecField(key="secret_access_key", value=AWS_SECRET_ACCESS_KEY),
            ])

        # Add role-based authentication if configured
        # Uncomment and configure these if using IAM role assumption
        if AWS_ROLE_ARN:
            connector_fields.append(
                ConnectorSpecField(key="role_arn", value=AWS_ROLE_ARN)
            )
        if AWS_EXTERNAL_ID:
            connector_fields.append(
                ConnectorSpecField(key="external_id", value=AWS_EXTERNAL_ID)
            )
        # if AWS_ROLE_DURATION_SECONDS:
        #     connector_fields.append(
        #         ConnectorSpecField(key="duration_seconds", value=str(AWS_ROLE_DURATION_SECONDS))
        #     )

        # Add custom endpoint if specified
        # Uncomment if using custom S3 endpoint
        # if S3_ENDPOINT:
        #     connector_fields.append(
        #         ConnectorSpecField(key="endpoint", value=S3_ENDPOINT)
        #     )

        try:
            connector = connectors_client.post_connector(
                project_id=ARTHUR_PROJECT_ID,
                post_connector_spec=PostConnectorSpec(
                    name=JPMC_CONNECTOR_NAME,
                    connector_type=ConnectorType.S3,
                    temporary=False,
                    data_plane_id=data_plane.id,
                    fields=connector_fields,
                ),
            )
            print(f"Created S3 Connector: {connector.id}")
        except Exception as e:
            if "not associated with project" in str(e):
                print(f"\nERROR: Data plane {data_plane.id} is not associated with project {ARTHUR_PROJECT_ID}")
                print("\nTo fix this:")
                print("1. Log into Arthur UI at https://platform.arthur.ai")
                print(f"2. Navigate to your project (ID: {ARTHUR_PROJECT_ID})")
                print("3. Find the correct data plane ID for this project")
                print("4. Set DATA_PLANE_ID at the top of this script to that ID")
                print("\nAlternatively, ask your Arthur admin to associate the data plane with your project.")
                raise
            else:
                raise

    print(f"Creating Available Dataset with prefix {S3_FILE_PREFIX}...")
    avail_dataset = datasets_client.post_available_dataset(
        connector_id=connector.id,
        put_available_dataset=PutAvailableDataset(
            name=JPMC_MODEL_NAME,
            dataset_locator=jpmc_dataset_locator,
        ),
    )
    print(f"Created Available Dataset: {avail_dataset.id}")

    print(f"Running schema inspection job...")
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
    # poll for job to finish
    while job.state == JobState.QUEUED or job.state == JobState.RUNNING:
        print(f"Job is in state {job.state}. Waiting...")
        sleep(1)
        job = jobs_client.get_job(job_id=job.id)
    print(f"Schema inspection job completed with state: {job.state} - {job.id}")
    if job.state != JobState.COMPLETED:
        raise Exception(
            f"Error completing schema inspection job, "
            f"see the activity log in the project for more information."
        )

    print(f"Fetching updated available dataset...")
    avail_dataset = datasets_client.get_available_dataset(
        available_dataset_id=avail_dataset.id
    )
    print(f"Retrieved updated available dataset: {avail_dataset.name}")
    print(f"Inferred schema: {avail_dataset.dataset_schema}")
    if avail_dataset.dataset_schema is None:
        raise Exception(
            "Error during schema inspection, schema came back None. "
            "See the activity log in the project for more information."
        )

    # update schema with known differences (set timestamp column)
    for column in avail_dataset.dataset_schema.columns:
        if column.source_name == TIMESTAMP_COLUMN_NAME:
            column.definition.actual_instance.tag_hints.append(
                ScopeSchemaTag.PRIMARY_TIMESTAMP
            )
            column.definition.actual_instance.dtype = DType.TIMESTAMP
            break
    else:
        raise Exception(
            f"Timestamp column: {TIMESTAMP_COLUMN_NAME} not found in schema"
        )

    print(f"Creating dataset with prefix {S3_FILE_PREFIX}...")
    dataset = datasets_client.post_connector_dataset(
        connector_id=connector.id,
        post_dataset=PostDataset(
            name=JPMC_MODEL_NAME,
            dataset_locator=jpmc_dataset_locator,
            dataset_schema=PutDatasetSchema(
                alias_mask=avail_dataset.dataset_schema.alias_mask,
                columns=avail_dataset.dataset_schema.columns,
            ),
            model_problem_type=ModelProblemType.BINARY_CLASSIFICATION,
        ),
    )
    print(f"Created dataset: {dataset.id}")

    print(f"Creating model {JPMC_MODEL_NAME}...")
    model = models_client.post_model(
        project_id=ARTHUR_PROJECT_ID,
        post_model=PostModel(
            name=JPMC_MODEL_NAME,
            description=JPMC_MODEL_DESCRIPTION,
            dataset_ids=[dataset.id],
            metric_config=PutModelMetricSpec(
                aggregation_specs=gen_aggregation_specs(dataset)
            ),
        ),
    )
    print(f"Created model {model.id}")

    print(f"Setting model refresh schedule...")
    models_client.put_model_metrics_schedule(
        model_id=model.id,
        put_model_metrics_schedule=PutModelMetricsSchedule(
            cron="0 */1 * * *",  # run every hour
            lookback_period_seconds=60 * 60 * 2,  # pull last 2 hours of data
            name="hourly",
        ),
    )
    print(f"Model refresh schedule set")
