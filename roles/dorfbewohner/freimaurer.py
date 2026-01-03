"""
Freimaurer - Geheime Loge im Dorf.

Die Freimaurer erkennen sich gegenseitig und wissen,
dass sie auf der gleichen Seite stehen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Freimaurer(Role):
    """
    Freimaurer - Gruppen-Vertrauensrolle.

    Fähigkeiten:
    - Erkennen sich alle in der ersten Nacht
    - Wissen wem sie vertrauen können

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=15,
            name="Freimaurer",
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist ein Freimaurer. In der ersten Nacht erkennen "
                "sich alle Freimaurer gegenseitig. Ihr wisst, dass ihr "
                "auf der gleichen Seite steht."
            ),
            icon="fa-solid fa-building-columns",
            farbe="#3b82f6",
            nacht_aktiv=True,
            prioritaet=9,
            erzaehler_nacht=("Die Freimaurer erwachen und erkennen sich gegenseitig."),
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Freimaurer erkennen sich in der ersten Nacht.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du erkennst deine Logenbrüder.",
            effekte={"erkennt_freimaurer": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
