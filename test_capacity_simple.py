"""
Simplified capacity test for SmartReview application
"""
import os
import sys
import time
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from database.handler import Database
from src.preprocessing.preprocess import clean_text, PorterStemmer

def generate_test_dataset(num_reviews: int, num_apps: int = 3) -> pd.DataFrame:
    """Generate synthetic test dataset"""
    print(f"\n📊 Generating {num_reviews:,} test reviews for {num_apps} apps...")
    
    sample_reviews = [
        "Great app, very useful and intuitive interface",
        "Terrible experience, crashes constantly and freezes",
        "Amazing features, love the interface design",
        "Buggy and slow, needs serious improvement",
        "Perfect for my needs, highly recommend to everyone",
        "Waste of money, doesn't work as advertised",
        "Excellent customer support and documentation",
        "Poor performance, very disappointed with this",
        "Best app in its category, worth every penny",
        "Not worth downloading, complete waste of time",
    ]
    
    apps = [f"App_{i}" for i in range(1, num_apps + 1)]
    
    data = {
        'app_name': np.random.choice(apps, num_reviews),
        'review_text': np.random.choice(sample_reviews, num_reviews),
        'rating': np.random.randint(1, 6, num_reviews),
        'review_date': [
            (datetime.now() - timedelta(days=np.random.randint(0, 365))).strftime('%Y-%m-%d')
            for _ in range(num_reviews)
        ],
        'app_version': [f"v{np.random.randint(1, 5)}.{np.random.randint(0, 10)}" for _ in range(num_reviews)]
    }
    
    return pd.DataFrame(data)

def test_dataset_capacity(test_sizes: list) -> dict:
    """Test application with different dataset sizes"""
    results = {}
    db_path = str(Path(__file__).parent / 'test_capacity.db')
    schema_path = str(Path(__file__).parent / 'database' / 'schema.sql')
    
    for size in test_sizes:
        print(f"\n{'='*70}")
        print(f"🧪 TESTING WITH {size:,} REVIEWS")
        print(f"{'='*70}")
        
        # Clean up previous test
        if os.path.exists(db_path):
            os.remove(db_path)
        
        try:
            # Initialize database
            db = Database(db_path, schema_path)
            
            # Generate and insert data
            print(f"⏱️  Generating dataset...")
            start_time = time.time()
            df = generate_test_dataset(size)
            gen_time = time.time() - start_time
            print(f"✅ Dataset generated in {gen_time:.2f}s")
            
            # Insert reviews
            print(f"⏱️  Inserting reviews into database...")
            start_time = time.time()
            inserted = db.bulk_insert_reviews(df)
            insert_time = time.time() - start_time
            print(f"✅ Inserted {inserted:,} reviews in {insert_time:.2f}s ({inserted/insert_time:.0f} reviews/sec)")
            
            # Test preprocessing
            print(f"⏱️  Testing preprocessing...")
            start_time = time.time()
            reviews = db.fetch_reviews_without_cleaned(limit=min(1000, size))
            fetch_time = time.time() - start_time
            print(f"✅ Fetched {len(reviews):,} reviews in {fetch_time:.2f}s")
            
            if reviews:
                start_time = time.time()
                stemmer = PorterStemmer()
                cleaned = []
                for r in reviews[:min(100, len(reviews))]:
                    cleaned_text, token_count = clean_text(r[1], stemmer)
                    cleaned.append((r[0], cleaned_text, token_count))
                db.insert_cleaned_batch(cleaned)
                clean_time = time.time() - start_time
                print(f"✅ Preprocessed {len(cleaned)} reviews in {clean_time:.2f}s")
            else:
                clean_time = 0
            
            # Test query performance
            print(f"⏱️  Testing query performance...")
            start_time = time.time()
            cur = db.conn.cursor()
            cur.execute('SELECT COUNT(*) FROM reviews')
            total_reviews = cur.fetchone()[0]
            cur.execute('SELECT COUNT(DISTINCT app_id) FROM reviews')
            total_apps = cur.fetchone()[0]
            cur.execute('SELECT AVG(LENGTH(review_text)) FROM reviews')
            avg_text_len = cur.fetchone()[0] or 0
            query_time = time.time() - start_time
            
            print(f"✅ Database contains {total_reviews:,} reviews across {total_apps} apps")
            print(f"✅ Average review length: {avg_text_len:.0f} characters")
            
            # Get database size
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            print(f"✅ Database size: {db_size_mb:.2f} MB")
            
            # Calculate metrics
            total_time = gen_time + insert_time + fetch_time + clean_time + query_time
            
            results[size] = {
                'status': 'SUCCESS',
                'insert_time': insert_time,
                'insert_rate': inserted / insert_time if insert_time > 0 else 0,
                'preprocess_time': clean_time,
                'db_size_mb': db_size_mb,
                'reviews_per_mb': total_reviews / db_size_mb if db_size_mb > 0 else 0,
                'total_time': total_time,
                'avg_text_len': avg_text_len
            }
            
            db.close()
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            results[size] = {
                'status': 'FAILED',
                'error': str(e)
            }
        
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
    
    return results

