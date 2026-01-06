"""
Polarwolf - Immun gegen Sandmann und Jäger.

Der Polarwolf ist ein Werwolf mit Immunität gegen
bestimmte Effekte durch seine Kälteresistenz.
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
from ..enums import Team, Kategorie, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Polarwolf(Role):
    """
    Polarwolf - Werwolf mit Immunitäten.

    Fähigkeiten:
    - Jagt mit den Wölfen
    - Immun gegen Sandmann (kann nicht eingeschläfert werden)
    - Immun gegen Jäger (Schuss verfehlt)

    Besonderheiten:
    - Passiver Schutz
    - Kann weiterhin von Hexe, Hinrichtung etc. getötet werden

    Gewinnbedingung: Werwölfe gewinnen.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=22,
            name="Polarwolf",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Polarwolf. Du bist immun gegen die Kälte - "
                "der Sandmann kann dich nicht einschläfern und der Jäger "
                "verfehlt dich immer!"
            ),
            icon="fa-solid fa-snowflake",
            farbe="#e0f2fe",
            prioritaet=50,
            erzaehler_nacht=("Der Polarwolf ist immun gegen Sandmann und Jäger."),
            erzaehler_tag=None,
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#e0f2fe",
            avatar_gradient_to="#0ea5e9",
            avatar_border_color="#38bdf8",
            badge_emoji="❄️",
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import AktionsTyp

        return AktionsTyp.KEINE  # Jagt mit dem Rudel

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    def is_active_on_first_night(self) -> bool:
        """Polarwolf acts with the pack."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Polarwolf acts with the pack."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Polarwolf's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Polarwolf - Passive Rolle",
            instructions="Du jagst mit den Wölfen. Du bist immun gegen Kälte (Sandmann/Jäger).",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_angegriffen(
        self, spieler: "Spieler", angreifer_id: int, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Polarwolf ist immun gegen Jäger.
        """
        # Wir müssen wissen wer der Angreifer ist
        # Das ist hier schwierig ohne direkten Zugriff auf die Rolle des Angreifers
        # Aber wir können prüfen ob es ein Jäger-Schuss war (über todesursache/aktionstyp)
        # Das muss in game_logic passieren, hier können wir nur Hinweise geben
        return None

    def ist_immun_gegen(self, effekt: str) -> bool:
        """
        Prüft Immunitäten.
        """
        if effekt in ["sandmann_schlaf", "jaeger_schuss"]:
            return True
        return False

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Polarwolf."""
        appearance_features = [
            AppearanceFeature(
                feature_type="wolf_ear_left",
                geometry="cone",
                position={"x": -0.18, "y": 2.25, "z": -0.05},
                scale={"x": 0.12, "y": 0.2, "z": 0.1},
                rotation={"x": 0, "y": 0, "z": -15},
                color_source="role",
                description="Left wolf ear",
            ),
            AppearanceFeature(
                feature_type="wolf_ear_right",
                geometry="cone",
                position={"x": 0.18, "y": 2.25, "z": -0.05},
                scale={"x": 0.12, "y": 0.2, "z": 0.1},
                rotation={"x": 0, "y": 0, "z": 15},
                color_source="role",
                description="Right wolf ear",
            ),
            AppearanceFeature(
                feature_type="mystical_aura",
                geometry="sphere",
                position={"x": 0, "y": 1.5, "z": 0},
                scale={"x": 0.6, "y": 0.8, "z": 0.5},
                color_source="role",
                description="Mystical aura effect",
            ),
        ]

        return RollenModell(
            modell_id="polarwolf",
            anzeige_name="Polarwolf",
            beschreibung="Polarwolf appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="bad",
        )
