"""Advanced Analytics Page with Time-Series, Rating Correlation, and Severity Leaderboard"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from nicegui import ui
from database.handler import Database


def _get_chart_colors(is_light_mode: bool = False) -> Dict:
    """Return theme-aware colors for charts"""
    if is_light_mode:
        return {
            'text': '#0f172a',
            'muted': '#64748b',
            'axis': '#475569',
            'grid': '#e2e8f0',
            'border': '#cbd5e1',
        }
    else:
        return {
            'text': '#e5e7eb',
            'muted': '#cbd5e1',
            'axis': '#cbd5e1',
            'grid': 'rgba(148,163,184,0.15)',
            'border': '#334155',
        }


def _detect_light_mode() -> bool:
    """Detect if light mode is active by checking data-theme attribute"""
    try:
        result = ui.run_javascript("document.documentElement.dataset.theme === 'light'")
        return result if result is not None else False
    except:
        return False


def _get_time_series_data(db: Database, app_id: Optional[int], date_from: str, date_to: str) -> Dict:
    """Get sentiment and volume data grouped by date (uses review_date if available, else groups by week)"""
    cur = db.conn.cursor()
    
    # Build WHERE clause - try to use review_date if available, otherwise show all
    where = []
    params = []
    
    if app_id:
        where.append("r.app_id = ?")
        params.append(app_id)
    
    # Only filter by date if review_date is not null
    where.append("r.review_date IS NOT NULL")
    where.append("r.review_date >= ?")
    params.append(date_from)
    where.append("r.review_date <= ?")
    params.append(date_to)
    
    where_sql = " AND ".join(where)
    
    try:
        cur.execute(f"""
            SELECT r.review_date, s.sentiment_label, COUNT(*) as count
            FROM reviews r
            LEFT JOIN sentiment_results s ON s.review_id = r.id
            WHERE {where_sql}
            GROUP BY r.review_date, s.sentiment_label
            ORDER BY r.review_date ASC
        """, tuple(params))
        
        rows = cur.fetchall()
        print(f"[TS] Query returned {len(rows)} rows | app_id={app_id} | date_from={date_from} | date_to={date_to}")
    except Exception as e:
        print(f"[TS] SQL Error: {e}")
        return {}
    
    # If no date data, show sentiment distribution by app instead
    if not rows:
        print("[TS] No date data found, showing sentiment distribution instead")
        where2 = []
        params2 = []
        if app_id:
            where2.append("r.app_id = ?")
            params2.append(app_id)
        where2_sql = " AND ".join(where2) if where2 else "1=1"
        
        cur.execute(f"""
            SELECT s.sentiment_label, COUNT(*) as count
            FROM reviews r
            LEFT JOIN sentiment_results s ON s.review_id = r.id
            WHERE {where2_sql}
            GROUP BY s.sentiment_label
        """, tuple(params2))
        
        dist_rows = cur.fetchall()
        data_by_date = {'Overall': {'positive': 0, 'neutral': 0, 'negative': 0, 'total': 0}}
        for sentiment, count in dist_rows:
            sentiment_label = sentiment or 'unknown'
            if sentiment_label in data_by_date['Overall']:
                data_by_date['Overall'][sentiment_label] = count
            data_by_date['Overall']['total'] += count
        print(f"[TS] Sentiment distribution: {data_by_date}")
        return data_by_date
    
    # Organize by date
    data_by_date = {}
    for date, sentiment, count in rows:
        if date not in data_by_date:
            data_by_date[date] = {'positive': 0, 'neutral': 0, 'negative': 0, 'total': 0}
        sentiment_label = sentiment or 'unknown'
        if sentiment_label in data_by_date[date]:
            data_by_date[date][sentiment_label] = count
        data_by_date[date]['total'] += count
    
    print(f"[TS] Organized data: {len(data_by_date)} dates")
    return data_by_date


def _get_rating_sentiment_correlation(db: Database, app_id: Optional[int]) -> List[Tuple]:
    """Get rating vs sentiment data for correlation analysis (or sentiment distribution if no ratings)"""
    cur = db.conn.cursor()
    
    where = ["r.rating IS NOT NULL"]
    params = []
    
    if app_id:
        where.append("r.app_id = ?")
        params.append(app_id)
    
    where_sql = " AND ".join(where)
    
    try:
        cur.execute(f"""
            SELECT r.rating, s.sentiment_label, COUNT(*) as count
            FROM reviews r
            LEFT JOIN sentiment_results s ON s.review_id = r.id
            WHERE {where_sql}
            GROUP BY r.rating, s.sentiment_label
        """, tuple(params))
        
        rows = cur.fetchall()
        print(f"[CORR] Query returned {len(rows)} rows | app_id={app_id}")
        
        # If no rating data, show sentiment distribution instead
        if not rows:
            print("[CORR] No rating data found, showing sentiment distribution instead")
            where2 = []
            params2 = []
            if app_id:
                where2.append("r.app_id = ?")
                params2.append(app_id)
            where2_sql = " AND ".join(where2) if where2 else "1=1"
            
            cur.execute(f"""
                SELECT s.sentiment_label, COUNT(*) as count
                FROM reviews r
                LEFT JOIN sentiment_results s ON s.review_id = r.id
                WHERE {where2_sql}
                GROUP BY s.sentiment_label
            """, tuple(params2))
            
            dist_rows = cur.fetchall()
            # Convert to rating-like format (use sentiment index as "rating")
            sentiment_to_rating = {'positive': 5, 'neutral': 3, 'negative': 1}
            converted = [(sentiment_to_rating.get(s[0], 3), s[0], s[1]) for s in dist_rows]
            print(f"[CORR] Sentiment distribution: {converted}")
            return converted
        
        return rows
    except Exception as e:
        print(f"[CORR] SQL Error: {e}")
        return []


def _compute_severity_leaderboard(db: Database, app_id: Optional[int], date_from: str, date_to: str) -> List[Dict]:
    """
    Compute severity leaderboard: severity = frequency × negativity × recency
    Returns list of themes with severity scores and trend data
    """
    from src.theme_extractor import compute_theme_counts, _recency_score
    
    try:
        # Get theme counts
        theme_counts = compute_theme_counts(db, app_id=app_id, date_from=date_from, date_to=date_to, top_k=20)
        print(f"[LEAD] Theme counts: {theme_counts} | app_id={app_id}")
        
        if not theme_counts:
            print("[LEAD] No theme counts found")
            return []
        
        # Get negativity scores per theme
        cur = db.conn.cursor()
        where = ["s.sentiment_label = 'negative'"]
        params = []
        
        if app_id:
            where.append("r.app_id = ?")
            params.append(app_id)
        
        where.append("r.review_date >= ?")
        params.append(date_from)
        where.append("r.review_date <= ?")
        params.append(date_to)
        
        where_sql = " AND ".join(where)
        
        cur.execute(f"""
            SELECT r.review_date FROM sentiment_results s
            JOIN reviews r ON r.id = s.review_id
            WHERE {where_sql}
        """, tuple(params))
        
        dates = [row[0] for row in cur.fetchall()]
        print(f"[LEAD] Found {len(dates)} negative review dates")
        recency = _recency_score(dates)
        
        # Normalize frequency
        max_freq = max(theme_counts.values()) if theme_counts else 1
        
        leaderboard = []
        for theme, freq in theme_counts.items():
            freq_score = freq / max_freq if max_freq > 0 else 0
            negativity_score = 1.0  # All themes are from negative reviews
            severity = (0.5 * freq_score) + (0.3 * negativity_score) + (0.2 * recency)
            severity_pct = round(severity * 100, 2)
            
            leaderboard.append({
                'theme': theme,
                'frequency': freq,
                'severity': severity_pct,
                'recency_score': round(recency * 100, 2)
            })
        
        leaderboard.sort(key=lambda x: x['severity'], reverse=True)
        print(f"[LEAD] Leaderboard: {len(leaderboard)} themes")
        return leaderboard
    except Exception as e:
        print(f"[LEAD] Error: {e}")
        return []


def mount_analytics(db: Database):
    """Mount analytics page with advanced features"""
    
    # Get data availability stats
    cur = db.conn.cursor()
    cur.execute('SELECT COUNT(*) FROM reviews')
    total_reviews = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM sentiment_results')
    sentiment_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM reviews WHERE rating IS NOT NULL')
    rated_reviews = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM reviews WHERE review_date IS NOT NULL')
    dated_reviews = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM apps')
    total_apps = cur.fetchone()[0]

    # Determine global date range present in DB (for better defaults)
    min_date, max_date = None, None
    try:
        cur.execute("SELECT MIN(review_date), MAX(review_date) FROM reviews WHERE review_date IS NOT NULL")
        row = cur.fetchone()
        if row:
            min_date, max_date = row[0], row[1]
    except Exception:
        pass
    
    # Page header
    with ui.element('section').classes('section reveal'):
        ui.html('<h2>Advanced Analytics</h2>', sanitize=False)
        ui.html('<p>Visualize trends, correlations, and severity rankings</p>', sanitize=False)
    
    # Data availability summary
    with ui.element('section').classes('section reveal'):
        ui.label('Data Summary').classes('text-h6')
        with ui.element('div').classes('panel'):
            with ui.row().classes('items-center gap-8 flex-wrap'):
                ui.label(f'📊 Total Reviews: {total_reviews:,}').classes('text-body1')
                ui.label(f'😊 Sentiment Analyzed: {sentiment_count:,}').classes('text-body1')
                ui.label(f'⭐ With Ratings: {rated_reviews:,}').classes('text-body1')
                ui.label(f'📅 With Dates: {dated_reviews:,}').classes('text-body1')
                ui.label(f'📱 Apps: {total_apps:,}').classes('text-body1')
    
    # Filters section
    with ui.element('section').classes('section reveal'):
        ui.label('Filters').classes('text-h6')
        with ui.element('div').classes('panel'):
            with ui.row().classes('items-center gap-4 flex-wrap'):
                # App selector with "All Apps" option
                apps_list = db.get_apps()
                apps = {'All Apps': None}  # Default: no app filter
                apps.update({i: name for i, name in apps_list})
                
                app_select = ui.select(options=apps, label='App', with_input=False, value=None).props(
                    'filled color=indigo popup-content-class=select-menu-dark options-dense dark'
                ).classes('w-96 select-themed')
                
                # Date range (prefer DB range if available)
                today = datetime.now().date()
                thirty_days_ago = today - timedelta(days=30)
                
                date_from = ui.input('From Date').props('type=date filled color=indigo').classes('w-40')
                date_to = ui.input('To Date').props('type=date filled color=indigo').classes('w-40')
                
                if min_date and max_date:
                    date_from.value = str(min_date)
                    date_to.value = str(max_date)
                else:
                    date_from.value = str(thirty_days_ago)
                    date_to.value = str(today)
                
                # Store references for later use in update functions
                filter_state = {'date_from': date_from, 'date_to': date_to, 'app_select': app_select}
    
    # Helpers to build initial chart options so first render is not empty
    def _build_ts_options():
        is_light = _detect_light_mode()
        colors = _get_chart_colors(is_light)
        app_id_init = None
        df_init = date_from.value or str(datetime.now().date() - timedelta(days=30))
        dt_init = date_to.value or str(datetime.now().date())
        data = _get_time_series_data(db, app_id_init, df_init, dt_init)
        if not data:
            return {
                'backgroundColor': 'transparent',
                'title': {'text': 'No data available', 'textStyle': {'color': colors['text']}},
                'grid': {'left': '10%', 'right': '10%', 'bottom': '10%', 'top': '15%', 'containLabel': True},
            }
        dates = sorted(data.keys())
        pos = [data[d].get('positive', 0) for d in dates]
        neu = [data[d].get('neutral', 0) for d in dates]
        neg = [data[d].get('negative', 0) for d in dates]
        return {
            'backgroundColor': 'transparent',
            'title': {'show': False},
            'tooltip': {'trigger': 'axis'},
            'legend': {'data': ['Positive', 'Neutral', 'Negative'], 'textStyle': {'color': colors['text']}},
            'grid': {'left': '10%', 'right': '10%', 'bottom': '10%', 'top': '10%', 'containLabel': True},
            'xAxis': {'type': 'category', 'data': dates, 'axisLabel': {'color': colors['axis']}, 'axisLine': {'lineStyle': {'color': colors['border']}}},
            'yAxis': {'type': 'value', 'axisLabel': {'color': colors['axis']}, 'splitLine': {'show': True, 'lineStyle': {'color': colors['grid']}}},
            'series': [
                {'name': 'Positive', 'type': 'line', 'data': pos, 'smooth': True, 'itemStyle': {'color': '#22c55e'}, 'areaStyle': {'color': 'rgba(34, 197, 94, 0.2)'}},
                {'name': 'Neutral', 'type': 'line', 'data': neu, 'smooth': True, 'itemStyle': {'color': '#3b82f6'}, 'areaStyle': {'color': 'rgba(59, 130, 246, 0.2)'}},
                {'name': 'Negative', 'type': 'line', 'data': neg, 'smooth': True, 'itemStyle': {'color': '#ef4444'}, 'areaStyle': {'color': 'rgba(239, 68, 68, 0.2)'}},
            ],
        }

    def _build_corr_options():
        is_light = _detect_light_mode()
        colors = _get_chart_colors(is_light)
        app_id_init = None
        data = _get_rating_sentiment_correlation(db, app_id_init)
        if not data:
            return {
                'backgroundColor': 'transparent',
                'title': {'text': 'No data available', 'textStyle': {'color': colors['text']}},
                'grid': {'left': '10%', 'right': '10%', 'bottom': '10%', 'top': '15%', 'containLabel': True},
            }
        ratings = sorted(set(d[0] for d in data if d[0] is not None))
        sentiments = ['positive', 'neutral', 'negative']
        heatmap_data, max_count = [], 1
        for i, r in enumerate(ratings):
            for j, s in enumerate(sentiments):
                c = next((d[2] for d in data if d[0] == r and d[1] == s), 0)
                heatmap_data.append([i, j, c])
                max_count = max(max_count, c)
        return {
            'backgroundColor': 'transparent',
            'title': {'show': False},
            'tooltip': {'trigger': 'item'},
            'grid': {'left': '10%', 'right': '10%', 'bottom': '10%', 'top': '10%', 'containLabel': True},
            'xAxis': {'type': 'category', 'data': [f'★{r}' for r in ratings], 'axisLabel': {'color': colors['axis']}, 'axisLine': {'lineStyle': {'color': colors['border']}}},
            'yAxis': {'type': 'category', 'data': sentiments, 'axisLabel': {'color': colors['axis']}, 'axisLine': {'lineStyle': {'color': colors['border']}}},
            'visualMap': {'min': 0, 'max': max_count, 'inRange': {'color': ['#1f2937', '#4f46e5', '#14b8a6']}, 'textStyle': {'color': colors['axis']}},
            'series': [{
                'name': 'Count',
                'type': 'heatmap',
                'data': heatmap_data,
                'itemStyle': {'borderColor': '#1f2937'}
            }],
        }

    # Time-Series Chart (no reveal to avoid zero-size init)
    with ui.element('section').classes('section'):
        with ui.row().classes('items-center gap-3'):
            ui.label('📈').classes('text-h5')
            with ui.column().classes('gap-1'):
                ui.label('Sentiment Trends Over Time').classes('text-h6 font-bold')
                ui.label('Track how sentiment distribution evolves across your selected date range. Green = Positive reviews, Blue = Neutral, Red = Negative.').classes('text-caption text-grey-7')
        with ui.element('div').classes('panel chart-panel'):
            # Initialize with actual options
            chart_ts = ui.echart(options=_build_ts_options()).style('width:100%;height:520px;')
            
            def update_timeseries():
                is_light = _detect_light_mode()
                colors = _get_chart_colors(is_light)
                app_id = app_select.value
                date_from_val = date_from.value or str(datetime.now().date() - timedelta(days=30))
                date_to_val = date_to.value or str(datetime.now().date())
                
                print(f"\n=== UPDATE TIMESERIES ===")
                print(f"App: {app_id}, From: {date_from_val}, To: {date_to_val}")
                data = _get_time_series_data(db, app_id, date_from_val, date_to_val)
                print(f"Result: {data}\n")
                
                if not data:
                    chart_ts.options = {
                        'backgroundColor': 'transparent',
                        'title': {'text': 'No data available', 'textStyle': {'color': colors['text']}},
                        'grid': {'left': '10%', 'right': '10%', 'bottom': '10%', 'top': '15%', 'containLabel': True}
                    }
                    chart_ts.update()
                    ui.run_javascript("window.dispatchEvent(new Event('resize'))")
                    return
                
                dates = sorted(data.keys())
                positive = [data[d].get('positive', 0) for d in dates]
                neutral = [data[d].get('neutral', 0) for d in dates]
                negative = [data[d].get('negative', 0) for d in dates]
                
                chart_ts.options = {
                    'backgroundColor': 'transparent',
                    'title': {'show': False},
                    'tooltip': {'trigger': 'axis'},
                    'legend': {'data': ['Positive', 'Neutral', 'Negative'], 'textStyle': {'color': colors['text']}},
                    'grid': {'left': '10%', 'right': '10%', 'bottom': '10%', 'top': '10%', 'containLabel': True},
                    'xAxis': {'type': 'category', 'data': dates, 'axisLabel': {'color': colors['axis']}, 'axisLine': {'lineStyle': {'color': colors['border']}}},
                    'yAxis': {'type': 'value', 'axisLabel': {'color': colors['axis']}, 'axisLine': {'lineStyle': {'color': colors['border']}}},
                    'series': [
                        {'name': 'Positive', 'type': 'line', 'data': positive, 'smooth': True, 'itemStyle': {'color': '#22c55e'}, 'areaStyle': {'color': 'rgba(34, 197, 94, 0.2)'}},
                        {'name': 'Neutral', 'type': 'line', 'data': neutral, 'smooth': True, 'itemStyle': {'color': '#3b82f6'}, 'areaStyle': {'color': 'rgba(59, 130, 246, 0.2)'}},
                        {'name': 'Negative', 'type': 'line', 'data': negative, 'smooth': True, 'itemStyle': {'color': '#ef4444'}, 'areaStyle': {'color': 'rgba(239, 68, 68, 0.2)'}},
                    ]
                }
                chart_ts.update()
                ui.run_javascript("window.dispatchEvent(new Event('resize'))")
            
            # Auto-load data on page load with delay
            ui.timer(1.0, lambda: update_timeseries(), once=True)
            
            ui.button('Update Chart', on_click=update_timeseries).props('color=indigo text-color=white no-caps unelevated rounded size=lg').classes('q-mt-md')
    
    # Rating vs Sentiment Correlation (no reveal to avoid zero-size init)
    with ui.element('section').classes('section'):
        with ui.row().classes('items-center gap-3'):
            ui.label('🔗').classes('text-h5')
            with ui.column().classes('gap-1'):
                ui.label('Rating vs Sentiment Correlation').classes('text-h6 font-bold')
                ui.label('Validate model accuracy by comparing predicted sentiment with actual star ratings. Darker colors indicate higher review counts.').classes('text-caption text-grey-7')
        with ui.element('div').classes('panel chart-panel'):
            # Initialize with actual options
            chart_corr = ui.echart(options=_build_corr_options()).style('width:100%;height:520px;')
            
            def update_correlation():
                try:
                    is_light = _detect_light_mode()
                    colors = _get_chart_colors(is_light)
                    app_id = app_select.value
                    print(f"\n=== UPDATE CORRELATION ===")
                    print(f"App: {app_id}")
                    data = _get_rating_sentiment_correlation(db, app_id)
                    print(f"Result: {data}\n")
                    
                    if not data:
                        chart_corr.options = {
                            'backgroundColor': 'transparent',
                            'title': {'text': 'No data available', 'textStyle': {'color': colors['text']}},
                            'grid': {'left': '10%', 'right': '10%', 'bottom': '10%', 'top': '15%', 'containLabel': True}
                        }
                        chart_corr.update()
                        ui.run_javascript("window.dispatchEvent(new Event('resize'))")
                        return
                    
                    # Organize data for heatmap
                    ratings = sorted(set(d[0] for d in data if d[0] is not None))
                    sentiments = ['positive', 'neutral', 'negative']
                    
                    if not ratings:
                        chart_corr.options = {
                            'backgroundColor': 'transparent',
                            'title': {'text': 'No rating data available', 'textStyle': {'color': colors['text']}},
                            'grid': {'left': '10%', 'right': '10%', 'bottom': '10%', 'top': '15%', 'containLabel': True}
                        }
                        chart_corr.update()
                        ui.run_javascript("window.dispatchEvent(new Event('resize'))")
                        return
                    
                    heatmap_data = []
                    max_count = 1
                    for i, rating in enumerate(ratings):
                        for j, sentiment in enumerate(sentiments):
                            count = next((d[2] for d in data if d[0] == rating and d[1] == sentiment), 0)
                            heatmap_data.append([i, j, count])
                            max_count = max(max_count, count)
                    
                    chart_corr.options = {
                        'backgroundColor': 'transparent',
                        'title': {'show': False},
                        'tooltip': {'trigger': 'item'},
                        'grid': {'left': '10%', 'right': '10%', 'bottom': '10%', 'top': '10%', 'containLabel': True},
                        'xAxis': {'type': 'category', 'data': [f'★{r}' for r in ratings], 'axisLabel': {'color': colors['axis']}, 'axisLine': {'lineStyle': {'color': colors['border']}}},
                        'yAxis': {'type': 'category', 'data': sentiments, 'axisLabel': {'color': colors['axis']}, 'axisLine': {'lineStyle': {'color': colors['border']}}},
                        'visualMap': {'min': 0, 'max': max_count, 'inRange': {'color': ['#1f2937', '#4f46e5', '#14b8a6']}, 'textStyle': {'color': colors['axis']}},
                        'series': [{
                            'name': 'Count',
                            'type': 'heatmap',
                            'data': heatmap_data,
                            'itemStyle': {'borderColor': '#1f2937'}
                        }]
                    }
                    chart_corr.update()
                    ui.run_javascript("window.dispatchEvent(new Event('resize'))")
                except Exception as e:
                    print(f"Error updating correlation: {e}")
                    chart_corr.options = {
                        'backgroundColor': 'transparent',
                        'title': {'text': f'Error: {str(e)[:50]}', 'textStyle': {'color': '#ef4444'}},
                    }
                    chart_corr.update()
            
            # Auto-load data on page load with delay
            ui.timer(1.2, lambda: update_correlation(), once=True)
            
            ui.button('Update Correlation', on_click=update_correlation).props('color=indigo text-color=white no-caps unelevated rounded size=lg').classes('q-mt-md')
    
    # Severity Leaderboard
    with ui.element('section').classes('section reveal'):
        with ui.row().classes('items-center gap-3'):
            ui.label('🏆').classes('text-h5')
            with ui.column().classes('gap-1'):
                ui.label('Severity Leaderboard').classes('text-h6 font-bold')
                ui.label('Top issues ranked by severity score (frequency × negativity × recency). Focus on high-severity themes first.').classes('text-caption text-grey-7')
        with ui.element('div').classes('panel chart-panel'):
            leaderboard_table = ui.table(
                columns=[
                    {'name': 'rank', 'label': '#', 'field': 'rank'},
                    {'name': 'theme', 'label': 'Theme', 'field': 'theme'},
                    {'name': 'frequency', 'label': 'Frequency', 'field': 'frequency'},
                    {'name': 'severity', 'label': 'Severity Score', 'field': 'severity'},
                    {'name': 'recency', 'label': 'Recency %', 'field': 'recency_score'},
                ],
                rows=[]
            ).classes('w-full table-themed').props('flat bordered dark separator=cell dense')
            
            def update_leaderboard():
                app_id = app_select.value
                date_from_val = date_from.value or str(datetime.now().date() - timedelta(days=30))
                date_to_val = date_to.value or str(datetime.now().date())
                
                print(f"\n=== UPDATE LEADERBOARD ===")
                print(f"App: {app_id}, From: {date_from_val}, To: {date_to_val}")
                leaderboard = _compute_severity_leaderboard(db, app_id, date_from_val, date_to_val)
                print(f"Result: {leaderboard}\n")
                
                rows = [
                    {
                        'rank': i + 1,
                        'theme': item['theme'].upper(),
                        'frequency': item['frequency'],
                        'severity': f"{item['severity']:.2f}",
                        'recency_score': f"{item['recency_score']:.1f}%"
                    }
                    for i, item in enumerate(leaderboard)
                ]
                
                leaderboard_table.rows = rows
                leaderboard_table.update()
            
            # Auto-load data on page load with delay
            ui.timer(1.4, lambda: update_leaderboard(), once=True)
            
            ui.button('Update Leaderboard', on_click=update_leaderboard).props('color=indigo text-color=white no-caps unelevated rounded size=lg').classes('q-mt-md')
    
    # Add event listeners to filters to update all charts when changed
    def on_filter_change():
        update_timeseries()
        update_correlation()
        update_leaderboard()
    
    app_select.on('update:model-value', lambda: on_filter_change())
    date_from.on('update:model-value', lambda: on_filter_change())
    date_to.on('update:model-value', lambda: on_filter_change())
