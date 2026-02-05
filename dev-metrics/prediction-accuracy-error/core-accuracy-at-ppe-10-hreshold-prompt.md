Prompt: Create a customm model evaluation metric documentation called `accuracy.md` for Arthur Platform according to the context below. Make sure both the SQL to generate the metric as well as the SQL to plot the data on dashboard chart exist.

Metric name: Core Accuracy at PPE 10% Threshold

Metric type: Model Performance - Prediction Accuracy & Error

Metric description: The accuracy of predictions within a 10% error threshold.

How to create an Arthur Platform custom metric: See `/resources/how-to-create-a-custom-metric.md` and `/resources/overview-metrics-and-querying.md`. Additional guideline can be found in `/resources/configuration-options.md`.

Example custom metrics documentation: See the files in the `/examples/metrics` folder.

Model dataset compatibililty: Examine the `/data` folder and list which dataset is compatible with this custom metric. Specify which columns in the dataset are relevant.
