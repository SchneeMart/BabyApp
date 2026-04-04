#!/usr/bin/env python3
"""Import-Script: BabyDaybook -> BabyApp"""

import sqlite3
from datetime import datetime, timedelta

daybook = sqlite3.connect('/app/BabyDaybook_20260403_auto.db')
daybook.row_factory = sqlite3.Row
dc = daybook.cursor()

babyapp = sqlite3.connect('/app/app_dev.db')
bc = babyapp.cursor()

KIND_ID = 3
ERSTELLT_VON = 3
NOW = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def ms_to_dtstr(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d %H:%M:%S')

def ms_to_datestr(ms):
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000).date().isoformat()

def side_map(s):
    if s == 'left':
        return 'links'
    if s == 'right':
        return 'rechts'
    return None

# Type-Lookup aufbauen
dc.execute('SELECT uid, icon, title, category FROM da_types')
type_map = {}
for r in dc.fetchall():
    type_map[r['uid']] = {'icon': r['icon'], 'title': r['title'], 'category': r['category']}

counts = {}

# Zuerst den Test-Eintrag entfernen
bc.execute("DELETE FROM fuetterungen WHERE kind_id=? AND created_at=?", (KIND_ID, NOW))

# =====================================================
# 1. STILLEN (breastfeeding)
# =====================================================
dc.execute("SELECT * FROM daily_actions WHERE type='breastfeeding' ORDER BY start_millis")
rows = dc.fetchall()
for r in rows:
    beginn = ms_to_dtstr(r['start_millis'])
    dauer_ms = r['duration'] or 0
    dauer_min = round(dauer_ms / 60000) if dauer_ms > 0 else None
    ende = ms_to_dtstr(r['end_millis']) if r['end_millis'] and r['end_millis'] > 0 else None
    seite = side_map(r['side'])
    notiz = r['notes'] if r['notes'] else None

    bc.execute(
        "INSERT INTO fuetterungen (kind_id, typ, beginn, ende, dauer_minuten, seite, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (KIND_ID, 'stillen', beginn, ende, dauer_min, seite, notiz, ERSTELLT_VON, NOW)
    )
counts['stillen'] = len(rows)
print(f"Stillen: {len(rows)} importiert")

# =====================================================
# 2. ABPUMPEN (pump)
# =====================================================
dc.execute("SELECT * FROM daily_actions WHERE type='pump' ORDER BY start_millis")
rows = dc.fetchall()
for r in rows:
    beginn = ms_to_dtstr(r['start_millis'])
    menge = r['volume'] if r['volume'] and r['volume'] > 0 else None
    seite = side_map(r['side'])
    notiz = r['notes'] if r['notes'] else None

    bc.execute(
        "INSERT INTO fuetterungen (kind_id, typ, beginn, menge_ml, seite, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (KIND_ID, 'abpumpen', beginn, menge, seite, notiz, ERSTELLT_VON, NOW)
    )
counts['abpumpen'] = len(rows)
print(f"Abpumpen: {len(rows)} importiert")

# =====================================================
# 3. WINDELN (diaper_change)
# =====================================================
dc.execute("SELECT * FROM daily_actions WHERE type='diaper_change' ORDER BY start_millis")
rows = dc.fetchall()
for r in rows:
    zeitpunkt = ms_to_dtstr(r['start_millis'])
    pee = r['pee'] or 0
    poo = r['poo'] or 0
    if pee and poo:
        typ = 'beides'
    elif poo:
        typ = 'stuhl'
    elif pee:
        typ = 'nass'
    else:
        typ = 'trocken'
    notiz = r['notes'] if r['notes'] else None

    bc.execute(
        "INSERT INTO windeln (kind_id, zeitpunkt, typ, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?)",
        (KIND_ID, zeitpunkt, typ, notiz, ERSTELLT_VON, NOW)
    )
counts['windeln'] = len(rows)
print(f"Windeln: {len(rows)} importiert")

