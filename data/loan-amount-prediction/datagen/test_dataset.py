import unittest
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, date
from generate_dataset import generate_dataset


class TestLoanAmountDatasetGeneration(unittest.TestCase):
    """Test suite for loan amount prediction dataset generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(__file__).parent / 'test_output'
        self.test_output_dir.mkdir(exist_ok=True)
        self.df = generate_dataset(n_samples=100, output_dir=None, seed=42)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove test output directory if it exists
        import shutil
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)
    
    def test_dataframe_shape(self):
        """Test that DataFrame has expected shape."""
        self.assertEqual(self.df.shape[0], 100)
        self.assertGreater(self.df.shape[1], 10)  # Should have many columns
    
    def test_required_columns(self):
        """Test that all required columns are present."""
        required_cols = [
            'partition_date', 'timestamp', 'loan_id', 'region',
            'actual_loan_amount', 'predicted_loan_amount',
            'credit_score', 'annual_income', 'age', 'employment_status',
            'years_at_job', 'debt_to_income_ratio', 'loan_purpose',
            'loan_term_months', 'years_credit_history', 'num_existing_loans'
        ]
        for col in required_cols:
            self.assertIn(col, self.df.columns, f"Missing required column: {col}")
    
    def test_actual_loan_amount_numeric(self):
        """Test that actual_loan_amount is continuous numeric."""
        self.assertTrue(pd.api.types.is_float_dtype(self.df['actual_loan_amount']))
        self.assertGreater(self.df['actual_loan_amount'].min(), 0)
        self.assertLessEqual(self.df['actual_loan_amount'].max(), 500000)
        self.assertGreaterEqual(self.df['actual_loan_amount'].min(), 5000)
    
    def test_predicted_loan_amount_numeric(self):
        """Test that predicted_loan_amount is continuous numeric."""
        self.assertTrue(pd.api.types.is_float_dtype(self.df['predicted_loan_amount']))
        self.assertGreater(self.df['predicted_loan_amount'].min(), 0)
        self.assertLessEqual(self.df['predicted_loan_amount'].max(), 500000)
        self.assertGreaterEqual(self.df['predicted_loan_amount'].min(), 5000)
    
    def test_loan_amounts_continuous(self):
        """Test that loan amounts are truly continuous (not just integers)."""
        # Check that we have non-integer values (continuous)
        actual_unique = self.df['actual_loan_amount'].nunique()
        predicted_unique = self.df['predicted_loan_amount'].nunique()
        # Should have many unique values (not just a few discrete values)
        self.assertGreater(actual_unique, 50)
        self.assertGreater(predicted_unique, 50)
    
    def test_timestamp_column(self):
        """Test that timestamp column is datetime type."""
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(self.df['timestamp']))
        # Check that timestamps are timezone-aware (UTC)
        sample_ts = self.df['timestamp'].iloc[0]
        self.assertIsNotNone(sample_ts.tzinfo)
    
    def test_partition_date_column(self):
        """Test that partition_date is date type."""
        # partition_date should be date objects, not datetime
        sample_date = self.df['partition_date'].iloc[0]
        self.assertIsInstance(sample_date, date)
        self.assertNotIsInstance(sample_date, datetime)
    
    def test_credit_score_range(self):
        """Test that credit scores are in valid range."""
        self.assertGreaterEqual(self.df['credit_score'].min(), 300)
        self.assertLessEqual(self.df['credit_score'].max(), 850)
    
    def test_annual_income_range(self):
        """Test that annual income is in valid range."""
        self.assertGreaterEqual(self.df['annual_income'].min(), 20000)
        self.assertLessEqual(self.df['annual_income'].max(), 200000)
    
    def test_age_range(self):
        """Test that age is in valid range."""
        self.assertGreaterEqual(self.df['age'].min(), 18)
        self.assertLessEqual(self.df['age'].max(), 75)
    
    def test_debt_to_income_range(self):
        """Test that debt-to-income ratio is in valid range."""
        self.assertGreaterEqual(self.df['debt_to_income_ratio'].min(), 0)
        self.assertLessEqual(self.df['debt_to_income_ratio'].max(), 0.8)
    
    def test_employment_status_values(self):
        """Test that employment status has valid values."""
        valid_statuses = ['Employed', 'Self-employed', 'Unemployed', 'Retired']
        self.assertTrue(self.df['employment_status'].isin(valid_statuses).all())
    
    def test_loan_purpose_values(self):
        """Test that loan purpose has valid values."""
        valid_purposes = ['Home Purchase', 'Debt Consolidation', 'Business', 'Education', 'Other']
        self.assertTrue(self.df['loan_purpose'].isin(valid_purposes).all())
    
    def test_loan_term_months_values(self):
        """Test that loan term months has valid values."""
        valid_terms = [12, 24, 36, 48, 60]
        self.assertTrue(self.df['loan_term_months'].isin(valid_terms).all())
    
    def test_unemployed_zero_years_at_job(self):
        """Test that unemployed/retired have 0 years at job."""
        unemployed = self.df[self.df['employment_status'].isin(['Unemployed', 'Retired'])]
        if len(unemployed) > 0:
            self.assertTrue((unemployed['years_at_job'] == 0).all())
    
    def test_json_serialization(self):
        """Test that DataFrame is JSON serializable."""
        # Test entire DataFrame
        try:
            test_record = self.df.iloc[0].to_dict()
            # Convert date/datetime objects to strings for JSON serialization
            for key, val in test_record.items():
                if isinstance(val, (pd.Timestamp, datetime)):
                    test_record[key] = val.isoformat()
                elif hasattr(val, 'isoformat'):  # date objects
                    test_record[key] = val.isoformat()
            json_str = json.dumps(test_record)
            self.assertIsInstance(json_str, str)
        except (TypeError, ValueError) as e:
            self.fail(f"DataFrame is not JSON serializable: {e}")
    
    def test_no_pandas_timestamps(self):
        """Test that there are no pandas Timestamp objects in date columns."""
        # partition_date should be date objects, not Timestamps
        for val in self.df['partition_date'].head(10):
            self.assertNotIsInstance(val, pd.Timestamp)
            self.assertIsInstance(val, date)
    
    def test_absolute_error_compatibility(self):
        """Test that dataset is compatible with Absolute Error metric."""
        # Both prediction and actual should be continuous numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(self.df['actual_loan_amount']))
        self.assertTrue(pd.api.types.is_numeric_dtype(self.df['predicted_loan_amount']))
        
        # Both should have non-null values
        self.assertFalse(self.df['actual_loan_amount'].isna().any())
        self.assertFalse(self.df['predicted_loan_amount'].isna().any())
        
        # Timestamp should be present
        self.assertFalse(self.df['timestamp'].isna().any())
        
        # Should be able to compute absolute error
        abs_error = abs(self.df['actual_loan_amount'] - self.df['predicted_loan_amount'])
        self.assertGreater(abs_error.mean(), 0)  # Should have some error
        self.assertLess(abs_error.mean(), 100000)  # But not too large
    
    def test_parquet_write_read(self):
        """Test that dataset can be written to and read from parquet."""
        import pyarrow.parquet as pq
        
        # Write to parquet
        test_file = self.test_output_dir / 'test.parquet'
        self.df.to_parquet(test_file, engine='pyarrow')
        
        # Read back
        df_read = pd.read_parquet(test_file)
        
        # Check that key columns are preserved
        self.assertIn('actual_loan_amount', df_read.columns)
        self.assertIn('predicted_loan_amount', df_read.columns)
        self.assertIn('timestamp', df_read.columns)
        
        # Check that numeric types are preserved
        self.assertTrue(pd.api.types.is_float_dtype(df_read['actual_loan_amount']))
        self.assertTrue(pd.api.types.is_float_dtype(df_read['predicted_loan_amount']))
    
    def test_reproducibility(self):
        """Test that dataset generation is reproducible with same seed."""
        df1 = generate_dataset(n_samples=50, output_dir=None, seed=42)
        df2 = generate_dataset(n_samples=50, output_dir=None, seed=42)
        
        # Check that actual and predicted loan amounts match
        pd.testing.assert_series_equal(
            df1['actual_loan_amount'], 
            df2['actual_loan_amount'],
            check_names=False
        )
        pd.testing.assert_series_equal(
            df1['predicted_loan_amount'], 
            df2['predicted_loan_amount'],
            check_names=False
        )
    
    def test_output_directory_creation(self):
        """Test that output directory is created when saving."""
        generate_dataset(n_samples=10, output_dir=self.test_output_dir, seed=42)
        
        # Check that output directory exists and has files
        self.assertTrue(self.test_output_dir.exists())
        
        # Check that parquet files were created (at least one partition)
        parquet_files = list(self.test_output_dir.rglob('*.parquet'))
        self.assertGreater(len(parquet_files), 0)
    
    def test_past_days_future_days_parameters(self):
        """Test that past_days and future_days parameters work correctly."""
        from datetime import datetime, timedelta
        
        # Generate with custom past_days and future_days
        df = generate_dataset(n_samples=50, output_dir=None, seed=42, past_days=7, future_days=7)
        
        # Verify date range
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        expected_start = today - timedelta(days=7)
        expected_end = today + timedelta(days=7)
        
        min_date = df['timestamp'].min().replace(tzinfo=None)
        max_date = df['timestamp'].max().replace(tzinfo=None)
        
        # Check that dates are within expected range (allow some variance due to random hour/minute)
        self.assertGreaterEqual(min_date.date(), expected_start.date())
        self.assertLessEqual(max_date.date(), expected_end.date())
        
        # Check that we have data spanning the expected number of days
        unique_dates = df['partition_date'].nunique()
        expected_days = 7 + 1 + 7  # past + today + future
        self.assertLessEqual(unique_dates, expected_days)
    
    def test_default_date_range(self):
        """Test that default date range uses ±90 days."""
        from datetime import datetime, timedelta
        
        # Generate with defaults (should use ±90 days)
        df = generate_dataset(n_samples=200, output_dir=None, seed=42)
        
        # Verify date range spans approximately 181 days (90 past + today + 90 future)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        expected_start = today - timedelta(days=90)
        expected_end = today + timedelta(days=90)
        
        min_date = df['timestamp'].min().replace(tzinfo=None)
        max_date = df['timestamp'].max().replace(tzinfo=None)
        
        # Check that dates are within expected range
        self.assertGreaterEqual(min_date.date(), expected_start.date())
        self.assertLessEqual(max_date.date(), expected_end.date())


if __name__ == '__main__':
    unittest.main()
