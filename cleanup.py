from datetime import datetime, timedelta, timezone
from models import db, Raum, Spieler, SpielAktion, SpielLog, ErzaehlerEvent, SeherinEnthuellung
from logger import logger

def cleanup_old_games(app, max_age_hours=24):
    """
    Löscht alte Spiele aus der Datenbank.
    Handles all related entities to avoid orphaned records.
    """
    with app.app_context():
        try:
            limit = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            old_rooms = Raum.query.filter(Raum.erstellt_am < limit).all()

            count = 0
            for room in old_rooms:
                room_id = room.id

                # Delete related entities first (order matters due to foreign keys)
                # 1. Delete Seherin revelations
                SeherinEnthuellung.query.filter_by(raum_id=room_id).delete()

                # 2. Delete game actions
                SpielAktion.query.filter_by(raum_id=room_id).delete()

                # 3. Delete game logs
                SpielLog.query.filter_by(raum_id=room_id).delete()

                # 4. Delete narrator events
                ErzaehlerEvent.query.filter_by(raum_id=room_id).delete()

                # 5. Delete players
                Spieler.query.filter_by(raum_id=room_id).delete()

                # 6. Finally delete the room
                db.session.delete(room)
                count += 1

            if count > 0:
                db.session.commit()
                logger.info(f"[Cleanup] {count} alte Räume gelöscht.")
            else:
                logger.debug("[Cleanup] Keine alten Räume gefunden.")

        except Exception as e:
            logger.error(f"[Cleanup] Fehler beim Bereinigen: {e}")
            db.session.rollback()

