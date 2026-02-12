import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json


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


def generate_dataset(input_csv_path=None, output_dir=None, seed=42, past_days=90, future_days=90):
    """
    Generate a comprehensive housing price prediction inference dataset from training data.
    
    This dataset simulates a housing price prediction model that predicts median house values
    based on housing features. The data includes features from the California housing dataset
    and supports evaluation of regression performance metrics like Absolute Error.
    
    Args:
        input_csv_path: Path to the housing.csv training file (if None, uses default location)
        output_dir: Directory to save partitioned CSV files (if None, returns DataFrame only)
        seed: Random seed for reproducibility
        past_days: Number of days in the past from today to generate data (default: 90)
        future_days: Number of days in the future from today to generate data (default: 90)
    
    Returns:
        pandas.DataFrame: Generated dataset with housing features and predictions
    """
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    # Default input path
    if input_csv_path is None:
        input_csv_path = Path(__file__).parent.parent / 'housing.csv'
    else:
        input_csv_path = Path(input_csv_path)
    
    # Read the training dataset
    print(f"Reading housing data from {input_csv_path}...")
    df_train = pd.read_csv(input_csv_path)
    
    n_samples = len(df_train)
    print(f"Loaded {n_samples} samples from training dataset")
    
    # Use median_house_value as ground truth (actual value)
    actual_house_values = df_train['median_house_value'].values.astype(float)
    
    # Generate model predictions (predicted house value)
    # Model predictions should be correlated with actual house value but include some error
    predicted_house_values = []
    
    for i in range(n_samples):
        actual_value = actual_house_values[i]
        
        # Model uses features to predict, but with some error
        # Create a prediction based on actual value with realistic model error
        
        # Use features to create a more realistic prediction
        # Model considers median_income (strong predictor)
        income_factor = df_train.iloc[i]['median_income']
        # Normalize income (typical range 0-15, but we'll use it as a multiplier)
        income_multiplier = 0.8 + (income_factor / 15.0) * 0.4  # Range: 0.8 to 1.2
        
        # Model considers housing_median_age
        age_factor = df_train.iloc[i]['housing_median_age']
        age_multiplier = 0.9 + (age_factor / 52.0) * 0.2  # Range: 0.9 to 1.1
        
        # Model considers total_rooms
        rooms_factor = df_train.iloc[i]['total_rooms']
        # Normalize rooms (typical range 0-40000)
        rooms_multiplier = 0.95 + min(1.0, rooms_factor / 40000.0) * 0.1  # Range: 0.95 to 1.05
        
        # Model considers population
        pop_factor = df_train.iloc[i]['population']
        # Normalize population (typical range 0-4000)
        pop_multiplier = 0.98 + min(1.0, pop_factor / 4000.0) * 0.04  # Range: 0.98 to 1.02
        
        # Model considers ocean_proximity (categorical feature)
        ocean_prox = df_train.iloc[i]['ocean_proximity']
        if ocean_prox == 'NEAR BAY':
            ocean_multiplier = 1.05  # Model slightly overvalues near bay
        elif ocean_prox == 'INLAND':
            ocean_multiplier = 0.95  # Model slightly undervalues inland
        elif ocean_prox == 'ISLAND':
            ocean_multiplier = 1.10  # Model overvalues islands
        elif ocean_prox == 'NEAR OCEAN':
            ocean_multiplier = 1.03  # Model slightly overvalues near ocean
        else:  # <1H OCEAN
            ocean_multiplier = 1.02
        
        # Combine model features (slightly different weights than actual value)
        model_base = actual_value * income_multiplier * age_multiplier * \
                     rooms_multiplier * pop_multiplier * ocean_multiplier
        
        # Add noise to simulate model imperfection (5-15% error)
        noise_factor = np.random.normal(1.0, 0.08)  # 8% standard deviation
        model_value = model_base * noise_factor
        
        # Correlate with actual value but add realistic model error
        # Blend actual value with model prediction to create realistic correlation
        correlation_factor = np.random.uniform(0.75, 0.90)  # 75-90% correlation
        predicted_value = actual_value * correlation_factor + model_value * (1 - correlation_factor)
        
        # Ensure predictions are positive and within reasonable bounds
        # Clip to 50% to 200% of actual value to avoid unrealistic predictions
        predicted_value = np.clip(predicted_value, actual_value * 0.5, actual_value * 2.0)
        
        # Round to nearest $100 for realistic house prices
        predicted_value = np.round(predicted_value / 100) * 100
        
        predicted_house_values.append(predicted_value)
    
    predicted_house_values = np.array(predicted_house_values)
    
    # Create the DataFrame with housing features
    df = df_train.copy()
    
    # Rename median_house_value to actual_house_value for clarity
    df = df.rename(columns={'median_house_value': 'actual_house_value'})
    
    # Update the actual values (in case of any processing)
    df['actual_house_value'] = actual_house_values.astype(float)
    
    # Add predicted house value
    df['predicted_house_value'] = predicted_house_values.astype(float)
    
    # Add metadata columns
    df['house_id'] = range(1, n_samples + 1)
    
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
    
    # Add timestamp column as datetime objects
    # Convert to UTC timezone-aware timestamps, then format as ISO strings for CSV
    utc_timestamps = [ts.replace(tzinfo=timezone.utc) for ts in timestamps]
    df['timestamp'] = pd.to_datetime(utc_timestamps)
    # Format timestamp as ISO string for CSV compatibility (YYYY-MM-DDTHH:MM:SS+00:00)
    df['timestamp'] = df['timestamp'].apply(lambda x: x.isoformat() if pd.notna(x) else None)
    
    # Ensure all integer columns are proper int64 (not object)
    int_cols = ['house_id', 'housing_median_age', 'total_rooms', 'total_bedrooms', 
                'population', 'households']
    for col in int_cols:
        if col in df.columns:
            # Handle NaN values by filling with 0, then convert to int
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')
    
    # Ensure string columns are strings
    str_cols = ['ocean_proximity']
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str)
    
    # Reorder columns for better readability
    column_order = ['timestamp', 'house_id', 'actual_house_value', 
                    'predicted_house_value', 'longitude', 'latitude', 'housing_median_age',
                    'total_rooms', 'total_bedrooms', 'population', 'households', 
                    'median_income', 'ocean_proximity']
    
    # Only include columns that exist
    column_order = [col for col in column_order if col in df.columns]
    # Add any remaining columns
    remaining_cols = [col for col in df.columns if col not in column_order]
    df = df[column_order + remaining_cols]
    
    # Save to CSV if output_dir is provided
    if output_dir is not None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Partition by date into separate CSV files
        files_created = []
        # Extract date from timestamp for partitioning
        df['_partition_date'] = pd.to_datetime(df['timestamp']).dt.date.astype(str)
        for partition_date, group_df in df.groupby('_partition_date'):
            # Create folder structure: YYYY-MM-DD/
            partition_dir = output_path / partition_date
            partition_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename: data-YYYY-MM-DD.csv
            partition_filename = f"data-{partition_date}.csv"
            output_file = partition_dir / partition_filename
            
            # Drop the temporary partition date column before saving
            group_df = group_df.drop(columns=['_partition_date'])
            
            # Save partitioned data
            group_df.to_csv(output_file, index=False)
            files_created.append(str(output_file))
        
        # Drop the temporary partition date column from the main dataframe
        df = df.drop(columns=['_partition_date'])
        
        print(f"Saved dataset to {len(files_created)} partitioned CSV files")
        print(f"Partition structure: {output_path}/YYYY-MM-DD/data-YYYY-MM-DD.csv")
    
    return df