# =====================================================
# 4. SCHLAF (sleeping)
# =====================================================
dc.execute("SELECT * FROM daily_actions WHERE type='sleeping' ORDER BY start_millis")
rows = dc.fetchall()
for r in rows:
    beginn = ms_to_dtstr(r['start_millis'])
    dauer_ms = r['duration'] or 0
    dauer_min = round(dauer_ms / 60000) if dauer_ms > 0 else None
    ende = ms_to_dtstr(r['end_millis']) if r['end_millis'] and r['end_millis'] > 0 else None
    notiz = r['notes'] if r['notes'] else None

    # Wenn kein Ende aber Dauer, berechne Ende
    if not ende and dauer_min and r['start_millis']:
        end_dt = datetime.fromtimestamp(r['start_millis'] / 1000) + timedelta(minutes=dauer_min)
        ende = end_dt.strftime('%Y-%m-%d %H:%M:%S')

    # Unrealistisch lange Einträge (>24h) markieren
    if dauer_min and dauer_min > 1440:
        notiz = (notiz + ' ' if notiz else '') + '[Import: Timer nicht gestoppt]'
        dauer_min = None
        ende = None

    bc.execute(
        "INSERT INTO schlafeintraege (kind_id, beginn, ende, dauer_minuten, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?,?)",
        (KIND_ID, beginn, ende, dauer_min, notiz, ERSTELLT_VON, NOW)
    )
counts['schlaf'] = len(rows)
print(f"Schlaf: {len(rows)} importiert")

# =====================================================
# 5. WACHSTUM (growth)
# =====================================================
dc.execute("SELECT * FROM growth ORDER BY date_millis")
rows = dc.fetchall()
inserted = 0
for r in rows:
    datum = ms_to_datestr(r['date_millis'])
    gewicht = r['weight'] if r['weight'] and r['weight'] > 0 else None
    groesse = r['height'] if r['height'] and r['height'] > 0 else None
    kopf = r['head_size'] if r['head_size'] and r['head_size'] > 0 else None
    notiz = r['notes'] if r['notes'] else None

    if not gewicht and not groesse and not kopf:
        continue

    # Duplikat-Check
    bc.execute("SELECT id FROM wachstumsdaten WHERE kind_id=? AND datum=?", (KIND_ID, datum))
    if bc.fetchone():
        continue

    bc.execute(
        "INSERT INTO wachstumsdaten (kind_id, datum, gewicht_kg, groesse_cm, kopfumfang_cm, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (KIND_ID, datum, gewicht, groesse, kopf, notiz, ERSTELLT_VON, NOW)
    )
    inserted += 1
counts['wachstum'] = inserted
print(f"Wachstum: {inserted} importiert")

# =====================================================
# 6. ZAHNUNG (teething)
# =====================================================
TOOTH_MAP = {
    ('central_incisor', 'upper', 'right'): (1, 'Oberer rechter mittlerer Schneidezahn', 'oben-rechts'),
    ('central_incisor', 'upper', 'left'): (6, 'Oberer linker mittlerer Schneidezahn', 'oben-links'),
    ('central_incisor', 'lower', 'left'): (11, 'Unterer linker mittlerer Schneidezahn', 'unten-links'),
    ('central_incisor', 'lower', 'right'): (16, 'Unterer rechter mittlerer Schneidezahn', 'unten-rechts'),
    ('lateral_incisor', 'upper', 'right'): (2, 'Oberer rechter seitlicher Schneidezahn', 'oben-rechts'),
    ('lateral_incisor', 'upper', 'left'): (7, 'Oberer linker seitlicher Schneidezahn', 'oben-links'),
    ('lateral_incisor', 'lower', 'left'): (12, 'Unterer linker seitlicher Schneidezahn', 'unten-links'),
    ('lateral_incisor', 'lower', 'right'): (17, 'Unterer rechter seitlicher Schneidezahn', 'unten-rechts'),
    ('canine', 'upper', 'right'): (3, 'Oberer rechter Eckzahn', 'oben-rechts'),
    ('canine', 'upper', 'left'): (8, 'Oberer linker Eckzahn', 'oben-links'),
    ('canine', 'lower', 'left'): (13, 'Unterer linker Eckzahn', 'unten-links'),
    ('canine', 'lower', 'right'): (18, 'Unterer rechter Eckzahn', 'unten-rechts'),
    ('first_molar', 'upper', 'right'): (4, 'Oberer rechter erster Backenzahn', 'oben-rechts'),
    ('first_molar', 'upper', 'left'): (9, 'Oberer linker erster Backenzahn', 'oben-links'),
    ('first_molar', 'lower', 'left'): (14, 'Unterer linker erster Backenzahn', 'unten-links'),
    ('first_molar', 'lower', 'right'): (19, 'Unterer rechter erster Backenzahn', 'unten-rechts'),
}

