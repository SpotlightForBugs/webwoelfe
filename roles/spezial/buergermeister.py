"""
Buergermeister - Hat doppeltes Stimmrecht.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Buergermeister(Role):
    """
    Der Buergermeister - Doppelte Stimme.
    
    Faehigkeiten:
    - Seine Stimme zaehlt doppelt bei Abstimmungen
    - Kann Buergermeister-Amt weitergeben bei Tod
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=90,
            name="Buergermeister",
            team=Team.DORF,
            kategorie=Kategorie.SPEZIAL,
            beschreibung=(
                "Du bist der Buergermeister. Deine Stimme zaehlt doppelt "
                "bei allen Abstimmungen. Bei deinem Tod kannst du das Amt "
                "an einen anderen Spieler weitergeben."
            ),
            icon="fa-solid fa-landmark",
            farbe="#6366f1",
            prioritaet=95,
            erzaehler_tag=(
                "Der Buergermeister hat doppeltes Stimmrecht."
            ),
        )
    
    def is_active_on_first_night(self) -> bool:
        """Bürgermeister is passive."""
        return False
    
    def is_active_on_every_night(self) -> bool:
        """Bürgermeister is passive."""
        return False
    
    def get_ui_definition(self) -> 'RollenUI':
        """Returns the UI definition for Bürgermeister's action panel."""
        from ..base import RollenUI
        return RollenUI(
            title="Bürgermeister - Passive Rolle",
            instructions="Deine Stimme zählt doppelt. Bei Tod wählst du einen Nachfolger.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True
        )
    
    def on_abstimmung(self, spieler: 'Spieler', ziel: 'Spieler',
                      kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Stimme zaehlt doppelt.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Deine Stimme zaehlt doppelt!",
            effekte={
                "stimmen_multiplikator": 2,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def on_eigener_tod(self, spieler: 'Spieler', todesursache: str,
                       kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Buergermeister kann Amt weitergeben.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Der Buergermeister stirbt. Er kann sein Amt weitergeben.",
            effekte={
                "amt_weitergeben": True,
                "warte_auf_nachfolger": True,
            },
            log_sichtbar_fuer="alle",
        )