def print_summary(results: dict):
    """Print comprehensive summary"""
    print(f"\n{'='*70}")
    print(f"📈 CAPACITY TEST SUMMARY")
    print(f"{'='*70}\n")
    
    successful = {k: v for k, v in results.items() if v['status'] == 'SUCCESS'}
    
    if not successful:
        print("❌ All tests failed")
        return
    
    print("Dataset Size | Insert Rate | DB Size | Reviews/MB | Total Time")
    print("-" * 70)
    
    for size in sorted(successful.keys()):
        result = successful[size]
        print(f"{size:>12,} | {result['insert_rate']:>10.0f}/s | {result['db_size_mb']:>7.2f}MB | "
              f"{result['reviews_per_mb']:>10.0f} | {result['total_time']:>8.2f}s")
    
    # Recommendations
    print(f"\n{'='*70}")
    print(f"💡 PERFORMANCE ANALYSIS")
    print(f"{'='*70}\n")
    
    max_size = max(successful.keys())
    max_result = successful[max_size]
    
    print(f"✅ Successfully tested with {max_size:,} reviews")
    print(f"✅ Insert rate: {max_result['insert_rate']:.0f} reviews/second")
    print(f"✅ Database size: {max_result['db_size_mb']:.2f} MB for {max_size:,} reviews")
    print(f"✅ Density: {max_result['reviews_per_mb']:.0f} reviews per MB")
    print(f"✅ Average review length: {max_result['avg_text_len']:.0f} characters")
    
    # Estimate capacity
    print(f"\n{'='*70}")
    print(f"📊 ESTIMATED CAPACITY & RECOMMENDATIONS")
    print(f"{'='*70}\n")
    
    # Calculate based on actual test results
    bytes_per_review = (max_result['db_size_mb'] * 1024 * 1024) / max_size
    
    print(f"📌 Based on test results:")
    print(f"   • Bytes per review: {bytes_per_review:.0f} bytes")
    print(f"   • Insert rate: {max_result['insert_rate']:.0f} reviews/second")
    print(f"   • Processing time per review: {(max_result['total_time'] / max_size) * 1000:.2f}ms")
    
    # Capacity estimates
    capacities = [
        (0.5, "Small Project (500MB)"),
        (1.0, "Medium Project (1GB)"),
        (5.0, "Large Project (5GB)"),
        (10.0, "Enterprise Project (10GB)"),
    ]
    
    print(f"\n🎯 CAPACITY ESTIMATES:\n")
    
    for gb_limit, label in capacities:
        mb_limit = gb_limit * 1024
        estimated_reviews = int((mb_limit / max_result['db_size_mb']) * max_size)
        processing_hours = (estimated_reviews / max_result['insert_rate']) / 3600
        
        print(f"   {label}:")
        print(f"      • Reviews: {estimated_reviews:,}")
        print(f"      • Processing time: ~{processing_hours:.1f} hours")
        print()
    
    print(f"{'='*70}")
    print(f"🎯 RECOMMENDED USAGE RANGES")
    print(f"{'='*70}\n")
    
    print(f"✅ OPTIMAL RANGE (Recommended):")
    print(f"   • Small projects: 10,000 - 100,000 reviews")
    print(f"   • Medium projects: 100,000 - 500,000 reviews")
    print(f"   • Large projects: 500,000 - 2,000,000 reviews")
    
    print(f"\n⚠️  CONSIDERATIONS:")
    print(f"   • For 1M+ reviews: Consider database optimization")
    print(f"   • For 5M+ reviews: May need distributed processing")
    print(f"   • Real-time processing: Best with <500K reviews")
    print(f"   • Batch processing: Can handle 1M+ reviews")
    
    print(f"\n💾 STORAGE REQUIREMENTS:")
    for gb_limit, label in capacities:
        print(f"   • {label}: ~{gb_limit:.1f}GB")

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 SmartReview Application Capacity Test")
    print("="*70)
    
    # Test with different dataset sizes
    test_sizes = [1000, 5000, 10000, 50000]
    
    results = test_dataset_capacity(test_sizes)
    print_summary(results)
    
    print(f"\n{'='*70}")
    print("✅ Capacity test completed!")
    print(f"{'='*70}\n")
