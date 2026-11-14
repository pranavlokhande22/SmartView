"""Debug script to verify analytics data pipeline"""

import sqlite3
from datetime import datetime

def check_database():
    """Check database state and verify analytics readiness"""
    
    con = sqlite3.connect('database/reviews.db')
    cur = con.cursor()
    
    print("=" * 70)
    print("ANALYTICS DATA VERIFICATION")
    print("=" * 70)
    
    # 1. Check reviews table
    print("\n1️⃣  REVIEWS TABLE")
    print("-" * 70)
    cur.execute('SELECT COUNT(*) FROM reviews')
    review_count = cur.fetchone()[0]
    print(f"   Total reviews: {review_count}")
    
    cur.execute('SELECT COUNT(*) FROM reviews WHERE rating IS NOT NULL')
    rated_count = cur.fetchone()[0]
    print(f"   Reviews with rating: {rated_count}")
    
    cur.execute('SELECT COUNT(*) FROM reviews WHERE review_date IS NOT NULL')
    dated_count = cur.fetchone()[0]
    print(f"   Reviews with review_date: {dated_count}")
    
    cur.execute('SELECT DISTINCT rating FROM reviews WHERE rating IS NOT NULL ORDER BY rating')
    ratings = cur.fetchall()
    print(f"   Distinct ratings: {[r[0] for r in ratings]}")
    
    cur.execute('SELECT DISTINCT review_date FROM reviews WHERE review_date IS NOT NULL ORDER BY review_date')
    dates = cur.fetchall()
    print(f"   Distinct dates: {[d[0] for d in dates]}")
    
    # 2. Check sentiment_results table
    print("\n2️⃣  SENTIMENT_RESULTS TABLE")
    print("-" * 70)
    cur.execute('SELECT COUNT(*) FROM sentiment_results')
    sentiment_count = cur.fetchone()[0]
    print(f"   Total sentiment results: {sentiment_count}")
    
    cur.execute('SELECT DISTINCT sentiment_label FROM sentiment_results ORDER BY sentiment_label')
    sentiments = cur.fetchall()
    print(f"   Distinct sentiments: {[s[0] for s in sentiments]}")
    
    # 3. Check apps table
    print("\n3️⃣  APPS TABLE")
    print("-" * 70)
    cur.execute('SELECT COUNT(*) FROM apps')
    app_count = cur.fetchone()[0]
    print(f"   Total apps: {app_count}")
    
    cur.execute('SELECT id, app_name FROM apps LIMIT 5')
    sample_apps = cur.fetchall()
    print(f"   Sample apps: {sample_apps}")
    
    # 4. Sample data from reviews
    print("\n4️⃣  SAMPLE REVIEWS DATA")
    print("-" * 70)
    cur.execute('SELECT id, app_id, rating, review_date FROM reviews WHERE rating IS NOT NULL AND review_date IS NOT NULL LIMIT 3')
    samples = cur.fetchall()
    if samples:
        print("   Reviews with both rating and date:")
        for row in samples:
            print(f"      {row}")
    else:
        print("   ⚠️  No reviews with both rating AND date found")
    
    # 5. Test time-series query
    print("\n5️⃣  TIME-SERIES QUERY TEST")
    print("-" * 70)
    try:
        cur.execute("""
            SELECT r.review_date, s.sentiment_label, COUNT(*) as count
            FROM reviews r
            LEFT JOIN sentiment_results s ON s.review_id = r.id
            WHERE r.review_date IS NOT NULL
            GROUP BY r.review_date, s.sentiment_label
            ORDER BY r.review_date ASC
        """)
        ts_rows = cur.fetchall()
        print(f"   Time-series query returned: {len(ts_rows)} rows")
        if ts_rows:
            print("   Sample results:")
            for row in ts_rows[:3]:
                print(f"      {row}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 6. Test correlation query
    print("\n6️⃣  CORRELATION QUERY TEST")
    print("-" * 70)
    try:
        cur.execute("""
            SELECT r.rating, s.sentiment_label, COUNT(*) as count
            FROM reviews r
            LEFT JOIN sentiment_results s ON s.review_id = r.id
            WHERE r.rating IS NOT NULL
            GROUP BY r.rating, s.sentiment_label
        """)
        corr_rows = cur.fetchall()
        print(f"   Correlation query returned: {len(corr_rows)} rows")
        if corr_rows:
            print("   Sample results:")
            for row in corr_rows[:3]:
                print(f"      {row}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 7. Test sentiment distribution query
    print("\n7️⃣  SENTIMENT DISTRIBUTION QUERY TEST")
    print("-" * 70)
    try:
        cur.execute("""
            SELECT s.sentiment_label, COUNT(*) as count
            FROM reviews r
            LEFT JOIN sentiment_results s ON s.review_id = r.id
            GROUP BY s.sentiment_label
        """)
        dist_rows = cur.fetchall()
        print(f"   Sentiment distribution query returned: {len(dist_rows)} rows")
        if dist_rows:
            print("   Results:")
            for row in dist_rows:
                print(f"      {row[0]}: {row[1]} reviews")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 8. Readiness check
    print("\n8️⃣  ANALYTICS READINESS CHECK")
    print("-" * 70)
    
    checks = {
        "✅ Reviews ingested": review_count > 0,
        "✅ Sentiment computed": sentiment_count > 0,
        "✅ Has ratings": rated_count > 0,
        "✅ Has dates": dated_count > 0,
        "✅ Sentiment labels exist": len(sentiments) > 0,
    }
    
    all_ready = all(checks.values())
    
    for check, status in checks.items():
        symbol = "✅" if status else "❌"
        print(f"   {symbol} {check}")
    
    print("\n" + "=" * 70)
    if all_ready:
        print("🎉 READY! Analytics should display data on page load.")
    else:
        print("⚠️  INCOMPLETE - Follow these steps:")
        if review_count == 0:
            print("   1. Upload sample_reviews.csv from Dashboard")
        if sentiment_count == 0:
            print("   2. Click 'Run Preprocessing' button")
            print("   3. Click 'Run Sentiment' button")
        if rated_count == 0 or dated_count == 0:
            print("   4. Ensure CSV has 'rating' and 'review_date' columns")
    print("=" * 70)
    
    con.close()

if __name__ == '__main__':
    check_database()
