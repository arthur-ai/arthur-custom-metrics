import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta, timezone
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
    Generate a comprehensive loan amount prediction dataset for regression metrics.
    
    This dataset simulates a loan approval model that predicts the approved loan amount
    based on applicant features. The data includes features relevant to loan underwriting
    and supports evaluation of regression performance metrics like Absolute Error.
    
    Args:
        n_samples: Number of samples to generate
        output_dir: Directory to save parquet files (if None, returns DataFrame only)
        seed: Random seed for reproducibility
        past_days: Number of days in the past from today to generate data (default: 90)
        future_days: Number of days in the future from today to generate data (default: 90)
    
    Returns:
        pandas.DataFrame: Generated dataset with loan application features
    """
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    # Create demographic/geographic groups for potential segmentation analysis
    groups = np.random.choice(['Region_North', 'Region_South', 'Region_East', 'Region_West'], 
                             size=n_samples, p=[0.3, 0.25, 0.25, 0.2])
    
    # Generate loan application features
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
    
    # Loan purpose
    loan_purpose = np.random.choice(
        ['Home Purchase', 'Debt Consolidation', 'Business', 'Education', 'Other'],
        size=n_samples,
        p=[0.35, 0.25, 0.15, 0.15, 0.1]
    )
    
    # Loan term in months (12, 24, 36, 48, 60 months)
    loan_term_months = np.random.choice([12, 24, 36, 48, 60], size=n_samples, p=[0.1, 0.2, 0.3, 0.25, 0.15])
    
    # Years of credit history (0-50, correlated with age)
    years_credit_history = np.clip(
        (age - 18 + np.random.normal(0, 3, n_samples)).astype(int),
        0, 50
    )
    years_credit_history = np.maximum(years_credit_history, 0)
    
    # Number of existing loans
    num_existing_loans = np.random.poisson(1.5, n_samples).astype(int)
    num_existing_loans = np.clip(num_existing_loans, 0, 5)
    
    # Generate ground truth loan amounts (actual approved loan amount)
    # Loan amount is based on creditworthiness and income, with realistic constraints
    actual_loan_amounts = []
    for i in range(n_samples):
        # Base loan amount from income (typically 0.5-2x annual income for personal loans)
        # Use a wider range to get more variation
        income_base = annual_income[i] * np.random.uniform(0.3, 1.2)
        
        # Adjust based on credit score (higher score = higher loan amount)
        credit_factor = (credit_score[i] - 300) / 550  # Normalize to 0-1
        credit_multiplier = 0.6 + credit_factor * 0.6  # Range: 0.6 to 1.2
        
        # Adjust based on debt-to-income (lower DTI = higher loan amount)
        dti_factor = 0.7 + (1.0 - debt_to_income[i]) * 0.4  # Range: 0.7 to 1.1
        
        # Adjust based on employment (employed = higher loan amount)
        employment_multiplier = 1.0 if employment_status[i] == 'Employed' else (
            0.85 if employment_status[i] == 'Self-employed' else 0.65
        )
        
        # Adjust based on credit history (longer history = higher loan amount)
        history_factor = 0.75 + min(1.0, years_credit_history[i] / 20) * 0.35  # Range: 0.75 to 1.1
        
        # Adjust based on loan purpose (home purchase typically gets larger loans)
        purpose_multiplier = 1.5 if loan_purpose[i] == 'Home Purchase' else (
            1.2 if loan_purpose[i] == 'Business' else 1.0
        )
        
        # Adjust based on existing loans (fewer existing loans = higher new loan amount)
        existing_loans_factor = 1.0 - (num_existing_loans[i] * 0.08)
        existing_loans_factor = np.clip(existing_loans_factor, 0.6, 1.0)
        
        # Combine factors
        base_amount = income_base * credit_multiplier * dti_factor * employment_multiplier * \
                     history_factor * purpose_multiplier * existing_loans_factor
        
        # Add some regional variation
        if groups[i] == 'Region_North':
            base_amount *= 1.1  # Slightly higher loan amounts
        elif groups[i] == 'Region_South':
            base_amount *= 0.95  # Slightly lower loan amounts
        
        # Round to nearest $1000 and apply realistic bounds ($5,000 to $500,000)
        loan_amount = np.round(base_amount / 1000) * 1000
        loan_amount = np.clip(loan_amount, 5000, 500000)
        
        actual_loan_amounts.append(loan_amount)
    
    actual_loan_amounts = np.array(actual_loan_amounts)
    
    # Generate model predictions (predicted loan amount)
    # Model predictions should be correlated with actual loan amount but include some error
    predicted_loan_amounts = []
    for i in range(n_samples):
        # Model uses similar logic to actual loan amount but with some noise/error
        # Base prediction from income (slightly different range)
        income_pred = annual_income[i] * np.random.uniform(0.3, 1.2)
        
        # Model considers credit score
        credit_pred_factor = (credit_score[i] - 300) / 550
        credit_pred_multiplier = 0.6 + credit_pred_factor * 0.6
        
        # Model considers debt-to-income
        dti_pred_factor = 0.7 + (1.0 - debt_to_income[i]) * 0.4
        
        # Model considers employment
        emp_pred_multiplier = 1.0 if employment_status[i] == 'Employed' else (
            0.85 if employment_status[i] == 'Self-employed' else 0.65
        )
        
        # Model considers credit history
        hist_pred_factor = 0.75 + min(1.0, years_credit_history[i] / 20) * 0.35
        
        # Model considers loan purpose
        purpose_pred_multiplier = 1.5 if loan_purpose[i] == 'Home Purchase' else (
            1.2 if loan_purpose[i] == 'Business' else 1.0
        )
        
        # Model considers existing loans
        existing_pred_factor = 1.0 - (num_existing_loans[i] * 0.08)
        existing_pred_factor = np.clip(existing_pred_factor, 0.6, 1.0)
        
        # Combine model features (slightly different weights than actual loan amount)
        model_amount = income_pred * credit_pred_multiplier * dti_pred_factor * \
                      emp_pred_multiplier * hist_pred_factor * purpose_pred_multiplier * \
                      existing_pred_factor
        
        # Add noise to simulate model imperfection (5-15% error)
        noise_factor = np.random.normal(1.0, 0.08)  # 8% standard deviation
        model_amount *= noise_factor
        
        # Add group-based bias (model may have learned biases)
        if groups[i] == 'Region_North':
            model_amount *= 1.08  # Model slightly favors this region
        elif groups[i] == 'Region_South':
            model_amount *= 0.95  # Model slightly disfavors this region
        
        # Correlate with actual loan amount but add realistic model error
        # Blend actual amount with model prediction to create realistic correlation
        correlation_factor = np.random.uniform(0.75, 0.90)  # 75-90% correlation
        predicted_amount = actual_loan_amounts[i] * correlation_factor + model_amount * (1 - correlation_factor)
        
        # Round to nearest $1000 and apply realistic bounds
        predicted_amount = np.round(predicted_amount / 1000) * 1000
        predicted_amount = np.clip(predicted_amount, 5000, 500000)
        
        predicted_loan_amounts.append(predicted_amount)
    
    predicted_loan_amounts = np.array(predicted_loan_amounts)
    
    # Create the DataFrame with loan application features
    df = pd.DataFrame({
        'actual_loan_amount': actual_loan_amounts.astype(float),  # Ground truth loan amount
        'predicted_loan_amount': predicted_loan_amounts.astype(float),  # Model's predicted loan amount
        'region': groups.astype(str),  # Geographic region
        'credit_score': credit_score,
        'annual_income': annual_income,
        'age': age,
        'employment_status': employment_status,
        'years_at_job': years_at_job,
        'debt_to_income_ratio': debt_to_income,
        'loan_purpose': loan_purpose,
        'loan_term_months': loan_term_months,
        'years_credit_history': years_credit_history,
        'num_existing_loans': num_existing_loans,
    })
    
    # Add metadata columns
    df['loan_id'] = range(1, n_samples + 1)
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
    partition_dates = [ts.date() for ts in timestamps]
    df['partition_date'] = pd.Series(partition_dates, dtype='object')
    
    # Add timestamp column as datetime objects (will be cast to timestamp type in parquet)
    # Convert to UTC timezone-aware timestamps
    utc_timestamps = [ts.replace(tzinfo=timezone.utc) for ts in timestamps]
    df['timestamp'] = pd.to_datetime(utc_timestamps)
    
    # Ensure all integer columns are proper int64 (not object)
    int_cols = ['loan_id', 'is_valid_application', 'credit_score', 'annual_income', 'age', 
                'years_at_job', 'loan_term_months', 'years_credit_history', 'num_existing_loans']
    for col in int_cols:
        if col in df.columns:
            df[col] = df[col].astype('int64')
    
    # Ensure string columns are strings
    str_cols = ['region', 'employment_status', 'loan_purpose']
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str)
    
    # Reorder columns for better readability
    df = df[['partition_date', 'timestamp', 'loan_id', 'region', 'actual_loan_amount', 
             'predicted_loan_amount', 'is_valid_application', 'credit_score', 'annual_income', 
             'age', 'employment_status', 'years_at_job', 'debt_to_income_ratio', 'loan_purpose',
             'loan_term_months', 'years_credit_history', 'num_existing_loans']]
    
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
    
    print(f"Loan Amount Prediction Dataset generated successfully!")
    print(f"Shape: {df.shape}")
    print(f"\nColumn descriptions:")
    print(f"- partition_date: Partition date (date type, DATE in parquet)")
    print(f"- timestamp: Timestamp (timestamp[ns] with UTC timezone in parquet)")
    print(f"- loan_id: Unique identifier for each loan application")
    print(f"- region: Geographic region (Region_North, Region_South, Region_East, Region_West)")
    print(f"- actual_loan_amount: Ground truth approved loan amount (continuous numeric, $5K-$500K)")
    print(f"- predicted_loan_amount: Model's predicted loan amount (continuous numeric, $5K-$500K)")
    print(f"- is_valid_application: Valid application indicator (1=valid, 0=invalid)")
    print(f"- credit_score: Applicant's credit score (300-850)")
    print(f"- annual_income: Applicant's annual income in USD")
    print(f"- age: Applicant's age (18-75)")
    print(f"- employment_status: Employment status (Employed, Self-employed, Unemployed, Retired)")
    print(f"- years_at_job: Years at current job")
    print(f"- debt_to_income_ratio: Debt-to-income ratio (0-0.8)")
    print(f"- loan_purpose: Purpose of the loan (Home Purchase, Debt Consolidation, Business, Education, Other)")
    print(f"- loan_term_months: Loan term in months (12, 24, 36, 48, 60)")
    print(f"- years_credit_history: Years of credit history (0-50)")
    print(f"- num_existing_loans: Number of existing loans (0-5)")
    print(f"\nDataset statistics:")
    print(f"Mean actual loan amount: ${df['actual_loan_amount'].mean():,.2f}")
    print(f"Mean predicted loan amount: ${df['predicted_loan_amount'].mean():,.2f}")
    print(f"Mean absolute error: ${abs(df['actual_loan_amount'] - df['predicted_loan_amount']).mean():,.2f}")
    print(f"RMSE: ${np.sqrt(((df['actual_loan_amount'] - df['predicted_loan_amount']) ** 2).mean()):,.2f}")
    print(f"\nActual loan amount distribution:")
    print(f"  Min: ${df['actual_loan_amount'].min():,.2f}")
    print(f"  25th percentile: ${df['actual_loan_amount'].quantile(0.25):,.2f}")
    print(f"  Median: ${df['actual_loan_amount'].median():,.2f}")
    print(f"  75th percentile: ${df['actual_loan_amount'].quantile(0.75):,.2f}")
    print(f"  Max: ${df['actual_loan_amount'].max():,.2f}")
    print(f"\nPredicted loan amount distribution:")
    print(f"  Min: ${df['predicted_loan_amount'].min():,.2f}")
    print(f"  25th percentile: ${df['predicted_loan_amount'].quantile(0.25):,.2f}")
    print(f"  Median: ${df['predicted_loan_amount'].median():,.2f}")
    print(f"  75th percentile: ${df['predicted_loan_amount'].quantile(0.75):,.2f}")
    print(f"  Max: ${df['predicted_loan_amount'].max():,.2f}")
    print(f"\nRegion distribution:\n{df['region'].value_counts().sort_index()}")
    print(f"\nLoan purpose distribution:\n{df['loan_purpose'].value_counts().sort_index()}")
    print(f"\nDate partitions: {df['partition_date'].nunique()} unique dates")
    print(f"Partition format: %Y-%m-%d (e.g., {df['partition_date'].iloc[0]})")
    print(f"\nSaved to: {output_dir} (partitioned by date in strftime format %Y-%m-%d/)")
