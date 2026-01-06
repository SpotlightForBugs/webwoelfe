"""
Selbstmörder - Gewinnt nur wenn er vom Dorf gehängt wird
"""

from typing import Optional, TYPE_CHECKING
from ..base import RollenModell, Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Selbstmoerder(Role):
    """
    Selbstmörder

    Solo-Rolle die gewinnt, wenn sie vom Dorf hingerichtet wird.
    Muss das Dorf überzeugen, ihn zu hängen, ohne zu offensichtlich zu sein.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=74,
            name="Selbstmörder",
            team=Team.SOLO,
            kategorie=Kategorie.SPEZIAL,
            beschreibung="Du bist der Selbstmörder. Du gewinnst NUR wenn du vom Dorf gehängt wirst! Versuche verdächtig zu wirken, ohne zu offensichtlich zu sein.",
            icon="fa-solid fa-skull",
            farbe="#374151",
            prioritaet=100,
            erzaehler_nacht="Der Selbstmörder liegt wach und plant, wie er morgen möglichst verdächtig wirken kann.",
            erzaehler_tag="Der Selbstmörder erwacht mit einem finsteren Plan. Sein Ziel: Vom Dorf gehängt werden! Aber nicht zu offensichtlich...",
            hinweis_config="Selbstmörder",
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#374151",
            avatar_gradient_to="#111827",
            avatar_border_color="#4b5563",
            badge_emoji="💀",
        )

    def is_active_on_first_night(self) -> bool:
        """Selbstmörder is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Selbstmörder is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Selbstmörder's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Selbstmörder - Passive Rolle",
            instructions="Mache dich verdächtig und lass dich hängen!",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE  # Passive Rolle

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob der Selbstmörder hingerichtet wird - dann gewinnt er!
        """
        if opfer.id != spieler.id:
            return None

        # Der Selbstmörder wurde gehängt - er gewinnt!
        return AktionsErgebnis(
            erfolg=True,
            nachricht="🎭 DER SELBSTMÖRDER HAT GEWONNEN! Er wurde vom Dorf gehängt, genau wie er es wollte!",
            effekte={
                "selbstmoerder_gewinnt": True,
                "spiel_ende": True,
                "gewinner": "Selbstmörder",
                "gewinner_team": Team.SOLO.value,
            },
            log_sichtbar_fuer="alle",
        )

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft die Todesursache - nur Hinrichtung führt zum Sieg.
        """
        if todesursache == "hinrichtung":
            return AktionsErgebnis(
                erfolg=True,
                nachricht="🎭 Der Selbstmörder wurde gehängt und hat damit sein Ziel erreicht!",
                effekte={
                    "selbstmoerder_gewinnt": True,
                    "spiel_ende": True,
                    "gewinner": "Selbstmörder",
                },
                log_sichtbar_fuer="alle",
            )
        else:
            # Andere Todesart = Niederlage
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"💀 Der Selbstmörder wurde durch {todesursache} getötet - das war nicht sein Plan!",
                effekte={"selbstmoerder_verliert": True},
                log_sichtbar_fuer="alle",
            )

    def on_spiel_ende(
        self, spieler: "Spieler", gewinner_team: Team, kontext: SpielKontext
    ) -> bool:
        """
        Der Selbstmörder gewinnt nur, wenn er gehängt wurde.
        Er teilt nie den Sieg mit einem anderen Team.
        """
        # Prüfe ob er durch Hinrichtung gestorben ist
        wurde_gehaengt = getattr(spieler, "wurde_gehaengt", False)
        return wurde_gehaengt

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Selbstmoerder."""
        return RollenModell(
            modell_id="selbstmoerder",
            anzeige_name="Selbstmoerder",
            beschreibung="Selbstmoerder appearance in Village 3D",
        )