dc.execute("SELECT * FROM teething WHERE erupted=1 ORDER BY erupted_millis")
rows = dc.fetchall()
inserted = 0
for r in rows:
    key = (r['name'], r['jaw'], r['side'])
    if key not in TOOTH_MAP:
        print(f"  WARNUNG: Zahn nicht gemappt: {key}")
        continue
    zahn_nr, zahn_name, position = TOOTH_MAP[key]
    datum = ms_to_datestr(r['erupted_millis'])
    notiz = r['notes'] if r['notes'] else None

    bc.execute("SELECT id FROM zahneintraege WHERE kind_id=? AND zahn_nr=?", (KIND_ID, zahn_nr))
    if bc.fetchone():
        continue

    bc.execute(
        "INSERT INTO zahneintraege (kind_id, zahn_nr, name, position, durchbruch_datum, notiz, created_at) VALUES (?,?,?,?,?,?,?)",
        (KIND_ID, zahn_nr, zahn_name, position, datum, notiz, NOW)
    )
    inserted += 1
counts['zahnung'] = inserted
print(f"Zahnung: {inserted} importiert")

# =====================================================
# 7. TAGEBUCH (moments + daily_notes)
# =====================================================
dc.execute("SELECT * FROM moments ORDER BY date_millis")
rows = dc.fetchall()
inserted = 0
for r in rows:
    datum = ms_to_datestr(r['date_millis'])
    text = r['description'] if r['description'] else None
    if not text or not text.strip():
        continue

    bc.execute(
        "INSERT INTO tagebucheintraege (kind_id, datum, titel, text, erstellt_von, created_at) VALUES (?,?,?,?,?,?)",
        (KIND_ID, datum, 'Daybook-Eintrag', text, ERSTELLT_VON, NOW)
    )
    inserted += 1
counts['tagebuch_moments'] = inserted
print(f"Tagebuch (Moments): {inserted} importiert")

dc.execute("SELECT * FROM daily_notes ORDER BY updated_millis")
rows = dc.fetchall()
inserted = 0
for r in rows:
    datum = ms_to_datestr(r['updated_millis'])
    text = r['note'] if r['note'] else None
    if not text or not text.strip():
        continue

    bc.execute(
        "INSERT INTO tagebucheintraege (kind_id, datum, titel, text, erstellt_von, created_at) VALUES (?,?,?,?,?,?)",
        (KIND_ID, datum, 'Tagesnotiz', text, ERSTELLT_VON, NOW)
    )
    inserted += 1
counts['tagebuch_notes'] = inserted
print(f"Tagebuch (Notizen): {inserted} importiert")

# =====================================================
# 8. GESUNDHEIT
# =====================================================

# Temperature
dc.execute("SELECT * FROM daily_actions WHERE type='temperature' ORDER BY start_millis")
rows = dc.fetchall()
for r in rows:
    datum = ms_to_dtstr(r['start_millis'])
    temp = r['temperature'] if r['temperature'] and r['temperature'] > 0 else None
    notiz = r['notes'] if r['notes'] else None
    bc.execute(
        "INSERT INTO gesundheitseintraege (kind_id, datum, typ, temperatur, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?,?)",
        (KIND_ID, datum, 'temperatur', temp, notiz, ERSTELLT_VON, NOW)
    )
counts['temperatur'] = len(rows)
print(f"Temperatur: {len(rows)} importiert")

# Symptom
dc.execute("SELECT * FROM daily_actions WHERE type='symptom' ORDER BY start_millis")
rows = dc.fetchall()
for r in rows:
    datum = ms_to_dtstr(r['start_millis'])
    notiz = r['notes'] if r['notes'] else None
    bc.execute(
        "INSERT INTO gesundheitseintraege (kind_id, datum, typ, symptome, erstellt_von, created_at) VALUES (?,?,?,?,?,?)",
        (KIND_ID, datum, 'symptom', notiz, ERSTELLT_VON, NOW)
    )
counts['symptom'] = len(rows)
print(f"Symptome: {len(rows)} importiert")

# Fieber (custom type)
fieber_uids = [uid for uid, info in type_map.items() if info['title'] == 'Fieber']
for uid in fieber_uids:
    dc.execute("SELECT * FROM daily_actions WHERE type=? ORDER BY start_millis", (uid,))
    rows = dc.fetchall()
    for r in rows:
        datum = ms_to_dtstr(r['start_millis'])
        notiz = r['notes'] if r['notes'] else None
        temp = None
        if notiz:
            try:
                temp = float(notiz.replace('Ca. ', '').replace(',', '.').strip())
            except:
                pass
        bc.execute(
            "INSERT INTO gesundheitseintraege (kind_id, datum, typ, temperatur, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?,?)",
            (KIND_ID, datum, 'temperatur', temp, notiz, ERSTELLT_VON, NOW)
        )
    counts['fieber'] = len(rows)
    print(f"Fieber: {len(rows)} importiert")

