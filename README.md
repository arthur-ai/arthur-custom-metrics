# Arthur Custom Metrics

Comprehensive documentation and examples for building custom metrics in the Arthur AI platform. This repository provides production-ready SQL queries, configuration guides, and visualization examples for monitoring machine learning models across multiple problem types.

## Overview

This repository contains metric definitions and chart specifications for:
- **Binary Classification** - 7 metrics, 16 charts
- **Multi-Classification** - 10 metrics, 23 charts
- **Regression** - Coming soon

Each metric includes:
- Complete SQL queries with CTEs and aggregations
- Detailed parameter configurations (Aggregate Arguments)
- Reported metrics specifications
- Interpretation guidance
- Use cases and examples
- Associated visualization charts

## Repository Structure

```
arthur-custom-metrics/
├── examples/
│   ├── binary-classification/          # Binary classification metrics
│   │   ├── curve-based-discrimination.md
│   │   ├── detection-acceptance-profile.md
│   │   ├── positive-class-error-profile.md
│   │   ├── rank-association-profile.md
│   │   ├── subgroup-rate-comparison.md
│   │   ├── gini-coefficient.md
│   │   └── population-stability-index.md
│   │
│   ├── multi-classification/           # Multi-label classification metrics
│   │   ├── multi-label-prediction-volume.md
│   │   ├── multi-label-class-count.md
│   │   ├── multi-label-confusion-matrix.md
│   │   ├── label-coverage-ratio.md
│   │   ├── multi-label-precision-recall-f1.md
│   │   ├── exact-match-ratio.md
│   │   ├── jaccard-similarity.md
│   │   ├── label-density.md
│   │   ├── label-cooccurrence-matrix.md
│   │   └── average-confidence-per-label.md
│   │
│   ├── regression/                     # Regression metrics (coming soon)
│   │
│   └── charts/
│       ├── binary-classification/      # 16 chart files
│       │   ├── auc-gini-over-time.md
│       │   ├── ks-statistic-over-time.md
│       │   └── ... (14 more)
│       │
│       └── multi-classification/       # 23 chart files
│           ├── prediction-volume-over-time.md
│           ├── class-count-by-label.md
│           └── ... (21 more)
│
└── README.md
```

## Binary Classification Metrics

### 1. Curve-Based Discrimination
**File**: `examples/binary-classification/curve-based-discrimination.md`

Calculates discrimination metrics from ROC curves:
- **AUC-ROC**: Area under the ROC curve
- **Gini Coefficient**: 2×AUC - 1
- **KS Statistic**: Maximum separation between distributions
- **KS Score**: Alias for KS statistic

**Charts**: 4 visualizations including AUC/Gini over time, KS statistic trends, and combined views.

### 2. Detection-Acceptance Profile
**File**: `examples/binary-classification/detection-acceptance-profile.md`

Tracks true positive and true negative variants:
- Capture Rate, Correct Detection Rate, True Positive Rate
- Precision, Correct Acceptance Rate, Valid Detection Rate

**Charts**: 3 visualizations for recall variants, acceptance accuracy, and tradeoff analysis.

### 3. Positive Class Error Profile
**File**: `examples/binary-classification/positive-class-error-profile.md`

Monitors false positive metrics:
- Adjusted FP Rate, Bad Case Rate, FP Ratio
- Valid Detection Rate, Overprediction Rate, Underprediction Rate, Total FP Rate

**Charts**: 3 visualizations for FP/bad case rates, over/under prediction, and FP ratio vs valid detection.

### 4. Rank Association Profile
**File**: `examples/binary-classification/rank-association-profile.md`

Measures correlation between predicted scores and outcomes:
- **Spearman's Rho**: Rank correlation
- **Kendall's Tau**: Concordance measure

**Charts**: 3 visualizations including individual trends and combined comparison.

### 5. Subgroup Rate Comparison
**File**: `examples/binary-classification/subgroup-rate-comparison.md`

