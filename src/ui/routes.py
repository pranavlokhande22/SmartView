from pathlib import Path
from typing import List, Dict

from nicegui import ui, app

from database.handler import Database
from src.ui.app import mount_ui


def _mount_assets_once():
    assets_dir = Path(__file__).resolve().parent / 'assets'
    try:
        app.add_static_files('/assets', str(assets_dir))
    except Exception:
        pass


def _inject_head():
    assets_dir = Path(__file__).resolve().parent / 'assets'
    css_path = assets_dir / 'styles.css'
    
    if css_path.exists():
        try:
            css = css_path.read_text(encoding='utf-8')
            ui.add_head_html(f'<style>{css}</style>')
        except Exception:
            pass
    
    ui.add_head_html('<script>(function(){var t=localStorage.getItem("theme")||"dark"; document.documentElement.dataset.theme=t;})();</script>')
    ui.add_head_html('''
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
    ''')
    
    # Load animations.js
    js_path = assets_dir / 'animations.js'
    if js_path.exists():
        try:
            js = js_path.read_text(encoding='utf-8')
            ui.add_body_html(f'<script>{js}</script>')
        except Exception:
            pass


def _navbar():
    with ui.element('div').classes('navbar'):
        with ui.element('div').classes('navbar-inner'):
            ui.link('SmartView', '/').classes('brand')
            with ui.row().classes('navbar-links items-center'):
                ui.link('Dashboard', '/dashboard').classes('nav-link')
                ui.link('Reviews', '/reviews').classes('nav-link')
                ui.link('Analytics', '/analytics').classes('nav-link')
                ui.link('About', '/#about').classes('nav-link')
                def _toggle_theme():
                    ui.run_javascript('(()=>{const d=document.documentElement; const cur=d.dataset.theme==="light"?"dark":"light"; d.dataset.theme=cur; localStorage.setItem("theme",cur);})()')
                ui.button('', on_click=_toggle_theme).props('icon=brightness_6 flat round dense color=white').classes('theme-toggle')


def _hero():
    with ui.element('section').classes('hero').props('id=home'):
        with ui.element('div').classes('container'):
            ui.html('<h1>Transform Reviews into Actionable Insights</h1>', sanitize=False)
            ui.html('<div class="subtitle">Powered by Advanced NLP & Machine Learning</div>', sanitize=False)
            ui.html('''
                <p>
                    Analyze customer sentiment, extract meaningful themes, and generate data-driven recommendations with our state-of-the-art sentiment analysis platform. Process thousands of reviews in seconds.
                </p>
            ''', sanitize=False)
            
            with ui.element('div').classes('cta'):
                ui.link('Get Started', '/dashboard').classes('cta-button')
                ui.link('Learn More', '#features').classes('cta-button secondary')

def _features_section():
    """Add detailed features on landing page"""
    with ui.element('section').classes('features-section'):
        ui.html('<h2>Why Choose Our Platform?</h2>', sanitize=False)
        
        with ui.element('div').classes('features-grid').props('id=features'):
            # Feature 1
            with ui.element('div').classes('feature-card'):
                ui.html('<div class="feature-icon">🧠</div>', sanitize=False)
                ui.html('<h3>AI-Powered Analysis</h3>', sanitize=False)
                ui.html('<p>Advanced NLP models trained on millions of reviews for accurate sentiment detection</p>', sanitize=False)
            
            # Feature 2
            with ui.element('div').classes('feature-card'):
                ui.html('<div class="feature-icon">⚡</div>', sanitize=False)
                ui.html('<h3>Lightning Fast</h3>', sanitize=False)
                ui.html('<p>Process thousands of reviews in seconds with optimized algorithms</p>', sanitize=False)
            
            # Feature 3
            with ui.element('div').classes('feature-card'):
                ui.html('<div class="feature-icon">📊</div>', sanitize=False)
                ui.html('<h3>Rich Visualizations</h3>', sanitize=False)
                ui.html('<p>Interactive charts and dashboards for deep insights</p>', sanitize=False)
            
            # Feature 4
            with ui.element('div').classes('feature-card'):
                ui.html('<div class="feature-icon">🎯</div>', sanitize=False)
                ui.html('<h3>Actionable Insights</h3>', sanitize=False)
                ui.html('<p>Get specific recommendations based on sentiment analysis</p>', sanitize=False)

