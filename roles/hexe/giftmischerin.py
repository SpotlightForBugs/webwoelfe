"""
Giftmischerin - Verzögerte Tötung.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Giftmischerin(Role):
    """
    Die Giftmischerin - Verzögerte Tötung.
    
    Fähigkeiten:
    - Kann einmal einen Spieler vergiften
    - Vergifteter stirbt nach 2 Tagen
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=161,
            name="Giftmischerin",
            team=Team.DORF,
            kategorie=Kategorie.HEXE,
            beschreibung=(
                "Du bist die Giftmischerin. Du kannst einmal pro Spiel "
                "einen Spieler vergiften. Dieser stirbt nach 2 Tagen "
                "an dem langsam wirkenden Gift."
            ),
            icon="fa-solid fa-flask-vial",
            farbe="#84cc16",
            nacht_aktiv=True,
            prioritaet=66,
            erzaehler_nacht=(
                "Die Giftmischerin erwacht. Möchte sie ihr Gift einsetzen?"
            ),
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.VERGIFTEN
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Giftmischerin vergiftet mit verzögerter Wirkung.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hebst dein Gift auf.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du hast {ziel.name} vergiftet. In 2 Tagen wird er sterben.",
            ziel_spieler_id=ziel.id,
            effekte={
                "vergiftet": ziel.id,
                "gift_countdown": 2,
                "gift_tod_runde": kontext.runde + 2,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
