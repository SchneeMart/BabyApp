# BabyApp

Umfassende, selbst-gehostete Baby-Tracker Web-App für Eltern und Betreuer. Open Source, kostenlos, keine Cloud, deine Daten bleiben bei dir.

## Features

### Tracking-Module
- **Fütterung** -- Stillen (Timer + Seitenwechsel), Flasche, Abpumpen, Beikost
- **Schlaf** -- Start/Stop-Timer, Schlafvorhersagen, Nickerchen & Nachtschlaf
- **Windeln** -- Schnellerfassung (nass/stuhl/beides/trocken)
- **Wachstum** -- Gewicht, Größe, Kopfumfang mit WHO-Perzentilkurven
- **Gesundheit** -- Temperatur, Symptome, Impfungen, Medikamente, Arztbesuche, Fotos
- **Zahnung** -- Interaktives SVG-Zahndiagramm (20 Milchzähne)
- **Meilensteine** -- 36 Standard-Meilensteine in 5 Kategorien
- **Aktivitäten** -- Bauchlage, Spaziergang, Spielzeit, Baden, frei konfigurierbar
- **Beikost** -- Lebensmittel-Tracking, 4-Tage-Regel, Allergieprotokoll
- **Tagebuch** -- Tageseinträge mit Fotos und Stimmung
- **Routinen** -- Tagesablauf-Checkliste
- **Milchvorrat** -- Abgepumpte Milch verwalten (Kühlschrank/Tiefkühler, Verfallsdatum)

### Vorsorge (AT/DE)
- **Österreich:** Mutter-Kind-Pass mit allen Untersuchungen + Gratisimpfprogramm
- **Deutschland:** Gelbes U-Heft (U1-U9, U7a, J1) + STIKO-Impfplan
- Automatische Soll-Termine basierend auf Geburtsdatum

### Benutzerverwaltung
- Rollen: Admin, Mutter, Vater, Betreuer, Leser
- Kind-Freigabe per E-Mail-Einladung oder öffentlichem Link (read/write)
- Jeder Benutzer sieht nur die Kinder auf die er Zugriff hat
- Eigenes Profil bearbeiten (Name, E-Mail, Passwort)

### Weitere Features
- **PWA** -- Installierbar auf iOS und Android, Offline-fähig
- **Dark Mode** -- Für nächtliches Füttern
- **Kamera** -- Native Browser-Kamera mit Fallback
- **PDF-Arztbericht** -- Druckbarer Bericht für den Kinderarzt
- **CSV-Export** -- Alle Module exportierbar
- **Notfallinfo** -- Arzt, Krankenhaus, Allergien -- teilbar per Token-Link
- **Mobiloptimiert** -- Responsive Design für alle Bildschirmgrößen

## Schnellstart

### Voraussetzungen

- [Docker](https://docs.docker.com/get-docker/) und [Docker Compose](https://docs.docker.com/compose/install/)

### Installation

```bash
# 1. Repository klonen
git clone https://github.com/SchneeMart/BabyApp.git
cd BabyApp

# 2. Umgebungsvariablen konfigurieren
cp .env.example .env
# .env bearbeiten: MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD etc. anpassen
# (optional -- App funktioniert auch ohne Mail, Einladungslinks werden dann direkt angezeigt)

# 3. Container bauen und starten
docker compose up -d

# 4. Fertig!
# App öffnen: http://localhost:5020
# Login: admin / admin
```

### Erster Login

1. Öffne `http://localhost:5020` im Browser
2. Melde dich mit **admin** / **admin** an
3. Gehe auf **Profil** (unten in der Sidebar) und ändere sofort dein Passwort
4. Gehe auf **Einstellungen** und lege dein erstes Kind an
5. Fertig -- alle Module sind sofort nutzbar

### Auf dem Handy installieren (PWA)

**iPhone (Safari):**
1. Öffne die App-URL in Safari
2. Tippe auf das Teilen-Symbol (Quadrat mit Pfeil)
3. Wähle "Zum Home-Bildschirm"

**Android (Chrome):**
1. Öffne die App-URL in Chrome
2. Tippe auf "App installieren" (oder Menu > "Zum Startbildschirm hinzufügen")

### Installation ohne Docker

```bash
# Python 3.10+ erforderlich
pip install -r requirements.txt
export FLASK_APP=src.app
export SECRET_KEY=dein-geheimer-key
flask run --host 0.0.0.0 --port 5020
```

## Konfiguration

### Umgebungsvariablen (.env)

| Variable | Beschreibung | Pflicht | Standard |
|----------|-------------|:---:|----------|
| `SECRET_KEY` | Flask Secret Key (zufälliger String) | Ja | dev-fallback |
| `DB_MODE` | Datenbank-Modus (`dev` oder `prod`) | Nein | dev |
| `MAIL_SERVER` | SMTP-Server für E-Mail-Versand | Nein | - |
| `MAIL_PORT` | SMTP-Port | Nein | 465 |
| `MAIL_USE_SSL` | SSL verwenden (`True`/`False`) | Nein | True |
| `MAIL_USERNAME` | SMTP-Benutzername | Nein | - |
| `MAIL_PASSWORD` | SMTP-Passwort | Nein | - |
| `MAIL_SENDER` | Absender-Adresse | Nein | - |

### Ohne Mail-Server

Die App funktioniert auch komplett ohne Mail-Server. Wenn kein `MAIL_SERVER` konfiguriert ist:
- Einladungslinks werden direkt in der Oberfläche angezeigt (zum manuellen Weitergeben)
- Passwort-Reset funktioniert nicht per E-Mail (Admin kann Nutzer neu einladen)

### Port ändern

In `docker-compose.yml` die Zeile `"5020:5000"` anpassen, z.B. `"8080:5000"` für Port 8080.

### HTTPS (empfohlen)

Für Kamera-Zugriff direkt im Browser (ohne App-Wechsel) ist HTTPS erforderlich. Optionen:
- Reverse-Proxy (Nginx, Caddy, Traefik) mit Let's Encrypt
- Cloudflare Tunnel

### Farben & App-Name

Über **Einstellungen > App** (nur als Admin) können Primärfarbe, Hover-Farbe und der App-Name geändert werden.

## Technologie

| Komponente | Technologie |
|-----------|-------------|
| Backend | Python 3.12, Flask, SQLAlchemy |
| Datenbank | SQLite |
| Frontend | Vanilla JS, eigenes CSS-System |
| Font | Nunito (Google Fonts) |
| Icons | SVG Sprite Sheet (48 Icons) |
| Fotos | Komprimierte BLOBs in DB (Pillow) |
| Mail | Flask-Mail (SMTP/SSL) |
| Container | Docker, Gunicorn |
| PWA | Service Worker, Web App Manifest |

## Sicherheit

- CSRF-Schutz auf allen API-Endpoints
- XSS-Schutz durch globale HTML-Escape-Funktion
- Kind-Zugriffskontrolle auf jedem API-Endpoint
- Rollen-basierte Schreibrechte (Leser-Modus blockiert alle Schreiboperationen)
- Token-basierte Freigabe-Links (kein Benutzer wird in der DB angelegt)
- Passwort-Hashing (Werkzeug/bcrypt)
- Rate-Limiting auf Login (10/Minute)
- Open-Redirect-Schutz

## Mitwirken

Beiträge sind willkommen! Bitte erstelle einen Fork und einen Pull Request.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE). Du kannst es frei verwenden, ändern und verbreiten.
