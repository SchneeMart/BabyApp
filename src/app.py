import os
import json
import hashlib
import time
import re
import logging
from datetime import datetime
from flask import Flask, request as flask_request
from src.extensions import db, login_manager, migrate, csrf, mail, limiter

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


def create_app():
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    # Konfiguration
    db_mode = os.environ.get('DB_MODE', 'dev')
    db_name = f'app_{db_mode}.db'
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Secret Key: Zufällig generieren wenn nicht gesetzt (sicher, aber Sessions verfallen bei Neustart)
    secret_key = os.environ.get('SECRET_KEY', '')
    if not secret_key:
        import secrets as _secrets
        secret_key = _secrets.token_hex(32)
        logging.warning('WARNUNG: Kein SECRET_KEY gesetzt! Zufälliger Key wird verwendet - Sessions werden beim Neustart ungültig. Bitte SECRET_KEY in .env setzen!')
    app.config['SECRET_KEY'] = secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(base_dir, db_name)}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # Session-Cookie-Sicherheit
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # SESSION_COOKIE_SECURE nur bei HTTPS (wird dynamisch in after_request gesetzt)

    # Mail (wie Energie: SSL auf Port 465)
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', '')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465))
    use_ssl = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
    app.config['MAIL_USE_SSL'] = use_ssl
    app.config['MAIL_USE_TLS'] = not use_ssl  # TLS nur wenn kein SSL
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', os.environ.get('MAIL_SENDER', ''))
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_SENDER', '')
    app.config['MAIL_TIMEOUT'] = 10  # 10 Sekunden Timeout

    # Extensions initialisieren
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Version & Cache-Buster
    version_file = os.path.join(base_dir, 'version.json')
    try:
        with open(version_file, 'r') as f:
            version_data = json.load(f)
    except Exception:
        version_data = {'version': '0.0.0', 'date': '', 'releases': []}

    cache_buster = hashlib.md5(
        f"{version_data['version']}-{time.time()}".encode()
    ).hexdigest()[:10]

    APP_VERSION = {
        'version': version_data.get('version', '0.0.0'),
        'date': version_data.get('date', ''),
        'releases': version_data.get('releases', []),
        'cache_buster': cache_buster,
    }

    # User-Loader
    from src.models import User

    class TokenGast:
        """Pseudo-User für Token-Zugriff. Lebt nur in der Session, nie in der DB."""
        is_authenticated = True
        is_active = True
        is_anonymous = False

        def __init__(self, kind_id, berechtigung):
            self.id = f'token_{kind_id}'
            self.kind_id = kind_id
            self.berechtigung = berechtigung
            self.username = f'Gast'
            self.email = ''
            self.role = 'betreuer' if berechtigung == 'write' else 'leser'

        def get_id(self):
            return self.id

        @property
        def is_admin(self):
            return False

        @property
        def is_elternteil(self):
            return False

        @property
        def kann_kind_erstellen(self):
            return False

        @property
        def kann_schreiben(self):
            return self.berechtigung == 'write'

        @property
        def rolle_label(self):
            return 'Gast (Schreiben)' if self.kann_schreiben else 'Gast (Lesen)'

        @property
        def erstellt_von_id(self):
            """TokenGast hat keinen DB-User - gibt None für DB-Felder zurück."""
            return None

        def can(self, module_id, perm_type):
            if perm_type == 'read':
                return True
            return self.kann_schreiben

    @login_manager.user_loader
    def load_user(user_id):
        if isinstance(user_id, str) and user_id.startswith('token_'):
            return None  # Token-Gäste werden über request_loader geladen
        return db.session.get(User, int(user_id))

    @login_manager.request_loader
    def load_user_from_request(req):
        from flask import session as sess
        if 'token_kind_id' in sess:
            return TokenGast(sess['token_kind_id'], sess.get('token_berechtigung', 'read'))
        return None

    # CSS-Farbvalidierung (verhindert CSS-Injection)
    def _validate_css_color(value, default):
        if value and re.match(r'^#[0-9a-fA-F]{3,8}$', value):
            return value
        return default

    # Site-Einstellungen laden
    def get_site_settings():
        from src.models import Einstellung
        return {
            'site_name': Einstellung.get_value('site_name', 'BabyApp'),
            'color_primary': _validate_css_color(Einstellung.get_value('color_primary'), '#5d7a54'),
            'color_primary_hover': _validate_css_color(Einstellung.get_value('color_primary_hover'), '#6e8e64'),
            'color_nav_bg': _validate_css_color(Einstellung.get_value('color_nav_bg'), '#3b3028'),
            'color_page_bg': _validate_css_color(Einstellung.get_value('color_page_bg'), '#f5f1ec'),
        }

    # Kontext-Prozessor
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from flask import request as req
        settings = get_site_settings()

        # Kind-Selector global bereitstellen
        kinder = []
        kind = None
        is_token_gast = isinstance(current_user, TokenGast) if current_user.is_authenticated else False

        if current_user.is_authenticated:
            from src.models import Kind, KindFreigabe

            if is_token_gast:
                # Token-Gast: nur das eine freigegebene Kind
                kind = db.session.get(Kind, current_user.kind_id)
                kinder = [kind] if kind else []
            elif current_user.is_admin:
                kinder = Kind.query.order_by(Kind.name).all()
            else:
                kind_ids = [f.kind_id for f in KindFreigabe.query.filter_by(user_id=current_user.id).all()]
                kinder = Kind.query.filter(Kind.id.in_(kind_ids)).order_by(Kind.name).all() if kind_ids else []

            if not is_token_gast:
                kind_id = req.cookies.get('active_kind_id')
                if kind_id:
                    try:
                        kind_id_int = int(kind_id)
                    except (ValueError, TypeError):
                        kind_id_int = None
                    if kind_id_int is not None:
                        erlaubte_ids = {k.id for k in kinder}
                        if kind_id_int in erlaubte_ids or current_user.is_admin:
                            kind = db.session.get(Kind, kind_id_int)
                        else:
                            kind = None  # Kein Zugriff auf dieses Kind
            if not kind and kinder:
                kind = kinder[0]

        return {
            'app_version': APP_VERSION,
            'cache_buster': cache_buster,
            'site_settings': settings,
            'now': datetime.utcnow(),
            'kinder': kinder,
            'kind': kind,
        }

    # CSRF-Fehler als JSON statt HTML zurückgeben
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        if '/api/' in flask_request.path:
            logging.warning(f'CSRF-Fehler auf {flask_request.path}: {e.description}')
            from flask import jsonify
            return jsonify({'error': f'CSRF-Token ungültig: {e.description}'}), 400
        return e.description, 400

    # Unbehandelte Exceptions als JSON für API-Requests
    @app.errorhandler(Exception)
    def handle_exception(e):
        if '/api/' in flask_request.path:
            logging.error(f'Unbehandelte Exception auf {flask_request.method} {flask_request.path}: {type(e).__name__}: {e}', exc_info=True)
            from flask import jsonify
            return jsonify({'error': f'Interner Serverfehler: {type(e).__name__}'}), 500
        raise e

    # API-Request-Logging
    @app.before_request
    def log_api_request():
        from flask_login import current_user
        from flask import request as req
        if '/api/' in req.path and current_user.is_authenticated:
            user_info = f'{current_user.username}(ID:{current_user.id})' if hasattr(current_user, 'username') else f'TokenGast({current_user.id})'
            body_info = ''
            if req.method in ('POST', 'PUT') and req.is_json:
                data = req.get_json(silent=True)
                if data:
                    safe_data = {k: v for k, v in data.items() if k not in ('password', 'passwort', 'neu', 'aktuell')}
                    body_info = f' body={safe_data}'
            logging.info(f'API {req.method} {req.path} | User: {user_info}{body_info}')

    @app.after_request
    def log_api_response(response):
        from flask import request as req
        if '/api/' in req.path and response.status_code >= 400:
            body_preview = response.data.decode('utf-8', errors='replace')[:200] if response.data else ''
            logging.warning(f'API {req.method} {req.path} -> {response.status_code} | {body_preview}')
        return response

    # Globale Sicherheitsprüfungen
    @app.before_request
    def global_security_check():
        from flask_login import current_user
        from flask import request as req
        import re

        if not current_user.is_authenticated:
            return
        if '/api/' not in req.path:
            return

        # Ausnahmen: Nur exakte Pfad-Prefixe (keine Substring-Matches)
        # /api/set-kind/ -- Kind-Auswahl (hat eigenen Check)
        # /api/settings -- App-Einstellungen lesen (hat eigenen Admin-Check für Schreiben)
        # /api/passwort -- Passwort ändern (betrifft eigenen User)
        # /api/typen -- Aktivitätstypen (global, kein Kind-Bezug)
        ausnahme_patterns = [
            r'/api/set-kind/',
            r'/api/settings$',
            r'/api/settings/update$',
            r'/api/passwort$',
            r'/aktivitaeten/api/typen$',
            r'/aktivitaeten/api/typen/',
            r'/api/aktiver-timer/',
            r'/profil/api/',
        ]
        for pattern in ausnahme_patterns:
            if re.search(pattern, req.path):
                return
        if '/benutzerverwaltung/api/' in req.path:
            return  # Hat eigenen Admin-Check

        # 1. Schreibschutz: Leser dürfen keine POST/PUT/DELETE
        if req.method in ('POST', 'PUT', 'DELETE'):
            if not current_user.kann_schreiben:
                logging.warning(f'SECURITY: Schreibversuch von Leser {current_user.username} auf {req.path}')
                from flask import jsonify
                return jsonify({'error': 'Keine Schreibberechtigung (Rolle: Leser)'}), 403

        # 2. Kind-Zugriffsprüfung: kind_id nur aus URLs extrahieren,
        # bei denen die Zahl tatsächlich eine Kind-ID ist (z.B. /api/list/<kind_id>).
        # Bei /api/stop/<id>, /api/update/<id>, /api/delete/<id>, /api/foto/<id>
        # ist die Zahl eine Eintrags-ID -- diese Endpoints prüfen selbst.
        kind_id = None
        eintrag_id_patterns = r'/api/(?:[a-z_-]+/)*(?:stop|update|delete|foto|create|check|toggle)/|/api/\d+/foto|/api/kinder/(?:freigabe|token)/\d+'
        if not re.search(eintrag_id_patterns, req.path):
            m = re.search(r'/api/(?:[a-z_-]+/)*(\d+)', req.path)
            if m:
                kind_id = int(m.group(1))
        # Aus Request-Body (POST/PUT)
        if not kind_id and req.method in ('POST', 'PUT') and req.is_json:
            data = req.get_json(silent=True)
            if data and isinstance(data, dict):
                kind_id = data.get('kind_id')

        if kind_id and not current_user.is_admin:
            is_token = isinstance(current_user, TokenGast)
            if is_token:
                if kind_id != current_user.kind_id:
                    logging.warning(f'SECURITY: Token-Gast versuchte Zugriff auf Kind {kind_id} (erlaubt: {current_user.kind_id})')
                    from flask import jsonify
                    return jsonify({'error': 'Kein Zugriff auf dieses Kind'}), 403
            else:
                from src.models import KindFreigabe
                hat_zugriff = KindFreigabe.query.filter_by(kind_id=kind_id, user_id=current_user.id).first()
                if not hat_zugriff:
                    logging.warning(f'SECURITY: User {current_user.username} (ID {current_user.id}) versuchte Zugriff auf Kind {kind_id}')
                    from flask import jsonify
                    return jsonify({'error': 'Kein Zugriff auf dieses Kind'}), 403

    # Security-Headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(self), microphone=()'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' blob: data:"
        if flask_request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # active_kind_id Cookie-Sicherheit verbessern
        return response

    # Blueprints registrieren
    from src.blueprints.auth import auth_bp
    from src.blueprints.main import main_bp
    from src.blueprints.fuetterung import fuetterung_bp
    from src.blueprints.schlaf import schlaf_bp
    from src.blueprints.windeln import windeln_bp
    from src.blueprints.wachstum import wachstum_bp
    from src.blueprints.gesundheit import gesundheit_bp
    from src.blueprints.zahnung import zahnung_bp
    from src.blueprints.meilensteine import meilensteine_bp
    from src.blueprints.aktivitaeten import aktivitaeten_bp
    from src.blueprints.statistiken import statistiken_bp
    from src.blueprints.einstellungen import einstellungen_bp
    from src.blueprints.benutzerverwaltung import benutzerverwaltung_bp
    from src.blueprints.tagebuch import tagebuch_bp
    from src.blueprints.routinen import routinen_bp
    from src.blueprints.beikost import beikost_bp
    from src.blueprints.notfallinfo import notfallinfo_bp
    from src.blueprints.milchvorrat import milchvorrat_bp
    from src.blueprints.mukipass import mukipass_bp
    from src.blueprints.export import export_bp
    from src.blueprints.profil import profil_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(fuetterung_bp)
    app.register_blueprint(schlaf_bp)
    app.register_blueprint(windeln_bp)
    app.register_blueprint(wachstum_bp)
    app.register_blueprint(gesundheit_bp)
    app.register_blueprint(zahnung_bp)
    app.register_blueprint(meilensteine_bp)
    app.register_blueprint(aktivitaeten_bp)
    app.register_blueprint(statistiken_bp)
    app.register_blueprint(einstellungen_bp)
    app.register_blueprint(benutzerverwaltung_bp)
    app.register_blueprint(tagebuch_bp)
    app.register_blueprint(routinen_bp)
    app.register_blueprint(beikost_bp)
    app.register_blueprint(notfallinfo_bp)
    app.register_blueprint(milchvorrat_bp)
    app.register_blueprint(mukipass_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(profil_bp)

    # Datenbank erstellen & Seed -- atomar mit Filelock
    with app.app_context():
        import fcntl
        lock_path = os.path.join(base_dir, '.db_init.lock')
        try:
            lock_fd = open(lock_path, 'w')
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            needs_seed = not inspector.has_table('users')
            db.create_all()
            if needs_seed:
                _seed_defaults()
        finally:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
            except Exception:
                pass

    return app


def _seed_defaults():
    """Standard-Aktivitätstypen und Admin-User anlegen."""
    from src.models import AktivitaetTyp, User, Einstellung

    # Standard-Aktivitätstypen
    if AktivitaetTyp.query.count() == 0:
        defaults = [
            ('Bauchlage', 'baby', '#8b6e4e'),
            ('Spaziergang', 'walk', '#6b8e5a'),
            ('Spielzeit', 'play', '#c49a3c'),
            ('Baden', 'bath', '#5b7f8e'),
            ('Massage', 'hand', '#7a6555'),
            ('Vorlesen', 'book', '#5d7a54'),
            ('Musik', 'music', '#5a7e6e'),
            ('Arztbesuch', 'medical', '#b55b4a'),
        ]
        for name, icon, farbe in defaults:
            db.session.add(AktivitaetTyp(name=name, icon=icon, farbe=farbe, ist_standard=True))
        db.session.commit()

    # Admin-User
    if User.query.count() == 0:
        admin = User(username='admin', email='admin@babyapp.local', role='admin')
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
