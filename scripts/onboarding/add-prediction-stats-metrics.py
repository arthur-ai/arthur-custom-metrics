"""
Add Prediction Statistics Metrics to Model

PURPOSE: Add prediction sum and distribution metrics
USAGE: python add-prediction-stats-metrics.py
WHEN: After initial model creation, standardizing metrics, enabling drift monitoring

ADDS:
  - Numeric Sum: Sum of predictions over time
  - Numeric Distribution: Min/max/mean/std of predictions

REQUIRES:
  - Model ID
  - Dataset with "prediction" and "timestamp" columns

CONFIGURE:
  - MODEL_ID
  - Update column names in gen_aggregation_specs() if needed

FEATURES: Auto-skips duplicates, preserves existing metrics, validates columns
"""

from arthur_client.api_bindings import (
    DatasetsV1Api,
    ModelsV1Api,
)
from arthur_client.api_bindings.models import *
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.auth import ArthurOAuthSessionAPIConfiguration, DeviceAuthorizer

ARTHUR_HOST = "https://platform.arthur.ai"

# SET THESE VARIABLES FOR THE MODEL
MODEL_ID = "YOUR_MODEL_ID_HERE"  # Replace with your model ID


def column_id_from_col_name(dataset: Dataset, col_name: str) -> str:
    for col in dataset.dataset_schema.columns:
        if col.source_name == col_name:
            return col.id
    else:
        raise ValueError(f"Could not find column {col_name}")


def gen_aggregation_specs(dataset: Dataset) -> list[AggregationSpec]:
    """
    Generate aggregation specs for prediction statistics.

    Customize this function based on your model's specific columns.
    This example assumes you have a 'prediction' column and 'timestamp' column.
    """
    # TODO: Update these column names to match your dataset schema
    prediction_col_id = column_id_from_col_name(dataset, "prediction")
    timestamp_col_id = column_id_from_col_name(dataset, "timestamp")

    aggregation_specs = [
        # Sum of predicted column
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000f",
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
                    arg_key="numeric_col",
                    arg_value=prediction_col_id,
                ),
            ],
        ),
        # distribution of predicted column
        AggregationSpec(
            aggregation_id="00000000-0000-0000-0000-00000000000d",
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
                    arg_key="numeric_col",
                    arg_value=prediction_col_id,
                ),
            ],
        ),
    ]
    return aggregation_specs


if __name__ == "__main__":
    sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
    api_client = ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
    )
    models_client = ModelsV1Api(api_client)
    datasets_client = DatasetsV1Api(api_client)

    model = models_client.get_model(model_id=MODEL_ID)
    if not model.datasets or len(model.datasets) == 0:
        raise ValueError(f"Model {MODEL_ID} has no associated datasets")
    dataset = datasets_client.get_dataset(dataset_id=model.datasets[0].dataset_id)
    print(f"Adding metrics to model {model.name}...")

    # This script adds the above metrics to the models configuration
    # it will skip adding if the model already has a metric with the same aggregation ID
    # so it doesn't add the same twice
    agg_ids = {a.aggregation_id for a in model.metric_config.aggregation_specs}
    new_aggs = gen_aggregation_specs(dataset)
    for agg in new_aggs:
        if agg.aggregation_id not in agg_ids:
            print(f"Including new aggregation for model {agg.aggregation_id}...")
            model.metric_config.aggregation_specs.append(agg)
        else:
            print(f"Skipping aggregation {agg.aggregation_id} - already exists")

    models_client.put_model_metric_config(
        model_id=MODEL_ID,
        put_model_metric_spec=PutModelMetricSpec(
            aggregation_specs=model.metric_config.aggregation_specs
        ),
    )

    print(f"Model metrics updated successfully")