def _stats_section():
    """Add statistics section"""
    with ui.element('section').classes('stats-section reveal'):
        with ui.element('div').classes('stats-grid'):
            stats = [
                ('10M+', 'Reviews Analyzed'),
                ('99.2%', 'Accuracy Rate'),
                ('< 2s', 'Avg Processing Time'),
                ('50+', 'Languages Supported'),
            ]
            
            for number, label in stats:
                with ui.element('div').classes('stat-card'):
                    ui.html(f'<div class="stat-number" data-target="{number}">{number}</div>', sanitize=False)
                    ui.html(f'<div class="stat-label">{label}</div>', sanitize=False)


def _pipeline_section():
    """3D animated workflow pipeline"""
    with ui.element('section').classes('pipeline reveal').props('id=pipeline-timeline'):
        ui.html('<h2>Our Advanced Processing Pipeline</h2>', sanitize=False)
        
        with ui.element('div').classes('steps'):
            steps = [
                ('📥', 'Data Ingestion', 'Upload CSV/XLSX files'),
                ('🧹', 'Preprocessing', 'Clean and normalize text'),
                ('🤖', 'NLP Processing', 'Tokenization & analysis'),
                ('💭', 'Sentiment Detection', 'ML-based classification'),
                ('🔍', 'Theme Extraction', 'Identify key topics'),
                ('💡', 'Recommendations', 'Generate insights'),
                ('📤', 'Export Results', 'Download reports'),
            ]
            
            for icon, title, desc in steps:
                with ui.element('div').classes('step').props(f'data-title="{title}" data-desc="{desc}"'):
                    ui.html(f'<div class="icon">{icon}</div>', sanitize=False)
                    ui.html(f'<div class="title">{title}</div>', sanitize=False)
                    ui.html(f'<div class="desc">{desc}</div>', sanitize=False)


def _pipeline_timeline():
    steps: List[Dict[str, str]] = [
        {'t': 'Input CSV', 'd': 'Upload reviews from CSV/XLSX'},
        {'t': 'Preprocess', 'd': 'Clean text & tokenize'},
        {'t': 'TF-IDF', 'd': 'Build sparse features'},
        {'t': 'Sentiment', 'd': 'Predict labels & scores'},
        {'t': 'Themes', 'd': 'Extract frequent topics'},
        {'t': 'Severity', 'd': 'Score by freq×neg×recency'},
        {'t': 'Dashboard', 'd': 'Filter, compare, export'},
    ]
    with ui.element('section').classes('section reveal'):
        ui.label('Animated Pipeline Timeline').classes('text-h5')
        with ui.element('div').classes('panel'):
            with ui.element('div').props('id=pipeline-timeline').classes('tl-wrap'):
                with ui.element('div').classes('tl-track'):
                    ui.element('div').classes('tl-bar')
                    ui.element('div').classes('tl-dot')
                with ui.element('div').classes('tl-steps'):
                    for s in steps:
                        with ui.element('div').classes('tl-step').props(f'data-title="{s["t"]}" data-desc="{s["d"]}"'):
                            ui.label(s['t'])
                with ui.row().classes('items-center q-gutter-sm'):
                    ui.button('Play demo', on_click=None).props('id=start-demo color=indigo text-color=white no-caps unelevated rounded size=lg')
                    ui.label(' ').props('id=tl-caption')
        # Optional Lottie (offline). Place lottie.min.js and pipeline.json in /assets to activate.
        ui.element('div').props('data-lottie=/assets/pipeline.json').classes('section reveal')


