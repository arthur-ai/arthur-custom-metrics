import unittest
import json
from pathlib import Path
from generate_dataset import generate_dataset


class TestCardFraudDatasetGeneration(unittest.TestCase):
    """Test suite for card fraud dataset generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_output_dir = Path(__file__).parent / 'test_output'
        self.test_output_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)
    
    def test_generate_dataset(self):
        """Test that dataset generation works."""
        stats = generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=60,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        self.assertGreater(stats['total_transactions'], 0)
        self.assertGreater(stats['total_fraud'], 0)
        self.assertGreater(stats['files_created'], 0)
        self.assertGreater(stats['fraud_rate'], 0)
        self.assertLess(stats['fraud_rate'], 0.15)  # Should be reasonable (5-10%)
    
    def test_json_file_structure(self):
        """Test that generated JSON files have correct structure."""
        generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=10,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        # Find a generated file
        file_path = self.test_output_dir / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        self.assertTrue(file_path.exists(), f"File not found: {file_path}")
        
        # Load and verify structure
        with open(file_path, 'r') as f:
            transactions = json.load(f)
        
        self.assertIsInstance(transactions, list)
        self.assertEqual(len(transactions), 10)  # 10 transactions per hour
        
        # Verify first transaction has all required fields
        required_fields = [
            'timestamp', 'txn_id', 'account_id', 'customer_id',
            'is_fraud', 'fraud_score', 'fraud_pred', 'rules_engine_flag',
            'risk_rank', 'customer_segment', 'channel', 'region',
            'txn_amount', 'distance_from_home_km', 'merchant_risk_score',
            'digital_engagement', 'tenure_months'
        ]
        
        txn = transactions[0]
        for field in required_fields:
            self.assertIn(field, txn, f"Missing field: {field}")
    
    def test_transaction_field_types(self):
        """Test that transaction fields have correct types."""
        generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=5,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        file_path = self.test_output_dir / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        with open(file_path, 'r') as f:
            transactions = json.load(f)
        
        txn = transactions[0]
        
        # Check types
        self.assertIsInstance(txn['timestamp'], str)
        self.assertIsInstance(txn['txn_id'], str)
        self.assertIsInstance(txn['account_id'], str)
        self.assertIsInstance(txn['customer_id'], str)
        self.assertIn(txn['is_fraud'], [0, 1])
        self.assertIsInstance(txn['fraud_score'], (int, float))
        self.assertGreaterEqual(txn['fraud_score'], 0.0)
        self.assertLessEqual(txn['fraud_score'], 1.0)
        self.assertIn(txn['fraud_pred'], [0, 1])
        self.assertIn(txn['rules_engine_flag'], [0, 1])
        self.assertIn(txn['risk_rank'], [1, 2, 3, 4, 5])
        self.assertIsInstance(txn['customer_segment'], str)
        self.assertIsInstance(txn['channel'], str)
        self.assertIsInstance(txn['region'], str)
        self.assertIsInstance(txn['txn_amount'], (int, float))
        self.assertIsInstance(txn['distance_from_home_km'], (int, float))
        self.assertIsInstance(txn['merchant_risk_score'], (int, float))
        self.assertIsInstance(txn['digital_engagement'], (int, float))
        self.assertIsInstance(txn['tenure_months'], int)
    
    def test_customer_segment_values(self):
        """Test that customer_segment has valid values."""
        generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=20,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        file_path = self.test_output_dir / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        with open(file_path, 'r') as f:
            transactions = json.load(f)
        
        valid_segments = ['new_to_bank', 'established', 'small_business']
        for txn in transactions:
            self.assertIn(txn['customer_segment'], valid_segments)
    
    def test_channel_values(self):
        """Test that channel has valid values."""
        generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=20,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        file_path = self.test_output_dir / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        with open(file_path, 'r') as f:
            transactions = json.load(f)
        
        valid_channels = ['ecom', 'in_store', 'atm']
        for txn in transactions:
            self.assertIn(txn['channel'], valid_channels)
    
    def test_region_values(self):
        """Test that region has valid values."""
        generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=20,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        file_path = self.test_output_dir / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        with open(file_path, 'r') as f:
            transactions = json.load(f)
        
        valid_regions = ['W', 'NE', 'MW', 'S']
        for txn in transactions:
            self.assertIn(txn['region'], valid_regions)
    
    def test_fraud_score_range(self):
        """Test that fraud_score is in valid range."""
        generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=20,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        file_path = self.test_output_dir / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        with open(file_path, 'r') as f:
            transactions = json.load(f)
        
        for txn in transactions:
            self.assertGreaterEqual(txn['fraud_score'], 0.0)
            self.assertLessEqual(txn['fraud_score'], 1.0)
    
    def test_fraud_pred_matches_fraud_score(self):
        """Test that fraud_pred is consistent with fraud_score threshold."""
        generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=20,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        file_path = self.test_output_dir / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        with open(file_path, 'r') as f:
            transactions = json.load(f)
        
        for txn in transactions:
            expected_pred = 1 if txn['fraud_score'] >= 0.5 else 0
            self.assertEqual(txn['fraud_pred'], expected_pred,
                           f"fraud_pred should match fraud_score threshold (0.5)")
    
    def test_risk_rank_calculation(self):
        """Test that risk_rank is calculated correctly from fraud_score."""
        generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=20,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        file_path = self.test_output_dir / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        with open(file_path, 'r') as f:
            transactions = json.load(f)
        
        for txn in transactions:
            score = txn['fraud_score']
            rank = txn['risk_rank']
            
            if score < 0.1:
                self.assertEqual(rank, 1)
            elif score < 0.2:
                self.assertEqual(rank, 2)
            elif score < 0.4:
                self.assertEqual(rank, 3)
            elif score < 0.6:
                self.assertEqual(rank, 4)
            else:
                self.assertEqual(rank, 5)
    
    def test_txn_amount_range(self):
        """Test that transaction amounts are in reasonable range."""
        generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=20,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        file_path = self.test_output_dir / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        with open(file_path, 'r') as f:
            transactions = json.load(f)
        
        for txn in transactions:
            self.assertGreaterEqual(txn['txn_amount'], 1.0)
            self.assertLessEqual(txn['txn_amount'], 10000.0)
    
    def test_reproducibility(self):
        """Test that dataset generation is reproducible with same seed."""
        # Generate twice with same seed
        stats1 = generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=10,
            output_dir=self.test_output_dir / "run1",
            seed=42
        )
        
        stats2 = generate_dataset(
            start_date="2025-11-01",
            end_date="2025-11-01",
            transactions_per_hour=10,
            output_dir=self.test_output_dir / "run2",
            seed=42
        )
        
        # Should have same statistics
        self.assertEqual(stats1['total_transactions'], stats2['total_transactions'])
        self.assertEqual(stats1['total_fraud'], stats2['total_fraud'])
        
        # Should have same transaction IDs
        file1 = self.test_output_dir / "run1" / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        file2 = self.test_output_dir / "run2" / "year=2025" / "month=11" / "day=01" / "inferences_hour=00.json"
        
        with open(file1, 'r') as f:
            txn1 = json.load(f)
        with open(file2, 'r') as f:
            txn2 = json.load(f)
        
        # Transaction IDs should match
        ids1 = [t['txn_id'] for t in txn1]
        ids2 = [t['txn_id'] for t in txn2]
        self.assertEqual(ids1, ids2)
    
    def test_past_days_future_days_parameters(self):
        """Test that past_days and future_days parameters work correctly."""
        from datetime import datetime, timedelta
        
        # Generate with custom past_days and future_days
        stats = generate_dataset(
            past_days=7,
            future_days=7,
            transactions_per_hour=10,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        # Verify date range
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        expected_start = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        expected_end = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        
        self.assertIn(expected_start, stats['date_range'])
        self.assertIn(expected_end, stats['date_range'])
        self.assertGreater(stats['total_transactions'], 0)
    
    def test_default_date_range(self):
        """Test that default date range uses ±90 days."""
        from datetime import datetime, timedelta
        
        # Generate with defaults (should use ±90 days)
        stats = generate_dataset(
            transactions_per_hour=10,
            output_dir=self.test_output_dir,
            seed=42
        )
        
        # Verify date range spans approximately 181 days (90 past + today + 90 future)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        expected_start = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        expected_end = (today + timedelta(days=90)).strftime("%Y-%m-%d")
        
        self.assertIn(expected_start, stats['date_range'])
        self.assertIn(expected_end, stats['date_range'])


if __name__ == '__main__':
    unittest.main()
