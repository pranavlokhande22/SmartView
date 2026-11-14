import io
import inspect
import asyncio
import os
import tempfile
from typing import Optional
from pathlib import Path

from nicegui import ui

from database.handler import Database
from src import ingestion
from src.preprocessing.preprocess import run_preprocessing
from src.classifier.sentiment_model import run_sentiment
from src.theme_extractor import generate_recommendations
from src.exporter import export_sentiment_counts, export_recommendations_csv, export_chart_png


def _get_apps(db: Database):
    return db.get_apps()


def _get_chart_colors(is_light_mode: bool = False) -> dict:
    """Return theme-aware colors for charts"""
    if is_light_mode:
        return {
            'text': '#0f172a',
            'muted': '#64748b',
            'axis': '#475569',
            'grid': '#e2e8f0',
            'border': '#cbd5e1',
            'tooltip_bg': 'rgba(255, 255, 255, 0.95)',
            'tooltip_border': '#e2e8f0',
        }
    else:
        return {
            'text': '#e5e7eb',
            'muted': '#cbd5e1',
            'axis': '#cbd5e1',
            'grid': 'rgba(148,163,184,0.15)',
            'border': '#334155',
            'tooltip_bg': 'rgba(15, 23, 42, 0.9)',
            'tooltip_border': '#1f2937',
        }


def _detect_light_mode() -> bool:
    """Detect if light mode is active by checking data-theme attribute"""
    try:
        result = ui.run_javascript("document.documentElement.dataset.theme === 'light'")
        return result if result is not None else False
    except:
        return False


def _echart_options(counts: dict) -> dict:
    is_light = _detect_light_mode()
    colors = _get_chart_colors(is_light)
    
    pos = int(counts.get('positive', 0))
    neu = int(counts.get('neutral', 0))
    neg = int(counts.get('negative', 0))
    total = pos + neu + neg
    
    # Calculate percentages
    pos_pct = round((pos / total * 100), 1) if total > 0 else 0
    neu_pct = round((neu / total * 100), 1) if total > 0 else 0
    neg_pct = round((neg / total * 100), 1) if total > 0 else 0
    
    data = [
        {'name': 'Positive', 'value': pos},
        {'name': 'Neutral', 'value': neu},
        {'name': 'Negative', 'value': neg},
    ]
    
    return {
        'backgroundColor': 'transparent',
        'title': {'show': False},
        'tooltip': {
            'trigger': 'item',
            'formatter': '{b}: {c} ({d}%)',
            'textStyle': {'color': colors['text']},
            'backgroundColor': colors['tooltip_bg'],
            'borderColor': colors['tooltip_border'],
        },
        'legend': {
            'show': True,
            'orient': 'horizontal',
            'top': 'top',
            'textStyle': {'color': colors['text'], 'fontSize': 13},
            'itemGap': 20,
            'data': [
                {'name': 'Positive', 'icon': 'circle'},
                {'name': 'Neutral', 'icon': 'circle'},
                {'name': 'Negative', 'icon': 'circle'},
            ]
        },
        'graphic': [] if total > 0 else [{
            'type': 'text', 'left': 'center', 'top': 'middle',
            'style': {'text': 'No data', 'fill': colors['muted'], 'fontSize': 18, 'fontWeight': 'bold'}
        }],
        'series': [{
            'name': 'Sentiment',
            'type': 'pie',
            'radius': ['45%', '70%'],
            'center': ['50%', '55%'],
            'avoidLabelOverlap': True,
            'label': {
                'show': True,
                'position': 'outside',
                'formatter': '{b}\n{d}%',
                'color': colors['text'],
                'fontSize': 12,
                'fontWeight': 'bold',
                'distance': 15,
            },
            'labelLine': {
                'show': True,
                'length': 10,
                'length2': 5,
                'lineStyle': {'color': colors['axis'], 'width': 1}
            },
            'data': data,
            'itemStyle': {
                'borderColor': colors['text'],
                'borderWidth': 2,
            },
            'emphasis': {
                'scale': True,
                'scaleSize': 8,
                'itemStyle': {'borderColor': '#4f46e5', 'borderWidth': 3}
            },
            'color': ['#22c55e', '#3b82f6', '#ef4444'],
        }],
    }

