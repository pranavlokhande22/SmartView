import os
import sqlite3
from typing import List, Tuple, Optional, Dict, Any

import pandas as pd


class Database:
    def __init__(self, db_path: str, schema_path: str):
        self.db_path = db_path
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute('PRAGMA foreign_keys = ON;')
        self.conn.execute('PRAGMA journal_mode = WAL;')
        self.conn.execute('PRAGMA synchronous = NORMAL;')
        self._init_schema(schema_path)

    def _init_schema(self, schema_path: str) -> None:
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            self.conn.executescript(sql)
            self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def get_or_create_app(self, app_name: str) -> int:
        name = (app_name or '').strip().lower()
        cur = self.conn.cursor()
        cur.execute('INSERT OR IGNORE INTO apps(app_name) VALUES (?)', (name,))
        self.conn.commit()
        cur.execute('SELECT id FROM apps WHERE app_name=?', (name,))
        row = cur.fetchone()
        return int(row[0])

    def bulk_insert_reviews(self, df: pd.DataFrame) -> int:
        required_cols = ['app_name', 'review_text', 'rating', 'review_date', 'app_version']
        for c in required_cols:
            if c not in df.columns:
                raise ValueError(f'Missing column: {c}')
        app_names = sorted(set(df['app_name'].astype(str).str.strip().str.lower().tolist()))
        app_id_map: Dict[str, int] = {}
        for name in app_names:
            app_id_map[name] = self.get_or_create_app(name)
        records: List[Tuple[Any, ...]] = []
        for _, r in df.iterrows():
            app = str(r['app_name']).strip().lower()
            app_id = app_id_map.get(app)
            review_text = str(r['review_text']) if pd.notna(r['review_text']) else ''
            # rating can be float/int/NA; coerce safely
            if pd.notna(r['rating']):
                try:
                    rating = int(float(r['rating']))
                except Exception:
                    rating = None
            else:
                rating = None
            review_date = str(r['review_date']) if pd.notna(r['review_date']) else None
            version = str(r['app_version']) if pd.notna(r['app_version']) else None
            if not review_text:
                continue
            records.append((app_id, review_text, rating, review_date, version))
        cur = self.conn.cursor()
        cur.executemany(
            'INSERT INTO reviews(app_id, review_text, rating, review_date, version) VALUES (?,?,?,?,?)',
            records,
        )
        self.conn.commit()
        return len(records)

    def fetch_reviews_without_cleaned(self, limit: int = 10000) -> List[Tuple[int, str]]:
        cur = self.conn.cursor()
        cur.execute(
            'SELECT r.id, r.review_text FROM reviews r '
            'LEFT JOIN cleaned_reviews c ON c.review_id = r.id '
            'WHERE c.review_id IS NULL LIMIT ?',
            (limit,),
        )
        return [(int(r[0]), str(r[1])) for r in cur.fetchall()]

    def insert_cleaned_batch(self, items: List[Tuple[int, str, int]]) -> None:
        cur = self.conn.cursor()
        cur.executemany(
            'INSERT OR REPLACE INTO cleaned_reviews(review_id, cleaned_text, token_count) VALUES (?,?,?)',
            items,
        )
        self.conn.commit()

    def fetch_cleaned_without_sentiment(self, limit: int = 10000) -> List[Tuple[int, str]]:
        cur = self.conn.cursor()
        cur.execute(
            'SELECT c.review_id, c.cleaned_text FROM cleaned_reviews c '
            'LEFT JOIN sentiment_results s ON s.review_id = c.review_id '
            'WHERE s.review_id IS NULL LIMIT ?',
            (limit,),
        )
        return [(int(r[0]), str(r[1])) for r in cur.fetchall()]

    def insert_sentiment_batch(self, items: List[Tuple[int, str, float]]) -> None:
        cur = self.conn.cursor()
        cur.executemany(
            'INSERT OR REPLACE INTO sentiment_results(review_id, sentiment_label, sentiment_score) VALUES (?,?,?)',
            items,
        )
        self.conn.commit()

    def get_apps(self) -> List[Tuple[int, str]]:
        cur = self.conn.cursor()
        cur.execute('SELECT id, app_name FROM apps ORDER BY app_name ASC')
        rows = cur.fetchall()
        return [(int(r[0]), str(r[1])) for r in rows]

    def get_sentiment_counts(
        self,
        app_id: Optional[int] = None,
        version: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, int]:
        where = []
        params: List[Any] = []
        if app_id is not None:
            where.append('r.app_id = ?')
            params.append(app_id)
        if version:
            where.append('r.version = ?')
            params.append(version)
        if date_from:
            where.append('r.review_date >= ?')
            params.append(date_from)
        if date_to:
            where.append('r.review_date <= ?')
            params.append(date_to)
        where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
        sql = (
            'SELECT s.sentiment_label, COUNT(*) FROM sentiment_results s '
            'JOIN reviews r ON r.id = s.review_id '
            f'{where_sql} GROUP BY s.sentiment_label'
        )
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        out = {'positive': 0, 'neutral': 0, 'negative': 0}
        for label, cnt in rows:
            out[str(label)] = int(cnt)
        return out
