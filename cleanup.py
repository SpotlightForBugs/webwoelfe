from datetime import datetime, timedelta, timezone
from models import db, Raum
from logger import logger


def cleanup_old_games(app, max_age_hours=24):
    """
    Löscht alte Spiele aus der Datenbank.
    """
    with app.app_context():
        try:
            limit = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            old_rooms = Raum.query.filter(Raum.erstellt_am < limit).all()

            count = 0
            for room in old_rooms:
                # Delete players first
                for spieler in room.spieler:
                    db.session.delete(spieler)
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
