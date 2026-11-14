import re
import math
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from database.handler import Database


THEME_KEYWORDS = {
    'crash': {'crash', 'crashes', 'crashin', 'force close', 'stopp', 'stop', 'hang', 'freeze', 'freez'},
    'battery': {'battery', 'drain', 'overheat', 'over heat'},
    'login': {'login', 'log in', 'signin', 'sign in', 'auth', 'otp'},
    'performance': {'lag', 'lagg', 'slow', 'delay', 'latency', 'stutter'},
    'ui': {'ui', 'interfac', 'design', 'button', 'layout', 'screen'},
    'payment': {'payment', 'pay', 'upi', 'refund', 'transact'},
    'notification': {'notification', 'notify', 'alert'},
    'ads': {'ad', 'ads', 'advert'},
}


def _tokenize(text: str) -> List[str]:
    return [t for t in text.split() if t]


def _ngrams(tokens: List[str], n: int) -> List[str]:
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)] if n >= 1 else []


def _map_to_theme(token: str) -> Optional[str]:
    t = token.lower()
    for theme, keys in THEME_KEYWORDS.items():
        for k in keys:
            if k in t:
                return theme
    return None


def compute_theme_counts(db: Database, app_id: Optional[int] = None, version: Optional[str] = None,
                          date_from: Optional[str] = None, date_to: Optional[str] = None,
                          top_k: int = 20) -> Dict[str, int]:
    cur = db.conn.cursor()
    where = ["s.sentiment_label = 'negative'"]
    params: List = []
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
    where_sql = 'WHERE ' + ' AND '.join(where)
    cur.execute(
        'SELECT c.cleaned_text, r.review_date FROM cleaned_reviews c '
        'JOIN sentiment_results s ON s.review_id = c.review_id '
        'JOIN reviews r ON r.id = c.review_id '
        f'{where_sql}',
        tuple(params),
    )
    rows = cur.fetchall()
    counts: Counter = Counter()
    for cleaned, _dt in rows:
        tokens = _tokenize(cleaned or '')
        for n in (1, 2, 3):
            for ng in _ngrams(tokens, n):
                theme = _map_to_theme(ng)
                if theme:
                    counts[theme] += 1
    # take top_k
    return dict(counts.most_common(top_k))


def _normalize01(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    v = (x - lo) / (hi - lo)
    return max(0.0, min(1.0, v))


def _recency_score(dates: List[Optional[str]]) -> float:
    # Simple: fraction of reviews in last 30 days
    now = datetime.utcnow().date()
    recent = 0
    total = 0
    for d in dates:
        if not d:
            continue
        try:
            dt = datetime.strptime(d, '%Y-%m-%d').date()
        except Exception:
            continue
        total += 1
        if (now - dt).days <= 30:
            recent += 1
    if total == 0:
        return 0.5
    return recent / total


def generate_recommendations(db: Database, app_id: Optional[int] = None, version: Optional[str] = None,
                              date_from: Optional[str] = None, date_to: Optional[str] = None,
                              top_n: int = 5) -> List[Tuple[str, str, float]]:
    # Compute theme counts and simple negativity/recency
    theme_counts = compute_theme_counts(db, app_id, version, date_from, date_to, top_k=50)

    # negativity: all are negatives (1.0)
    neg_score = 1.0

    # recency from dates of negative reviews
    cur = db.conn.cursor()
    where = ["s.sentiment_label = 'negative'"]
    params: List = []
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
    where_sql = 'WHERE ' + ' AND '.join(where)
    cur.execute(
        'SELECT r.review_date FROM sentiment_results s '
        'JOIN reviews r ON r.id = s.review_id '
        f'{where_sql}',
        tuple(params),
    )
    dates = [row[0] for row in cur.fetchall()]
    recency = _recency_score(dates)

    # normalize frequency
    if theme_counts:
        max_f = max(theme_counts.values())
    else:
        max_f = 1

    recs: List[Tuple[str, str, float]] = []
    for theme, freq in theme_counts.items():
        freq_score = _normalize01(freq, 0, max_f)
        severity = (0.5 * freq_score) + (0.3 * neg_score) + (0.2 * recency)
        sev100 = round(severity * 100.0, 2)
        action = _theme_to_action(theme)
        recs.append((theme, action, sev100))

    recs.sort(key=lambda x: x[2], reverse=True)

    # Store to recommendations table if app is specified
    if app_id is not None:
        _store_recommendations(db, app_id, version, recs[:top_n])

    return recs[:top_n]


def _theme_to_action(theme: str) -> str:
    mapping = {
        'crash': 'Stabilize crash-prone flows; analyze crash logs and fix exceptions in media/upload modules.',
        'battery': 'Optimize background sync and wakelocks; reduce polling and excessive CPU usage.',
        'login': 'Improve auth latency/reliability; add retries, better error messages, and fallback flows.',
        'performance': 'Profile rendering and network calls; reduce main-thread work and optimize caching.',
        'ui': 'Refine layout and touch targets; ensure accessibility and consistent components.',
        'payment': 'Harden payment flows; better error handling and reconciliation; add detailed logs.',
        'notification': 'Ensure reliable delivery; check channels and background restrictions; debounced sends.',
        'ads': 'Limit disruptive ad frequency; avoid interstitials on critical tasks; respect user context.',
        'other': 'Triage grouped feedback; monitor logs; prioritize based on frequency and recency.',
    }
    return mapping.get(theme, mapping['other'])


def _store_recommendations(db: Database, app_id: int, version: Optional[str],
                           items: List[Tuple[str, str, float]]) -> None:
    cur = db.conn.cursor()
    if version:
        cur.execute('DELETE FROM recommendations WHERE app_id=? AND version=?', (app_id, version))
    else:
        cur.execute('DELETE FROM recommendations WHERE app_id=? AND (version IS NULL OR version="")', (app_id,))
    rows = [(t, rec, float(sev), app_id, version) for (t, rec, sev) in items]
    cur.executemany(
        'INSERT INTO recommendations(theme_label, recommendation_text, severity, app_id, version) VALUES (?,?,?,?,?)',
        rows,
    )
    db.conn.commit()
