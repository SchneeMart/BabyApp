from functools import wraps
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
mail = Mail()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def schreib_required(f):
    """Decorator: Nur Benutzer mit Schreibrecht (nicht Leser) dürfen diese Route nutzen."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Nicht angemeldet'}), 401
        if not current_user.kann_schreiben:
            return jsonify({'error': 'Keine Schreibberechtigung (Rolle: Leser)'}), 403
        return f(*args, **kwargs)
    return decorated
