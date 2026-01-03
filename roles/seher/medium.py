"""
Medium - Kann mit Toten kommunizieren.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Medium(Role):
    """
    Das Medium - Kontakt zu den Toten.
    
    Fähigkeiten:
    - Kann jede Nacht die Rolle eines Toten erfahren
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=52,
            name="Medium",
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                "Du bist das Medium. Jede Nacht kannst du die Rolle "
                "eines verstorbenen Spielers erfahren."
            ),
            icon="fa-solid fa-ghost",
            farbe="#c084fc",
            nacht_aktiv=True,
            prioritaet=25,
            erzaehler_nacht=(
                "Das Medium erwacht und wählt einen Toten. "
                "Flüster dem Medium die Rolle des Toten zu."
            ),
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN
    
    @property
    def erlaubte_ziele(self) -> str:
        return "tote"
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Medium erfährt die Rolle eines Toten.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast diese Nacht keinen Toten befragt.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        if ziel.id not in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nur mit Toten sprechen.",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Der Geist von {ziel.name} flüstert: 'Ich war {ziel.rolle}'",
            ziel_spieler_id=ziel.id,
            effekte={
                "rolle_erfahren": ziel.rolle,
                "toter_befragt": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
