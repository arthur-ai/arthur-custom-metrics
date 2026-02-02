"""
Unit tests for the credit card application dataset to ensure JSON serialization compatibility
and data integrity. Tests validate the dataset structure, feature ranges, and business logic
for credit card application approval/rejection predictions.
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
import unittest
import tempfile
import shutil
import sys

# Import the generate_dataset function
sys.path.insert(0, str(Path(__file__).parent))
from generate_dataset import generate_dataset


class TestDatasetGeneration(unittest.TestCase):
    """Test suite for credit card application dataset generation, JSON serialization, and data integrity."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "model_predictions"
        
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_json_serialization_of_dataframe(self):
        """Test that the DataFrame can be serialized to JSON."""
        # Generate dataset to temp directory
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        # Test JSON serialization of entire DataFrame
        # Convert date/datetime objects to strings for JSON serialization
        try:
            records = df.to_dict('records')
            # Convert date/datetime objects to ISO format strings for JSON
            from datetime import date, datetime
            for record in records:
                for key, val in record.items():
                    if isinstance(val, (date, datetime, pd.Timestamp)):
                        record[key] = val.isoformat()
            json_str = json.dumps(records)
            self.assertIsInstance(json_str, str)
            self.assertGreater(len(json_str), 0)
        except TypeError as e:
            self.fail(f"DataFrame is not JSON serializable: {e}")
    
    def test_json_serialization_of_single_row(self):
        """Test that a single row can be serialized to JSON."""
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        # Test single row
        # Convert date/datetime objects to strings for JSON serialization
        from datetime import date, datetime
        row = df.iloc[0].to_dict()
        # Convert date/datetime objects to ISO format strings
        for key, val in row.items():
            if isinstance(val, (date, datetime, pd.Timestamp)):
                row[key] = val.isoformat()
        try:
            json_str = json.dumps(row)
            parsed = json.loads(json_str)
            self.assertIsInstance(parsed, dict)
        except TypeError as e:
            self.fail(f"Single row is not JSON serializable: {e}")
    
    def test_no_timestamp_objects(self):
        """Test that pandas Timestamp objects are only in the timestamp column."""
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        # timestamp column should have Timestamp objects, but other columns should not
        timestamp_columns = ['timestamp']
        
        # Check all columns for Timestamp objects (except timestamp column)
        for col in df.columns:
            if col not in timestamp_columns:
                for val in df[col].head(10):
                    if pd.notna(val):
                        self.assertNotIsInstance(
                            val, pd.Timestamp,
                            f"Column {col} contains Timestamp object: {val} (type: {type(val)})"
                        )
                        self.assertNotIsInstance(
                            val, (pd.Timedelta, pd.Period),
                            f"Column {col} contains pandas datetime object: {val} (type: {type(val)})"
                        )
    
    def test_date_objects_only_in_date_columns(self):
        """Test that date/datetime objects are only in partition_date and timestamp columns."""
        from datetime import date, datetime
        
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        # partition_date should have date objects, timestamp should have datetime objects
        date_columns = ['partition_date', 'timestamp']
        
        # Check that other columns don't have date/datetime objects
        for col in df.columns:
            if col not in date_columns:
                for val in df[col].head(10):
                    if pd.notna(val):
                        self.assertNotIsInstance(
                            val, (date, datetime),
                            f"Column {col} should not contain date/datetime object: {val} (type: {type(val)})"
                        )
    
    def test_date_is_date(self):
        """Test that partition_date column is date type."""
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        # partition_date should be date type (object dtype containing date objects)
        self.assertTrue(
            df['partition_date'].dtype == 'object',
            f"Partition date column should be object (date), got {df['partition_date'].dtype}"
        )
        
        # Check that values are date objects
        from datetime import date
        for val in df['partition_date'].head(10):
            self.assertIsInstance(val, date)
    
    def test_timestamp_format(self):
        """Test that timestamp column is datetime/timestamp type."""
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        # timestamp should be datetime64 type (timestamp type)
        self.assertTrue(
            pd.api.types.is_datetime64_any_dtype(df['timestamp']),
            f"Timestamp column should be datetime64 type, got {df['timestamp'].dtype}"
        )
        
        # Check that values are pandas Timestamp objects or datetime objects
        from datetime import datetime
        for val in df['timestamp'].head(10):
            self.assertTrue(
                isinstance(val, (pd.Timestamp, datetime)),
                f"Timestamp should be pd.Timestamp or datetime, got {type(val)}"
            )
            # Check that it's timezone-aware (UTC)
            if isinstance(val, pd.Timestamp):
                self.assertIsNotNone(
                    val.tz,
                    f"Timestamp should be timezone-aware (UTC), got timezone-naive"
                )
                self.assertEqual(
                    str(val.tz), 'UTC',
                    f"Timestamp should be UTC timezone, got {val.tz}"
                )
    
    def test_parquet_read_write_compatibility(self):
        """Test that parquet files can be read and are JSON serializable."""
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        # Read back from parquet
        df_read = pd.read_parquet(self.output_dir)
        
        # Test JSON serialization of read data
        # Convert date/datetime objects to strings for JSON serialization
        from datetime import date, datetime
        try:
            records = df_read.to_dict('records')
            # Convert date/datetime objects to ISO format strings
            for record in records:
                for key, val in record.items():
                    if isinstance(val, (date, datetime, pd.Timestamp)):
                        record[key] = val.isoformat()
            json_str = json.dumps(records)
            self.assertIsInstance(json_str, str)
        except TypeError as e:
            self.fail(f"Parquet-read data is not JSON serializable: {e}")
    
    def test_all_numpy_types_converted(self):
        """Test that all numpy types are converted to native Python types."""
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        # Convert to dict and check types
        row = df.iloc[0].to_dict()
        
        for key, val in row.items():
            if pd.notna(val):
                # Check that it's not a numpy scalar type that can't be JSON serialized
                if isinstance(val, (np.integer, np.floating)):
                    # These should be JSON serializable, but let's verify
                    try:
                        json.dumps({key: val})
                    except TypeError:
                        self.fail(f"Column {key} has non-JSON-serializable numpy type: {type(val)}")
                elif isinstance(val, np.ndarray):
                    self.fail(f"Column {key} contains numpy array: {val}")
    
    def test_data_structure(self):
        """Test that the dataset has the expected credit card application structure."""
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        expected_columns = [
            'partition_date', 'timestamp', 'application_id', 'region', 'actual_label',
            'predicted_label', 'predicted_probability', 'is_valid_application',
            'credit_score', 'annual_income', 'age', 'employment_status',
            'years_at_job', 'debt_to_income_ratio', 'num_credit_cards',
            'years_credit_history'
        ]
        
        self.assertEqual(list(df.columns), expected_columns)
        self.assertEqual(len(df), 100)
    
    def test_data_ranges(self):
        """Test that credit card application data values are in expected ranges."""
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        # Test label ranges (1=Approved, 0=Rejected)
        self.assertTrue(df['actual_label'].isin([0, 1]).all())
        self.assertTrue(df['predicted_label'].isin([0, 1]).all())
        self.assertTrue(df['is_valid_application'].isin([0, 1]).all())
        
        # Test probability range
        self.assertTrue((df['predicted_probability'] >= 0).all())
        self.assertTrue((df['predicted_probability'] <= 1).all())
        
        # Test credit score range (300-850)
        self.assertTrue((df['credit_score'] >= 300).all())
        self.assertTrue((df['credit_score'] <= 850).all())
        
        # Test annual income range (reasonable bounds)
        self.assertTrue((df['annual_income'] >= 20000).all())
        self.assertTrue((df['annual_income'] <= 200000).all())
        
        # Test age range (18-75)
        self.assertTrue((df['age'] >= 18).all())
        self.assertTrue((df['age'] <= 75).all())
        
        # Test debt-to-income ratio (0-0.8)
        self.assertTrue((df['debt_to_income_ratio'] >= 0).all())
        self.assertTrue((df['debt_to_income_ratio'] <= 0.8).all())
        
        # Test years at job (0-40)
        self.assertTrue((df['years_at_job'] >= 0).all())
        self.assertTrue((df['years_at_job'] <= 40).all())
        
        # Test number of credit cards (0-10)
        self.assertTrue((df['num_credit_cards'] >= 0).all())
        self.assertTrue((df['num_credit_cards'] <= 10).all())
        
        # Test years of credit history (0-50)
        self.assertTrue((df['years_credit_history'] >= 0).all())
        self.assertTrue((df['years_credit_history'] <= 50).all())
        
        # Test employment status values
        valid_employment = ['Employed', 'Self-employed', 'Unemployed', 'Retired']
        self.assertTrue(df['employment_status'].isin(valid_employment).all())
        
        # Test region values
        valid_regions = ['Region_North', 'Region_South', 'Region_East', 'Region_West']
        self.assertTrue(df['region'].isin(valid_regions).all())
    
    def test_credit_card_business_logic(self):
        """Test credit card application business logic constraints."""
        df = generate_dataset(n_samples=100, output_dir=self.output_dir)
        
        # Unemployed and Retired should have 0 years at job
        unemployed_retired = df[df['employment_status'].isin(['Unemployed', 'Retired'])]
        if len(unemployed_retired) > 0:
            all_zero = (unemployed_retired['years_at_job'] == 0).all()
            self.assertTrue(
                bool(all_zero),  # Convert numpy bool to Python bool
                "Unemployed and Retired applicants should have 0 years at job"
            )
        
        # Years of credit history should be reasonable relative to age
        # Credit history can be up to age - 18, but with some variance (normal distribution with std=3)
        # So we allow up to age - 18 + 10 (3 standard deviations) as reasonable
        df['max_possible_history'] = df['age'] - 18 + 10
        is_reasonable = (df['years_credit_history'] <= df['max_possible_history']).all()
        self.assertTrue(
            bool(is_reasonable),  # Convert numpy bool to Python bool
            f"Years of credit history should be reasonable relative to age. "
            f"Found {df[df['years_credit_history'] > df['max_possible_history']].shape[0]} cases exceeding limit"
        )
        
        # Approval rate should be reasonable (not all approved or all rejected)
        approval_rate = df['actual_label'].mean()
        self.assertGreater(approval_rate, 0.05, "Approval rate should be at least 5%")
        self.assertLess(approval_rate, 0.95, "Approval rate should be at most 95%")
    
    def test_past_days_future_days_parameters(self):
        """Test that past_days and future_days parameters work correctly."""
        from datetime import datetime, timedelta
        
        # Generate with custom past_days and future_days
        df = generate_dataset(n_samples=50, output_dir=self.output_dir, seed=42, past_days=7, future_days=7)
        
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
        df = generate_dataset(n_samples=200, output_dir=self.output_dir, seed=42)
        
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