Compares error rates across demographic groups:
- Rate Difference (absolute)
- Relative Bad Rate Difference (multiplicative)

**Charts**: 3 visualizations for absolute difference, relative difference, and combined disparity view.

### 6. Gini Coefficient
**File**: `examples/binary-classification/gini-coefficient.md`

Measures model discrimination capability (derived from AUC):
- Gini = 2×AUC - 1
- Range: -1 to 1 (higher is better)

### 7. Population Stability Index (PSI)
**File**: `examples/binary-classification/population-stability-index.md`

Detects distribution drift:
- PSI score measuring distribution changes
- Bins predicted probabilities and compares distributions over time

## Multi-Classification Metrics

### Core Metrics

#### 1. Multi-Label Prediction Volume
**File**: `examples/multi-classification/multi-label-prediction-volume.md`

Tracks average number of labels predicted per inference.

**Chart**: 1 time series visualization

**Use Case**: Monitor overall prediction behavior and label volume trends.

#### 2. Multi-Label Class Count
**File**: `examples/multi-classification/multi-label-class-count.md`

Counts how many times each label appears in predictions.

**Charts**: 2 visualizations (time series per label, top 20 labels)

**Use Case**: Understand label distribution and identify most/least common labels.

#### 3. Label Coverage Ratio
**File**: `examples/multi-classification/label-coverage-ratio.md`

Proportion of inferences containing each label (0-1 scale).

**Charts**: 2 visualizations (coverage over time, distribution ranking)

**Use Case**: Track label prevalence and identify rare vs common labels.

### Performance Metrics

#### 4. Multi-Label Confusion Matrix
**File**: `examples/multi-classification/multi-label-confusion-matrix.md`

Calculates TP, FP, FN for each label separately.

**Charts**: 3 visualizations (components over time, comparison bars, error rates)

**Use Case**: Detailed per-label performance analysis, identify precision vs recall issues.

#### 5. Precision, Recall, and F1 per Label
**File**: `examples/multi-classification/multi-label-precision-recall-f1.md`

Quality metrics derived from confusion matrix:
- **Precision**: TP / (TP + FP)
- **Recall**: TP / (TP + FN)
- **F1 Score**: Harmonic mean of precision and recall

**Charts**: 3 visualizations (all metrics over time, F1 ranking, precision vs recall scatter)

**Use Case**: Primary quality metrics for monitoring and reporting.

### Overall Accuracy Metrics

#### 6. Exact Match Ratio
**File**: `examples/multi-classification/exact-match-ratio.md`

Proportion of predictions with perfect label set match.

**Chart**: 1 time series + 1 combined with Jaccard

**Use Case**: Strictest accuracy measure, executive KPI for "% perfect predictions".

#### 7. Jaccard Similarity
**File**: `examples/multi-classification/jaccard-similarity.md`

Intersection over Union between predicted and ground truth label sets.
- Formula: |A ∩ B| / |A ∪ B|
- Range: 0 to 1 (higher is better)

**Charts**: 2 visualizations (similarity over time, combined with exact match)

**Use Case**: More lenient accuracy metric that rewards partial correctness.

### Distribution Metrics

#### 8. Label Density
**File**: `examples/multi-classification/label-density.md`

Average labels per inference normalized by total catalog size.
- Formula: (Avg labels per inference) / (Total unique labels)
- Range: 0 to 1

**Chart**: 1 time series

**Use Case**: Understand catalog utilization and prediction sparsity.

#### 9. Label Co-occurrence Matrix
**File**: `examples/multi-classification/label-cooccurrence-matrix.md`

Tracks which label pairs appear together:
- **Predicted co-occurrence**: How often model predicts pairs together
- **Ground truth co-occurrence**: How often pairs actually occur together

**Charts**: 4 visualizations (predicted heatmap, ground truth heatmap, comparison, top pairs)

**Use Case**: Understand label relationships and dependencies, validate model learning.

### Confidence Metrics

#### 10. Average Confidence per Label
**File**: `examples/multi-classification/average-confidence-per-label.md`

