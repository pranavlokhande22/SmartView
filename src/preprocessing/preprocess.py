import re
import string
from typing import List, Tuple

try:
    from nltk.stem import PorterStemmer  # type: ignore
except Exception:  # nltk not available; provide a no-op fallback
    class PorterStemmer:  # type: ignore
        def stem(self, w: str) -> str:
            return w

from database.handler import Database


# Minimal offline stopword list (extendable)
STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'if', 'while', 'with', 'for', 'on', 'in', 'to', 'from', 'by', 'of',
    'this', 'that', 'these', 'those', 'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being', 'it', 'as', 'at',
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'they', 'them', 'his', 'her', 'their', 'its',
    'not', "don't", "didn't", "isn't", "wasn't", "aren't", "weren't", "can't", "couldn't", "won't",
}

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
EMOJI_RE = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
PUNCT_TABLE = str.maketrans('', '', string.punctuation)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str, stemmer: PorterStemmer) -> Tuple[str, int]:
    if not text:
        return "", 0
    t = text.lower()
    t = URL_RE.sub(" ", t)
    t = EMOJI_RE.sub(" ", t)
    t = t.translate(PUNCT_TABLE)
    t = re.sub(r"[^a-z\s]", " ", t)
    tokens = [w for w in t.split() if w and w not in STOPWORDS and len(w) > 1]
    stemmed = [stemmer.stem(w) for w in tokens]
    cleaned = _normalize_whitespace(" ".join(stemmed))
    return cleaned, len(stemmed)


def run_preprocessing(db: Database, batch_size: int = 10000) -> int:
    """Process reviews lacking cleaned text and write to cleaned_reviews.

    Returns total processed rows.
    """
    total = 0
    stemmer = PorterStemmer()
    while True:
        batch: List[Tuple[int, str]] = db.fetch_reviews_without_cleaned(limit=batch_size)
        if not batch:
            break
        out_rows: List[Tuple[int, str, int]] = []
        for review_id, raw_text in batch:
            cleaned, token_count = clean_text(raw_text or "", stemmer)
            out_rows.append((review_id, cleaned, token_count))
        if out_rows:
            db.insert_cleaned_batch(out_rows)
            total += len(out_rows)
    return total

