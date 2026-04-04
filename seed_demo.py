"""Seed-Script: Füllt alle Module mit Beispieldaten."""
import sys
sys.path.insert(0, '/app')

from src.app import create_app
from src.extensions import db
from src.models import *
from src.models import KindFreigabe
from datetime import datetime, date, timedelta
import random

app = create_app()

with app.app_context():
    # Prüfe ob Kind existiert
    admin = User.query.filter_by(username='admin').first()

    kind = Kind.query.first()
    if not kind:
        kind = Kind(name='Emma', geburtsdatum=date(2026, 1, 15), geschlecht='w')
        db.session.add(kind)
        db.session.flush()
        # Admin als Owner zuweisen
        if admin and not KindFreigabe.query.filter_by(kind_id=kind.id, user_id=admin.id).first():
            db.session.add(KindFreigabe(kind_id=kind.id, user_id=admin.id, rolle='owner'))
        db.session.commit()
        print(f"Kind angelegt: {kind.name} (ID: {kind.id})")
    else:
        # Sicherstellen dass Admin als Owner zugewiesen ist
        if admin and not KindFreigabe.query.filter_by(kind_id=kind.id, user_id=admin.id).first():
            db.session.add(KindFreigabe(kind_id=kind.id, user_id=admin.id, rolle='owner'))
            db.session.commit()
        print(f"Kind vorhanden: {kind.name} (ID: {kind.id})")

    # --- Fütterungen (letzte 3 Tage) ---
    if Fuetterung.query.filter_by(kind_id=kind.id).count() == 0:
        for d in range(3):
            tag = date.today() - timedelta(days=d)
            for stunde in [6, 9, 12, 15, 18, 21]:
                typ = random.choice(['stillen', 'stillen', 'stillen', 'flasche'])
                beginn = datetime.combine(tag, datetime.min.time().replace(hour=stunde, minute=random.randint(0, 30)))
                dauer = random.randint(10, 25)
                ende = beginn + timedelta(minutes=dauer)
                f = Fuetterung(
                    kind_id=kind.id, typ=typ, beginn=beginn, ende=ende,
                    dauer_minuten=dauer,
                    seite=random.choice(['links', 'rechts', 'beide']) if typ == 'stillen' else None,
                    menge_ml=random.randint(80, 150) if typ == 'flasche' else None,
                    inhalt='muttermilch' if typ == 'flasche' else None,
                    erstellt_von=admin.id if admin else None,
                )
                db.session.add(f)
        db.session.commit()
        print(f"  Fütterungen: {Fuetterung.query.filter_by(kind_id=kind.id).count()} Einträge")

    # --- Schlaf (letzte 3 Tage) ---
    if Schlaf.query.filter_by(kind_id=kind.id).count() == 0:
        for d in range(3):
            tag = date.today() - timedelta(days=d)
            # Nickerchen
            for stunde in [10, 14]:
                beginn = datetime.combine(tag, datetime.min.time().replace(hour=stunde))
                dauer = random.randint(30, 90)
                db.session.add(Schlaf(
                    kind_id=kind.id, beginn=beginn, ende=beginn + timedelta(minutes=dauer),
                    dauer_minuten=dauer, typ='nickerchen',
                    qualitaet=random.randint(3, 5), ort=random.choice(['bett', 'kinderwagen', 'arm']),
                    erstellt_von=admin.id if admin else None,
                ))
            # Nachtschlaf
            beginn = datetime.combine(tag, datetime.min.time().replace(hour=20))
            dauer = random.randint(480, 600)
            db.session.add(Schlaf(
                kind_id=kind.id, beginn=beginn, ende=beginn + timedelta(minutes=dauer),
                dauer_minuten=dauer, typ='nachtschlaf', qualitaet=random.randint(3, 5), ort='bett',
                erstellt_von=admin.id if admin else None,
            ))
        db.session.commit()
        print(f"  Schlaf: {Schlaf.query.filter_by(kind_id=kind.id).count()} Einträge")

    # --- Windeln (letzte 3 Tage) ---
    if Windel.query.filter_by(kind_id=kind.id).count() == 0:
        for d in range(3):
            tag = date.today() - timedelta(days=d)
            for stunde in [7, 9, 11, 13, 15, 17, 19]:
                typ = random.choice(['nass', 'nass', 'stuhl', 'beides'])
                db.session.add(Windel(
                    kind_id=kind.id,
                    zeitpunkt=datetime.combine(tag, datetime.min.time().replace(hour=stunde, minute=random.randint(0, 45))),
                    typ=typ, farbe='gelb' if 'stuhl' in typ or typ == 'beides' else None,
                    erstellt_von=admin.id if admin else None,
                ))
        db.session.commit()
        print(f"  Windeln: {Windel.query.filter_by(kind_id=kind.id).count()} Einträge")

    # --- Wachstum ---
    if Wachstum.query.filter_by(kind_id=kind.id).count() == 0:
        messungen = [
            (date(2026, 1, 15), 3.2, 50.0, 34.5),
            (date(2026, 2, 1), 3.8, 52.0, 35.5),
            (date(2026, 2, 15), 4.3, 54.5, 36.5),
            (date(2026, 3, 1), 4.9, 56.0, 37.5),
            (date(2026, 3, 15), 5.3, 58.5, 38.5),
            (date(2026, 4, 1), 5.8, 61.0, 39.5),
        ]
        for datum, gew, gr, kopf in messungen:
            db.session.add(Wachstum(kind_id=kind.id, datum=datum, gewicht_kg=gew, groesse_cm=gr, kopfumfang_cm=kopf))
        db.session.commit()
        print(f"  Wachstum: {Wachstum.query.filter_by(kind_id=kind.id).count()} Messungen")

    # --- Gesundheit ---
    if Gesundheit.query.filter_by(kind_id=kind.id).count() == 0:
        db.session.add(Gesundheit(kind_id=kind.id, datum=datetime(2026, 3, 10, 8, 0), typ='temperatur', temperatur=37.8, symptome='Leichter Schnupfen'))
        db.session.add(Gesundheit(kind_id=kind.id, datum=datetime(2026, 3, 20, 14, 0), typ='symptom', symptome='Leichter Husten', beschreibung='Seit gestern, kein Fieber'))
        db.session.commit()
        print(f"  Gesundheit: {Gesundheit.query.filter_by(kind_id=kind.id).count()} Einträge")

    # --- Impfungen ---
    if Impfung.query.filter_by(kind_id=kind.id).count() == 0:
        db.session.add(Impfung(kind_id=kind.id, datum=date(2026, 3, 15), name='6-fach Impfung (1. Dosis)', arzt='Dr. Huber', naechster_termin=date(2026, 5, 15)))
        db.session.add(Impfung(kind_id=kind.id, datum=date(2026, 3, 15), name='Pneumokokken (1. Dosis)', arzt='Dr. Huber', naechster_termin=date(2026, 5, 15)))
        db.session.add(Impfung(kind_id=kind.id, datum=date(2026, 3, 15), name='Rotaviren (1. Dosis)', arzt='Dr. Huber'))
        db.session.commit()
        print(f"  Impfungen: {Impfung.query.filter_by(kind_id=kind.id).count()} Einträge")

    # --- Medikamente ---
    if Medikament.query.filter_by(kind_id=kind.id).count() == 0:
        db.session.add(Medikament(kind_id=kind.id, name='Vitamin D', dosis='1', einheit='tropfen', frequenz='1x täglich', beginn=date(2026, 1, 15), grund='Rachitisprophylaxe'))
        db.session.add(Medikament(kind_id=kind.id, name='Vitamin K', dosis='2', einheit='mg', frequenz='bei U-Untersuchung', beginn=date(2026, 1, 15), ende=date(2026, 2, 15)))
        db.session.commit()
        print(f"  Medikamente: {Medikament.query.filter_by(kind_id=kind.id).count()} Einträge")

    # --- Arztbesuche ---
    if Arztbesuch.query.filter_by(kind_id=kind.id).count() == 0:
        db.session.add(Arztbesuch(kind_id=kind.id, datum=datetime(2026, 1, 20, 9, 0), arzt='Dr. Huber', grund='U2 Vorsorge', diagnose='Alles in Ordnung', naechster_termin=date(2026, 2, 15)))
        db.session.add(Arztbesuch(kind_id=kind.id, datum=datetime(2026, 2, 15, 10, 0), arzt='Dr. Huber', grund='U3 Vorsorge', diagnose='Entwicklung altersgerecht', naechster_termin=date(2026, 4, 15)))
        db.session.commit()
        print(f"  Arztbesuche: {Arztbesuch.query.filter_by(kind_id=kind.id).count()} Einträge")

    # --- Zahnung ---
    if Zahn.query.filter_by(kind_id=kind.id).count() == 0:
        zaehne = [
            (11, 'Unterer linker mittlerer Schneidezahn', 'unten-links', date(2026, 3, 10)),
            (16, 'Unterer rechter mittlerer Schneidezahn', 'unten-rechts', date(2026, 3, 15)),
            (1,  'Oberer rechter mittlerer Schneidezahn', 'oben-rechts', date(2026, 3, 25)),
            (6,  'Oberer linker mittlerer Schneidezahn', 'oben-links', date(2026, 3, 28)),
        ]
        for nr, name, pos, datum in zaehne:
            db.session.add(Zahn(kind_id=kind.id, zahn_nr=nr, name=name, position=pos, durchbruch_datum=datum))
        db.session.commit()
        print(f"  Zahnung: {Zahn.query.filter_by(kind_id=kind.id).count()} Zähne")

    # --- Meilensteine ---
    if Meilenstein.query.filter_by(kind_id=kind.id).count() == 0:
        from src.blueprints.meilensteine import STANDARD_MEILENSTEINE
        for m in STANDARD_MEILENSTEINE:
            erreicht = m['alter_monate'] <= 2  # Alles bis 2 Monate als erreicht
            db.session.add(Meilenstein(
                kind_id=kind.id, kategorie=m['kategorie'], titel=m['titel'],
                alter_monate=m['alter_monate'], erreicht=erreicht,
                datum=date(2026, 2, 1) if erreicht else None,
            ))
        db.session.commit()
        print(f"  Meilensteine: {Meilenstein.query.filter_by(kind_id=kind.id).count()} Einträge ({Meilenstein.query.filter_by(kind_id=kind.id, erreicht=True).count()} erreicht)")

    # --- Aktivitäten ---
    if Aktivitaet.query.filter_by(kind_id=kind.id).count() == 0:
        typen = AktivitaetTyp.query.all()
        for d in range(3):
            tag = date.today() - timedelta(days=d)
            for t in random.sample(typen, min(3, len(typen))):
                beginn = datetime.combine(tag, datetime.min.time().replace(hour=random.randint(8, 17), minute=random.randint(0, 45)))
                dauer = random.randint(5, 30)
                db.session.add(Aktivitaet(
                    kind_id=kind.id, typ_id=t.id, beginn=beginn,
                    ende=beginn + timedelta(minutes=dauer), dauer_minuten=dauer,
                    erstellt_von=admin.id if admin else None,
                ))
        db.session.commit()
        print(f"  Aktivitäten: {Aktivitaet.query.filter_by(kind_id=kind.id).count()} Einträge")

    # --- Beikost ---
    if Beikost.query.filter_by(kind_id=kind.id).count() == 0:
        beikost_daten = [
            ('Karotte', 'gemuese', 4, False, date(2026, 3, 20), True),
            ('Pastinake', 'gemuese', 3, False, date(2026, 3, 24), True),
            ('Kürbis', 'gemuese', 5, False, date(2026, 3, 28), True),
            ('Banane', 'obst', 5, False, date(2026, 4, 1), None),
            ('Avocado', 'obst', 2, False, date(2026, 4, 2), None),
            ('Erdbeere', 'obst', 4, True, date(2026, 4, 3), False),
        ]
        for lm, kat, akz, allergie, datum, vier_ok in beikost_daten:
            db.session.add(Beikost(
                kind_id=kind.id, lebensmittel=lm, kategorie=kat,
                akzeptanz=akz, allergie_verdacht=allergie, datum=datum,
                vier_tage_test_start=datum, vier_tage_test_ok=vier_ok,
                reaktion='Leichter Ausschlag am Mund' if allergie else None,
            ))
        db.session.commit()
        print(f"  Beikost: {Beikost.query.filter_by(kind_id=kind.id).count()} Lebensmittel")

    # --- Tagebuch ---
    if Tagebuch.query.filter_by(kind_id=kind.id).count() == 0:
        eintraege = [
            (date(2026, 3, 20), 'Erster Brei!', 'Emma hat heute zum ersten Mal Karottenbrei probiert. Sie hat zuerst ganz überrascht geschaut und dann den Mund aufgemacht. Die Hälfte ist auf dem Lätzchen gelandet, aber sie hat es geliebt!', 5),
            (date(2026, 3, 25), 'Erster Zahn!', 'Heute Morgen beim Stillen hat es plötzlich gepiekt -- der erste Zahn ist da! Unterer linker Schneidezahn. Emma war die letzten Tage etwas quengelig, jetzt wissen wir warum.', 4),
            (date(2026, 4, 1), 'Umdrehen geschafft', 'Emma hat sich heute zum ersten Mal alleine vom Bauch auf den Rücken gedreht! Sie war selbst so überrascht, dass sie danach ganz still lag und uns angeschaut hat.', 5),
            (date(2026, 4, 3), 'Spielplatz', 'Zum ersten Mal auf der Schaukel gesessen (natürlich die Babyschaukel). Hat die ganze Zeit gelacht und wollte gar nicht mehr runter.', 4),
        ]
        for datum, titel, text, stimmung in eintraege:
            db.session.add(Tagebuch(kind_id=kind.id, datum=datum, titel=titel, text=text, stimmung=stimmung, erstellt_von=admin.id if admin else None))
        db.session.commit()
        print(f"  Tagebuch: {Tagebuch.query.filter_by(kind_id=kind.id).count()} Einträge")

    # --- Routinen ---
    if Routine.query.filter_by(kind_id=kind.id).count() == 0:
        routinen = [
            ('Morgenroutine', 'Wickeln, Stillen, Bauchlage', '07:00'),
            ('Vormittags-Nickerchen', 'Schlafanzug, Verdunkeln, Spieluhr', '10:00'),
            ('Mittagsbrei', 'Beikost + Stillen', '12:00'),
            ('Nachmittags-Nickerchen', 'Schlafanzug, Verdunkeln', '14:00'),
            ('Spaziergang', 'Kinderwagen, frische Luft', '16:00'),
            ('Abendroutine', 'Baden, Massage, Schlafanzug, Stillen, Gute-Nacht-Lied', '19:00'),
        ]
        for name, beschr, uhrzeit in routinen:
            db.session.add(Routine(kind_id=kind.id, name=name, beschreibung=beschr, uhrzeit=uhrzeit, aktiv=True))
        db.session.commit()
        # Einige als erledigt markieren
        for r in Routine.query.filter_by(kind_id=kind.id).limit(3).all():
            db.session.add(RoutineCheck(routine_id=r.id, datum=date.today(), erledigt=True, erledigt_um=datetime.utcnow()))
        db.session.commit()
        print(f"  Routinen: {Routine.query.filter_by(kind_id=kind.id).count()} Einträge")

    # --- Notfallinfo ---
    if not Notfallinfo.query.filter_by(kind_id=kind.id).first():
        db.session.add(Notfallinfo(
            kind_id=kind.id,
            kinderarzt_name='Dr. Maria Huber',
            kinderarzt_telefon='0664 1234567',
            kinderarzt_adresse='Hauptstraße 12, 4020 Linz',
            krankenhaus='Kepler Universitätsklinikum',
            krankenhaus_telefon='0732 7806 0',
            versicherung='ÖGK Oberösterreich',
            versicherungsnummer='1234 150126',
            allergien='Verdacht auf Erdbeer-Allergie (wird beobachtet)',
            blutgruppe='A+',
            notfallkontakt_name='Oma Ingrid',
            notfallkontakt_telefon='0664 9876543',
            notfallkontakt_beziehung='Großmutter',
        ))
        db.session.commit()
        print("  Notfallinfo: angelegt")

    print("\nSeed komplett!")
