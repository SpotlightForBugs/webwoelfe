"""
Prinz - Immun gegen Hinrichtung.
"""

from typing import Optional, TYPE_CHECKING
from ..base import (
    RollenModell,
    AppearanceFeature,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Prinz(Role):
    """
    Der Prinz - Immunität gegen Hinrichtung.

    Fähigkeiten:
    - Kann nicht vom Dorf gehängt werden (einmalig)
    - Bei Versuch wird Rolle enthüllt

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=70,
            name="Prinz",
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der Prinz. Wenn das Dorf versucht dich zu "
                "hängen, wird deine Rolle enthüllt und du überlebst. "
                "Dies funktioniert nur einmal!"
            ),
            icon="fa-solid fa-crown",
            farbe="#eab308",
            prioritaet=98,
            erzaehler_tag=(
                "Der Prinz kann nicht gehängt werden! Seine Identität " "wird enthüllt."
            ),
            erweiterung=Erweiterung.COMMUNITY,
            # Visual Styling
            avatar_gradient_from="#eab308",
            avatar_gradient_to="#a16207",
            avatar_border_color="#facc15",
            badge_emoji="🤴",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Prinz does not act at night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Prinz is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Prinz's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Prinz - Passive Rolle",
            instructions="Du bist immun gegen die erste Hinrichtung.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prinz überlebt die erste Hinrichtung.
        """
        if opfer.id == spieler.id:
            return AktionsErgebnis(
                erfolg=False,  # Hinrichtung schlaegt fehl
                nachricht=(
                    "Das Dorf versucht den Prinzen zu hängen, aber sein "
                    "königliches Blut schützt ihn! Er überlebt und seine "
                    "Identität ist nun bekannt."
                ),
                effekte={
                    "hinrichtung_verhindert": True,
                    "rolle_enthuellt": True,
                    "prinz_schutz_verbraucht": True,
                },
                log_sichtbar_fuer="alle",
            )

        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Prinz."""
        appearance_features = [
            AppearanceFeature(
                feature_type="sword",
                geometry="box",
                position={"x": 0.3, "y": 1.0, "z": -0.1},
                scale={"x": 0.05, "y": 0.6, "z": 0.05},
                rotation={"x": 45, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#C0C0C0",
                description="Royal sword",
            ),
            AppearanceFeature(
                feature_type="crown",
                geometry="cylinder",
                position={"x": 0, "y": 2.3, "z": 0},
                scale={"x": 0.25, "y": 0.15, "z": 0.25},
                color_source="custom",
                custom_color="#FFD700",
                description="Royal crown or halo",
            ),
        ]

        return RollenModell(
            modell_id="prinz",
            anzeige_name="Prinz",
            beschreibung="Prinz appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
