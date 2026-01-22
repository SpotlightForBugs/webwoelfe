"""
Dorfbewohner - Die Basis-Rolle für das Dorf-Team.

Der Dorfbewohner hat keine speziellen Fähigkeiten,
aber seine Stimme in der Abstimmung ist entscheidend.
"""

from typing import Optional, List
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
    DistributionConfig,
    create_death_marker,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry


@RoleRegistry.register
class Dorfbewohner(Role):
    """
    Einfacher Dorfbewohner ohne spezielle Fähigkeiten.

    Gewinnbedingung: Alle Werwoelfe werden eliminiert.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=1,
            name="Dorfbewohner",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist ein einfacher Dorfbewohner. Hilf dem Dorf, die Werwoelfe "
                "zu entlarven! Du hast keine speziellen Fähigkeiten, aber deine "
                "Stimme zählt."
            ),
            icon="fa-solid fa-user",
            farbe="#6b7280",
            prioritaet=100,
            erweiterung=Erweiterung.BASISSPIEL,
            erzaehler_nacht=(
                "Der Dorfbewohner schläft friedlich. "
                "Er hat keine nächtlichen Fähigkeiten."
            ),
            erzaehler_tag=(
                "Der Dorfbewohner erwacht und hofft, die Woelfe zu entlarven. "
                "Seine Stimme ist seine einzige Waffe."
            ),
            # Visual Styling
            avatar_gradient_from="#0369a1",
            avatar_gradient_to="#075985",
            avatar_border_color="#0ea5e9",
            badge_emoji="fas fa-house",
            distribution=DistributionConfig(
                min_players=0,
                count_func=lambda n: 0,  # Wird als Filler berechnet
                min_role_count=1,
                max_role_count=None,
                priority=100,
                exclusive_with=[],
                is_filler=True,
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Dorfbewohner does not act on the first night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Dorfbewohner does not act every night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        from ..base import RollenUI

        return RollenUI(
            title="Dorfbewohner - Schlafen",
            instructions="Du schläfst friedlich. Du hast keine nächtliche Aktion.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def get_win_conditions(self) -> List["WinCondition"]:
        """Dorf gewinnt über Team-Level Win Conditions (nicht hier)."""
        # Village win condition is handled at the TEAM level in pruefe_spielende()
        # Individual roles should not define team-wide win conditions
        # Only SOLO roles should define individual win conditions here
        return []

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Dorfbewohner (Villager).

        The baseline villager appearance that other roles build upon.
        Simple, humble appearance of a medieval villager.
        """
        villager_features = [
            # Simple peasant hat
            AppearanceFeature(
                feature_type="peasant_hat",
                geometry="cylinder",
                position={"x": 0, "y": 2.12, "z": 0},
                scale={"x": 0.22, "y": 0.08, "z": 0.22},
                color_source="custom",
                custom_color="#8B7355",
                roughness=0.8,
                description="Simple peasant cap",
            ),
            # Simple tunic/shirt
            AppearanceFeature(
                feature_type="tunic",
                geometry="box",
                position={"x": 0, "y": 1.1, "z": 0},
                scale={"x": 0.35, "y": 0.5, "z": 0.25},
                color_source="custom",
                custom_color="#D2B48C",  # Tan color
                roughness=0.8,
                description="Simple tunic",
            ),
            # Pants/lower body
            AppearanceFeature(
                feature_type="pants",
                geometry="box",
                position={"x": 0, "y": 0.5, "z": 0},
                scale={"x": 0.3, "y": 0.5, "z": 0.22},
                color_source="custom",
                custom_color="#5D4E37",  # Brown
                roughness=0.7,
                description="Simple pants",
            ),
            # Belt
            AppearanceFeature(
                feature_type="belt",
                geometry="box",
                position={"x": 0, "y": 0.82, "z": 0},
                scale={"x": 0.36, "y": 0.04, "z": 0.26},
                color_source="custom",
                custom_color="#3D2817",
                roughness=0.6,
                description="Leather belt",
            ),
            # Simple boots
            AppearanceFeature(
                feature_type="boot_left",
                geometry="box",
                position={"x": -0.1, "y": 0.1, "z": 0},
                scale={"x": 0.1, "y": 0.2, "z": 0.15},
                color_source="custom",
                custom_color="#3D2817",
                roughness=0.7,
                description="Left boot",
            ),
            AppearanceFeature(
                feature_type="boot_right",
                geometry="box",
                position={"x": 0.1, "y": 0.1, "z": 0},
                scale={"x": 0.1, "y": 0.2, "z": 0.15},
                color_source="custom",
                custom_color="#3D2817",
                roughness=0.7,
                description="Right boot",
            ),
        ]

        return RollenModell(
            modell_id="dorfbewohner",
            anzeige_name="Dorfbewohner",
            beschreibung="Ein einfacher Dorfbewohner in bescheidener Kleidung",
            body=BodyModification(
                height_multiplier=1.0,
                skin_texture="smooth",
            ),
            appearance_self_alive=villager_features,
            appearance_others_alive=villager_features,
            appearance_dead=create_death_marker(),
            seher_sicht="good",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.015,
                    sway_speed=0.6,
                    head_tilt_range=20,
                    look_around=True,
                    blink_rate=3.0,
                    breathing_visible=True,
                    gesture_chance=0.1,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="nervous",
                    effect_type="shake",
                    shake_intensity=0.03,
                    shake_duration=0.5,
                ),
                HintEffect3D(
                    effect_id="stumble",
                    effect_type="transform",
                    rotate_to={"x": 5, "y": 0, "z": 3},
                ),
            ],
        )
