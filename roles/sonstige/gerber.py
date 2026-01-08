"""
Gerber - Alle verlieren wenn er gehängt wird.

Der Gerber gewinnt wenn er gehängt wird.
Anders als Selbstmörder: Alle anderen verlieren!
"""

from typing import Optional, TYPE_CHECKING
from ..base import (
    AppearanceFeature,
    Role,
    RollenInfo,
    RollenModell,
    AktionsErgebnis,
    SpielKontext,
    RollenModell,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Gerber(Role):
    """
    Gerber - Destruktiver Sieg.

    Fähigkeiten:
    - Passive Rolle
    - Gewinnt wenn gehängt
    - Alle anderen verlieren dann!

    Besonderheiten:
    - Sehr gefährlich fürs Dorf
    - Muss sich verdächtig machen
    - Unterschied zu Selbstmörder: Fluch auf alle

    Gewinnbedingung: Wird gehängt (alle anderen verlieren).
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=92,
            name="Gerber",
            team=Team.SOLO,
            kategorie=Kategorie.SONSTIGE,
            beschreibung=(
                "Du bist der Gerber. Du gewinnst wenn du gehängt wirst! "
                "Aber anders als der Selbstmörder - wenn du gewinnst, "
                "verlieren ALLE anderen!"
            ),
            icon="fa-solid fa-face-angry",
            farbe="#78350f",
            prioritaet=100,
            erzaehler_nacht=(
                "Der Gerber arbeitet an seinen stinkenden Fellen. "
                "Ein verbitterter Mann mit einem düsteren Plan."
            ),
            erzaehler_tag=(
                "ÜBERRASCHUNG! Der Gerber wurde gehängt und er lacht "
                "triumphierend! Sein Fluch verflucht das gesamte Dorf - "
                "ALLE verlieren außer ihm!"
            ),
            erweiterung=Erweiterung.COMMUNITY,
            hinweis_config="Gerber",
            # Visual Styling
            avatar_gradient_from="#78350f",
            avatar_gradient_to="#451a03",
            avatar_border_color="#92400e",
            badge_emoji="😡",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Gerber is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Gerber is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Gerber's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Gerber - Passive Rolle",
            instructions="Dein Ziel ist es, gehängt zu werden (und alle anderen mitzureißen).",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    @property
    def kann_hinweis_senden(self) -> bool:
        """Gerber kann Hinweise senden um sich verdächtig zu machen."""
        return True

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob der Gerber gehängt wird.
        """
        if opfer.id == spieler.id:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="FLUCH! Der Gerber wurde gehängt! "
                "Sein Fluch verflucht alle anderen - "
                "NUR der Gerber gewinnt, alle anderen verlieren!",
                effekte={
                    "gerber_gewonnen": True,
                    "spiel_ende": True,
                    "alle_verlieren": True,
                    "gewinner": "gerber",
                },
                log_sichtbar_fuer="alle",
            )

        return None

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Gerber gewinnt nur wenn gehängt.
        """
        if getattr(spieler, "gerber_gewonnen", False):
            return Team.SOLO
        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Gerber."""
        appearance_features = [
            AppearanceFeature(
                feature_type="accessory",
                geometry="box",
                position={"x": 0.25, "y": 1.0, "z": 0.15},
                scale={"x": 0.1, "y": 0.15, "z": 0.08},
                color_source="role",
                description="Role-specific accessory",
            )
        ]

        return RollenModell(
            modell_id="gerber",
            anzeige_name="Gerber",
            beschreibung="Gerber appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