def _render_counts(db: Database, app_id: Optional[int]) -> dict:
    return db.get_sentiment_counts(app_id=app_id)

def _matplotlib_figure_from_counts(counts: dict):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5, 5))
    labels = ['positive', 'neutral', 'negative']
    sizes = [int(counts.get('positive', 0)), int(counts.get('neutral', 0)), int(counts.get('negative', 0))]
    total = sum(sizes)
    if total > 0:
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#22c55e', '#3b82f6', '#ef4444'])
    else:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
    ax.set_title('Sentiment Distribution')
    return fig


def mount_ui(db: Database):
    selected_app: dict = {'id': None}
    apps_select = {'obj': None}
    chart_ref = {'obj': None}
    last_file = {'path': None}
    recs_state = {'rows': []}

    def _style_btn(b):
        b.props('color=indigo text-color=white no-caps unelevated rounded size=lg')
        b.classes('q-mr-sm q-mb-sm')
        return b

    with ui.row().classes('w-full items-center gap-4'):
        status = ui.label('Ready.').style('display:none')

    # Centered alert dialog helper
    with ui.dialog() as alert_dialog:
        with ui.card().classes('items-center justify-center text-center p-6'):
            alert_label = ui.label('').classes('text-lg')

    def show_alert(msg: str, duration: float = 2.5):
        alert_label.text = msg
        alert_dialog.open()
        ui.timer(duration, lambda: alert_dialog.close(), once=True)

    with ui.element('section').classes('section reveal'):
        ui.label('Data Ingestion').classes('text-h6')
        async def _ensure_bytes(obj):
            if obj is None:
                return None
            # Await awaitables
            if inspect.isawaitable(obj):
                obj = await obj
            # Resolve file-like .read()
            if hasattr(obj, 'read'):
                r = obj.read()
                if inspect.isawaitable(r):
                    r = await r
                obj = r
            # Buffer types
            if isinstance(obj, (bytes, bytearray)):
                return bytes(obj)
            if isinstance(obj, io.BytesIO):
                return obj.getvalue()
            return None

        async def _get_bytes_from_event(e):
            try:
                for cand in [getattr(e, 'content', None), getattr(e, 'file', None)]:
                    b = await _ensure_bytes(cand)
                    if b:
                        return b
                files = getattr(e, 'files', None)
                if files:
                    for f in files:
                        b = await _ensure_bytes(getattr(f, 'content', None) or f)
                        if b:
                            return b
            except Exception:
                return None
            return None

        async def _save_event(e, dest_path: str):
            saver = getattr(e, 'save', None)
            if callable(saver):
                res = saver(dest_path)
                if inspect.isawaitable(res):
                    await res
                return dest_path
            # fallback
            b = await _get_bytes_from_event(e)
            if b is None:
                raise ValueError('No upload content')
            with open(dest_path, 'wb') as f:
                f.write(b)
            return dest_path

        async def on_upload(e):
            try:
                ext = os.path.splitext(getattr(e, 'name', ''))[1] or '.csv'
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp.close()
                saved_path = await _save_event(e, tmp.name)
                last_file['path'] = saved_path
                show_alert('Processing upload...', duration=0.5)
                info = ingestion.ingest_file(saved_path, db)
                status.text = f"Ingested: {info['inserted']}/{info['total_rows']}"
                show_alert(status.text, duration=2.0)
                sel = apps_select['obj']
                if sel:
                    sel.options = {i: name for i, name in _get_apps(db)}
            except Exception as ex:
                msg = str(ex) or ex.__class__.__name__
                status.text = f'Upload error: {msg}'
                show_alert(status.text, duration=2.0)
        with ui.element('div').classes('panel'):
            with ui.element('div').classes('flex justify-center'):
                uploader = ui.upload(on_upload=on_upload, auto_upload=True, label='Upload CSV/XLSX')
                uploader.props('color=indigo')
                uploader.classes('q-mb-sm')

            file_path = ui.input('Or enter local CSV/XLSX path').props('filled color=indigo').classes('w-96 q-mb-sm')
            ingest_btn = _style_btn(ui.button('Ingest File'))
            _style_btn(ui.button('Ingest Sample Dataset', on_click=lambda: manual_ingest_sample()))

        def manual_ingest():
            try:
                path = (file_path.value or '').strip()
                if not path:
                    # fallback to last uploaded file if available
                    if last_file['path']:
                        path = last_file['path']
                    else:
                        raise FileNotFoundError('No path provided. Use Upload above or type a local path.')
                show_alert('Processing file...', duration=0.5)
                info = ingestion.ingest_file(path, db)
                status.text = f"Ingested: {info['inserted']}/{info['total_rows']}"
                show_alert(status.text, duration=2.0)
                sel = apps_select['obj']
                if sel:
                    sel.options = {i: name for i, name in _get_apps(db)}
                    sel.update()
            except Exception as ex:
                msg = str(ex) or ex.__class__.__name__
                status.text = f'Ingest error: {msg}'
                show_alert(status.text, duration=2.0)
        ingest_btn.on('click', manual_ingest)

        def manual_ingest_sample():
            try:
                sample = 'data/raw/sample_reviews.csv'
                show_alert('Loading sample data...', duration=0.5)
                info = ingestion.ingest_file(sample, db)
                status.text = f"Sample ingested: {info['inserted']}/{info['total_rows']}"
                show_alert(status.text, duration=2.0)
                sel = apps_select['obj']
                if sel:
                    sel.options = {i: name for i, name in _get_apps(db)}
                    sel.update()
            except Exception as ex:
                msg = str(ex) or ex.__class__.__name__
                status.text = f'Ingest error: {msg}'
                show_alert(status.text, duration=2.0)

        def toggle_ingest_btn(e=None):
            ingest_btn.disabled = not bool((file_path.value or '').strip()) and not bool(last_file['path'])
        file_path.on('update:model-value', toggle_ingest_btn)
        toggle_ingest_btn()

    with ui.element('section').classes('section reveal'):
        ui.label('Processing').classes('text-h6')

        def refresh_chart():
            c = _render_counts(db, selected_app['id'])
            ch = chart_ref['obj']
            if ch is not None:
                ch.options = _echart_options(c)
                ch.update()

        def do_preprocess():
            show_alert('Preprocessing reviews...', duration=0.5)
            n = run_preprocessing(db)
            setattr(status, 'text', f'Preprocessing done. Cleaned: {n}')
            show_alert(status.text, duration=2.0)
            refresh_chart()

        def do_sentiment():
            show_alert('Analyzing sentiment...', duration=0.5)
            n = run_sentiment(db, force_retrain=False)
            setattr(status, 'text', f'Sentiment done. Predicted: {n}')
            show_alert(status.text, duration=2.0)
            refresh_chart()

        # Processing actions combined in a single boxed panel
        def do_themes():
            show_alert('Extracting themes...', duration=0.5)
            app_id = selected_app['id']
            recs = generate_recommendations(db, app_id=app_id, version=None)
            recs_state['rows'] = [{'theme': t, 'recommendation': r, 'severity': s} for (t, r, s) in recs]
            recs_table.rows = recs_state['rows']
            recs_table.update()
            setattr(status, 'text', f'Recommendations computed: {len(recs)}')
            show_alert(status.text, duration=2.0)

        def run_full_pipeline():
            show_alert('Running full pipeline...', duration=0.5)
            do_preprocess()
            do_sentiment()
            do_themes()
            show_alert('Pipeline complete!', duration=2.0)

        with ui.element('div').classes('panel'):
            with ui.row().classes('items-center q-gutter-sm flex-wrap'):
                _style_btn(ui.button('Run Preprocessing', on_click=do_preprocess))
                _style_btn(ui.button('Run Sentiment', on_click=do_sentiment))
                _style_btn(ui.button('Generate Themes & Recommendations', on_click=do_themes))
                _style_btn(ui.button('Run Full Pipeline', on_click=run_full_pipeline))

    with ui.element('section').classes('section reveal'):
        ui.label('Filters').classes('text-h6')
        with ui.element('div').classes('panel'):
            apps_select['obj'] = ui.select(options={i: name for i, name in _get_apps(db)}, label='Select App', with_input=False).props('filled color=indigo popup-content-class=select-menu-dark options-dense').classes('w-96 select-themed')
        def on_app_change(e):
            selected_app['id'] = e.value
            c = _render_counts(db, selected_app['id'])
            ch = chart_ref['obj']
            if ch is not None:
                ch.options = _echart_options(c)
                ch.update()
            show_alert('Chart updated', duration=1.5)
        apps_select['obj'].on('update:model-value', on_app_change)

    with ui.element('section').classes('section section-wide'):
        with ui.row().classes('items-center gap-3'):
            ui.label('📊').classes('text-h5')
            with ui.column().classes('gap-1'):
                ui.label('Sentiment Distribution').classes('text-h6 font-bold')
                ui.label('Overview of review sentiment breakdown. Green = Positive, Blue = Neutral, Red = Negative. Select an app to filter by specific application.').classes('text-caption text-grey-7')
        with ui.element('div').classes('panel'):
            chart_ref['obj'] = ui.echart(options=_echart_options(_render_counts(db, None))).style('width:clamp(320px,50vw,680px);height:420px;margin:0 auto;background:transparent')
            ui.timer(0.3, lambda: (chart_ref['obj'] and chart_ref['obj'].update()), once=True)
            ui.timer(0.35, lambda: ui.run_javascript('window.dispatchEvent(new Event("resize"))'), once=True)

    with ui.element('section').classes('section reveal'):
        ui.label('Recommendations').classes('text-h6')
        recs_columns = [
            {'name': 'theme', 'label': 'Theme', 'field': 'theme'},
            {'name': 'severity', 'label': 'Severity', 'field': 'severity'},
            {'name': 'recommendation', 'label': 'Recommendation', 'field': 'recommendation'},
        ]
        with ui.element('div').classes('panel'):
            recs_table = ui.table(columns=recs_columns, rows=[]).classes('w-full table-themed').props('flat bordered dark separator=cell dense')

    with ui.element('section').classes('section reveal'):
        ui.label('Export').classes('text-h6')
        def export_counts():
            show_alert('Exporting sentiment data...', duration=0.5)
            p = export_sentiment_counts(db, selected_app['id'])
            setattr(status, 'text', f'Exported sentiment CSV: {p}')
            show_alert(status.text, duration=1.8)
            ui.download(Path(p).as_posix())
        def export_recs():
            if not recs_state['rows']:
                setattr(status, 'text', 'No recommendations to export. Click Generate Themes & Recommendations.')
                show_alert(status.text, duration=1.5)
                return
            show_alert('Exporting recommendations...', duration=0.5)
            rows = recs_state['rows']
            p = export_recommendations_csv([(r['theme'], r['recommendation'], r['severity']) for r in rows])
            setattr(status, 'text', f'Exported recommendations CSV: {p}')
            show_alert(status.text, duration=1.8)
            ui.download(Path(p).as_posix())
        def export_chart():
            show_alert('Generating chart...', duration=0.5)
            counts = _render_counts(db, selected_app['id'])
            fig = _matplotlib_figure_from_counts(counts)
            p = export_chart_png(fig)
            setattr(status, 'text', f'Exported chart PNG: {p}')
            show_alert(status.text, duration=1.8)
            ui.download(Path(p).as_posix())
        with ui.element('div').classes('panel'):
            _style_btn(ui.button('Export Sentiment CSV', on_click=export_counts))
            _style_btn(ui.button('Export Recommendations CSV', on_click=export_recs))
            _style_btn(ui.button('Export Current Chart PNG', on_click=export_chart))

    # Footer handled by site routes
