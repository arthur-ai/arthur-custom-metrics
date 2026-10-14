import unittest
import shutil
from pathlib import Path

import pandas as pd

from generate_dataset import generate_dataset, generate_reference_dataset, SLATE_SIZE, CATALOG_SIZE


class TestRankingDatasetGeneration(unittest.TestCase):
    """Test suite for the recommendation / ads ranking dataset generator."""

    def setUp(self):
        self.test_output_dir = Path(__file__).parent / 'test_output'
        self.test_output_dir.mkdir(exist_ok=True)

    def tearDown(self):
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)

    def test_generate_dataset(self):
        stats = generate_dataset(
            start_date='2026-01-01',
            end_date='2026-01-01',
            requests_per_hour=5,
            output_dir=self.test_output_dir,
            seed=42,
        )
        self.assertEqual(stats['total_requests'], 24 * 5)
        self.assertEqual(stats['total_impressions'], 24 * 5 * SLATE_SIZE)
        self.assertGreater(stats['total_clicks'], 0)
        self.assertGreater(stats['click_rate'], 0.03)
        self.assertLess(stats['click_rate'], 0.25)
        self.assertEqual(stats['files_created'], 1)

    def test_parquet_structure(self):
        generate_dataset(
            start_date='2026-01-01',
            end_date='2026-01-02',
            requests_per_hour=3,
            output_dir=self.test_output_dir,
            seed=42,
        )
        file_path = self.test_output_dir / '2026-01-01' / 'data-2026-01-01.parquet'
        self.assertTrue(file_path.exists(), f'File not found: {file_path}')

        df = pd.read_parquet(file_path)
        required_columns = [
            'timestamp', 'request_id', 'impression_id', 'user_id', 'user_segment',
            'placement', 'device', 'model_version', 'slate_size', 'position',
            'item_id', 'item_category', 'predicted_score', 'clicked', 'converted',
            'relevance_grade', 'revenue',
        ]
        for col in required_columns:
            self.assertIn(col, df.columns, f'Missing column: {col}')
        self.assertEqual(len(df), 24 * 3 * SLATE_SIZE)

    def test_slate_integrity(self):
        generate_dataset(
            start_date='2026-01-01',
            end_date='2026-01-01',
            requests_per_hour=10,
            output_dir=self.test_output_dir,
            seed=7,
        )
        df = pd.read_parquet(self.test_output_dir)

        # Every request has exactly SLATE_SIZE rows with positions 1..SLATE_SIZE
        per_request = df.groupby('request_id')['position'].agg(['count', 'min', 'max', 'nunique'])
        self.assertTrue((per_request['count'] == SLATE_SIZE).all())
        self.assertTrue((per_request['min'] == 1).all())
        self.assertTrue((per_request['max'] == SLATE_SIZE).all())
        self.assertTrue((per_request['nunique'] == SLATE_SIZE).all())

        # No item repeats inside a slate
        self.assertTrue((df.groupby('request_id')['item_id'].nunique() == SLATE_SIZE).all())

        # Impression IDs are unique; item IDs come from the catalog
        self.assertEqual(df['impression_id'].nunique(), len(df))
        self.assertLessEqual(df['item_id'].nunique(), CATALOG_SIZE)

    def test_label_consistency(self):
        generate_dataset(
            start_date='2026-01-01',
            end_date='2026-01-01',
            requests_per_hour=10,
            output_dir=self.test_output_dir,
            seed=3,
        )
        df = pd.read_parquet(self.test_output_dir)

        self.assertTrue(df['predicted_score'].between(0, 1).all())
        self.assertTrue(df['clicked'].isin([0, 1]).all())
        self.assertTrue(df['converted'].isin([0, 1]).all())
        # Conversions require a click
        self.assertTrue((df['converted'] <= df['clicked']).all())
        # relevance_grade = 2 for conversion, 1 for click, else 0
        expected = df['clicked'] + df['converted']
        self.assertTrue((df['relevance_grade'] == expected).all())
        # Revenue only on conversions
        self.assertTrue((df.loc[df['converted'] == 0, 'revenue'] == 0).all())
        self.assertTrue((df.loc[df['converted'] == 1, 'revenue'] > 0).all())

    def test_drift_switches_model_version(self):
        generate_dataset(
            start_date='2026-01-01',
            end_date='2026-01-04',
            requests_per_hour=2,
            output_dir=self.test_output_dir,
            seed=42,
            drift_start_offset_days=2,
        )
        df = pd.read_parquet(self.test_output_dir)
        df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
        versions = df.groupby('date')['model_version'].unique()
        self.assertEqual(list(versions['2026-01-01']), ['ranker_v1'])
        self.assertEqual(list(versions['2026-01-03']), ['ranker_v2'])

    def test_reference_dataset(self):
        stats = generate_reference_dataset(
            start_date='2026-01-01',
            reference_days=2,
            requests_per_hour=2,
            output_dir=self.test_output_dir,
            seed=42,
        )
        self.assertEqual(stats['date_range'], '2026-01-01 to 2026-01-02')
        ref_dir = self.test_output_dir / 'ranking-recsys-ads-reference'
        self.assertTrue(ref_dir.exists())
        df = pd.read_parquet(ref_dir)
        self.assertEqual(set(df['model_version']), {'ranker_v1'})

    def test_deterministic(self):
        a = generate_dataset(start_date='2026-01-01', end_date='2026-01-01', requests_per_hour=3, seed=11)
        b = generate_dataset(start_date='2026-01-01', end_date='2026-01-01', requests_per_hour=3, seed=11)
        self.assertEqual(a['total_clicks'], b['total_clicks'])
        self.assertEqual(a['distinct_items'], b['distinct_items'])


if __name__ == '__main__':
    unittest.main()
