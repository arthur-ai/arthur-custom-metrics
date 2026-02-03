import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
import pyarrow as pa
import pyarrow.parquet as pq


def ensure_json_serializable(df):
    """
    Ensure all columns in the DataFrame are JSON serializable.
    Converts numpy types to native Python types and handles datetime objects.
    """
    df = df.copy()
    
    for col in df.columns:
        if pd.api.types.is_integer_dtype(df[col]):
            # Convert numpy integers to Python int
            df[col] = df[col].astype('Int64').astype(object).where(
                df[col].notna(), None
            )
            # Convert back to int, handling NaN
            df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)
        elif pd.api.types.is_float_dtype(df[col]):
            # Convert numpy floats to Python float
            df[col] = df[col].astype('float64')
            df[col] = df[col].apply(lambda x: float(x) if pd.notna(x) else None)
        elif pd.api.types.is_string_dtype(df[col]):
            # Ensure strings are plain Python strings
            df[col] = df[col].astype(str).replace('nan', None)
        elif pd.api.types.is_object_dtype(df[col]):
            # Check for any remaining datetime/date objects
            df[col] = df[col].apply(lambda x: str(x) if isinstance(x, (datetime, timedelta)) else x)
    
    return df


def generate_dataset(n_samples=1000, output_dir=None, seed=42, past_days=90, future_days=90):
    """
    Generate a comprehensive credit card application dataset for classification and discrimination metrics.
    
    This dataset simulates a credit card application model that evaluates applicant risk and
    makes approval/rejection decisions. The data includes features relevant to credit risk assessment
    and supports evaluation of classification performance and fairness metrics.
    
    Args:
        n_samples: Number of samples to generate
        output_dir: Directory to save parquet files (if None, returns DataFrame only)
        seed: Random seed for reproducibility
        past_days: Number of days in the past from today to generate data (default: 90)
        future_days: Number of days in the future from today to generate data (default: 90)
    
    Returns:
        pandas.DataFrame: Generated dataset with credit card application features
    """
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    # Create demographic/geographic groups for discrimination/fairness metrics
    # These represent different regions or demographic groups that may have different approval rates
    groups = np.random.choice(['Region_North', 'Region_South', 'Region_East', 'Region_West'], 
                             size=n_samples, p=[0.3, 0.25, 0.25, 0.2])
    
    # Generate credit card application features
    # Credit score (300-850, normally distributed around 650)
    credit_score = np.clip(np.random.normal(650, 100, n_samples), 300, 850).astype(int)
    
    # Annual income (skewed right, typical income distribution)
    annual_income = np.random.lognormal(mean=10.5, sigma=0.8, size=n_samples).astype(int)
    annual_income = np.clip(annual_income, 20000, 200000)
    
    # Age (18-75, slightly skewed towards younger applicants)
    age = np.random.gamma(shape=2, scale=15, size=n_samples).astype(int)
    age = np.clip(age, 18, 75)
    
    # Employment status
    employment_status = np.random.choice(
        ['Employed', 'Self-employed', 'Unemployed', 'Retired'],
        size=n_samples,
        p=[0.6, 0.15, 0.15, 0.1]
    )
    
    # Years at current job (0-40, correlated with age)
    years_at_job = np.clip((age * np.random.uniform(0.1, 0.4, n_samples)).astype(int), 0, 40)
    # Unemployed/Retired have 0 years at job
    unemployed_or_retired = np.isin(employment_status, ['Unemployed', 'Retired'])
    years_at_job[unemployed_or_retired] = 0
    
    # Debt-to-income ratio (0-0.8, higher for lower income)
    debt_to_income = np.random.beta(2, 5, n_samples) * 0.8
    debt_to_income = np.clip(debt_to_income + (1 - annual_income / 200000) * 0.2, 0, 0.8)
    
    # Number of existing credit cards (0-10, correlated with credit score)
    num_credit_cards = np.clip(
        ((credit_score - 300) / 550 * 8 + np.random.poisson(2, n_samples)).astype(int),
        0, 10
    )
    
    # Years of credit history (0-50, correlated with age)
    years_credit_history = np.clip(
        (age - 18 + np.random.normal(0, 3, n_samples)).astype(int),
        0, 50
    )
    years_credit_history = np.maximum(years_credit_history, 0)
    
    # Generate ground truth approval labels (1=Approved, 0=Rejected)
    # Approval probability based on creditworthiness features
    actual_labels = []
    for i in range(n_samples):
        # Base approval probability from credit score
        base_prob = (credit_score[i] - 300) / 550  # Normalize to 0-1
        
        # Adjust based on income (higher income = higher approval)
        income_factor = min(1.0, annual_income[i] / 100000)
        
        # Adjust based on debt-to-income (lower DTI = higher approval)
        dti_factor = 1.0 - debt_to_income[i]
        
        # Adjust based on employment (employed = higher approval)
        employment_factor = 1.0 if employment_status[i] == 'Employed' else (
            0.8 if employment_status[i] == 'Self-employed' else 0.5
        )
        
        # Adjust based on credit history (longer history = higher approval)
        history_factor = min(1.0, years_credit_history[i] / 10)
        
        # Combine factors
        approval_prob = base_prob * 0.4 + income_factor * 0.2 + dti_factor * 0.15 + \
                       employment_factor * 0.15 + history_factor * 0.1
        
        # Add group-based differences for discrimination analysis
        # Different regions may have different approval rates due to various factors
        if groups[i] == 'Region_North':
            approval_prob *= 1.1  # Slightly higher approval rate
        elif groups[i] == 'Region_South':
            approval_prob *= 0.9  # Slightly lower approval rate
        elif groups[i] == 'Region_East':
            approval_prob *= 1.05  # Slightly higher
        
        approval_prob = np.clip(approval_prob, 0.05, 0.95)  # Keep reasonable bounds
        
        actual_labels.append(np.random.binomial(1, approval_prob))
    
    actual_labels = np.array(actual_labels)
    
    # Generate model predictions (approval probabilities)
    # Model predictions should be correlated with actual approval but include some error
    # This simulates a real ML model that uses the features to predict approval
    predicted_probs = []
    for i in range(n_samples):
        # Model uses similar logic to actual approval but with some noise/error
        # Base prediction from credit score
        base_pred = (credit_score[i] - 300) / 550
        
        # Model considers income
        income_pred = min(1.0, annual_income[i] / 100000)
        
        # Model considers debt-to-income
        dti_pred = 1.0 - debt_to_income[i]
        
        # Model considers employment
        emp_pred = 1.0 if employment_status[i] == 'Employed' else (
            0.8 if employment_status[i] == 'Self-employed' else 0.5
        )
        
        # Model considers credit history
        hist_pred = min(1.0, years_credit_history[i] / 10)
        
        # Combine model features (slightly different weights than actual approval)
        model_prob = base_pred * 0.35 + income_pred * 0.25 + dti_pred * 0.2 + \
                    emp_pred * 0.1 + hist_pred * 0.1
        
        # Add noise to simulate model imperfection
        noise = np.random.normal(0, 0.1)
        model_prob += noise
        
        # Add group-based bias (model may have learned biases)
        if groups[i] == 'Region_North':
            model_prob *= 1.08  # Model slightly favors this region
        elif groups[i] == 'Region_South':
            model_prob *= 0.92  # Model slightly disfavors this region
        
        # Correlate with actual label but add realistic model error
        if actual_labels[i] == 1:
            # If actually approved, model should generally predict higher (but not perfect)
            model_prob = model_prob * 0.7 + np.random.beta(6, 2) * 0.3
        else:
            # If actually rejected, model should generally predict lower (but not perfect)
            model_prob = model_prob * 0.7 + np.random.beta(2, 6) * 0.3
        
        model_prob = np.clip(model_prob, 0.01, 0.99)
        predicted_probs.append(model_prob)
    
    predicted_probs = np.array(predicted_probs)
    
    # Generate predicted labels using a threshold (0.5 is standard for approval)
    threshold = 0.5
    predicted_labels = (predicted_probs >= threshold).astype(int)
    
    # Create the DataFrame with credit card application features
    df = pd.DataFrame({
        'actual_label': actual_labels.astype(int),  # 1=Approved, 0=Rejected
        'predicted_label': predicted_labels.astype(int),  # Model prediction: 1=Approved, 0=Rejected
        'predicted_probability': predicted_probs.astype(float),  # Model's approval probability
        'region': groups.astype(str),  # Geographic region (for discrimination analysis)
        'credit_score': credit_score,
        'annual_income': annual_income,
        'age': age,
        'employment_status': employment_status,
        'years_at_job': years_at_job,
        'debt_to_income_ratio': debt_to_income,
        'num_credit_cards': num_credit_cards,
        'years_credit_history': years_credit_history,
    })
    
    # Add metadata columns
    df['application_id'] = range(1, n_samples + 1)
    df['is_valid_application'] = np.random.choice([0, 1], size=n_samples, p=[0.01, 0.99]).astype(int)  # 99% valid
    
    # Add timestamp column - spread over past_days + future_days + 1 days from today
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=past_days)  # Start past_days ago
    total_days = past_days + future_days + 1  # +1 to include today
    timestamps = []
    for i in range(n_samples):
        # Spread timestamps over total_days (from -past_days to +future_days days relative to today, inclusive)
        days_offset = i % total_days
        hours_offset = np.random.randint(0, 24)
        minutes_offset = np.random.randint(0, 60)
        seconds_offset = np.random.randint(0, 60)
        timestamp = start_date + timedelta(days=days_offset, hours=hours_offset, 
                                           minutes=minutes_offset, seconds=seconds_offset)
        timestamps.append(timestamp)
    
    # Convert partition dates to date type (DATE type for parquet)
    # Extract date from each timestamp and convert to date objects
    partition_dates = [ts.date() for ts in timestamps]
    df['partition_date'] = pd.Series(partition_dates, dtype='object')
    
    # Add timestamp column as datetime objects (will be cast to timestamp type in parquet)
    # Convert to UTC timezone-aware timestamps
    from datetime import timezone
    utc_timestamps = [ts.replace(tzinfo=timezone.utc) for ts in timestamps]
    df['timestamp'] = pd.to_datetime(utc_timestamps)
    
    # Ensure all integer columns are proper int64 (not object)
    int_cols = ['application_id', 'actual_label', 'predicted_label', 'is_valid_application',
                'credit_score', 'annual_income', 'age', 'years_at_job', 'num_credit_cards', 'years_credit_history']
    for col in int_cols:
        if col in df.columns:
            df[col] = df[col].astype('int64')
    
    # Ensure string columns are strings
    str_cols = ['region', 'employment_status']
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str)
    
    # Reorder columns for better readability
    df = df[['partition_date', 'timestamp', 'application_id', 'region', 'actual_label', 'predicted_label', 'predicted_probability',
             'is_valid_application', 'credit_score', 'annual_income', 'age', 'employment_status',
             'years_at_job', 'debt_to_income_ratio', 'num_credit_cards', 'years_credit_history']]
    
    # Verify JSON serialization before saving (convert date types to strings for check)
    try:
        test_record = df.iloc[0].to_dict()
        # Convert date/datetime objects to strings for JSON serialization check
        for key, val in test_record.items():
            if isinstance(val, (pd.Timestamp, datetime)):
                test_record[key] = val.isoformat()
            elif hasattr(val, 'isoformat'):  # date objects
                test_record[key] = val.isoformat()
        json.dumps(test_record)
    except (TypeError, ValueError) as e:
        raise ValueError(f"DataFrame contains non-JSON-serializable data: {e}")
    
    # Save to parquet if output_dir is provided
    # Use strftime format for partitions: %Y-%m-%d/ (e.g., 2026-01-20/)
    if output_dir is not None:
        output_path = Path(output_dir)
        
        # Manually partition by date to get strftime format directories (e.g., 2026-01-20/)
        # instead of pyarrow's default column=value format
        for partition_date, group_df in df.groupby('partition_date'):
            # Convert date to string for directory name
            partition_date_str = partition_date.strftime('%Y-%m-%d') if hasattr(partition_date, 'strftime') else str(partition_date)
            partition_dir = output_path / partition_date_str
            partition_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert to pyarrow table to explicitly set types
            table = pa.Table.from_pandas(group_df)
            
            # Create schema with explicit types
            fields = []
            for field in table.schema:
                if field.name == 'timestamp':
                    # Cast to timestamp type with UTC timezone
                    fields.append(pa.field('timestamp', pa.timestamp('ns', tz='UTC')))
                elif field.name == 'partition_date':
                    # Explicitly set as DATE type
                    fields.append(pa.field('partition_date', pa.date32()))
                else:
                    fields.append(field)
            
            schema = pa.schema(fields)
            table = table.cast(schema)
            
            # Write parquet file with explicit schema
            pq.write_table(table, partition_dir / f"data-{partition_date_str}.parquet")
    
    return df


