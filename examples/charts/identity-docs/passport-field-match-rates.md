# Passport Field Match Rates

## Metrics Used

* `numeric_sum` (columns: `pp_surname_match`, `pp_given_names_match`, `pp_passport_num_match`, `pp_dob_match`, `pp_expiry_match`, `pp_nationality_match`, `pp_sex_match`, `pp_mrz_match`)

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
    dimensions ->> 'column_name' AS field_name,
    CASE
        WHEN dimensions ->> 'column_name' = 'pp_surname_match'      THEN 'Surname'
        WHEN dimensions ->> 'column_name' = 'pp_given_names_match'  THEN 'Given Names'
        WHEN dimensions ->> 'column_name' = 'pp_passport_num_match' THEN 'Passport Number'
        WHEN dimensions ->> 'column_name' = 'pp_dob_match'          THEN 'Date of Birth'
        WHEN dimensions ->> 'column_name' = 'pp_expiry_match'       THEN 'Expiry Date'
        WHEN dimensions ->> 'column_name' = 'pp_nationality_match'  THEN 'Nationality'
        WHEN dimensions ->> 'column_name' = 'pp_sex_match'          THEN 'Sex'
        WHEN dimensions ->> 'column_name' = 'pp_mrz_match'          THEN 'MRZ'
        ELSE dimensions ->> 'column_name'
    END AS friendly_name,
    COALESCE(AVG(value), 0) AS metric_value

FROM metrics_numeric_latest_version
WHERE metric_name = 'numeric_sum'
  AND dimensions ->> 'column_name' IN (
    'pp_surname_match',
    'pp_given_names_match',
    'pp_passport_num_match',
    'pp_dob_match',
    'pp_expiry_match',
    'pp_nationality_match',
    'pp_sex_match',
    'pp_mrz_match'
)
[[AND timestamp BETWEEN '{{dateStart}}' AND '{{dateEnd}}']]

GROUP BY time_bucket_1d, field_name
ORDER BY time_bucket_1d, field_name;
```

## What this shows

Per-field extraction accuracy for passports — one line per extracted attribute. The MRZ line is especially useful as a signal: MRZ is machine-printed and should have near-perfect extraction; degradation there usually points to image quality or scan angle issues rather than model problems.

## How to interpret it

* **MRZ dropping** while other fields hold: likely an image quality or resolution issue — MRZ should be the easiest field to read.
* **Given names dropping** while surname holds: the model may be struggling with multi-name formats (hyphenated names, long name strings).
* **All fields dropping for passports** while driver license fields are stable: the model may have regressed on passport-specific layouts.