if __name__ == '__main__':
    # Generate dataset with default settings (±90 days from today)
    input_csv = Path(__file__).parent.parent / 'housing.csv'
    output_dir = Path(__file__).parent / '../output'
    
    df = generate_dataset(input_csv_path=input_csv, output_dir=output_dir, past_days=90, future_days=90)
    
    print(f"\nHousing Price Prediction Dataset generated successfully!")
    print(f"Shape: {df.shape}")
    print(f"\nColumn descriptions:")
    print(f"- timestamp: Timestamp (ISO 8601 format string with UTC timezone)")
    print(f"- house_id: Unique identifier for each house")
    print(f"- actual_house_value: Ground truth median house value (continuous numeric)")
    print(f"- predicted_house_value: Model's predicted house value (continuous numeric)")
    print(f"- longitude: Longitude coordinate")
    print(f"- latitude: Latitude coordinate")
    print(f"- housing_median_age: Median age of houses in block")
    print(f"- total_rooms: Total number of rooms in block")
    print(f"- total_bedrooms: Total number of bedrooms in block")
    print(f"- population: Population in block")
    print(f"- households: Number of households in block")
    print(f"- median_income: Median income in block (tens of thousands)")
    print(f"- ocean_proximity: Proximity to ocean (NEAR BAY, INLAND, ISLAND, NEAR OCEAN, <1H OCEAN)")
    print(f"\nDataset statistics:")
    print(f"Mean actual house value: ${df['actual_house_value'].mean():,.2f}")
    print(f"Mean predicted house value: ${df['predicted_house_value'].mean():,.2f}")
    print(f"Mean absolute error: ${abs(df['actual_house_value'] - df['predicted_house_value']).mean():,.2f}")
    print(f"RMSE: ${np.sqrt(((df['actual_house_value'] - df['predicted_house_value']) ** 2).mean()):,.2f}")
    print(f"\nActual house value distribution:")
    print(f"  Min: ${df['actual_house_value'].min():,.2f}")
    print(f"  25th percentile: ${df['actual_house_value'].quantile(0.25):,.2f}")
    print(f"  Median: ${df['actual_house_value'].median():,.2f}")
    print(f"  75th percentile: ${df['actual_house_value'].quantile(0.75):,.2f}")
    print(f"  Max: ${df['actual_house_value'].max():,.2f}")
    print(f"\nPredicted house value distribution:")
    print(f"  Min: ${df['predicted_house_value'].min():,.2f}")
    print(f"  25th percentile: ${df['predicted_house_value'].quantile(0.25):,.2f}")
    print(f"  Median: ${df['predicted_house_value'].median():,.2f}")
    print(f"  75th percentile: ${df['predicted_house_value'].quantile(0.75):,.2f}")
    print(f"  Max: ${df['predicted_house_value'].max():,.2f}")
    print(f"\nOcean proximity distribution:\n{df['ocean_proximity'].value_counts().sort_index()}")
    # Extract dates from timestamps for statistics
    df_dates = pd.to_datetime(df['timestamp']).dt.date.astype(str)
    print(f"\nDate partitions: {df_dates.nunique()} unique dates")
    print(f"Date range: {df_dates.min()} to {df_dates.max()}")
    if output_dir is not None:
        print(f"\nSaved to: {output_dir}/YYYY-MM-DD/data-YYYY-MM-DD.csv")