def _top_apps_slider(db: Database):
    # Build Top 10 apps by review count with one latest review each
    # Inject component-scoped CSS to avoid touching global stylesheet
    ui.add_head_html('''
    <style>
      .topapps-wrapper { width: 100%; padding: 0 5vw; }
      .top-apps-slider { position: relative; width: 100%; max-width: 1100px; margin: 8px auto 0; }
      .top-apps-track { position: relative; height: 320px; perspective: 1000px; }
      .top-app-slide { position: absolute; left: 50%; top: 20px; transform: translate(-50%, 0); transition: transform .45s cubic-bezier(.2,.8,.2,1), opacity .3s ease; will-change: transform; }
      .top-app-card { width: min(760px, 92vw); background: #0f172a; border: 1px solid #1f2937; box-shadow: 0 20px 40px rgba(0,0,0,.35); border-radius: 14px; padding: 16px 18px; }
      .card-head { display: grid; grid-template-columns: 44px 1fr auto; align-items: center; gap: 10px; margin-bottom: 8px; }
      .app-icon-image { width: 44px; height: 44px; border-radius: 10px; object-fit: cover; border: 1px solid #334155; box-shadow: 0 6px 16px rgba(0,0,0,.25); }
      .app-icon-fallback { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 10px; font-weight: 900; color: #c7d2fe; background: radial-gradient(120px 80px at 50% 50%, rgba(79,70,229,.25), rgba(20,184,166,.15)); border: 1px solid #334155; box-shadow: 0 6px 16px rgba(0,0,0,.25); }
      .app-title { font-weight: 800; letter-spacing: .3px; color: #e5e7eb; }
      .app-review { color: #e5e7eb; opacity: .9; line-height: 1.5; }
      .top-apps-nav { display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 16px; }
      .top-apps-btn { background: rgba(79,70,229,.18) !important; color: #c7d2fe !important; border-radius: 10px !important; }
      .top-apps-btn:hover { background: rgba(79,70,229,.35) !important; }
      :root[data-theme='light'] .top-app-card { background: #ffffff; border-color: #e2e8f0; }
      :root[data-theme='light'] .app-icon-image { border-color: #e2e8f0; }
      :root[data-theme='light'] .app-icon-fallback { color: #3730a3; background: radial-gradient(120px 80px at 50% 50%, rgba(99,102,241,.15), rgba(20,184,166,.12)); border-color: #e2e8f0; }
      :root[data-theme='light'] .app-title { color: #0f172a; }
      :root[data-theme='light'] .app-review { color: #334155; }
      :root[data-theme='light'] .top-apps-btn { background: rgba(79,70,229,.10) !important; color: #4f46e5 !important; }
      @media (max-width: 640px) {
        .top-apps-track { height: 360px; }
        .top-app-card { width: 94vw; }
      }
    </style>
    ''')
    with ui.element('section').classes('section reveal').props('id=top-apps'):
        ui.html('<h2>Top Apps</h2>', sanitize=False)
        # query data
        cur = db.conn.cursor()
        try:
            cur.execute(
                'SELECT a.id, a.app_name, COUNT(r.id) as cnt '
                'FROM apps a JOIN reviews r ON r.app_id = a.id '
                'GROUP BY a.id, a.app_name '
                'ORDER BY cnt DESC LIMIT 10'
            )
            top = cur.fetchall()
        except Exception:
            top = []
        slides: List[Dict[str, str]] = []
        assets_root = Path(__file__).resolve().parent / 'assets' / 'icons'
        for app_id, app_name, _ in top:
            # latest review for this app
            cur.execute(
                'SELECT r.review_text, IFNULL(s.sentiment_label, "neutral") '
                'FROM reviews r LEFT JOIN sentiment_results s ON s.review_id=r.id '
                'WHERE r.app_id=? ORDER BY r.id DESC LIMIT 1',
                (app_id,),
            )
            row = cur.fetchone()
            review_text = (row[0] if row else 'No review available yet.') or 'No review available yet.'
            sentiment = (row[1] if row else 'neutral') or 'neutral'
            slug = str(app_name).strip().lower().replace(' ', '').replace('&', 'and')
            icon_src = None
            if assets_root.exists():
                for ext in ('.svg', '.png', '.jpg', '.jpeg', '.webp'):
                    p = assets_root / f'{slug}{ext}'
                    if p.exists():
                        icon_src = f'/assets/icons/{p.name}'
                        break
            slides.append({'name': app_name, 'text': review_text, 'sent': sentiment, 'icon': icon_src})
        # fallback demo slides if no data
        if not slides:
            demo = [
                ('whatsapp', 'Fast, reliable messaging. Love the new features!', 'positive'),
                ('facebook', 'The app is okay, but needs performance improvements.', 'neutral'),
                ('swiggy', 'Late deliveries and missing items. Please fix.', 'negative'),
                ('instagram', 'Stories load quickly and filters are fun!', 'positive'),
            ]
            for n, t, s in demo:
                slides.append({'name': n, 'text': t, 'sent': s, 'icon': None})
        with ui.element('div').classes('topapps-wrapper'):
            with ui.element('div').classes('top-apps-slider'):
                with ui.element('div').props('id=top-apps-track').classes('top-apps-track'):
                    for item in slides:
                        # sentiment class
                        scls = 'pos' if item['sent'] == 'positive' else ('neg' if item['sent'] == 'negative' else 'neu')
                        with ui.element('div').classes('top-app-slide'):
                            with ui.element('div').classes('top-app-card'):
                                with ui.element('div').classes('card-head'):
                                    if item['icon']:
                                        ui.html(f'<img class="app-icon-image" src="{item["icon"]}" alt="{item["name"]}">', sanitize=False)
                                    else:
                                        initial = str(item['name']).strip()[:1].upper()
                                        ui.html(f'<div class="app-icon-fallback">{initial}</div>', sanitize=False)
                                    ui.html(f'<div class="app-title">{item["name"]}</div>', sanitize=False)
                                    ui.element('span').classes(f'sent {scls}').text = item['sent']
                                ui.html(f'<p class="app-review">{item["text"][:220]}{"…" if len(item["text"])>220 else ""}</p>', sanitize=False)
                with ui.element('div').classes('top-apps-nav'):
                    ui.button('', on_click=None).props('icon=chevron_left flat round dense').classes('top-apps-btn').props('id=top-prev')
                    ui.button('', on_click=None).props('icon=chevron_right flat round dense').classes('top-apps-btn').props('id=top-next')
        ui.run_javascript('''
            (function(){
              const track = document.getElementById('top-apps-track');
              if(!track){return;}
              const slides = Array.from(track.querySelectorAll('.top-app-slide'));
              if(slides.length===0){return;}
              let i = 0;
              const clampIdx = (v)=> (v+slides.length)%slides.length;
              function render(){
                slides.forEach((s, idx)=>{
                  const off = idx - i;
                  const wrapLeft = off < -Math.floor(slides.length/2);
                  const wrapRight = off > Math.floor(slides.length/2);
                  let k = off;
                  if (wrapLeft) k = off + slides.length;
                  if (wrapRight) k = off - slides.length;
                  const dz = Math.min(Math.abs(k), 3);
                  const ty = dz * 14;
                  const sc = 1 - dz*0.07;
                  const rot = k*2;
                  const tx = k*36;
                  s.style.zIndex = String(100 - dz*10 + (k===0?100:0));
                  s.style.opacity = String(1 - Math.min(dz*0.15, 0.45));
                  s.style.transform = `translate(-50%, ${ty}px) translateX(${tx}px) scale(${sc}) rotate(${rot}deg)`;
                });
              }
              document.getElementById('top-next')?.addEventListener('click', ()=>{ i = clampIdx(i+1); render(); });
              document.getElementById('top-prev')?.addEventListener('click', ()=>{ i = clampIdx(i-1); render(); });
              render();
            })();
        ''')

