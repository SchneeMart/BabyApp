import enum
from datetime import datetime, date
from src.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


# =============================================================================
# BENUTZER & BERECHTIGUNGEN
# =============================================================================

class UserRole(str, enum.Enum):
    ADMIN = 'admin'
    MUTTER = 'mutter'
    VATER = 'vater'
    BETREUER = 'betreuer'
    LESER = 'leser'

class Permission(db.Model):
    __tablename__ = 'permissions'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    module_id = db.Column(db.String(50), primary_key=True)
    can_read = db.Column(db.Boolean, default=True)
    can_write = db.Column(db.Boolean, default=False)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.BETREUER)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    password_reset_token = db.Column(db.String(100), nullable=True, unique=True)
    password_reset_expiration = db.Column(db.DateTime, nullable=True)
    invite_token = db.Column(db.String(100), nullable=True, unique=True)
    invite_expiration = db.Column(db.DateTime, nullable=True)

    module_permissions = db.relationship('Permission', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_elternteil(self):
        """Mutter, Vater oder Admin -- darf Kinder anlegen."""
        return self.role in (UserRole.ADMIN, UserRole.MUTTER, UserRole.VATER)

    @property
    def kann_kind_erstellen(self):
        return self.is_elternteil

    @property
    def kann_schreiben(self):
        """Alle außer Leser dürfen Einträge erstellen."""
        return self.role != UserRole.LESER

    @property
    def rolle_label(self):
        labels = {
            'admin': 'Admin',
            'mutter': 'Mutter',
            'vater': 'Vater',
            'betreuer': 'Betreuer',
            'leser': 'Leser',
        }
        return labels.get(self.role, self.role)

    def can(self, module_id, perm_type):
        if self.is_admin:
            return True
        perm = self.module_permissions.filter_by(module_id=module_id).first()
        if not perm:
            return False
        return getattr(perm, f'can_{perm_type}', False)


# =============================================================================
# KINDER
# =============================================================================

class Kind(db.Model):
    __tablename__ = 'kinder'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    geburtsdatum = db.Column(db.Date, nullable=False)
    geschlecht = db.Column(db.String(10), nullable=True)  # m/w/d
    land = db.Column(db.String(5), nullable=False, default='AT')  # AT oder DE
    fruehgeburt_wochen = db.Column(db.Integer, nullable=True)
    blutgruppe = db.Column(db.String(10), nullable=True)
    foto = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Beziehungen
    fuetterungen = db.relationship('Fuetterung', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    schlafeintraege = db.relationship('Schlaf', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    windeln = db.relationship('Windel', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    wachstumsdaten = db.relationship('Wachstum', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    gesundheitseintraege = db.relationship('Gesundheit', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    zahneintraege = db.relationship('Zahn', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    meilensteine = db.relationship('Meilenstein', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    aktivitaeten = db.relationship('Aktivitaet', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    tagebucheintraege = db.relationship('Tagebuch', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    routinen = db.relationship('Routine', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    beikosteintraege = db.relationship('Beikost', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    notfallinfo = db.relationship('Notfallinfo', backref='kind', uselist=False, cascade='all, delete-orphan')
    impfungen = db.relationship('Impfung', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    medikamente = db.relationship('Medikament', backref='kind', lazy='dynamic', cascade='all, delete-orphan')
    arztbesuche = db.relationship('Arztbesuch', backref='kind', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def alter_tage(self):
        if not self.geburtsdatum:
            return 0
        return (date.today() - self.geburtsdatum).days

    @property
    def alter_text(self):
        tage = self.alter_tage
        if tage < 0:
            return f"ET in {-tage} Tagen"
        if tage < 31:
            return f"{tage} Tage"
        monate = tage // 30
        rest_tage = tage % 30
        if monate < 12:
            return f"{monate} Mon. {rest_tage} T."
        jahre = monate // 12
        rest_monate = monate % 12
        return f"{jahre} J. {rest_monate} Mon."


# Zuordnung Benutzer <-> Kinder (mit Berechtigungen)
class KindFreigabe(db.Model):
    """Verknüpft Benutzer mit Kindern inkl. Berechtigung."""
    __tablename__ = 'kind_freigaben'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rolle = db.Column(db.String(20), nullable=False, default='read')  # owner/write/read
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    kind = db.relationship('Kind', backref=db.backref('freigaben', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('kind_freigaben', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('kind_id', 'user_id', name='uq_kind_user'),)


class KindToken(db.Model):
    """Öffentliche Freigabe-Tokens für Kinder."""
    __tablename__ = 'kind_tokens'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    token = db.Column(db.String(64), nullable=False, unique=True)
    berechtigung = db.Column(db.String(20), nullable=False, default='read')  # read/write
    erstellt_von = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    aktiv = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    kind = db.relationship('Kind', backref=db.backref('tokens', lazy='dynamic', cascade='all, delete-orphan'))


# =============================================================================
# FÜTTERUNG
# =============================================================================

class FuetterungsTyp(str, enum.Enum):
    STILLEN = 'stillen'
    FLASCHE = 'flasche'
    ABPUMPEN = 'abpumpen'
    BEIKOST = 'beikost'

class Fuetterung(db.Model):
    __tablename__ = 'fuetterungen'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    typ = db.Column(db.String(20), nullable=False)  # stillen/flasche/abpumpen/beikost
    beginn = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ende = db.Column(db.DateTime, nullable=True)
    dauer_minuten = db.Column(db.Integer, nullable=True)
    # Stillen-spezifisch
    seite = db.Column(db.String(10), nullable=True)  # links/rechts/beide
    letzte_seite = db.Column(db.String(10), nullable=True)
    # Flasche/Abpumpen
    menge_ml = db.Column(db.Float, nullable=True)
    inhalt = db.Column(db.String(50), nullable=True)  # muttermilch/formula/wasser
    # Beikost
    lebensmittel = db.Column(db.String(200), nullable=True)
    reaktion = db.Column(db.String(200), nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    erstellt_von = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# SCHLAF
# =============================================================================

class Schlaf(db.Model):
    __tablename__ = 'schlafeintraege'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    beginn = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ende = db.Column(db.DateTime, nullable=True)
    dauer_minuten = db.Column(db.Integer, nullable=True)
    typ = db.Column(db.String(20), default='nickerchen')  # nickerchen/nachtschlaf
    qualitaet = db.Column(db.Integer, nullable=True)  # 1-5 Sterne
    ort = db.Column(db.String(50), nullable=True)  # bett/kinderwagen/auto/arm
    notiz = db.Column(db.Text, nullable=True)
    erstellt_von = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# WINDELN
# =============================================================================

class Windel(db.Model):
    __tablename__ = 'windeln'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    zeitpunkt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    typ = db.Column(db.String(20), nullable=False)  # nass/stuhl/beides/trocken
    farbe = db.Column(db.String(30), nullable=True)
    konsistenz = db.Column(db.String(30), nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    erstellt_von = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# WACHSTUM
# =============================================================================

class Wachstum(db.Model):
    __tablename__ = 'wachstumsdaten'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    datum = db.Column(db.Date, nullable=False, default=date.today)
    gewicht_kg = db.Column(db.Float, nullable=True)
    groesse_cm = db.Column(db.Float, nullable=True)
    kopfumfang_cm = db.Column(db.Float, nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    erstellt_von = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# GESUNDHEIT
# =============================================================================

class Gesundheit(db.Model):
    __tablename__ = 'gesundheitseintraege'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    datum = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    typ = db.Column(db.String(30), nullable=False)  # symptom/temperatur/sonstiges
    temperatur = db.Column(db.Float, nullable=True)
    symptome = db.Column(db.String(500), nullable=True)
    beschreibung = db.Column(db.Text, nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    erstellt_von = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    fotos = db.relationship('GesundheitFoto', backref='eintrag', lazy='dynamic', cascade='all, delete-orphan')


class GesundheitFoto(db.Model):
    """Fotos zu Gesundheitseinträgen, als BLOB in der DB gespeichert."""
    __tablename__ = 'gesundheit_fotos'
    id = db.Column(db.Integer, primary_key=True)
    gesundheit_id = db.Column(db.Integer, db.ForeignKey('gesundheitseintraege.id'), nullable=False)
    daten = db.Column(db.LargeBinary, nullable=False)
    mime_type = db.Column(db.String(50), nullable=False, default='image/jpeg')
    dateiname = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Impfung(db.Model):
    __tablename__ = 'impfungen'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    datum = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    arzt = db.Column(db.String(100), nullable=True)
    charge = db.Column(db.String(50), nullable=True)
    reaktion = db.Column(db.Text, nullable=True)
    naechster_termin = db.Column(db.Date, nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Medikament(db.Model):
    __tablename__ = 'medikamente'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    dosis = db.Column(db.String(50), nullable=True)
    einheit = db.Column(db.String(20), nullable=True)  # ml/mg/tropfen
    frequenz = db.Column(db.String(50), nullable=True)  # 3x täglich etc.
    beginn = db.Column(db.Date, nullable=False)
    ende = db.Column(db.Date, nullable=True)
    grund = db.Column(db.String(200), nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Arztbesuch(db.Model):
    __tablename__ = 'arztbesuche'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    datum = db.Column(db.DateTime, nullable=False)
    arzt = db.Column(db.String(100), nullable=True)
    grund = db.Column(db.String(200), nullable=False)
    diagnose = db.Column(db.Text, nullable=True)
    behandlung = db.Column(db.Text, nullable=True)
    naechster_termin = db.Column(db.Date, nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# ZAHNUNG
# =============================================================================

class Zahn(db.Model):
    __tablename__ = 'zahneintraege'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    zahn_nr = db.Column(db.Integer, nullable=False)  # 1-20 Milchzähne
    name = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(20), nullable=False)  # oben-links/oben-rechts/unten-links/unten-rechts
    durchbruch_datum = db.Column(db.Date, nullable=True)
    ausfall_datum = db.Column(db.Date, nullable=True)
    foto = db.Column(db.String(200), nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# MEILENSTEINE
# =============================================================================

class MeilensteinKategorie(str, enum.Enum):
    MOTORIK = 'motorik'
    SPRACHE = 'sprache'
    SOZIAL = 'sozial'
    KOGNITIV = 'kognitiv'
    SELBSTSTAENDIGKEIT = 'selbststaendigkeit'

class Meilenstein(db.Model):
    __tablename__ = 'meilensteine'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    kategorie = db.Column(db.String(30), nullable=False)
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text, nullable=True)
    datum = db.Column(db.Date, nullable=True)
    alter_monate = db.Column(db.Integer, nullable=True)
    erreicht = db.Column(db.Boolean, default=False)
    foto = db.Column(db.String(200), nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    fotos = db.relationship('MeilensteinFoto', backref='meilenstein', lazy='dynamic', cascade='all, delete-orphan')


# =============================================================================
# AKTIVITÄTEN
# =============================================================================

class AktivitaetTyp(db.Model):
    __tablename__ = 'aktivitaet_typen'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(30), nullable=True)
    farbe = db.Column(db.String(7), nullable=True)
    ist_standard = db.Column(db.Boolean, default=False)

class Aktivitaet(db.Model):
    __tablename__ = 'aktivitaeten'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    typ_id = db.Column(db.Integer, db.ForeignKey('aktivitaet_typen.id'), nullable=False)
    beginn = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ende = db.Column(db.DateTime, nullable=True)
    dauer_minuten = db.Column(db.Integer, nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    erstellt_von = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    typ = db.relationship('AktivitaetTyp', backref='aktivitaeten')


# =============================================================================
# TAGEBUCH
# =============================================================================

class Tagebuch(db.Model):
    __tablename__ = 'tagebucheintraege'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    datum = db.Column(db.Date, nullable=False, default=date.today)
    titel = db.Column(db.String(200), nullable=True)
    text = db.Column(db.Text, nullable=True)
    stimmung = db.Column(db.Integer, nullable=True)  # 1-5
    foto = db.Column(db.String(200), nullable=True)
    erstellt_von = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    fotos = db.relationship('TagebuchFoto', backref='eintrag', lazy='dynamic', cascade='all, delete-orphan')


class TagebuchFoto(db.Model):
    """Fotos zu Tagebucheinträgen, als BLOB in der DB gespeichert."""
    __tablename__ = 'tagebuch_fotos'
    id = db.Column(db.Integer, primary_key=True)
    tagebuch_id = db.Column(db.Integer, db.ForeignKey('tagebucheintraege.id'), nullable=False)
    daten = db.Column(db.LargeBinary, nullable=False)
    mime_type = db.Column(db.String(50), nullable=False, default='image/jpeg')
    dateiname = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# ROUTINEN
# =============================================================================

class Routine(db.Model):
    __tablename__ = 'routinen'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.Text, nullable=True)
    uhrzeit = db.Column(db.String(5), nullable=True)  # HH:MM
    wochentage = db.Column(db.String(20), nullable=True)  # "1,2,3,4,5" Mo-Fr
    aktiv = db.Column(db.Boolean, default=True)
    erinnerung = db.Column(db.Boolean, default=False)
    erinnerung_minuten_vorher = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RoutineCheck(db.Model):
    __tablename__ = 'routine_checks'
    id = db.Column(db.Integer, primary_key=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routinen.id'), nullable=False)
    datum = db.Column(db.Date, nullable=False, default=date.today)
    erledigt = db.Column(db.Boolean, default=False)
    erledigt_um = db.Column(db.DateTime, nullable=True)
    notiz = db.Column(db.Text, nullable=True)

    routine = db.relationship('Routine', backref=db.backref('checks', lazy='dynamic', cascade='all, delete-orphan'))


# =============================================================================
# BEIKOST-PLANER
# =============================================================================

class Beikost(db.Model):
    __tablename__ = 'beikosteintraege'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    datum = db.Column(db.Date, nullable=False, default=date.today)
    lebensmittel = db.Column(db.String(100), nullable=False)
    kategorie = db.Column(db.String(50), nullable=True)  # obst/gemuese/getreide/protein/milch
    menge = db.Column(db.String(50), nullable=True)
    akzeptanz = db.Column(db.Integer, nullable=True)  # 1-5 (mag nicht bis liebt)
    allergie_verdacht = db.Column(db.Boolean, default=False)
    reaktion = db.Column(db.Text, nullable=True)
    vier_tage_test_start = db.Column(db.Date, nullable=True)
    vier_tage_test_ok = db.Column(db.Boolean, nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# NOTFALLINFO
# =============================================================================

class Notfallinfo(db.Model):
    __tablename__ = 'notfallinfo'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, unique=True)
    share_token = db.Column(db.String(64), nullable=True, unique=True)
    kinderarzt_name = db.Column(db.String(100), nullable=True)
    kinderarzt_telefon = db.Column(db.String(30), nullable=True)
    kinderarzt_adresse = db.Column(db.String(200), nullable=True)
    krankenhaus = db.Column(db.String(100), nullable=True)
    krankenhaus_telefon = db.Column(db.String(30), nullable=True)
    versicherung = db.Column(db.String(100), nullable=True)
    versicherungsnummer = db.Column(db.String(50), nullable=True)
    allergien = db.Column(db.Text, nullable=True)
    unvertraeglichkeiten = db.Column(db.Text, nullable=True)
    chronische_erkrankungen = db.Column(db.Text, nullable=True)
    blutgruppe = db.Column(db.String(10), nullable=True)
    notfallkontakt_name = db.Column(db.String(100), nullable=True)
    notfallkontakt_telefon = db.Column(db.String(30), nullable=True)
    notfallkontakt_beziehung = db.Column(db.String(50), nullable=True)
    sonstiges = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# EINSTELLUNGEN
# =============================================================================

# =============================================================================
# MILCHVORRAT
# =============================================================================

class Milchvorrat(db.Model):
    __tablename__ = 'milchvorrat'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    datum = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    menge_ml = db.Column(db.Float, nullable=False)
    typ = db.Column(db.String(20), nullable=False, default='eingelagert')  # eingelagert/verbraucht/entsorgt
    lagerort = db.Column(db.String(30), nullable=True)  # kuehlschrank/tiefkuehl
    flasche_nr = db.Column(db.String(20), nullable=True)
    verfallsdatum = db.Column(db.Date, nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    erstellt_von = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# ERINNERUNGEN
# =============================================================================

class Erinnerung(db.Model):
    __tablename__ = 'erinnerungen'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text, nullable=True)
    faellig_am = db.Column(db.DateTime, nullable=False)
    typ = db.Column(db.String(30), nullable=True)  # impfung/arzt/medikament/sonstiges
    erledigt = db.Column(db.Boolean, default=False)
    erledigt_am = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# MUTTER-KIND-PASS (Österreich)
# =============================================================================

class MuKiUntersuchung(db.Model):
    """Österreichische Mutter-Kind-Pass Untersuchungen."""
    __tablename__ = 'muki_untersuchungen'
    id = db.Column(db.Integer, primary_key=True)
    kind_id = db.Column(db.Integer, db.ForeignKey('kinder.id'), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)  # U1, U2, ... U9
    bezeichnung = db.Column(db.String(200), nullable=False)
    alter_von_wochen = db.Column(db.Integer, nullable=True)
    alter_bis_wochen = db.Column(db.Integer, nullable=True)
    soll_datum = db.Column(db.Date, nullable=True)
    durchgefuehrt_am = db.Column(db.Date, nullable=True)
    arzt = db.Column(db.String(100), nullable=True)
    befund = db.Column(db.Text, nullable=True)
    gewicht = db.Column(db.Float, nullable=True)
    groesse = db.Column(db.Float, nullable=True)
    kopfumfang = db.Column(db.Float, nullable=True)
    notiz = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# FOTOS FÜR MEILENSTEINE
# =============================================================================

class MeilensteinFoto(db.Model):
    __tablename__ = 'meilenstein_fotos'
    id = db.Column(db.Integer, primary_key=True)
    meilenstein_id = db.Column(db.Integer, db.ForeignKey('meilensteine.id'), nullable=False)
    daten = db.Column(db.LargeBinary, nullable=False)
    mime_type = db.Column(db.String(50), nullable=False, default='image/jpeg')
    dateiname = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =============================================================================
# EINSTELLUNGEN
# =============================================================================

class Einstellung(db.Model):
    __tablename__ = 'einstellungen'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=True)

    @staticmethod
    def get_value(key, default=None):
        e = Einstellung.query.filter_by(key=key).first()
        return e.value if e else default

    @staticmethod
    def set_value(key, value):
        e = Einstellung.query.filter_by(key=key).first()
        if e:
            e.value = str(value)
        else:
            e = Einstellung(key=key, value=str(value))
            db.session.add(e)
        db.session.commit()