# Erbrechen (custom type)
erbrechen_uids = [uid for uid, info in type_map.items() if 'Erbrechen' in (info['title'] or '')]
for uid in erbrechen_uids:
    dc.execute("SELECT * FROM daily_actions WHERE type=? ORDER BY start_millis", (uid,))
    rows = dc.fetchall()
    for r in rows:
        datum = ms_to_dtstr(r['start_millis'])
        notiz = r['notes'] if r['notes'] else None
        bc.execute(
            "INSERT INTO gesundheitseintraege (kind_id, datum, typ, symptome, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?,?)",
            (KIND_ID, datum, 'symptom', 'Erbrechen/Aufstoßen', notiz, ERSTELLT_VON, NOW)
        )
    counts['erbrechen'] = len(rows)
    print(f"Erbrechen: {len(rows)} importiert")

# Gelb-grüner Schleim (custom type)
schleim_uids = [uid for uid, info in type_map.items() if 'Gelb' in (info['title'] or '')]
for uid in schleim_uids:
    dc.execute("SELECT * FROM daily_actions WHERE type=? ORDER BY start_millis", (uid,))
    rows = dc.fetchall()
    for r in rows:
        datum = ms_to_dtstr(r['start_millis'])
        notiz = r['notes'] if r['notes'] else None
        bc.execute(
            "INSERT INTO gesundheitseintraege (kind_id, datum, typ, symptome, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?,?)",
            (KIND_ID, datum, 'symptom', 'Gelb-grüner Schleim', notiz, ERSTELLT_VON, NOW)
        )
    counts['schleim'] = len(rows)
    print(f"Schleim: {len(rows)} importiert")

# =====================================================
# 9. AKTIVITÄTEN (tummy_time=1, bath=4)
# =====================================================
dc.execute("SELECT * FROM daily_actions WHERE type='tummy_time' ORDER BY start_millis")
rows = dc.fetchall()
for r in rows:
    beginn = ms_to_dtstr(r['start_millis'])
    dauer_ms = r['duration'] or 0
    dauer_min = round(dauer_ms / 60000) if dauer_ms > 0 else None
    ende = ms_to_dtstr(r['end_millis']) if r['end_millis'] and r['end_millis'] > 0 else None
    notiz = r['notes'] if r['notes'] else None
    bc.execute(
        "INSERT INTO aktivitaeten (kind_id, typ_id, beginn, ende, dauer_minuten, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (KIND_ID, 1, beginn, ende, dauer_min, notiz, ERSTELLT_VON, NOW)
    )
counts['bauchlage'] = len(rows)
print(f"Bauchlage: {len(rows)} importiert")

dc.execute("SELECT * FROM daily_actions WHERE type='bath' ORDER BY start_millis")
rows = dc.fetchall()
for r in rows:
    beginn = ms_to_dtstr(r['start_millis'])
    notiz = r['notes'] if r['notes'] else None
    reaction = r['reaction'] if r['reaction'] else ''
    if reaction:
        notiz = (notiz + ' | ' if notiz else '') + 'Reaktion: ' + reaction
    bc.execute(
        "INSERT INTO aktivitaeten (kind_id, typ_id, beginn, notiz, erstellt_von, created_at) VALUES (?,?,?,?,?,?)",
        (KIND_ID, 4, beginn, notiz, ERSTELLT_VON, NOW)
    )
counts['baden'] = len(rows)
print(f"Baden: {len(rows)} importiert")

# =====================================================
# COMMIT
# =====================================================
babyapp.commit()

print()
print("=== IMPORT ABGESCHLOSSEN ===")
total = sum(counts.values())
print(f"Gesamt: {total} Einträge importiert")
print()

# Verifizierung
print("=== VERIFIZIERUNG ===")
for table in ['fuetterungen', 'schlafeintraege', 'windeln', 'wachstumsdaten', 'zahneintraege', 'tagebucheintraege', 'gesundheitseintraege', 'aktivitaeten']:
    bc.execute(f'SELECT COUNT(*) FROM {table} WHERE kind_id=?', (KIND_ID,))
    cnt = bc.fetchone()[0]
    print(f"  {table}: {cnt}")

daybook.close()
babyapp.close()
