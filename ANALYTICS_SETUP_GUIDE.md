# Analytics Page Setup Guide

## Overview
The Analytics page displays three advanced visualizations:
1. **Sentiment Trends Over Time** - Line chart of sentiment distribution
2. **Rating vs Sentiment Correlation** - Heatmap showing rating-sentiment alignment
3. **Severity Leaderboard** - Ranked themes by severity score

For these to work, your data must flow through the complete pipeline.

---

## Prerequisites Checklist

### ✅ Step 1: Verify CSV Format
Your `data/raw/sample_reviews.csv` must have these columns:
```
app_name,review_text,rating,review_date,app_version
```

**Example:**
```
alpha,Great performance and clean UI!,5,2024-06-10,1.2.0
alpha,Crashes on image upload.,1,2024-06-11,1.2.0
alpha,Login is slow but works.,3,2024-06-12,1.2.1
beta,Battery draining quickly!,2,2024-06-13,3.4.5
beta,Smooth animations and fast load.,5,2024-06-14,3.4.6
```

**Required fields:**
- `app_name` - Application name (string)
- `review_text` - Review content (string)
- `rating` - Star rating (1-5, integer)
- `review_date` - Date in YYYY-MM-DD format (string)
- `app_version` - Version number (string)

---

### ✅ Step 2: Ingest Data via Dashboard

1. **Start the application:**
   ```bash
   python main.py
   ```

2. **Navigate to Dashboard:**
   - Go to http://localhost:8080/dashboard

3. **Upload CSV:**
   - Click "Upload CSV/XLSX" in the Data Ingestion section
   - Select `data/raw/sample_reviews.csv`
   - Wait for upload confirmation

4. **Verify ingestion:**
   - You should see a status message: "✅ X reviews ingested"

---

### ✅ Step 3: Run Preprocessing

1. **Click "Run Preprocessing" button**
   - This cleans and tokenizes review text
   - Creates entries in `cleaned_reviews` table
   - Status message: "✅ X reviews cleaned"

2. **Wait for completion**
   - Processing may take a few seconds for larger datasets

---

### ✅ Step 4: Run Sentiment Analysis

1. **Click "Run Sentiment" button**
   - This applies the NLP model to classify sentiment
   - Creates entries in `sentiment_results` table
   - Status message: "✅ X reviews analyzed"

2. **Wait for completion**
   - This is the most time-consuming step

---

### ✅ Step 5: Verify Data Pipeline

Run the debug script to confirm everything is working:

```bash
python debug_analytics.py
```

**Expected output:**
```
1️⃣  REVIEWS TABLE
   Total reviews: 5
   Reviews with rating: 5
   Reviews with review_date: 5
   Distinct ratings: [1, 2, 3, 5]
   Distinct dates: ['2024-06-10', '2024-06-11', '2024-06-12', '2024-06-13', '2024-06-14']

2️⃣  SENTIMENT_RESULTS TABLE
   Total sentiment results: 5
   Distinct sentiments: ['negative', 'neutral', 'positive']

...

8️⃣  ANALYTICS READINESS CHECK
   ✅ Reviews ingested
   ✅ Sentiment computed
   ✅ Has ratings
   ✅ Has dates
   ✅ Sentiment labels exist

🎉 READY! Analytics should display data on page load.
```

---

## Accessing Analytics

### Navigate to Analytics Page
1. Go to http://localhost:8080/analytics
2. You should see:
   - **Data Summary** section showing counts
   - **Filters** section with app selector and date range
   - **Three visualization sections** (may be empty until you click Update)

### Using the Visualizations

#### 1. Sentiment Trends Over Time
- **What it shows:** Sentiment distribution over time
- **How to use:**
  - Select an app from dropdown (or "All Apps")
  - Adjust date range if needed
  - Click "Update Chart"
  - Chart displays positive/neutral/negative counts by date

#### 2. Rating vs Sentiment Correlation
- **What it shows:** How star ratings align with predicted sentiment
- **How to use:**
  - Select an app from dropdown
  - Click "Update Correlation"
  - Heatmap shows rating (rows) vs sentiment (columns)
  - Darker colors = more reviews

#### 3. Severity Leaderboard
- **What it shows:** Top issues ranked by severity
- **Severity formula:** `(0.5 × frequency) + (0.3 × negativity) + (0.2 × recency)`
- **How to use:**
  - Select an app and date range
  - Click "Update Leaderboard"
  - Table shows themes ranked by severity score

---

## Troubleshooting

### Problem: Charts are empty
**Solution:**
1. Run `python debug_analytics.py`
2. Check if sentiment_results count is 0
3. If 0, you haven't run sentiment analysis yet
4. Go back to Dashboard and click "Run Sentiment"

### Problem: "No data available" message
**Solution:**
1. Check if you selected an app that has no data
2. Try "All Apps" option
3. Verify date range includes your data dates
4. Run debug script to see available dates

### Problem: Charts show but look wrong
**Solution:**
1. Check console for error messages (F12 → Console)
2. Run debug script to verify column names match
3. Ensure all three steps completed: Ingest → Preprocess → Sentiment

---

## Data Flow Diagram

```
CSV File (sample_reviews.csv)
    ↓
[Upload] → reviews table
    ↓
[Run Preprocessing] → cleaned_reviews table
    ↓
[Run Sentiment] → sentiment_results table
    ↓
Analytics Queries
    ↓
Charts & Visualizations
```

---

## Database Schema

### reviews table
```sql
CREATE TABLE reviews (
  id INTEGER PRIMARY KEY,
  app_id INTEGER NOT NULL,
  review_text TEXT NOT NULL,
  rating INTEGER,              -- 1-5, can be NULL
  review_date TEXT,            -- YYYY-MM-DD format, can be NULL
  version TEXT,
  FOREIGN KEY (app_id) REFERENCES apps(id)
);
```

### sentiment_results table
```sql
CREATE TABLE sentiment_results (
  review_id INTEGER PRIMARY KEY,
  sentiment_label TEXT,        -- 'positive', 'neutral', or 'negative'
  sentiment_score REAL,        -- 0.0-1.0 confidence
  FOREIGN KEY (review_id) REFERENCES reviews(id)
);
```

### apps table
```sql
CREATE TABLE apps (
  id INTEGER PRIMARY KEY,
  app_name TEXT NOT NULL UNIQUE
);
```

---

## Quick Commands

### Check review count
```bash
python -c "import sqlite3; con=sqlite3.connect('database/reviews.db'); print('Reviews:', con.cursor().execute('SELECT COUNT(*) FROM reviews').fetchone()[0])"
```

### Check sentiment count
```bash
python -c "import sqlite3; con=sqlite3.connect('database/reviews.db'); print('Sentiments:', con.cursor().execute('SELECT COUNT(*) FROM sentiment_results').fetchone()[0])"
```

### Full debug check
```bash
python debug_analytics.py
```

---

## Support

If charts still don't display after following these steps:
1. Run `python debug_analytics.py` and share the output
2. Check browser console (F12) for JavaScript errors
3. Check server terminal for Python errors
4. Verify all three pipeline steps completed successfully
