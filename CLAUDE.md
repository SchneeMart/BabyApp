# CLAUDE.md

Diese Datei bietet Orientierung für Claude Code bei der Arbeit mit diesem Repository.

## Projektübersicht

**BabyApp** ist eine umfassende Baby-Tracker Web-App, entwickelt mit Flask. Sie verwaltet Fütterung, Schlaf, Windeln, Wachstum, Gesundheit, Zahnung, Meilensteine, Aktivitäten, Beikost, Tagebuch, Routinen, Milchvorrat, MuKi-Pass/U-Heft, Notfallinfo, Export und Benutzerverwaltung.

## Docker Setup

- **Web Container:** `babyapp-web` (Port 5020)
- **Compose-Pfad:** Projektverzeichnis

### Container-Restart
```bash
docker compose restart web
```

### Wichtig
- **NIEMALS die Datenbank löschen** (`app_dev.db`) ohne explizite Anweisung
- **NIEMALS `rm -f app_dev.db`** -- Daten sind produktiv und nicht wiederherstellbar
- Container-Restart reicht für Code-Änderungen (Volume ist gemountet)

## Entwicklungsbefehle

```bash
# Neustart nach Code-Änderungen
docker compose restart web

# Logs anzeigen
docker logs babyapp-web --since 30s

# Seed-Daten (NUR bei expliziter Anweisung)
docker exec babyapp-web python3 /app/seed_demo.py
```

## Datenbank

- **Datei:** `app_dev.db` (SQLite, im Projektroot)
- **NICHT löschen, NICHT zurücksetzen** ohne explizite Anweisung
- DB-Schema wird automatisch beim Start erstellt/erweitert (`db.create_all()` mit Filelock)
- Migrationen: Aktuell über `db.create_all()`, keine Flask-Migrate Skripte

## Architektur

### Anwendungsfabrik-Muster
- `src/app.py`: Flask-App über `create_app()`, Extensions, Context-Processor, globale Security-Checks
- Datenbank: SQLite
- Session-basierte Token-Gäste (kein DB-User für öffentliche Links)

### Blueprints (Module)
| Blueprint | Pfad | Zweck |
|-----------|------|-------|
| `auth` | `/auth` | Login, Logout, Registrierung, Passwort-Reset |
| `main` | `/` | Dashboard, Kind-Wechsel, Token-Share, Service Worker |
| `profil` | `/profil` | Eigenes Profil bearbeiten (Name, E-Mail, Passwort) |
| `fuetterung` | `/fuetterung` | Stillen, Flasche, Abpumpen, Beikost-Tracking |
| `schlaf` | `/schlaf` | Schlaf-Timer, Vorhersagen, Schlafprotokoll |
| `windeln` | `/windeln` | Windel-Tracking (nass/stuhl/beides/trocken) |
| `wachstum` | `/wachstum` | Gewicht, Größe, Kopfumfang, WHO-Perzentilkurven |
| `gesundheit` | `/gesundheit` | Symptome, Temperatur, Impfungen, Medikamente, Arztbesuche, Fotos |
| `zahnung` | `/zahnung` | Zahndiagramm mit SVG-Zähnen (20 Milchzähne) |
| `meilensteine` | `/meilensteine` | 36 Standard-Meilensteine, 5 Kategorien, eigene Meilensteine |
| `aktivitaeten` | `/aktivitaeten` | Bauchlage, Spaziergang, Spielzeit etc., konfigurierbare Typen |
| `beikost` | `/beikost` | Lebensmittel-Tracking, 4-Tage-Regel, Allergieprotokoll |
| `tagebuch` | `/tagebuch` | Tageseinträge mit Fotos, Stimmung |
| `routinen` | `/routinen` | Tagesroutinen-Checkliste |
| `milchvorrat` | `/milchvorrat` | Abgepumpte Milch verwalten (Kühlschrank/Tiefkühler) |
| `mukipass` | `/mukipass` | MuKi-Pass (AT) / Gelbes U-Heft (DE), Impfplan |
| `notfallinfo` | `/notfallinfo` | Kinderarzt, Krankenhaus, Versicherung, Allergien |
| `export` | `/export` | CSV-Export, druckbarer Arztbericht |
| `einstellungen` | `/einstellungen` | Kinder verwalten, Freigaben, Tokens, App-Config |
| `benutzerverwaltung` | `/benutzerverwaltung` | Benutzer einladen, Rollen, Berechtigungen (nur Admin) |

