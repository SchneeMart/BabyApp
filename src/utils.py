"""Sicherheits-Hilfsfunktionen für die BabyApp."""
from flask import jsonify
from flask_login import current_user
from src.extensions import db


def get_erstellt_von():
    """Gibt die User-ID für DB-Einträge zurück. None für TokenGast."""
    if hasattr(current_user, 'erstellt_von_id'):
        return current_user.erstellt_von_id
    return current_user.id if isinstance(current_user.id, int) else None


def check_kind_zugriff(kind_id):
    """Prüft ob der aktuelle User Zugriff auf das Kind hat.

    Returns:
        None wenn Zugriff erlaubt, sonst eine Flask-Response (403).
    """
    if not current_user.is_authenticated:
        return jsonify({'error': 'Nicht authentifiziert'}), 401

    if current_user.is_admin:
        return None

    # TokenGast: Prüfe über kind_id-Attribut
    if hasattr(current_user, 'kind_id') and isinstance(current_user.id, str) and current_user.id.startswith('token_'):
        if kind_id != current_user.kind_id:
            return jsonify({'error': 'Kein Zugriff auf dieses Kind'}), 403
        return None

    # Normaler User: Prüfe KindFreigabe
    from src.models import KindFreigabe
    hat_zugriff = KindFreigabe.query.filter_by(kind_id=kind_id, user_id=current_user.id).first()
    if not hat_zugriff:
        return jsonify({'error': 'Kein Zugriff auf dieses Kind'}), 403

    return None


def check_owner_oder_admin(kind_id):
    """Prüft ob der User Owner des Kindes oder Admin ist.

    Für Einstellungen-Endpoints: Kinder bearbeiten/löschen, Freigaben, Tokens.

    Returns:
        None wenn erlaubt, sonst eine Flask-Response (403).
    """
    if not current_user.is_authenticated:
        return jsonify({'error': 'Nicht authentifiziert'}), 401

    if current_user.is_admin:
        return None

    # TokenGast darf niemals Owner-Aktionen ausführen
    if hasattr(current_user, 'kind_id') and isinstance(current_user.id, str) and current_user.id.startswith('token_'):
        return jsonify({'error': 'Keine Berechtigung für diese Aktion'}), 403

    # Prüfe ob User Owner oder Elternteil mit Freigabe ist
    from src.models import KindFreigabe
    freigabe = KindFreigabe.query.filter_by(kind_id=kind_id, user_id=current_user.id).first()
    if not freigabe or freigabe.rolle not in ('owner',):
        # Elternteile (Mutter/Vater) mit irgendeiner Freigabe dürfen auch
        if current_user.is_elternteil and freigabe:
            return None
        return jsonify({'error': 'Nur der Besitzer oder Admin darf das'}), 403

    return None