def _about():
    with ui.element('section').classes('section about-section reveal').props('id=about'):
        with ui.element('div').classes('about-grid'):
            with ui.column().classes('gap-2'):
                ui.label('About SmartView').classes('text-h5')
                ui.label('SmartView transforms raw app reviews into actionable developer insights entirely offline. It stores data in SQLite, applies an NLP pipeline, classifies sentiment, extracts themes, ranks issues by severity, renders interactive charts, and exports reports.').classes('text-body1')
            ui.element('object').props('type=image/svg+xml data=/assets/character.svg aria-label=Animated character').classes('about-art')


def _footer():
    with ui.element('footer').classes('footer-container'):
        with ui.element('div').classes('footer-content'):
            # Social Media Section
            with ui.element('div').classes('footer-section social-section'):
                ui.html('''
                    <div class="social-icons">
                        <a href="#" class="social-icon" title="Facebook">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                            </svg>
                        </a>
                        <a href="#" class="social-icon" title="Instagram">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
                                <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
                                <circle cx="17.5" cy="6.5" r="1.5"></circle>
                            </svg>
                        </a>
                        <a href="#" class="social-icon" title="YouTube">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                            </svg>
                        </a>
                        <a href="#" class="social-icon" title="Twitter/X">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.6l-5.165-6.75-5.91 6.75H2.556l7.73-8.835L1.966 2.25h6.772l4.683 6.18 5.367-6.18zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                            </svg>
                        </a>
                    </div>
                ''', sanitize=False)
            
            # Links Section
            with ui.element('div').classes('footer-section links-section'):
                with ui.element('div').classes('footer-links-column'):
                    ui.html('<h4>Company</h4>', sanitize=False)
                    ui.link('About Us', '#about').classes('footer-link')
                    ui.link('Contact Us', '/contact').classes('footer-link')
                    ui.link('Careers', '#').classes('footer-link')
                
                with ui.element('div').classes('footer-links-column'):
                    ui.html('<h4>Product</h4>', sanitize=False)
                    ui.link('Features', '/features').classes('footer-link')
                    ui.link('Pricing', '#').classes('footer-link')
                    ui.link('Documentation', '/docs').classes('footer-link')
                
                with ui.element('div').classes('footer-links-column'):
                    ui.html('<h4>Legal</h4>', sanitize=False)
                    ui.link('Privacy Policy', '#').classes('footer-link')
                    ui.link('Terms & Conditions', '#').classes('footer-link')
                    ui.link('Cookie Policy', '#').classes('footer-link')
        
        # Copyright Section
        with ui.element('div').classes('footer-bottom'):
            ui.html('<p>© 2025 SmartView. All rights reserved. | Offline • Privacy-Preserving • Built with NiceGUI</p>', sanitize=False)


