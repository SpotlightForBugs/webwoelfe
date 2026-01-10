"""
Heiler - Schützt Spieler vor nächtlichen Angriffen.

Der Heiler kann jede Nacht einen Spieler schützen,
aber nicht zweimal hintereinander denselben.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    AppearanceFeature,
    RollenModell,
    BodyModification,
    AnimationState,
    HintEffect3D,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
    DistributionConfig,
    # Factory functions
    create_weapon,
    create_aura,
    create_robe,
    create_death_marker,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Heiler(Role):
    """
    Der Heiler - Beschützer-Rolle.

    Fähigkeiten:
    - Kann jede Nacht einen Spieler vor Werwölfen schützen
    - Darf nicht zweimal hintereinander denselben Spieler schützen

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        return [
            StateField(
                "letztes_ziel_id",
                StateType.PLAYER_ID,
                None,
                "Zuletzt geschützter Spieler",
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=6,
            name="Heiler",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist der Heiler. Jede Nacht kannst du einen Spieler vor den "
                "Werwölfen schützen. Du darfst aber nicht zweimal hintereinander "
                "denselben Spieler schützen."
            ),
            icon="fa-solid fa-hand-holding-medical",
            farbe="#10b981",
            prioritaet=10,
            erzaehler_nacht=(
                "Der Heiler erwacht. Wen möchtest du diese Nacht vor den "
                "Werwölfen schützen?"
            ),
            erweiterung=Erweiterung.NEUMOND,
            # Visual Styling
            avatar_gradient_from="#10b981",
            avatar_gradient_to="#047857",
            avatar_border_color="#34d399",
            badge_emoji="🛡️",
            distribution=DistributionConfig(
                min_players=6,
                count_func=lambda n: 1,
                priority=10,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SCHUETZEN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Heiler acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Heiler acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Heiler's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Heiler - Spieler schützen",
            instructions="Wähle einen Spieler, den du vor den Werwölfen schützen möchtest.",
            buttons=[
                UIButton(
                    label="Schützen",
                    action_type="schuetzen",
                    icon="fa-solid fa-shield-halved",
                    css_class="btn-success",
                    requires_confirmation=True,
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Heiler schützt einen Spieler.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst einen Spieler wählen.",
            )

        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel.",
            )

        # Prüfe ob Ziel == letztes Ziel
        letztes_ziel_id = self.get_state(spieler, "letztes_ziel_id")
        if letztes_ziel_id == ziel.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nicht zweimal hintereinander denselben Spieler schützen.",
            )

        # Speichere neues Ziel
        self.set_state(spieler, "letztes_ziel_id", ziel.id)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du beschützt {ziel.name} in dieser Nacht.",
            ziel_spieler_id=ziel.id,
            effekte={
                "heiler_schutz": True,
            },
            multi_target_updates={
                ziel.id: {"global.ist_beschuetzt": True}
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Heiler.

        Features:
        - Healing staff with glowing green orb
        - Green healing aura
        - Healer robes
        - Medical bag
        """
        heiler_features = [
            # Healing staff
            *create_weapon("healing_staff"),
            # Green healing aura
            create_aura(color="#00FF88", intensity=0.4, pulsing=True),
            # Healer robes
            AppearanceFeature(
                feature_type="healer_robe",
                geometry="cone",
                position={"x": 0, "y": 0.7, "z": 0},
                scale={"x": 0.4, "y": 1.1, "z": 0.35},
                color_source="custom",
                custom_color="#F0FFF0",  # Honeydew white
                roughness=0.7,
                description="White healer robes",
            ),
            # Green cross on chest
            AppearanceFeature(
                feature_type="cross_vertical",
                geometry="box",
                position={"x": 0, "y": 1.1, "z": 0.18},
                scale={"x": 0.04, "y": 0.15, "z": 0.02},
                color_source="custom",
                custom_color="#10B981",
                emissive=True,
                emissive_intensity=0.3,
                description="Healer cross (vertical)",
            ),
            AppearanceFeature(
                feature_type="cross_horizontal",
                geometry="box",
                position={"x": 0, "y": 1.1, "z": 0.18},
                scale={"x": 0.1, "y": 0.04, "z": 0.02},
                color_source="custom",
                custom_color="#10B981",
                emissive=True,
                emissive_intensity=0.3,
                description="Healer cross (horizontal)",
            ),
            # Medical pouch on belt
            AppearanceFeature(
                feature_type="medical_pouch",
                geometry="box",
                position={"x": -0.25, "y": 0.75, "z": 0.15},
                scale={"x": 0.1, "y": 0.12, "z": 0.08},
                color_source="custom",
                custom_color="#8B4513",
                roughness=0.7,
                description="Medical supply pouch",
            ),
            # Herbs poking out of pouch
            AppearanceFeature(
                feature_type="herbs",
                geometry="cone",
                position={"x": -0.25, "y": 0.85, "z": 0.15},
                scale={"x": 0.04, "y": 0.08, "z": 0.04},
                color_source="custom",
                custom_color="#228B22",
                description="Healing herbs",
            ),
        ]

        return RollenModell(
            modell_id="heiler",
            anzeige_name="Heiler",
            beschreibung="Ein weiser Heiler mit heilenden Kräutern und grüner Aura",
            body=BodyModification(
                height_multiplier=0.98,
                skin_texture="smooth",
            ),
            appearance_self_alive=heiler_features,
            appearance_others_alive=heiler_features,
            appearance_dead=create_death_marker(),
            seher_sicht="good",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.01,
                    sway_speed=0.5,
                    head_tilt_range=15,
                    look_around=True,
                    blink_rate=2.5,
                    breathing_visible=True,
                ),
                "healing": AnimationState(
                    state_name="healing",
                    sway_amplitude=0.02,
                    gesture_chance=0.4,
                    breathing_visible=True,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="aura_glow",
                    effect_type="glow",
                    glow_color="#00FF88",
                    glow_intensity=0.6,
                    glow_pulse=True,
                ),
            ],
            sound_on_action="healing_chime.mp3",
        )
