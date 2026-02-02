## Overview

This custom metric computes a **daily Gini value at a fixed decision threshold** on your prediction column.  
It treats rows as being **above** or **below** the threshold and measures how _mixed_ those two groups are.

* Lower values (closer to 0) → more **pure** (most predictions on one side of the threshold).
* Higher values (toward the maximum) → more **mixed**, i.e., less separation at that threshold.

This is useful when you want a **simple, threshold-specific impurity measure** that you can track over time alongside other classification metrics.

***

## Step 1: Write the SQL

This SQL computes Gini impurity at a fixed threshold. It measures how "mixed" the predictions are around that threshold - lower values indicate purer separation.

```sql
WITH counts AS (
  SELECT
    time_bucket(INTERVAL '1 day', {{timestampColumnName}}) AS ts,
    SUM(
      CASE
        WHEN {{predictionColumnName}} >= {{thresholdValue}} THEN 1
        ELSE 0
      END
    )::float AS pos_count,
    COUNT(*)::float AS total_count
  FROM
    {{dataset}}
  GROUP BY
    1
)
SELECT
  ts,
  CASE
    WHEN total_count > 0 THEN
      1
      - (
          POWER(pos_count / total_count, 2)
          + POWER((total_count - pos_count) / total_count, 2)
        )
    ELSE 0
  END AS gini_coefficient
FROM
  counts
ORDER BY
  ts;
```

**What this query returns**

* `ts` — timestamp bucket (1 day)
* `gini_coefficient` — Gini impurity at the specified threshold (0 = pure, higher = more mixed)

***

## Step 2: Fill Basic Information

When creating the custom metric in the Arthur UI:

1. **Name**:  
   `Gini Coefficient`

2. **Description** (optional but recommended):  
   `Daily Gini-style impurity at a fixed prediction threshold, based on how many predictions fall above vs below the threshold.`

***

## Step 3: Configure the Aggregate Arguments

You will set up four aggregate arguments to parameterize the SQL.

### Argument 1 — Timestamp Column

<Image border={false} src="https://files.readme.io/25f425013ce876958693a0f59d0705742a06c1c88781398ff48dffbaa4b10957-Screenshot_2025-12-05_at_11.32.36.png" />

1. **Parameter Key:** `timestampColumnName`
2. **Friendly Name:** `TimestampColumnName`
3. **Description:** `Column parameter: timestampColumnName`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `Dataset (dataset)`
6. **Allow Any Column Type:** `No`
7. **Tag hints (optional):** `primary_timestamp`
8. **Allowed Column Types (optional):** `timestamp`

This tells Arthur which timestamp column to use for the `time_bucket` function.

***

### Argument 2 — Prediction Column

<Image border={false} src="https://files.readme.io/c83a91a5d80fa8d319af8efb1c7c2c4dc6759948af4e2c739273e6f4f8e06bd7-Screenshot_2025-12-05_at_11.32.46.png" />

1. **Parameter Key:** `predictionColumnName`
2. **Friendly Name:** `PredictionColumnName`
3. **Description:** `Column parameter: predictionColumnName`
4. **Parameter Type:** `Column`
5. **Source Dataset Parameter Key:** `Dataset (dataset)`
6. **Allow Any Column Type:** `No`
7. **Tag hints (optional):** `prediction`
8. **Allowed Column Types (optional):** `float`

This should point to your model’s **prediction or score column** (typically a probability for the positive class).

***

### Argument 3 — Threshold Value

<Image border={false} src="https://files.readme.io/5d0042f06db1670cf340abff1732c705c9cc71d55fc9ddbb82089ac0eb70583e-Screenshot_2025-12-05_at_11.32.54.png" />

1. **Parameter Key:** `thresholdValue`
2. **Friendly Name:** `ThresholdValue`
3. **Description:** `Literal threshold used to split predictions into high vs low groups.`
4. **Parameter Type:** `Literal`
5. **Data Type:** `Float`

Use this to match your **operating threshold** (e.g., `0.5`) or any other cutpoint you care about. You can later clone this metric with different thresholds if needed.

***

### Argument 4 — Dataset

<Image border={false} src="https://files.readme.io/04270733ad8aae000b8ae12fec70fedeec84812850926d01414e398d7a5745fb-Screenshot_2025-12-05_at_12.49.54.png" />

1. **Parameter Key:** `dataset`
2. **Friendly Name:** `Dataset`
3. **Description:** `Dataset for the aggregation.`
4. **Parameter Type:** `Dataset`

This links the metric definition to whichever **Arthur dataset** (inference or batch) you want to compute Gini on.

***

## Step 4: Configure the Reported Metrics

### Reported Metric 1 — Gini Coefficient

<Image border={false} src="https://files.readme.io/fae577726d40dee6dc36240a9bb7aac3933bb5dd1b2861b5416727df15306f37-Screenshot_2025-12-05_at_11.32.25.png" />

1. **Metric Name:** `Gini Coefficient`
2. **Description:** `Daily Gini-style impurity of predictions at the configured threshold.`
3. **Value Column:** `gini_coefficient`
4. **Timestamp Column:** `ts`
5. **Metric Kind:** `Numeric`

This tells Arthur which column from the SQL result to store as the metric value and which column is the associated timestamp.

***

## Interpreting the Gini Coefficient

* **Low values (close to 0)**
  * Most predictions are concentrated on one side of the threshold.
  * The split is “pure”: the threshold is separating your dataset into a dominant group and a small minority.
* **Higher values**
  * Predictions are more evenly split above vs below the threshold.
  * The threshold is less discriminative in terms of how it partitions the population.

You can:

* Plot this metric over time to see whether the **sharpness of your decision boundary** is changing.
* Use multiple versions (different `thresholdValue`s) to compare how different thresholds behave operationally.

> Preview Data
>
> for startDate use 2025-11-26T17:54:05.425Z
> for endDate use 2025-12-10T17:54:05.425Z
