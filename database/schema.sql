PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS apps (
  id INTEGER PRIMARY KEY,
  app_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY,
  app_id INTEGER NOT NULL,
  review_text TEXT NOT NULL,
  rating INTEGER,
  review_date TEXT,
  version TEXT,
  FOREIGN KEY (app_id) REFERENCES apps(id)
);

CREATE TABLE IF NOT EXISTS cleaned_reviews (
  review_id INTEGER PRIMARY KEY,
  cleaned_text TEXT,
  token_count INTEGER,
  FOREIGN KEY (review_id) REFERENCES reviews(id)
);

CREATE TABLE IF NOT EXISTS sentiment_results (
  review_id INTEGER PRIMARY KEY,
  sentiment_label TEXT,
  sentiment_score REAL,
  FOREIGN KEY (review_id) REFERENCES reviews(id)
);

CREATE TABLE IF NOT EXISTS themes (
  id INTEGER PRIMARY KEY,
  review_id INTEGER,
  theme_label TEXT,
  ngram TEXT,
  frequency INTEGER,
  FOREIGN KEY (review_id) REFERENCES reviews(id)
);

CREATE TABLE IF NOT EXISTS recommendations (
  id INTEGER PRIMARY KEY,
  theme_label TEXT,
  recommendation_text TEXT,
  severity REAL,
  app_id INTEGER,
  version TEXT,
  FOREIGN KEY (app_id) REFERENCES apps(id)
);

CREATE TABLE IF NOT EXISTS report_cache (
  id INTEGER PRIMARY KEY,
  report_type TEXT,
  generated_at TEXT,
  file_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_reviews_app ON reviews(app_id);
CREATE INDEX IF NOT EXISTS idx_reviews_date ON reviews(review_date);
CREATE INDEX IF NOT EXISTS idx_sentiment_label ON sentiment_results(sentiment_label);
