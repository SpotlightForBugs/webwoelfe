"""
Jäger - Stirbt nicht kampflos.

Der Jäger kann bei seinem Tod einen letzten Schuss abfeuern
und einen beliebigen Spieler mit in den Tod reißen.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    AppearanceFeature,
    RollenModell,
    BodyModification,
    AnimationState,
    HintEffect3D,
    SpecialPhaseConfig,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
    DistributionConfig,
    # Factory functions
    create_weapon,
    create_cape,
    create_death_marker,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Jaeger(Role):
    """
    Der Jäger - Rache-Rolle.

    Fähigkeiten:
    - Wenn er stirbt, kann er einen anderen Spieler mit in den Tod reißen.

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        return [
            StateField(
                "schuss_verfuegbar",
                StateType.BOOL,
                True,
                "Schuss bereit",
                icon="fa-solid fa-gun",
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=5,
            name="Jäger",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist der Jäger. Wenn du stirbst, kannst du einen letzten "
                "Schuss abfeuern und einen Spieler deiner Wahl mit in den Tod reißen."
            ),
            icon="fa-solid fa-crosshairs",
            farbe="#f97316",
            prioritaet=100,
            erzaehler_nacht=("Der Jäger schläft. Er wird nur aktiv, wenn er stirbt."),
            erweiterung=Erweiterung.BASISSPIEL,
            # Visual Styling
            avatar_gradient_from="#f97316",
            avatar_gradient_to="#c2410c",
            avatar_border_color="#fb923c",
            badge_emoji="fas fa-gun",
            distribution=DistributionConfig(
                min_players=5,
                count_func=lambda n: 1,
                priority=10,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SCHIESSEN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Jäger does not act on first night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Jäger does not act every night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Jäger's action panel (only when dead)."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Jäger - Letzter Schuss",
            instructions="Du stirbst! Wähle jemanden, den du mit in den Tod reißen willst.",
            buttons=[
                UIButton(
                    label="Schießen",
                    action_type="jaeger_schuss",
                    icon="fa-solid fa-crosshairs",
                    css_class="btn-danger",
                    requires_confirmation=True,
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def get_triggered_phases(self) -> List[SpecialPhaseConfig]:
        """
        Jäger triggers a special phase when he dies.
        This replaces the hardcoded 'jaeger_phase' in phase_generator.py.
        """
        return [
            SpecialPhaseConfig(
                phase_name="jaeger_phase",
                trigger_event="on_death",
                trigger_condition=lambda spieler, kontext: spieler.get_state(
                    "jaeger.schuss_verfuegbar", True
                ),
                next_phase_override=None,  # Return to normal flow after
                priority=100,  # High priority - happens immediately
                interruptible=False,  # Cannot be interrupted
            )
        ]

    def execute_action(
        self,
        action_type: str,
        spieler: "Spieler",
        targets: List["Spieler"],
        kontext: "SpielKontext",
    ) -> Optional[AktionsErgebnis]:
        """
        Execute Jäger actions dynamically.

        Handles:
        - jaeger_schuss / schuss: The last shot when dying
        """
        # Handle both prefixed and unprefixed action types
        if action_type in ("jaeger_schuss", "schuss"):
            return self._execute_schuss(
                spieler, targets[0] if targets else None, kontext
            )

        # Delegate to parent for skip handling etc.
        return super().execute_action(action_type, spieler, targets, kontext)

    def _execute_schuss(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: "SpielKontext"
    ) -> AktionsErgebnis:
        """Execute the hunter's last shot."""
        # Check if shot is available
        if not self.get_state(spieler, "schuss_verfuegbar", True):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deinen Schuss bereits abgefeuert.",
            )

        if not ziel:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst ein Ziel für deinen Schuss wählen.",
            )

        # Mark shot as used
        self.set_state(spieler, "schuss_verfuegbar", False)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Der Jäger schießt auf {ziel.name}!",
            ziel_spieler_id=ziel.id,
            effekte={
                "jaeger_schuss": True,
                "toeten": ziel.id,
                "todesursache": "jaeger",
            },
            state_updates={"jaeger.schuss_verfuegbar": False},
            log_sichtbar_fuer="alle",
        )

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn der Jäger stirbt, darf er noch schießen.
        Returns effect that triggers the jaeger_phase.
        """
        if self.get_state(spieler, "schuss_verfuegbar", True):
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Der Jäger greift zu seiner Waffe!",
                effekte={
                    "trigger_phase": "jaeger_phase",
                    "jaeger_schuss_bereit": True,
                },
                log_sichtbar_fuer="alle",
            )
        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Jäger.

        Features:
        - Crossbow weapon
        - Hunting cape
        - Quiver with bolts
        - Rugged outdoorsman appearance
        - Hat
        """
        jaeger_features = [
            # Crossbow in hand
            *create_weapon("crossbow"),
            # Hunting cape
            create_cape(color="#4a3020", length="medium"),
            # Hunter's hat
            AppearanceFeature(
                feature_type="hunter_hat",
                geometry="cylinder",
                position={"x": 0, "y": 2.15, "z": 0},
                scale={"x": 0.25, "y": 0.1, "z": 0.25},
                color_source="custom",
                custom_color="#3d2817",
                roughness=0.7,
                description="Hunter's hat brim",
            ),
            AppearanceFeature(
                feature_type="hunter_hat_top",
                geometry="cylinder",
                position={"x": 0, "y": 2.22, "z": 0},
                scale={"x": 0.18, "y": 0.12, "z": 0.18},
                color_source="custom",
                custom_color="#4a3520",
                roughness=0.7,
                description="Hunter's hat top",
            ),
            # Feather on hat
            AppearanceFeature(
                feature_type="hat_feather",
                geometry="cone",
                position={"x": 0.12, "y": 2.35, "z": 0},
                scale={"x": 0.02, "y": 0.2, "z": 0.05},
                rotation={"x": 0, "y": 0, "z": 15},
                color_source="custom",
                custom_color="#8B4513",
                description="Feather on hat",
            ),
            # Quiver on back
            AppearanceFeature(
                feature_type="quiver",
                geometry="cylinder",
                position={"x": 0.15, "y": 1.2, "z": -0.2},
                scale={"x": 0.08, "y": 0.4, "z": 0.08},
                rotation={"x": -15, "y": 0, "z": 10},
                color_source="custom",
                custom_color="#5a4030",
                roughness=0.8,
                description="Bolt quiver",
            ),
            # Bolts in quiver
            AppearanceFeature(
                feature_type="bolts",
                geometry="cylinder",
                position={"x": 0.15, "y": 1.5, "z": -0.2},
                scale={"x": 0.02, "y": 0.25, "z": 0.02},
                rotation={"x": -15, "y": 0, "z": 10},
                color_source="custom",
                custom_color="#8B7355",
                count=4,
                count_arrangement="radial",
                count_spacing=0.03,
                description="Crossbow bolts",
            ),
            # Belt
            AppearanceFeature(
                feature_type="belt",
                geometry="box",
                position={"x": 0, "y": 0.85, "z": 0},
                scale={"x": 0.35, "y": 0.05, "z": 0.32},
                color_source="custom",
                custom_color="#3d2817",
                roughness=0.6,
                description="Leather belt",
            ),
            # Belt buckle
            AppearanceFeature(
                feature_type="belt_buckle",
                geometry="box",
                position={"x": 0, "y": 0.85, "z": 0.16},
                scale={"x": 0.06, "y": 0.06, "z": 0.02},
                color_source="custom",
                custom_color="#B8860B",
                metallic=True,
                roughness=0.3,
                description="Belt buckle",
            ),
        ]

        return RollenModell(
            modell_id="jaeger",
            anzeige_name="Jäger",
            beschreibung="Ein erfahrener Jäger mit Armbrust und scharfem Blick",
            body=BodyModification(
                height_multiplier=1.02,
                width_multiplier=1.05,
                skin_texture="smooth",
            ),
            appearance_self_alive=jaeger_features,
            appearance_others_alive=jaeger_features,
            appearance_dead=create_death_marker(),
            seher_sicht="good",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.01,
                    sway_speed=0.6,
                    head_tilt_range=25,
                    look_around=True,
                    blink_rate=2.5,
                    breathing_visible=True,
                ),
                "aim": AnimationState(
                    state_name="aim",
                    sway_amplitude=0.0,
                    head_tilt_range=5,
                    look_around=False,
                    blink_rate=1.0,
                    gesture_chance=0.0,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="look_away",
                    effect_type="transform",
                    rotate_to={"x": 0, "y": 45, "z": 0},
                ),
            ],
            sound_on_action="crossbow_shot.mp3",
            sound_on_death="hunter_death.mp3",
        )
