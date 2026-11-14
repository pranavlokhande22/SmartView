# SmartReview

SmartReview is an offline, end-to-end app reviews analytics tool. It ingests CSV/XLSX files of user reviews, cleans and normalizes text, predicts sentiment using a lightweight ML model, extracts high-impact themes, ranks issues by severity, and provides an interactive NiceGUI dashboard with export options.

## Key Features
- **Ingestion**: Upload CSV/XLSX and auto-normalize common column names.
- **Preprocessing**: Text cleaning, tokenization, stemming (offline, no downloads required).
- **Sentiment**: TF‑IDF + Logistic Regression stored on disk and reused.
- **Themes & Recommendations**: Identify frequent negative themes and suggest actions.
- **Dashboard & Analytics**: Interactive charts, filters, and advanced analytics.
- **Exports**: CSV for counts/recommendations and PNG for charts.
- **Persistence**: SQLite at `database/reviews.db`; models saved in `src/models/`.

## Tech Stack
- Python 3.10+
- NiceGUI (UI & routing)
- SQLite (embedded DB)
- pandas, numpy
- scikit-learn, joblib (model + persistence)
- matplotlib (chart image export)
- openpyxl (Excel ingestion)
- nltk (PorterStemmer; no extra downloads required)

## Project Structure
- `main.py`: App entrypoint; creates DB and runs NiceGUI server.
- `database/`:
  - `schema.sql`: All tables and indexes.
  - `reviews.db`: Created on first run.
- `src/`:
  - `ingestion.py`: CSV/XLSX loader and column normalization.
  - `preprocessing/preprocess.py`: Text cleaning & stemming.
  - `classifier/sentiment_model.py`: TF‑IDF + Logistic Regression training/inference.
  - `theme_extractor.py`: Theme counting and severity scoring.
  - `exporter.py`: CSV/PNG export helpers.
  - `ui/`: Pages, components, styling, and analytics dashboard.
- `data/raw/sample_reviews.csv`: Sample dataset.
- `exports/`: Generated CSV/PNG files.

## One‑Click Setup and Run
1) Create and activate a virtual environment
- Windows (PowerShell)
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
- macOS / Linux (bash/zsh)
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

2) Install dependencies
```bash
pip install -r requirements.txt
```

3) Start the app
```bash
python main.py
```

4) Open the UI
- Visit http://localhost:8080 in your browser.

## Step‑by‑Step Usage Flow
1) Dashboard → Data Ingestion
- Click “Upload CSV/XLSX” or enter a local path and ingest.
- Or use the sample: `data/raw/sample_reviews.csv`.

2) Processing
- Click “Run Preprocessing” to clean text.
- Click “Run Sentiment” to train/refresh the model and classify reviews.
- Click “Generate Themes & Recommendations” to extract themes and rank issues.
- Or click “Run Full Pipeline” to execute all steps.

3) Explore
- Charts update automatically; filter by App in “Filters”.
- Navigate to “Analytics” for time series, correlation, and severity leaderboard.

4) Export
- Export sentiment counts (CSV), recommendations (CSV), or the current chart (PNG) from the “Export” section.
- Files are saved under `exports/csv/` and `exports/charts/`.

## Supported Input Columns
Minimum required: `app_name`, `review_text`.

The loader also auto-detects common synonyms:
- `app_name`: app, appname, name
- `review_text`: translated_review, content, text, review, review_body, comments, comment
- `rating`: rating, score, stars, star, user_rating (optional)
- `review_date`: at, date, time, timestamp, last updated/last_updated/posted_at/review_time (optional)
- `app_version`: version, current ver/current_ver, version_name, software_version, version code/version_code (optional)

Notes
- Empty/very short reviews are dropped; duplicates are removed.
- If you upload an apps metadata file (no user text), ingestion will warn you.

## Configuration & Paths
- Database file: `database/reviews.db` (auto-created).
- Saved model & vectorizer: `src/models/`.
- Server port: `8080` (change in `main.py` if needed).

## Troubleshooting
- Port in use: change the port in `main.py` → `ui.run(..., port=YOUR_PORT)`.
- Excel read errors: ensure `openpyxl` is installed (bundled via requirements).
- NLTK downloads: not required; only `PorterStemmer` is used.
- Reset state: stop the app and delete `database/reviews.db` and files under `src/models/`.

## License
For internal or educational use unless a license file is provided.

