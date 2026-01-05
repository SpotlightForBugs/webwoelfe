"""
Zwei Schwestern - Kennen sich gegenseitig.

Die zwei Schwestern erkennen sich in der ersten Nacht
und können sich jede Nacht kurz absprechen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class ZweiSchwestern(Role):
    """
    Zwei Schwestern - Gruppen-Informationsrolle.

    Fähigkeiten:
    - Erkennen sich in der ersten Nacht
    - Können sich jede Nacht kurz absprechen

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=14,
            name="Zwei Schwestern",
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist eine der zwei Schwestern. In der ersten Nacht "
                "erkennt ihr euch gegenseitig. Ihr dürft jede Nacht "
                "kurz die Augen öffnen und euch absprechen."
            ),
            icon="fa-solid fa-user-group",
            farbe="#f472b6",
            prioritaet=8,
            erzaehler_nacht=(
                "Die zwei Schwestern erwachen und erkennen sich. "
                "Sie dürfen sich kurz absprechen."
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            # Visual Styling
            avatar_gradient_from="#f472b6",
            avatar_gradient_to="#db2777",
            avatar_border_color="#fbcfe8",
            badge_emoji="👭",
        )

    def is_active_on_first_night(self) -> bool:
        """Zwei Schwestern act on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Zwei Schwestern act every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Zwei Schwestern's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Zwei Schwestern - Absprache",
            instructions="Ihr erkennt euch und dürft kurz sprechen.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Schwestern erkennen sich in der ersten Nacht.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du erkennst deine Schwester.",
            effekte={"erkennt_schwester": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Schwestern dürfen sich kurz absprechen.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Die Schwestern haben sich kurz abgesprochen.",
            effekte={"schwestern_absprache": True},
            log_sichtbar_fuer="erzaehler",
        )
