import json
import uuid
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random
import hashlib


def generate_dataset(
    start_date: str = None,
    end_date: str = None,
    past_days: int = 90,
    future_days: int = 90,
    transactions_per_hour: int = 60,
    output_dir: Path = None,
    seed: int = 42
):
    """
    Generate synthetic card fraud transaction dataset.
    
    This dataset simulates credit card transactions with fraud detection features.
    The data is organized in a hierarchical structure: year/month/day/hour JSON files.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (if None, calculated from past_days)
        end_date: End date in YYYY-MM-DD format (inclusive, if None, calculated from future_days)
        past_days: Number of days in the past from today to generate data (default: 90)
        future_days: Number of days in the future from today to generate data (default: 90)
        transactions_per_hour: Number of transactions per hour
        output_dir: Base output directory (will create ccb-card-fraud/ structure)
        seed: Random seed for reproducibility
    
    Returns:
        dict: Statistics about generated dataset
    """
    # Calculate dates if not provided
    if start_date is None or end_date is None:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date is None:
            start_date = (today - timedelta(days=past_days)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = (today + timedelta(days=future_days)).strftime("%Y-%m-%d")
    # Set random seed
    np.random.seed(seed)
    random.seed(seed)
    
    # Parse dates
    start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
    
    # Customer segments and their characteristics
    customer_segments = ['new_to_bank', 'established', 'small_business']
    channels = ['ecom', 'in_store', 'atm']
    regions = ['W', 'NE', 'MW', 'S']
    
    # Generate unique account and customer IDs
    account_ids = [f"acct_{random.randint(10000, 50000)}" for _ in range(1000)]
    customer_ids = [f"cust_{random.randint(10000, 30000)}" for _ in range(2000)]
    
    # Track statistics
    stats = {
        'total_transactions': 0,
        'total_fraud': 0,
        'files_created': 0,
        'date_range': f"{start_date} to {end_date}"
    }
    
    # Generate data hour by hour
    current_dt = start_dt
    while current_dt <= end_dt:
        # Create directory structure: year=YYYY/month=MM/day=DD/
        year = current_dt.year
        month = current_dt.month
        day = current_dt.day
        hour = current_dt.hour
        
        # Generate transactions for this hour
        transactions = []
        for _ in range(transactions_per_hour):
            # Select customer segment
            segment = np.random.choice(
                customer_segments,
                p=[0.15, 0.70, 0.15]  # 15% new, 70% established, 15% small business
            )
            
            # Select channel
            channel = np.random.choice(
                channels,
                p=[0.60, 0.35, 0.05]  # 60% ecom, 35% in_store, 5% atm
            )
            
            # Select region
            region = np.random.choice(regions, p=[0.25, 0.25, 0.25, 0.25])
            
            # Generate transaction amount (skewed right, typical for transactions)
            txn_amount = np.random.lognormal(mean=3.0, sigma=0.8)
            txn_amount = round(txn_amount, 2)
            txn_amount = max(1.0, min(txn_amount, 10000.0))  # Clamp between $1 and $10,000
            
            # Generate distance from home (km)
            # Fraud transactions tend to be further from home
            distance_from_home = np.random.exponential(scale=10.0)
            distance_from_home = round(distance_from_home, 2)
            distance_from_home = min(distance_from_home, 1000.0)
            
            # Generate merchant risk score (0-1)
            merchant_risk_score = np.random.beta(2, 8)
            merchant_risk_score = round(merchant_risk_score, 4)
            
            # Generate digital engagement score
            digital_engagement = np.random.gamma(shape=2, scale=2)
            digital_engagement = round(digital_engagement, 2)
            digital_engagement = min(digital_engagement, 10.0)
            
            # Generate tenure in months
            if segment == 'new_to_bank':
                tenure_months = np.random.randint(0, 12)
            elif segment == 'small_business':
                tenure_months = np.random.randint(12, 120)
            else:  # established
                tenure_months = np.random.randint(6, 120)
            
            # Determine if this is fraud (ground truth)
            # Fraud probability depends on multiple factors
            fraud_base_prob = 0.05  # Base fraud rate ~5%
            
            # Higher fraud risk for:
            # - New customers
            if segment == 'new_to_bank':
                fraud_base_prob *= 1.5
            # - Large transactions
            if txn_amount > 500:
                fraud_base_prob *= 1.3
            # - Far from home
            if distance_from_home > 50:
                fraud_base_prob *= 1.4
            # - High merchant risk
            if merchant_risk_score > 0.5:
                fraud_base_prob *= 1.2
            # - ATM transactions
            if channel == 'atm':
                fraud_base_prob *= 1.3
            
            # Clip to reasonable bounds
            fraud_base_prob = min(fraud_base_prob, 0.30)
            
            is_fraud = 1 if np.random.random() < fraud_base_prob else 0
            
            # Generate fraud score (model prediction probability)
            # Should be correlated with actual fraud but not perfect
            if is_fraud == 1:
                # If actually fraud, model should generally predict higher (but not perfect)
                fraud_score = np.random.beta(3, 7)  # Skewed towards lower values
                # But add some correlation
                fraud_score = fraud_score * 0.4 + np.random.beta(6, 2) * 0.6
            else:
                # If not fraud, model should generally predict lower (but not perfect)
                fraud_score = np.random.beta(2, 8)  # Skewed towards lower values
                # But add some false positives
                fraud_score = fraud_score * 0.7 + np.random.beta(3, 7) * 0.3
            
            fraud_score = round(fraud_score, 6)
            fraud_score = max(0.0, min(1.0, fraud_score))
            
            # Generate fraud prediction (binary, threshold at 0.5)
            fraud_pred = 1 if fraud_score >= 0.5 else 0
            
            # Rules engine flag (simple rule-based system)
            # Flags transactions with high amount + high distance
            rules_engine_flag = 1 if (txn_amount > 200 and distance_from_home > 30) else 0
            
            # Risk rank (1-5, based on fraud_score)
            if fraud_score < 0.1:
                risk_rank = 1
            elif fraud_score < 0.2:
                risk_rank = 2
            elif fraud_score < 0.4:
                risk_rank = 3
            elif fraud_score < 0.6:
                risk_rank = 4
            else:
                risk_rank = 5
            
            # Generate unique transaction ID (deterministic based on timestamp and index)
            # Use hash of timestamp and transaction index to create deterministic UUID
            txn_hash = hashlib.md5(f"{current_dt.isoformat()}_{len(transactions)}".encode()).hexdigest()
            txn_id = str(uuid.UUID(txn_hash))
            
            # Select account and customer IDs
            account_id = random.choice(account_ids)
            customer_id = random.choice(customer_ids)
            
            # Create transaction record
            transaction = {
                "timestamp": current_dt.isoformat(),
                "txn_id": txn_id,
                "account_id": account_id,
                "customer_id": customer_id,
                "is_fraud": is_fraud,
                "fraud_score": fraud_score,
                "fraud_pred": fraud_pred,
                "rules_engine_flag": rules_engine_flag,
                "risk_rank": risk_rank,
                "customer_segment": segment,
                "channel": channel,
                "region": region,
                "txn_amount": txn_amount,
                "distance_from_home_km": distance_from_home,
                "merchant_risk_score": merchant_risk_score,
                "digital_engagement": digital_engagement,
                "tenure_months": tenure_months
            }
            
            transactions.append(transaction)
            stats['total_transactions'] += 1
            if is_fraud == 1:
                stats['total_fraud'] += 1
        
        # Save to JSON file
        if output_dir is not None:
            output_path = Path(output_dir)
            # Match existing structure: year=YYYY/month=MM/day=DD/inferences_hour=HH.json
            file_path = output_path / f"year={year}" / f"month={month:02d}" / f"day={day:02d}" / f"inferences_hour={hour:02d}.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(transactions, f, indent=2)
            
            stats['files_created'] += 1
        
        # Move to next hour
        current_dt += timedelta(hours=1)
    
    # Calculate fraud rate
    stats['fraud_rate'] = stats['total_fraud'] / stats['total_transactions'] if stats['total_transactions'] > 0 else 0
    
    return stats


def generate_reference_dataset(
    start_date: str = None,
    end_date: str = None,
    past_days: int = 90,
    future_days: int = 90,
    reference_days: int = 14,
    transactions_per_hour: int = 60,
    output_dir: Path = None,
    seed: int = 42
):
    """
    Generate reference/baseline card fraud dataset (typically smaller, for comparison).
    
    Args:
        start_date: Start date in YYYY-MM-DD format (if None, calculated from past_days)
        end_date: End date in YYYY-MM-DD format (inclusive, if None, calculated from past_days + reference_days)
        past_days: Number of days in the past from today to start reference dataset (default: 90)
        future_days: Unused for reference dataset, kept for API consistency
        reference_days: Number of days to generate for reference dataset (default: 14)
        transactions_per_hour: Number of transactions per hour
        output_dir: Base output directory (will create ccb-card-fraud-reference/ structure)
        seed: Random seed for reproducibility
    
    Returns:
        dict: Statistics about generated dataset
    """
    # Calculate dates if not provided
    if start_date is None or end_date is None:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date is None:
            start_date = (today - timedelta(days=past_days)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = (datetime.fromisoformat(start_date) + timedelta(days=reference_days - 1)).strftime("%Y-%m-%d")
    if output_dir is not None:
        output_path = Path(output_dir) / "ccb-card-fraud-reference"
    else:
        output_path = None
    
    return generate_dataset(
        start_date=start_date,
        end_date=end_date,
        transactions_per_hour=transactions_per_hour,
        output_dir=output_path,
        seed=seed
    )


if __name__ == '__main__':
    from pathlib import Path
    
    # Configuration
    base_output_dir = Path(__file__).parent / '../output'
    
    # Generate main dataset (default: ±90 days from today)
    print("Generating card fraud dataset...")
    main_output = base_output_dir / "ccb-card-fraud"
    stats = generate_dataset(
        past_days=90,
        future_days=90,
        transactions_per_hour=60,
        output_dir=main_output,
        seed=42
    )
    
    print(f"\nMain Dataset Statistics:")
    print(f"  Date range: {stats['date_range']}")
    print(f"  Total transactions: {stats['total_transactions']:,}")
    print(f"  Total fraud: {stats['total_fraud']:,}")
    print(f"  Fraud rate: {stats['fraud_rate']:.2%}")
    print(f"  Files created: {stats['files_created']:,}")
    print(f"  Output directory: {main_output}")
    
    # Generate reference dataset (first 14 days of the range)
    print("\nGenerating reference dataset...")
    ref_output = base_output_dir / "ccb-card-fraud-reference"
    ref_stats = generate_reference_dataset(
        past_days=90,
        reference_days=14,
        transactions_per_hour=60,
        output_dir=base_output_dir,
        seed=42
    )
    
    print(f"\nReference Dataset Statistics:")
    print(f"  Date range: {ref_stats['date_range']}")
    print(f"  Total transactions: {ref_stats['total_transactions']:,}")
    print(f"  Total fraud: {ref_stats['total_fraud']:,}")
    print(f"  Fraud rate: {ref_stats['fraud_rate']:.2%}")
    print(f"  Files created: {ref_stats['files_created']:,}")
    print(f"  Output directory: {ref_output}")
    
    print("\n✅ Dataset generation complete!")