Average confidence score for each label (includes 0 for non-predicted).

**Charts**: 4 visualizations (confidence over time, distribution, low-confidence labels, calibration scatter)

**Use Case**: Identify uncertain labels, quality control, human review routing.

## Metric Documentation Structure

Each metric file follows this structure:

### 1. Overview
- What the metric tracks
- Key insights it provides
- When to use it

### 2. Data Requirements
- Required columns (timestamp, IDs, labels, scores)
- Data types and formats

### 3. Base Metric SQL
- Complete SQL query with CTEs
- TimescaleDB time_bucket aggregation
- Handles NULL values and edge cases

### 4. Aggregate Arguments
Detailed parameter configuration for each argument:
- Parameter Key (variable name in SQL)
- Friendly Name (UI display)
- Description
- Parameter Type (Column, Dataset, etc.)
- Source Dataset Parameter Key
- Allow Any Column Type (Yes/No)
- Tag Hints (e.g., primary_timestamp, prediction)
- Allowed Column Types (timestamp, int, str, uuid, etc.)

### 5. Reported Metrics
Specification for each output metric:
- Metric Name
- Description
- Value Column (column name in SQL output)
- Timestamp Column
- Metric Kind (Numeric, Categorical)
- Dimension Column (for per-label metrics)

### 6. Interpreting the Metric
- What different values mean
- Trends to watch for
- Common patterns
- When to investigate

### 7. Use Cases
- Real-world applications
- Example scenarios
- When this metric is most valuable

## Chart Documentation Structure

Each chart file follows this structure:

### 1. Chart Title
Clear, descriptive name

### 2. Metrics Used
- Which metrics this chart visualizes
- Column names and dimensions

### 3. SQL Query
- Query to fetch data for visualization
- Often aggregates or filters base metrics
- Includes time range filters

### 4. What this shows
- Visual description of the chart
- What patterns it reveals

### 5. How to interpret it
- How to read the visualization
- What different patterns mean
- When to take action
- Typical value ranges

## Key Concepts

### Time Bucketing
All metrics use daily aggregation via TimescaleDB's `time_bucket(INTERVAL '1 day', timestamp)`:
- Provides consistent time series data
- Reduces data volume
- Enables trend analysis

### Dimension Columns
Many metrics include dimension columns:
- **Binary Classification**: Often subgroup dimensions for fairness analysis
- **Multi-Classification**: Label name (series) as dimension
- **Co-occurrence**: Two dimensions (label_1, label_2) for pairs

### NULL Handling
All queries use `COALESCE` and `NULLIF` for robust handling:
- `COALESCE(array, ARRAY[]::TEXT[])` - Empty array for NULL
- `NULLIF(denominator, 0)` - Avoid division by zero

### Array Operations
Multi-classification metrics heavily use PostgreSQL array functions:
- `unnest()` - Expand arrays to rows
- `array_length()` - Count elements
- `ARRAY(SELECT DISTINCT unnest())` - Deduplicate arrays
- `CROSS JOIN LATERAL` - Explode arrays with context

## Use Cases by Role

### ML Engineers
**Focus on**: Performance and debugging metrics
- Precision/Recall/F1 per label
- Confusion matrix components
- Error rates and calibration
- Co-occurrence patterns

**Charts**: Scatter plots, error analysis, calibration checks

### Data Scientists
**Focus on**: Model behavior and relationships
- Label co-occurrence matrices
- Distribution metrics (density, coverage)
- Confidence analysis
- Rank correlation

**Charts**: Heatmaps, distribution charts, relationship analysis

### Operations Teams
**Focus on**: Monitoring and alerting
- Prediction volume
- Exact match ratio
- Jaccard similarity
- Low confidence labels

**Charts**: Time series, threshold monitoring, alert triggers

### Executives
**Focus on**: High-level KPIs
- Exact match ratio (% perfect)
- Jaccard similarity (% similar)
- F1 score trends
- Top performing labels

