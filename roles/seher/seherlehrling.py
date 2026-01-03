"""
Seherlehrling - Wird zur Seherin wenn die Original-Seherin stirbt.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Seherlehrling(Role):
    """
    Der Seherlehrling - Nachfolger der Seherin.
    
    Fähigkeiten:
    - Keine aktiven Fähigkeiten zu Beginn
    - Wenn Seherin stirbt: Übernimmt ihre Fähigkeit
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=50,
            name="Seherlehrling",
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                "Du bist der Seherlehrling. Du hast noch keine Fähigkeiten, "
                "aber wenn die Seherin stirbt, übernimmst du ihre Gabe "
                "und kannst selbst sehen."
            ),
            icon="fa-solid fa-eye-low-vision",
            farbe="#8b5cf6",
            nacht_aktiv=False,  # Wird aktiv wenn Seherin stirbt
            prioritaet=21,
            erzaehler_nacht=(
                "Der Seherlehrling schläft. Noch lernt er..."
            ),
        )
    
    def on_spieler_stirbt(self, spieler: 'Spieler', opfer: 'Spieler',
                          todesursache: str, kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Prüft ob die Seherin stirbt und der Lehrling übernimmt.
        """
        if opfer.rolle == "Seherin":
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Die Seherin ist tot! Der Seherlehrling übernimmt "
                    "ihre Gabe und wird zur neuen Seherin."
                ),
                effekte={
                    "wird_seherin": True,
                    "nacht_aktiv": True,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        return None
