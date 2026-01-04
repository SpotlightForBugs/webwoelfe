from datetime import datetime, timedelta
from models import (
    db,
    Raum,
    Spieler,
    SpielAktion,
    SpielLog,
    ErzaehlerEvent,
    SeherinEnthuellung,
    SpielerPosition,
)


def cleanup_old_games(app, max_age_hours=24):
    """
    Löscht alte Spiele und zugehörige Daten aus der Datenbank.
    """
    with app.app_context():
        # Executes transactional cleanup of old game data
        try:
            cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

            # Finde alte Räume
            old_rooms = Raum.query.filter(Raum.erstellt_am < cutoff).all()
            count = len(old_rooms)

            if count == 0:
                return

            print(
                f"[Cleanup] Lösche {count} alte Räume (älter als {max_age_hours}h)..."
            )

            for room in old_rooms:
                room_id = room.id

                # 1. Lösche abhängige Tabellen
                SpielAktion.query.filter_by(raum_id=room_id).delete()
                SpielLog.query.filter_by(raum_id=room_id).delete()
                ErzaehlerEvent.query.filter_by(raum_id=room_id).delete()
                SeherinEnthuellung.query.filter_by(raum_id=room_id).delete()

                # 2. Lösche Spieler und deren Abhängigkeiten
                players = Spieler.query.filter_by(raum_id=room_id).all()
                for player in players:
                    # Lösche Spieler-Positionen
                    SpielerPosition.query.filter_by(spieler_id=player.id).delete()

                    # Setze Selbst-Referenzen auf None um FK-Fehler zu vermeiden
                    player.verliebt_mit_id = None
                    player.vorbild_id = None
                    player.doppelgaenger_ziel_id = None
                    player.henker_ziel_id = None
                    player.herrchen_id = None

                # Commit um FK-Constraints zu lösen
                db.session.commit()

                # Jetzt Spieler löschen
                for player in players:
                    db.session.delete(player)

                # 3. Raum löschen
                db.session.delete(room)

            db.session.commit()
            print(f"[Cleanup] Erfolgreich {count} Räume bereinigt.")

        except Exception as e:
            db.session.rollback()
            print(f"[Cleanup] Fehler bei der Bereinigung: {e}")