**Charts**: Simple time series, summary dashboards

## Implementation Guide

### Step 1: Choose Your Metric
Browse the relevant directory (binary-classification or multi-classification) and select the metric that fits your use case.

### Step 2: Configure Aggregate Arguments
For each argument in the metric documentation:
1. Set the Parameter Key (used in SQL)
2. Set the Friendly Name (user-facing)
3. Add Description
4. Specify Parameter Type
5. Set Source Dataset Parameter Key
6. Configure column type restrictions
7. Add relevant Tag Hints

### Step 3: Deploy Base Metric SQL
Copy the SQL query from the "Base Metric SQL" section:
- Replace `{{parameter_name}}` with your configured parameters
- Test the query on your dataset
- Validate output columns match Reported Metrics

### Step 4: Configure Reported Metrics
For each metric in the output:
1. Set Metric Name
2. Add Description
3. Specify Value Column
4. Set Timestamp Column
5. Define Metric Kind
6. Add Dimension Column if applicable

### Step 5: Create Visualizations
Browse the corresponding charts directory:
- Choose relevant visualizations
- Adapt SQL queries for your schema
- Configure chart type (line, bar, scatter, heatmap)
- Set up alerts and thresholds

## Best Practices

### Query Performance
- Use time_bucket for consistent aggregation
- Add WHERE clauses to filter relevant time ranges
- Create indexes on timestamp columns
- Use DISTINCT carefully (can be expensive)
- Consider materialized views for expensive metrics

### Monitoring
- Set up alerts on key metrics (exact match, F1, confidence)
- Monitor trends, not just absolute values
- Look for sudden changes or anomalies
- Compare multiple related metrics for context

### Interpretation
- Always consider sample size (low counts = high variance)
- Compare metrics over consistent time windows
- Account for seasonality and known patterns
- Validate unexpected changes against deployments

### Data Quality
- Check for NULL values in key columns
- Validate array lengths are as expected
- Ensure timestamp coverage is complete
- Monitor for missing or duplicate data

## Common Patterns

### Multi-Label Classification Analysis Workflow

1. **Start with overall accuracy**:
   - Exact Match Ratio - How many perfect?
   - Jaccard Similarity - How close overall?

2. **Drill into per-label performance**:
   - F1 Score Comparison - Which labels struggle?
   - Confusion Matrix - What type of errors?

3. **Understand behavior**:
   - Prediction Volume - How many labels predicted?
   - Coverage Ratio - Which labels are common?
   - Label Density - Using full catalog?

4. **Analyze relationships**:
   - Co-occurrence Matrix - Which labels appear together?
   - Compare predicted vs ground truth patterns

5. **Quality control**:
   - Average Confidence - Which labels uncertain?
   - Confidence vs Accuracy - Is model calibrated?

## Troubleshooting

### Query Returns No Data
- Check timestamp filter range
- Verify dataset name is correct
- Ensure columns exist and are named correctly
- Check for NULL timestamps

### Metrics Look Wrong
- Verify parameter mapping is correct
- Check array column formats (should be PostgreSQL arrays)
- Validate label values match expectations
- Review NULL handling in query

### Performance Issues
- Add time range filters to reduce data volume
- Create indexes on timestamp and join columns
- Consider aggregating less frequently (weekly vs daily)
- Review explain plans for slow queries

## Contributing

When adding new metrics:
1. Follow the established documentation structure
2. Include complete SQL with NULL handling
3. Provide clear interpretation guidance
4. Add relevant visualizations
5. Include real-world use cases
6. Test on actual data

## Support

For issues or questions:
- Review the specific metric documentation
- Check interpretation guidelines
- Validate SQL against your schema
- Consult Arthur platform documentation

## License

This repository contains documentation and examples for use with the Arthur AI platform.

---

**Total Metrics**: 17 (7 binary-classification + 10 multi-classification)
**Total Charts**: 39 (16 binary-classification + 23 multi-classification)
**Status**: Production-ready with comprehensive documentation
