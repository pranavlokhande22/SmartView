import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from database.handler import Database


def _ts() -> str:
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def ensure_dirs() -> Dict[str, str]:
    base = Path('exports')
    charts = base / 'charts'
    csvdir = base / 'csv'
    base.mkdir(exist_ok=True)
    charts.mkdir(parents=True, exist_ok=True)
    csvdir.mkdir(parents=True, exist_ok=True)
    return {'base': str(base), 'charts': str(charts), 'csv': str(csvdir)}


def export_sentiment_counts(db: Database, app_id: Optional[int]) -> str:
    paths = ensure_dirs()
    counts = db.get_sentiment_counts(app_id=app_id)
    out_path = os.path.join(paths['csv'], f'sentiment_counts_{_ts()}.csv')
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['label', 'count'])
        for k, v in counts.items():
            w.writerow([k, v])
    return out_path


def export_recommendations_csv(recs: List[Tuple[str, str, float]]) -> str:
    paths = ensure_dirs()
    out_path = os.path.join(paths['csv'], f'recommendations_{_ts()}.csv')
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['theme', 'recommendation', 'severity'])
        for theme, rec, sev in recs:
            w.writerow([theme, rec, sev])
    return out_path


def export_chart_png(fig) -> str:
    paths = ensure_dirs()
    out_path = os.path.join(paths['charts'], f'chart_{_ts()}.png')
    fig.savefig(out_path, dpi=200, bbox_inches='tight')
    return out_path
