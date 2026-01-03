"""
Heiler - Schützt Spieler vor nächtlichen Angriffen.

Der Heiler kann jede Nacht einen Spieler schützen,
aber nicht zweimal hintereinander denselben.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Heiler(Role):
    """
    Der Heiler - Schutz-Rolle.
    
    Fähigkeiten:
    - Kann jede Nacht einen Spieler schützen
    - Nicht zweimal hintereinander denselben Spieler
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=6,
            name="Heiler",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist der Heiler. Jede Nacht kannst du einen Spieler vor "
                "dem Werwolf-Angriff schützen. Du darfst nicht zweimal "
                "hintereinander denselben Spieler schützen!"
            ),
            icon="fa-solid fa-heart-pulse",
            farbe="#10b981",
            nacht_aktiv=True,
            prioritaet=55,
            erzaehler_nacht=(
                "Der Heiler erwacht und zeigt auf den Spieler, den er diese "
                "Nacht beschützen möchte. Nicht denselben wie letzte Nacht!"
            ),
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SCHUETZEN
    
    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Heiler schützt einen Spieler.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst jemanden zum Schützen wählen.",
            )
        
        # Prüfe ob es das gleiche Ziel wie letzte Nacht ist
        letztes_ziel = getattr(spieler, 'heiler_geschuetzt', None)
        
        if letztes_ziel == ziel.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht=(
                    "Du kannst nicht zweimal hintereinander denselben "
                    "Spieler schützen!"
                ),
            )
        
        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel.",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du beschützt {ziel.name} diese Nacht.",
            ziel_spieler_id=ziel.id,
            effekte={
                "geschuetzt": ziel.id,
                "heiler_ziel_merken": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