### Rollen-System
| Rolle | Kinder anlegen | Schreiben | Lesen | Benutzerverwaltung |
|-------|:-:|:-:|:-:|:-:|
| Admin | Ja | Ja | Ja | Ja |
| Mutter | Ja | Ja | Ja | Nein |
| Vater | Ja | Ja | Ja | Nein |
| Betreuer | Nein | Ja | Ja | Nein |
| Leser | Nein | Nein | Ja | Nein |

### Kind-Zugriffskontrolle
- Jedes Kind gehört einem Besitzer (owner) über `KindFreigabe`
- Zugriff nur über explizite Freigabe (read/write/owner)
- `check_kind_zugriff()` in `src/utils.py` -- wird in JEDEM API-Endpoint aufgerufen
- `check_owner_oder_admin()` für Einstellungen/Freigaben
- Globaler `before_request` Check in `app.py` als zusätzliche Absicherung
- Token-Gäste (`TokenGast`) leben nur in der Session, kein DB-User

### Sicherheit
- CSRF-Token wird im `api()` JS-Helper mitgesendet
- XSS-Schutz: Globale `esc()` Funktion für alle innerHTML-Einfügungen
- Alle onclick-Handler nutzen ID-basierte Lookups statt String-Interpolation
- Fotos werden als komprimierte BLOBs in der DB gespeichert (Pillow, max 1200px, JPEG 80%)
- Notfallinfo-Share über zufälligen Token statt Integer-ID
- Login: Open-Redirect-Schutz auf `next`-Parameter
- Readonly-Mode (CSS + Backend) für Leser-Rolle

### CSS-Architektur
Eigenes CSS-System (kein Framework), aufgeteilt in:
- `base.css` -- Fonts (Nunito), CSS-Variablen, Dark Mode, Readonly Mode
- `layout.css` -- Header, Sidebar, Content, Footer, Mobile
- `buttons.css` -- Button-Varianten, Quick-Actions
- `forms.css` -- Formulare, Inputs, Toggles, Floating Labels
- `cards.css` -- Karten, Module-Tiles, Stats, Timeline, Timer, Kind-Dropdown
- `tables.css` -- Tabellen, Mobile-responsive
- `modals.css` -- Modale, Toasts
- `utilities.css` -- Hilfsklassen, Badges, Tabs, Login

### Farbschema (Natur-Braun-Grün)
- Primary: `#5d7a54` (Waldgrün)
- Accent: `#8b6e4e` (Braun)
- Dark BG: `#3b3028` (Holzbraun)
- Page BG: `#f5f1ec` (Beige)
- Konfigurierbar über Einstellungen (DB)

### JavaScript-Systeme
- `app.js` -- API-Helper, Timer, Datum-Formatierung, Navigation, Dark Mode, Service Worker, `esc()`
- `global-modals.js` -- Toast, Modal, Confirm, Prompt (alles DOM-basiert, kein innerHTML)
- `global-camera.js` -- Native Kamera (getUserMedia) mit File-Input-Fallback
- `global-icons.js` -- SVG Icon-Helper `icon(name)`
- `who-perzentile.js` -- WHO Wachstumsstandards (AT/DE), Canvas-basierte Perzentilkurven

### PWA
- `manifest.json` mit App-Name, Icons, Shortcuts
- Service Worker (`sw.js`) mit Cache-Strategien
- Installierbar auf iOS (Safari) und Android (Chrome)

### Mail
- Konfiguration über `.env`
- SSL auf Port 465
- HTML-Mail-Template in `src/mail_template.py` im App-Design
- Verwendet für: Einladungen, Passwort-Reset

### Länder-Unterstützung (AT/DE)
- Pro Kind konfigurierbar (`Kind.land`)
- **Österreich:** MuKi-Pass (12 Untersuchungen), Österreichisches Gratisimpfprogramm
- **Deutschland:** Gelbes U-Heft (U1-U9, U7a, J1), STIKO-Impfempfehlungen
- Dynamische Titel und Labels je nach Land

## Versionierung & Cache-Buster

- `version.json` im Projektroot
- Cache-Buster: MD5 aus Version + Startup-Timestamp
- Alle static-Referenzen mit `?v={{ cache_buster }}`

## Umgebungsvariablen (.env)

Siehe `.env.example` für alle Variablen und Standardwerte.
