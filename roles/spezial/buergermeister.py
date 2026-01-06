"""
Buergermeister - Hat doppeltes Stimmrecht.
"""

from typing import Optional, TYPE_CHECKING
from ..base import AppearanceFeature, Role, RollenInfo, AktionsErgebnis, SpielKontext, RollenModell
from ..enums import Team, Kategorie, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Buergermeister(Role):
    """
    Der Bürgermeister - doppelte Stimme.

    Fähigkeiten:
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
            erzaehler_tag=("Der Buergermeister hat doppeltes Stimmrecht."),
            erweiterung=Erweiterung.CHARAKTERE,
            # Visual Styling
            avatar_gradient_from="#6366f1",
            avatar_gradient_to="#4f46e5",
            avatar_border_color="#818cf8",
            badge_emoji="👑",
        )

    def is_active_on_first_night(self) -> bool:
        """Bürgermeister is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Bürgermeister is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Bürgermeister's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Bürgermeister - Passive Rolle",
            instructions="Deine Stimme zählt doppelt. Bei Tod wählst du einen Nachfolger.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_abstimmung(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
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

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
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

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Buergermeister."""
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
            modell_id="buergermeister",
            anzeige_name="Buergermeister",
            beschreibung="Buergermeister appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
