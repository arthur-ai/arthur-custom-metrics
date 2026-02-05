import unittest
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from generate_dataset import generate_dataset


class TestHousingDatasetGeneration(unittest.TestCase):
    """Test suite for housing price prediction dataset generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(__file__).parent / 'test_output'
        self.test_output_dir.mkdir(exist_ok=True)
        # Use a small sample for faster tests
        self.input_csv = Path(__file__).parent.parent / 'housing.csv'
        # Verify input file exists
        if not self.input_csv.exists():
            self.skipTest(f"Input CSV file not found: {self.input_csv}")
        # Generate a small dataset for testing (use first 100 rows of input)
        self.df = generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=None,
            seed=42
        )
        # Limit to first 100 rows for faster tests
        self.df = self.df.head(100)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)
    
    def test_dataframe_shape(self):
        """Test that DataFrame has expected shape."""
        self.assertGreater(self.df.shape[0], 0)
        self.assertGreater(self.df.shape[1], 10)  # Should have many columns
    
    def test_required_columns(self):
        """Test that all required columns are present."""
        required_cols = [
            'partition_date', 'timestamp', 'house_id',
            'actual_house_value', 'predicted_house_value',
            'longitude', 'latitude', 'housing_median_age',
            'total_rooms', 'total_bedrooms', 'population',
            'households', 'median_income', 'ocean_proximity'
        ]
        for col in required_cols:
            self.assertIn(col, self.df.columns, f"Missing required column: {col}")
    
    def test_actual_house_value_numeric(self):
        """Test that actual_house_value is continuous numeric."""
        self.assertTrue(pd.api.types.is_float_dtype(self.df['actual_house_value']))
        self.assertGreater(self.df['actual_house_value'].min(), 0)
        # Check reasonable range (California housing prices)
        self.assertGreater(self.df['actual_house_value'].min(), 10000)
        self.assertLess(self.df['actual_house_value'].max(), 1000000)
    
    def test_predicted_house_value_numeric(self):
        """Test that predicted_house_value is continuous numeric."""
        self.assertTrue(pd.api.types.is_float_dtype(self.df['predicted_house_value']))
        self.assertGreater(self.df['predicted_house_value'].min(), 0)
        # Check reasonable range
        self.assertGreater(self.df['predicted_house_value'].min(), 10000)
        self.assertLess(self.df['predicted_house_value'].max(), 1000000)
    
    def test_house_values_continuous(self):
        """Test that house values are truly continuous (not just integers)."""
        # Check that we have many unique values (continuous)
        actual_unique = self.df['actual_house_value'].nunique()
        predicted_unique = self.df['predicted_house_value'].nunique()
        # Should have many unique values (not just a few discrete values)
        self.assertGreater(actual_unique, 10)
        self.assertGreater(predicted_unique, 10)
    
    def test_timestamp_column_format(self):
        """Test that timestamp column is ISO format string."""
        # Timestamp should be string (ISO format) for CSV
        self.assertTrue(pd.api.types.is_string_dtype(self.df['timestamp']))
        
        # Check ISO format (YYYY-MM-DDTHH:MM:SS+00:00 or similar)
        sample_ts = self.df['timestamp'].iloc[0]
        self.assertIsInstance(sample_ts, str)
        # Should contain 'T' separator and timezone info
        self.assertIn('T', sample_ts)
        
        # Should be parseable as datetime
        parsed_ts = pd.to_datetime(sample_ts)
        self.assertIsNotNone(parsed_ts)
    
    def test_partition_date_column(self):
        """Test that partition_date is string format."""
        # partition_date should be string (YYYY-MM-DD format) for CSV
        self.assertTrue(pd.api.types.is_string_dtype(self.df['partition_date']))
        
        # Check format
        sample_date = self.df['partition_date'].iloc[0]
        self.assertIsInstance(sample_date, str)
        # Should be parseable as date
        parsed_date = pd.to_datetime(sample_date)
        self.assertIsNotNone(parsed_date)
    
    def test_house_id_unique(self):
        """Test that house_id is unique and sequential."""
        self.assertTrue(self.df['house_id'].is_unique)
        self.assertEqual(self.df['house_id'].min(), 1)
        self.assertEqual(self.df['house_id'].dtype, 'int64')
    
    def test_longitude_range(self):
        """Test that longitude is in valid range for California."""
        # California longitude range: approximately -124 to -114
        self.assertGreaterEqual(self.df['longitude'].min(), -125)
        self.assertLessEqual(self.df['longitude'].max(), -114)
    
    def test_latitude_range(self):
        """Test that latitude is in valid range for California."""
        # California latitude range: approximately 32 to 42
        self.assertGreaterEqual(self.df['latitude'].min(), 32)
        self.assertLessEqual(self.df['latitude'].max(), 42)
    
    def test_housing_median_age_range(self):
        """Test that housing_median_age is in valid range."""
        self.assertGreaterEqual(self.df['housing_median_age'].min(), 1)
        self.assertLessEqual(self.df['housing_median_age'].max(), 52)
        self.assertEqual(self.df['housing_median_age'].dtype, 'int64')
    
    def test_total_rooms_range(self):
        """Test that total_rooms is in valid range."""
        self.assertGreaterEqual(self.df['total_rooms'].min(), 0)
        self.assertLess(self.df['total_rooms'].max(), 50000)
        self.assertEqual(self.df['total_rooms'].dtype, 'int64')
    
    def test_total_bedrooms_range(self):
        """Test that total_bedrooms is in valid range."""
        self.assertGreaterEqual(self.df['total_bedrooms'].min(), 0)
        self.assertLess(self.df['total_bedrooms'].max(), 10000)
        self.assertEqual(self.df['total_bedrooms'].dtype, 'int64')
    
    def test_population_range(self):
        """Test that population is in valid range."""
        self.assertGreaterEqual(self.df['population'].min(), 0)
        self.assertLess(self.df['population'].max(), 50000)
        self.assertEqual(self.df['population'].dtype, 'int64')
    
    def test_households_range(self):
        """Test that households is in valid range."""
        self.assertGreaterEqual(self.df['households'].min(), 0)
        self.assertLess(self.df['households'].max(), 10000)
        self.assertEqual(self.df['households'].dtype, 'int64')
    
    def test_median_income_range(self):
        """Test that median_income is in valid range."""
        self.assertGreaterEqual(self.df['median_income'].min(), 0)
        self.assertLessEqual(self.df['median_income'].max(), 16)
        self.assertTrue(pd.api.types.is_float_dtype(self.df['median_income']))
    
    def test_ocean_proximity_values(self):
        """Test that ocean_proximity has valid values."""
        valid_proximities = ['NEAR BAY', 'INLAND', 'ISLAND', 'NEAR OCEAN', '<1H OCEAN']
        self.assertTrue(self.df['ocean_proximity'].isin(valid_proximities).all())
        self.assertTrue(pd.api.types.is_string_dtype(self.df['ocean_proximity']))
    
    def test_no_null_values_in_key_columns(self):
        """Test that key columns have no null values."""
        key_cols = [
            'timestamp', 'house_id', 'actual_house_value',
            'predicted_house_value', 'longitude', 'latitude'
        ]
        for col in key_cols:
            self.assertFalse(
                self.df[col].isna().any(),
                f"Column {col} contains null values"
            )
    
    def test_json_serialization(self):
        """Test that DataFrame is JSON serializable (for CSV compatibility)."""
        try:
            test_record = self.df.iloc[0].to_dict()
            # All values should be JSON serializable (strings, numbers, etc.)
            json_str = json.dumps(test_record)
            self.assertIsInstance(json_str, str)
        except (TypeError, ValueError) as e:
            self.fail(f"DataFrame is not JSON serializable: {e}")
    
    def test_absolute_error_compatibility(self):
        """Test that dataset is compatible with Absolute Error metric."""
        # Both prediction and actual should be continuous numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(self.df['actual_house_value']))
        self.assertTrue(pd.api.types.is_numeric_dtype(self.df['predicted_house_value']))
        
        # Both should have non-null values
        self.assertFalse(self.df['actual_house_value'].isna().any())
        self.assertFalse(self.df['predicted_house_value'].isna().any())
        
        # Timestamp should be present
        self.assertFalse(self.df['timestamp'].isna().any())
        
        # Should be able to compute absolute error
        abs_error = abs(self.df['actual_house_value'] - self.df['predicted_house_value'])
        self.assertGreater(abs_error.mean(), 0)  # Should have some error
        self.assertLess(abs_error.mean(), 500000)  # But not too large (reasonable for house prices)
    
    def test_ppe_threshold_compatibility(self):
        """Test that dataset is compatible with PPE threshold metric."""
        # Actual values should be non-zero (to avoid division by zero in PPE calculation)
        self.assertTrue((self.df['actual_house_value'] != 0).all())
        
        # Should be able to compute percentage prediction error
        ppe = abs(self.df['actual_house_value'] - self.df['predicted_house_value']) / self.df['actual_house_value']
        self.assertGreater(ppe.mean(), 0)  # Should have some error
        self.assertLess(ppe.mean(), 1.0)  # But not more than 100% error
    
    def test_csv_write_read(self):
        """Test that dataset can be written to and read from partitioned CSV files."""
        # Generate and save partitioned CSV files
        generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=self.test_output_dir,
            seed=42,
            past_days=7,
            future_days=7
        )
        
        # Find all CSV files
        csv_files = list(self.test_output_dir.rglob('data-*.csv'))
        self.assertGreater(len(csv_files), 0)
        
        # Read one partition
        df_read = pd.read_csv(csv_files[0])
        
        # Check that key columns are preserved
        self.assertIn('actual_house_value', df_read.columns)
        self.assertIn('predicted_house_value', df_read.columns)
        self.assertIn('timestamp', df_read.columns)
        self.assertIn('partition_date', df_read.columns)
        
        # Check that numeric types are preserved
        self.assertTrue(pd.api.types.is_numeric_dtype(df_read['actual_house_value']))
        self.assertTrue(pd.api.types.is_numeric_dtype(df_read['predicted_house_value']))
        
        # Check that timestamp can be parsed
        df_read['timestamp'] = pd.to_datetime(df_read['timestamp'])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df_read['timestamp']))
        
        # Check that partition_date matches folder name
        folder_name = csv_files[0].parent.name
        self.assertEqual(df_read['partition_date'].iloc[0], folder_name)
    
    def test_reproducibility(self):
        """Test that dataset generation is reproducible with same seed."""
        df1 = generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=None,
            seed=42
        ).head(50)
        
        df2 = generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=None,
            seed=42
        ).head(50)
        
        # Check that actual and predicted house values match
        pd.testing.assert_series_equal(
            df1['actual_house_value'],
            df2['actual_house_value'],
            check_names=False
        )
        pd.testing.assert_series_equal(
            df1['predicted_house_value'],
            df2['predicted_house_value'],
            check_names=False
        )
    
    def test_output_directory_creation(self):
        """Test that output directory is created when saving."""
        generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        # Check that output directory exists
        self.assertTrue(self.test_output_dir.exists())
        
        # Check that partitioned CSV files were created
        csv_files = list(self.test_output_dir.rglob('data-*.csv'))
        self.assertGreater(len(csv_files), 0)
        
        # Check that at least one file is readable
        df_read = pd.read_csv(csv_files[0])
        self.assertGreater(len(df_read), 0)
        
        # Check folder structure (YYYY-MM-DD/data-YYYY-MM-DD.csv)
        for csv_file in csv_files:
            # File should be in a date folder
            date_folder = csv_file.parent
            self.assertTrue(date_folder.name.count('-') == 2)  # Should be YYYY-MM-DD format
            # Filename should match folder name
            expected_filename = f"data-{date_folder.name}.csv"
            self.assertEqual(csv_file.name, expected_filename)
    
    def test_past_days_future_days_parameters(self):
        """Test that past_days and future_days parameters work correctly."""
        # Generate with custom past_days and future_days
        df = generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=None,
            seed=42,
            past_days=7,
            future_days=7
        )
        
        # Convert timestamp strings to datetime
        df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
        
        # Verify date range
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        expected_start = today - timedelta(days=7)
        expected_end = today + timedelta(days=7)
        
        min_date = df['timestamp_dt'].min().replace(tzinfo=None)
        max_date = df['timestamp_dt'].max().replace(tzinfo=None)
        
        # Check that dates are within expected range (allow some variance due to random hour/minute)
        self.assertGreaterEqual(min_date.date(), expected_start.date())
        self.assertLessEqual(max_date.date(), expected_end.date())
    
    def test_default_date_range(self):
        """Test that default date range uses ±90 days."""
        # Generate with defaults (should use ±90 days)
        df = generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=None,
            seed=42
        )
        
        # Convert timestamp strings to datetime
        df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
        
        # Verify date range spans approximately 181 days (90 past + today + 90 future)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        expected_start = today - timedelta(days=90)
        expected_end = today + timedelta(days=90)
        
        min_date = df['timestamp_dt'].min().replace(tzinfo=None)
        max_date = df['timestamp_dt'].max().replace(tzinfo=None)
        
        # Check that dates are within expected range
        self.assertGreaterEqual(min_date.date(), expected_start.date())
        self.assertLessEqual(max_date.date(), expected_end.date())
    
    def test_prediction_correlation(self):
        """Test that predictions are correlated with actual values."""
        # Predictions should be correlated with actual values (not random)
        correlation = self.df['actual_house_value'].corr(self.df['predicted_house_value'])
        self.assertGreater(correlation, 0.5)  # Should have reasonable correlation
        self.assertLess(correlation, 1.0)  # But not perfect (realistic model error)
    
    def test_prediction_error_distribution(self):
        """Test that prediction errors are realistic."""
        abs_error = abs(self.df['actual_house_value'] - self.df['predicted_house_value'])
        relative_error = abs_error / self.df['actual_house_value']
        
        # Mean relative error should be reasonable (5-20% is typical for house price models)
        mean_relative_error = relative_error.mean()
        self.assertGreater(mean_relative_error, 0.01)  # At least 1% error
        self.assertLess(mean_relative_error, 0.5)  # But not more than 50% error
    
    def test_partitioned_output_structure(self):
        """Test that output is partitioned by date into YYYY-MM-DD folders."""
        generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=self.test_output_dir,
            seed=42,
            past_days=7,
            future_days=7
        )
        
        # Check that partitioned folders exist
        date_folders = [d for d in self.test_output_dir.iterdir() if d.is_dir()]
        self.assertGreater(len(date_folders), 0)
        
        # Check that each folder has the correct format (YYYY-MM-DD)
        for folder in date_folders:
            folder_name = folder.name
            # Should match YYYY-MM-DD format
            self.assertRegex(folder_name, r'^\d{4}-\d{2}-\d{2}$')
            
            # Should contain a data file
            data_file = folder / f"data-{folder_name}.csv"
            self.assertTrue(data_file.exists(), f"Data file not found: {data_file}")
            
            # File should be readable
            df = pd.read_csv(data_file)
            self.assertGreater(len(df), 0)
            
            # All records in this partition should have the same partition_date
            self.assertTrue((df['partition_date'] == folder_name).all(),
                          f"Partition date mismatch in {folder_name}")
    
    def test_input_csv_path_parameter(self):
        """Test that custom input_csv_path parameter works."""
        # Should work with explicit path
        df = generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=None,
            seed=42
        )
        self.assertGreater(len(df), 0)
        self.assertIn('actual_house_value', df.columns)
    
    def test_partition_date_matches_folder(self):
        """Test that partition_date in CSV matches the folder name."""
        generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=self.test_output_dir,
            seed=42,
            past_days=7,
            future_days=7
        )
        
        # Check all partitions
        csv_files = list(self.test_output_dir.rglob('data-*.csv'))
        for csv_file in csv_files:
            folder_name = csv_file.parent.name
            df = pd.read_csv(csv_file)
            
            # All partition_date values should match folder name
            self.assertTrue((df['partition_date'] == folder_name).all(),
                          f"Partition date mismatch: folder={folder_name}, "
                          f"data={df['partition_date'].unique()}")
    
    def test_all_partitions_readable(self):
        """Test that all partitioned CSV files can be read and combined."""
        generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=self.test_output_dir,
            seed=42,
            past_days=7,
            future_days=7
        )
        
        # Read all partitions
        csv_files = list(self.test_output_dir.rglob('data-*.csv'))
        self.assertGreater(len(csv_files), 0)
        
        dfs = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            dfs.append(df)
        
        # Combine all partitions
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Should have all expected columns
        required_cols = ['partition_date', 'timestamp', 'house_id',
                        'actual_house_value', 'predicted_house_value']
        for col in required_cols:
            self.assertIn(col, combined_df.columns)
        
        # Should have data from multiple dates
        unique_dates = combined_df['partition_date'].nunique()
        self.assertGreater(unique_dates, 1)
        
        # All house_ids should be unique across partitions
        self.assertTrue(combined_df['house_id'].is_unique)
    
    def test_date_range_coverage(self):
        """Test that generated data covers the full ±90 day range by default."""
        df = generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=None,
            seed=42
        )
        
        # Convert partition_date to datetime for comparison
        df['partition_date_dt'] = pd.to_datetime(df['partition_date'])
        
        # Get unique dates
        unique_dates = df['partition_date_dt'].dt.date.unique()
        
        # Should span approximately 181 days (90 past + today + 90 future)
        date_range = (max(unique_dates) - min(unique_dates)).days
        self.assertGreaterEqual(date_range, 170)  # Allow some variance
        self.assertLessEqual(date_range, 181)  # Should not exceed 181 days
        
        # Verify dates are within ±90 days
        today = datetime.now().date()
        min_date = min(unique_dates)
        max_date = max(unique_dates)
        
        days_before_today = (today - min_date).days
        days_after_today = (max_date - today).days
        
        self.assertLessEqual(days_before_today, 90)
        self.assertLessEqual(days_after_today, 90)
    
    def test_no_output_directory(self):
        """Test that function works when output_dir is None."""
        df = generate_dataset(
            input_csv_path=self.input_csv,
            output_dir=None,
            seed=42
        )
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        # Should not create any output files
        csv_files = list(self.test_output_dir.rglob('*.csv'))
        self.assertEqual(len(csv_files), 0)


if __name__ == '__main__':
    unittest.main()