def register_routes(db: Database) -> None:
    _mount_assets_once()

    @_page('/')
    def landing_page():
        _inject_head()
        _navbar()
        _hero()
        _features_section()
        _stats_section()
        _pipeline_section()
        _top_apps_slider(db)
        _about()
        _footer()

    @_page('/dashboard')
    def dashboard_page():
        _inject_head()
        _navbar()
        mount_ui(db)
        _footer()

    @_page('/reviews')
    def reviews_page():
        _inject_head()
        _navbar()
        with ui.element('section').classes('section reveal'):
            ui.label('Recent Reviews').classes('text-h5')
            with ui.element('div').classes('reviews-list'):
                cur = db.conn.cursor()
                cur.execute(
                    'SELECT a.app_name, r.review_text, IFNULL(s.sentiment_label, "neutral") as lab '
                    'FROM reviews r JOIN apps a ON a.id=r.app_id '
                    'LEFT JOIN sentiment_results s ON s.review_id=r.id '
                    'ORDER BY r.id DESC LIMIT 30'
                )
                rows = cur.fetchall()
                if not rows:
                    ui.label('No reviews yet. Go to Dashboard to ingest a dataset.').classes('text-body1')
                for app_name, text, lab in rows:
                    cls = 'pos' if lab == 'positive' else ('neg' if lab == 'negative' else 'neu')
                    with ui.element('div').classes('review-row'):
                        ui.label(str(app_name)).classes('app-pill')
                        ui.label(str(text)[:220] + ('…' if len(str(text)) > 220 else '')).classes('text')
                        ui.element('span').classes(f'sent {cls}').text = lab
        _footer()

    @_page('/features')
    def features_page():
        _inject_head()
        _navbar()
        with ui.element('section').classes('section reveal'):
            ui.label('Features').classes('text-h5')
            ui.label('Offline ingestion, NLP preprocessing, TF-IDF, sentiment classification, theme extraction, severity scoring, interactive dashboard, exports.').classes('text-body1')
        _footer()

    @_page('/docs')
    def docs_page():
        _inject_head()
        _navbar()
        with ui.element('section').classes('section reveal'):
            ui.label('Documentation').classes('text-h5')
            ui.label('Refer to your 38-section enterprise document for full system specification and architecture.').classes('text-body1')
        _footer()

    @_page('/about')
    def about_page():
        _inject_head()
        _navbar()
        _about()
        _footer()

    @_page('/contact')
    def contact_page():
        _inject_head()
        _navbar()
        with ui.element('section').classes('section reveal'):
            ui.html('<h2>Contact Us</h2>', sanitize=False)
            ui.html('''
                <p>For support, integration requests, or feedback, please reach out to us:</p>
                <div style="margin-top: 30px; max-width: 600px;">
                    <div style="margin-bottom: 20px;">
                        <strong>Email:</strong> support@smartview.io
                    </div>
                    <div style="margin-bottom: 20px;">
                        <strong>Phone:</strong> +1 (555) 123-4567
                    </div>
                    <div style="margin-bottom: 20px;">
                        <strong>Address:</strong> 123 Tech Street, San Francisco, CA 94105
                    </div>
                </div>
            ''', sanitize=False)
        _footer()

    @_page('/demos')
    def demos_page():
        _inject_head()
        _navbar()
        with ui.element('section').classes('section reveal'):
            ui.label('Live Demos').classes('text-h5')
            ui.label('Use the Dashboard to ingest a dataset and see live analytics. This page can embed saved charts or walkthrough videos.').classes('text-body1')
        _footer()

    @_page('/how-it-works')
    def how_page():
        _inject_head()
        _navbar()
        _pipeline_timeline()
        _footer()

    @_page('/analytics')
    def analytics_page():
        from src.ui.analytics import mount_analytics
        _inject_head()
        _navbar()
        mount_analytics(db)
        _footer()


# NiceGUI 3.x decorator helper to avoid circular imports when registering pages before ui.run
def _page(path: str):
    def deco(fn):
        ui.page(path)(lambda: fn())
        return fn
    return deco
