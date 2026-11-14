import os
from pathlib import Path
from typing import List, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from database.handler import Database


MODEL_DIR = Path(__file__).resolve().parents[1] / 'models'
MODEL_DIR.mkdir(parents=True, exist_ok=True)
VEC_PATH = MODEL_DIR / 'tfidf_vectorizer.pkl'
MODEL_PATH = MODEL_DIR / 'sentiment_model.pkl'


def _label_from_rating(r: int) -> str:
    if r is None:
        return 'neutral'
    try:
        r = int(r)
    except Exception:
        return 'neutral'
    if r >= 4:
        return 'positive'
    if r <= 2:
        return 'negative'
    return 'neutral'


def _load_training_data(db: Database) -> Tuple[List[str], List[str]]:
    cur = db.conn.cursor()
    cur.execute(
        'SELECT c.cleaned_text, r.rating FROM cleaned_reviews c '
        'JOIN reviews r ON r.id = c.review_id '
        'WHERE c.cleaned_text IS NOT NULL AND LENGTH(c.cleaned_text) > 0 AND r.rating IS NOT NULL'
    )
    rows = cur.fetchall()
    X = [str(t[0]) for t in rows]
    y = [_label_from_rating(int(t[1])) for t in rows]
    return X, y


def train_from_db(db: Database, min_per_class: int = 30) -> bool:
    X, y = _load_training_data(db)
    if not X:
        return False
    # Ensure class balance existence
    counts = {k: y.count(k) for k in {'positive', 'neutral', 'negative'}}
    if any(counts[k] < min_per_class for k in counts):
        # still proceed but warn via return value
        pass
    # Try robust vectorization settings for tiny datasets
    tried = [
        dict(ngram_range=(1, 2), max_features=10000, min_df=2),
        dict(ngram_range=(1, 2), max_features=10000, min_df=1),
        dict(analyzer='char_wb', ngram_range=(3, 5), max_features=20000, min_df=1),
    ]
    vec = None
    Xv = None
    last_err = None
    for params in tried:
        try:
            v = TfidfVectorizer(**params)
            Xv_try = v.fit_transform(X)
            if Xv_try is not None and Xv_try.shape[1] > 0:
                vec = v
                Xv = Xv_try
                break
        except Exception as ex:
            last_err = ex
            continue
    if vec is None or Xv is None or Xv.shape[1] == 0:
        return False
    clf = LogisticRegression(max_iter=1000, class_weight='balanced')
    clf.fit(Xv, y)
    joblib.dump(vec, VEC_PATH)
    joblib.dump(clf, MODEL_PATH)
    return True


def _ensure_model(db: Database) -> bool:
    # Ensure files exist and are non-empty, and loadable
    if VEC_PATH.exists() and MODEL_PATH.exists():
        try:
            if VEC_PATH.stat().st_size > 0 and MODEL_PATH.stat().st_size > 0:
                _ = joblib.load(VEC_PATH)
                _ = joblib.load(MODEL_PATH)
                return True
        except Exception:
            pass
    return train_from_db(db)


def predict_and_store(db: Database, batch_size: int = 10000) -> int:
    if not _ensure_model(db):
        return 0
    vec = joblib.load(VEC_PATH)
    clf = joblib.load(MODEL_PATH)

    total = 0
    while True:
        batch: List[Tuple[int, str]] = db.fetch_cleaned_without_sentiment(limit=batch_size)
        if not batch:
            break
        texts = [b[1] or '' for b in batch]
        if not any(len(t) > 0 for t in texts):
            break
        Xv = vec.transform(texts)
        probs = None
        try:
            probs = clf.predict_proba(Xv)
        except Exception:
            pass
        preds = clf.predict(Xv)
        rows = []
        for i, (rid, _) in enumerate(batch):
            label = str(preds[i])
            score = float(np.max(probs[i])) if probs is not None else 0.0
            rows.append((rid, label, score))
        if rows:
            db.insert_sentiment_batch(rows)
            total += len(rows)
    return total


def run_sentiment(db: Database, force_retrain: bool = False) -> int:
    if force_retrain or not (VEC_PATH.exists() and MODEL_PATH.exists()):
        _ = train_from_db(db)
    return predict_and_store(db)
