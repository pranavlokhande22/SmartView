import os
from typing import Dict, Any, Optional

import pandas as pd

from database.handler import Database


MANDATORY_MIN_COLUMNS = ['app_name', 'review_text']


def _first(df: pd.DataFrame, names: list[str]) -> Optional[str]:
    cols = {c.lower().strip(): c for c in df.columns}
    for n in names:
        nn = n.lower().strip()
        if nn in cols:
            return cols[nn]
    return None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # lowercase headers for lookup
    low_df = df.rename(columns={c: c.lower().strip() for c in df.columns})
    # Identify likely columns across common datasets
    app_col = _first(low_df, ['app_name', 'app', 'appname', 'name'])
    text_col = _first(low_df, [
        'review_text', 'translated_review', 'content', 'text', 'review',
        'review_body', 'review_content', 'body', 'comments', 'comment'
    ])
    rating_col = _first(low_df, ['rating', 'score', 'stars', 'star', 'user_rating'])
    date_col = _first(low_df, [
        'review_date', 'at', 'date', 'time', 'timestamp', 'last updated', 'last_updated', 'posted_at', 'review_time'
    ])
    ver_col = _first(low_df, [
        'app_version', 'version', 'current ver', 'current_ver', 'version_name', 'software_version', 'version code', 'version_code'
    ])

    if not text_col:
        cols_lower = set(low_df.columns)
        maybe_apps_meta = {'app', 'category', 'installs'}.issubset(cols_lower) or 'size' in cols_lower
        if maybe_apps_meta:
            raise ValueError(
                'The file seems to be the Google Play Apps metadata dataset (no textual user reviews). '
                'Please upload a user reviews file (e.g., googleplaystore_user_reviews.csv) containing a review text '
                'column such as translated_review/content/text.'
            )
        raise ValueError('Missing review text column (expected: review_text/translated_review/content/text).')

    out = pd.DataFrame()
    out['review_text'] = low_df[text_col].astype(str)
    out['app_name'] = low_df[app_col].astype(str) if app_col else 'unknown'

    # rating (optional)
    if rating_col and rating_col in low_df.columns:
        r = pd.to_numeric(low_df[rating_col], errors='coerce')
        # Convert to 1-5 integer if possible
        r = r.clip(lower=1, upper=5).round().astype('Int64')
        out['rating'] = r
    else:
        out['rating'] = pd.Series([pd.NA] * len(out), dtype='Int64')

    # date (optional)
    if date_col and date_col in low_df.columns:
        dt = pd.to_datetime(low_df[date_col], errors='coerce')
        out['review_date'] = dt.dt.strftime('%Y-%m-%d')
    else:
        out['review_date'] = None

    # version (optional)
    if ver_col and ver_col in low_df.columns:
        out['app_version'] = low_df[ver_col].astype(str)
    else:
        out['app_version'] = None

    return out


def ingest_file(path: str, db: Database) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    ext = os.path.splitext(path)[1].lower()
    if ext == '.csv':
        df = pd.read_csv(path, encoding='utf-8')
    elif ext in ('.xlsx', '.xls'):
        try:
            df = pd.read_excel(path, engine='openpyxl')
        except Exception:
            # Fallback without engine specification
            df = pd.read_excel(path)
    else:
        raise ValueError('Only CSV and Excel files are supported.')

    df = _normalize_columns(df)
    # Ensure minimal required columns
    for c in MANDATORY_MIN_COLUMNS:
        if c not in df.columns:
            raise ValueError(f'Missing required columns: {MANDATORY_MIN_COLUMNS}')
    # Drop empty / short reviews
    df = df[df['review_text'].astype(str).str.len() >= 5].copy()
    # Normalize app_name
    df['app_name'] = df['app_name'].astype(str).str.strip().str.lower()
    # Deduplicate based on text+app+date
    subset_cols = ['review_text', 'app_name']
    if 'review_date' in df.columns:
        subset_cols.append('review_date')
    df = df.drop_duplicates(subset=subset_cols)

    inserted = db.bulk_insert_reviews(df)
    return {'inserted': inserted, 'total_rows': len(df)}