if __name__ == '__main__':
    # Generate dataset with default settings
    n_samples = 1000
    output_dir = Path(__file__).parent / '../output'
    
    df = generate_dataset(n_samples=n_samples, output_dir=output_dir)
    
    print(f"Credit Card Application Dataset generated successfully!")
    print(f"Shape: {df.shape}")
    print(f"\nColumn descriptions:")
    print(f"- partition_date: Partition date (date type, DATE in parquet)")
    print(f"- timestamp: Timestamp (timestamp[ns] with UTC timezone in parquet)")
    print(f"- application_id: Unique identifier for each credit card application")
    print(f"- region: Geographic region (Region_North, Region_South, Region_East, Region_West) for discrimination analysis")
    print(f"- actual_label: Ground truth approval decision (1=Approved, 0=Rejected)")
    print(f"- predicted_label: Model's predicted approval decision (1=Approved, 0=Rejected)")
    print(f"- predicted_probability: Model's approval probability score (0-1)")
    print(f"- is_valid_application: Valid application indicator (1=valid, 0=invalid)")
    print(f"- credit_score: Applicant's credit score (300-850)")
    print(f"- annual_income: Applicant's annual income in USD")
    print(f"- age: Applicant's age (18-75)")
    print(f"- employment_status: Employment status (Employed, Self-employed, Unemployed, Retired)")
    print(f"- years_at_job: Years at current job")
    print(f"- debt_to_income_ratio: Debt-to-income ratio (0-0.8)")
    print(f"- num_credit_cards: Number of existing credit cards (0-10)")
    print(f"- years_credit_history: Years of credit history (0-50)")
    print(f"\nDataset statistics:")
    print(f"Approval rate (actual): {df['actual_label'].mean():.2%}")
    print(f"Approval rate (predicted): {df['predicted_label'].mean():.2%}")
    print(f"\nActual label distribution:\n{df['actual_label'].value_counts().sort_index()}")
    print(f"\nPredicted label distribution:\n{df['predicted_label'].value_counts().sort_index()}")
    print(f"\nRegion distribution:\n{df['region'].value_counts().sort_index()}")
    print(f"\nApproval rates by region:")
    for region in df['region'].unique():
        region_df = df[df['region'] == region]
        approval_rate = region_df['actual_label'].mean()
        print(f"  {region}: {approval_rate:.2%}")
    print(f"\nDate partitions: {df['partition_date'].nunique()} unique dates")
    print(f"Partition format: %Y-%m-%d (e.g., {df['partition_date'].iloc[0]})")
    print(f"\nConfusion matrix (Actual vs Predicted Approval):")
    print(pd.crosstab(df['actual_label'], df['predicted_label'], 
                     rownames=['Actual'], colnames=['Predicted'], margins=True))
    print(f"\nSaved to: {output_dir} (partitioned by date in strftime format %Y-%m-%d/)")
