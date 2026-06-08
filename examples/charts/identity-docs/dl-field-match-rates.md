# Driver License Field Match Rates

## Metrics Used

* `dl_name_match_rate_metric`
* `dl_dob_match_rate_metric`
* `dl_license_num_match_rate_metric`
* `dl_expiry_match_rate_metric`
* `dl_address_match_rate_metric`

## Axes

* **X axis:** Date (`time_bucket_1d`)
* **Y axis:** Match Rate (`metric_value`, 0–1)
* **Series:** Field (`friendly_name`)

## SQL Query

```sql
SELECT
    time_bucket_gapfill(
        '1 day',
        timestamp,
        '{{dateStart}}'::timestamptz,
        '{{dateEnd}}'::timestamptz
    ) AS time_bucket_1d,
    metric_name,
    CASE
        WHEN metric_name = 'dl_name_match_rate_metric'        THEN 'Name'
        WHEN metric_name = 'dl_dob_match_rate_metric'         THEN 'Date of Birth'
        WHEN metric_name = 'dl_license_num_match_rate_metric' THEN 'License Number'
        WHEN metric_name = 'dl_expiry_match_rate_metric'      THEN 'Expiry Date'
        WHEN metric_name = 'dl_address_match_rate_metric'     THEN 'Address'
        ELSE metric_name
    END AS friendly_name,
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name IN (
    'dl_name_match_rate_metric',
    'dl_dob_match_rate_metric',
    'dl_license_num_match_rate_metric',
    'dl_expiry_match_rate_metric',
    'dl_address_match_rate_metric'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, metric_name
ORDER BY time_bucket_1d, metric_name;
```

## What this shows

Per-field extraction accuracy for driver licenses — one line per extracted attribute. Shows which specific fields the model gets right or wrong independently of each other.

## How to interpret it

* A **single field dropping** while others stay stable points to a format change for that specific field (e.g., states moving the address to a new zone on the card).
* **All fields dropping** together suggests a general OCR or image quality regression for driver licenses.
* Address and date fields tend to be harder to extract and may naturally sit lower than name or license number.
