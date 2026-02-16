able_schema:
  - column_name: max_version_for_timestamp
    data_type: integer
    nullable: true
    default: null

  - column_name: model_id
    data_type: uuid
    nullable: true
    default: null

  - column_name: project_id
    data_type: uuid
    nullable: true
    default: null

  - column_name: workspace_id
    data_type: uuid
    nullable: true
    default: null

  - column_name: organization_id
    data_type: uuid
    nullable: true
    default: null

  - column_name: metric_name
    data_type: character varying
    nullable: true
    default: null

  - column_name: timestamp
    data_type: timestamp with time zone
    nullable: true
    default: null

  - column_name: metric_version
    data_type: integer
    nullable: true
    default: null

  - column_name: value
    data_type: user-defined
    nullable: true
    default: null

  - column_name: dimensions
    data_type: jsonb
    nullable: true
    default: null