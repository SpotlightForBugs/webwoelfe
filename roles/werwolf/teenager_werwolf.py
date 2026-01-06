"""
Teenager-Werwolf - Der rebellische Wolf.

Der Teenager-Werwolf ist ein normaler Werwolf, der sich
einmal pro Spiel weigern kann, beim Angriff mitzumachen.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    AppearanceFeature,
    AppearanceFeature,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
)
from ..enums import Team, Kategorie, SichtTyp, Erweiterung, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class TeenagerWerwolf(Role):
    """
    Der Teenager-Werwolf

    Fähigkeiten:
    - Jagt mit den Woelfen
    - Kann einmal pro Spiel den Angriff verweigern

    Gewinnbedingung: Werwoelfe gewinnen.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Teenager-Werwolfs."""
        return [
            StateField(
                "hat_verweigert", StateType.BOOL, False, "Hat bereits verweigert"
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=24,
            name="Teenager-Werwolf",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Teenager-Werwolf. Du bist ein rebellischer junger Wolf! "
                "Einmal pro Spiel kannst du dich weigern, beim nächtlichen Angriff "
                "mitzumachen. Das Opfer stirbt dann nicht!"
            ),
            icon="fa-solid fa-user-slash",
            farbe="#7f1d1d",
            prioritaet=50,
            erzaehler_nacht=(
                "Der Teenager-Werwolf jagt mit dem Rudel. Er kann einmal "
                "den Angriff verweigern."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#7f1d1d",
            avatar_gradient_to="#450a0a",
            avatar_border_color="#b91c1c",
            badge_emoji="🐺",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE  # Jagt mit dem Rudel, hat aber Sonderaktion

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    def is_active_on_first_night(self) -> bool:
        """Teenager-Werwolf acts with the pack."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Teenager-Werwolf acts with the pack."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Teenager-Werwolf's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Teenager-Werwolf - Rebellieren",
            instructions="Du kannst einmal pro Spiel den Angriff des Rudels stoppen.",
            buttons=[
                UIButton(
                    label="Angriff verweigern",
                    action_type="verweigern",
                    icon="fa-solid fa-hand",
                    css_class="btn-warning",
                    requires_confirmation=True,
                )
            ],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Teenager-Werwolf kann Angriff verweigern.
        """
        # Dies ist eine Zusatzaktion parallel zum Rudel-Angriff
        # Wir prüfen hier nur auf die Verweigerung

        # Check if action is "verweigern" (needs to be passed somehow, maybe via ziel=None but specific intent?)
        # Actually, the UI button sends action_type="verweigern".
        # The game logic needs to route this correctly.

        # Assuming this method is called when he clicks the button
        hat_verweigert = self.get_state(spieler, "hat_verweigert")

        if hat_verweigert:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast bereits einmal rebelliert!",
            )

        # Mark as used
        self.set_state(spieler, "hat_verweigert", True)

        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du verweigerst den Angriff! Das Rudel ist verwirrt und tötet niemanden.",
            effekte={
                "angriff_verweigert": True,
                "teenager_rebelliert": True,
            },
            log_sichtbar_fuer="werwolf",  # Alle Wölfe sehen es
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for TeenagerWerwolf."""
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
                feature_type="accessory",
                geometry="box",
                position={"x": 0.25, "y": 1.0, "z": 0.15},
                scale={"x": 0.1, "y": 0.15, "z": 0.08},
                color_source="role",
                description="Role-specific accessory",
            )
        ]
        
        return RollenModell(
            modell_id="teenagerwerwolf",
            anzeige_name="TeenagerWerwolf",
            beschreibung="TeenagerWerwolf appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="bad",
        )
