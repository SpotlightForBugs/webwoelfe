"""
Drei Brüder - Kennen sich gegenseitig.

Die drei Brüder erkennen sich in der ersten Nacht
und können sich jede Nacht kurz absprechen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class DreiBrueder(Role):
    """
    Drei Brüder - Gruppen-Informationsrolle.

    Fähigkeiten:
    - Erkennen sich in der ersten Nacht
    - Können sich jede Nacht kurz absprechen

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=13,
            name="Drei Brüder",
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist einer der drei Brüder. In der ersten Nacht "
                "erkennt ihr euch gegenseitig. Ihr dürft jede Nacht "
                "kurz die Augen oeffnen und euch absprechen."
            ),
            icon="fa-solid fa-people-group",
            farbe="#4f46e5",
            nacht_aktiv=True,
            prioritaet=8,
            erzaehler_nacht=(
                "Die drei Brüder erwachen und erkennen sich. "
                "Sie dürfen sich kurz absprechen."
            ),
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Brueder erkennen sich in der ersten Nacht.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du erkennst deine Brüder.",
            effekte={"erkennt_brueder": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Brüder dürfen sich kurz absprechen.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Die Brüder haben sich kurz abgesprochen.",
            effekte={"brueder_absprache": True},
            log_sichtbar_fuer="erzaehler",
        )
