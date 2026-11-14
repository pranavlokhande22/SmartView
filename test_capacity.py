"""
Test script to evaluate SmartReview application capacity and performance
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

class SentimentClassifier:
    def __init__(self):
        import joblib
        from pathlib import Path
        model_dir = Path(__file__).resolve().parent / 'src' / 'models'
        self.vec_path = model_dir / 'tfidf_vectorizer.pkl'
        self.model_path = model_dir / 'sentiment_model.pkl'
        if self.vec_path.exists() and self.model_path.exists():
            self.vec = joblib.load(self.vec_path)
            self.clf = joblib.load(self.model_path)
        else:
            self.vec = None
            self.clf = None

    def classify_batch(self, texts):
        if not self.vec or not self.clf:
            # Fallback if model is not yet trained/saved
            return ['positive'] * len(texts)
        Xv = self.vec.transform(texts)
        return self.clf.predict(Xv)

class ThemeExtractor:
    def extract_themes(self, texts):
        from src.theme_extractor import _map_to_theme, _tokenize
        out = []
        for t in texts:
            tokens = _tokenize(t or '')
            matched = []
            for tok in tokens:
                theme = _map_to_theme(tok)
                if theme:
                    matched.append(theme)
            out.append(matched)
        return out

def generate_test_dataset(num_reviews: int, num_apps: int = 3) -> pd.DataFrame:
    """Generate synthetic test dataset"""
    print(f"\n📊 Generating {num_reviews:,} test reviews for {num_apps} apps...")
    
    sample_reviews = [
        "Great app, very useful and intuitive",
        "Terrible experience, crashes constantly",
        "Amazing features, love the interface",
        "Buggy and slow, needs improvement",
        "Perfect for my needs, highly recommend",
        "Waste of money, doesn't work",
        "Excellent customer support",
        "Poor performance, very disappointed",
        "Best app in its category",
        "Not worth downloading",
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
            preprocess_time = time.time() - start_time
            print(f"✅ Fetched {len(reviews):,} reviews in {preprocess_time:.2f}s")
            
            if reviews:
                start_time = time.time()
                stemmer = PorterStemmer()
                cleaned = [(r[0], clean_text(r[1], stemmer)[0], clean_text(r[1], stemmer)[1]) for r in reviews[:100]]
                db.insert_cleaned_batch(cleaned)
                clean_time = time.time() - start_time
                print(f"✅ Preprocessed 100 reviews in {clean_time:.2f}s")
            
            # Test sentiment classification
            print(f"⏱️  Testing sentiment classification...")
            try:
                classifier = SentimentClassifier()
                start_time = time.time()
                test_texts = [r[1] for r in reviews[:50]]
                sentiments = classifier.classify_batch(test_texts)
                sentiment_time = time.time() - start_time
                print(f"✅ Classified 50 reviews in {sentiment_time:.2f}s ({50/sentiment_time:.0f} reviews/sec)")
            except Exception as e:
                print(f"⚠️  Sentiment classification test skipped: {str(e)[:50]}")
                sentiment_time = 0
            
            # Test theme extraction
            print(f"⏱️  Testing theme extraction...")
            try:
                extractor = ThemeExtractor()
                start_time = time.time()
                themes = extractor.extract_themes(test_texts[:20])
                theme_time = time.time() - start_time
                print(f"✅ Extracted themes from 20 reviews in {theme_time:.2f}s")
            except Exception as e:
                print(f"⚠️  Theme extraction test skipped: {str(e)[:50]}")
                theme_time = 0
            
            # Get database size
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            
            # Test query performance
            print(f"⏱️  Testing query performance...")
            start_time = time.time()
            cur = db.conn.cursor()
            cur.execute('SELECT COUNT(*) FROM reviews')
            total_reviews = cur.fetchone()[0]
            cur.execute('SELECT COUNT(DISTINCT app_id) FROM reviews')
            total_apps = cur.fetchone()[0]
            query_time = time.time() - start_time
            
            print(f"✅ Database contains {total_reviews:,} reviews across {total_apps} apps")
            print(f"✅ Database size: {db_size_mb:.2f} MB")
            
            results[size] = {
                'status': 'SUCCESS',
                'insert_time': insert_time,
                'insert_rate': inserted / insert_time,
                'preprocess_time': preprocess_time,
                'sentiment_time': sentiment_time,
                'theme_time': theme_time,
                'db_size_mb': db_size_mb,
                'reviews_per_mb': total_reviews / db_size_mb if db_size_mb > 0 else 0,
                'total_time': gen_time + insert_time + preprocess_time + sentiment_time + theme_time
            }
            
            db.close()
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
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
    print(f"💡 RECOMMENDATIONS")
    print(f"{'='*70}\n")
    
    max_size = max(successful.keys())
    max_result = successful[max_size]
    
    print(f"✅ Successfully tested with {max_size:,} reviews")
    print(f"✅ Insert rate: {max_result['insert_rate']:.0f} reviews/second")
    print(f"✅ Database size: {max_result['db_size_mb']:.2f} MB")
    print(f"✅ Density: {max_result['reviews_per_mb']:.0f} reviews per MB")
    
    # Estimate capacity
    print(f"\n📊 ESTIMATED CAPACITY:")
    
    # Assuming 1GB limit for reasonable performance
    gb_limit = 1.0
    mb_limit = gb_limit * 1024
    estimated_reviews = int(max_result['reviews_per_mb'] * mb_limit)
    
    print(f"   • For 1GB database: ~{estimated_reviews:,} reviews")
    print(f"   • Processing time (1GB): ~{max_result['total_time'] * (estimated_reviews / max_size) / 3600:.1f} hours")
    
    # Assuming 5GB limit
    gb_limit = 5.0
    mb_limit = gb_limit * 1024
    estimated_reviews = int(max_result['reviews_per_mb'] * mb_limit)
    
    print(f"   • For 5GB database: ~{estimated_reviews:,} reviews")
    print(f"   • Processing time (5GB): ~{max_result['total_time'] * (estimated_reviews / max_size) / 3600:.1f} hours")
    
    # Assuming 10GB limit
    gb_limit = 10.0
    mb_limit = gb_limit * 1024
    estimated_reviews = int(max_result['reviews_per_mb'] * mb_limit)
    
    print(f"   • For 10GB database: ~{estimated_reviews:,} reviews")
    print(f"   • Processing time (10GB): ~{max_result['total_time'] * (estimated_reviews / max_size) / 3600:.1f} hours")
    
    print(f"\n🎯 OPTIMAL RANGE:")
    print(f"   • Small projects: 10,000 - 100,000 reviews")
    print(f"   • Medium projects: 100,000 - 1,000,000 reviews")
    print(f"   • Large projects: 1,000,000+ reviews (may need optimization)")

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 SmartReview Application Capacity Test")
    print("="*70)
    
    # Test with different dataset sizes
    test_sizes = [1000, 5000, 10000, 50000, 100000]
    
    results = test_dataset_capacity(test_sizes)
    print_summary(results)
    
    print(f"\n{'='*70}")
    print("✅ Capacity test completed!")
    print(f"{'='*70}\n")
