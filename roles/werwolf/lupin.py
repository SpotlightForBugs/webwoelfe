"""
Lupin - Der Werwolf mit wechselnder Identitaet.

Lupin verwandelt sich nur bei Vollmond. In geraden Runden
erscheint er der Seherin als Mensch, in ungeraden als Wolf.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    RollenModell,
    AppearanceFeature,
    BodyModification,
    AnimationState,
    HintEffect3D,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    create_wolf_ears,
    create_claws,
    create_fangs,
    create_glowing_eyes,
    create_tail,
    create_aura,
    create_death_marker,
    DistributionConfig,
)
from ..enums import Team, Kategorie, SichtTyp, Erweiterung, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Lupin(Role):
    """
    Lupin - Werwolf mit wechselnder Identitaet.

    Faehigkeiten:
    - Jagt mit den Woelfen
    - In geraden Runden erscheint er der Seherin als Mensch
    - In ungeraden Runden erscheint er als Werwolf

    Gewinnbedingung: Werwoelfe gewinnen.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=26,
            name="Lupin",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist Lupin. Du verwandelst dich nur bei Vollmond - "
                "in geraden Runden bist du ein harmloser Mensch, in ungeraden ein Wolf!"
            ),
            icon="fa-solid fa-moon",
            farbe="#ca8a04",
            prioritaet=50,
            erzaehler_nacht="Lupin ist in geraden Runden Mensch, in ungeraden Wolf.",
            erweiterung=Erweiterung.COMMUNITY,
            distribution=DistributionConfig(
                min_players=12,
                count_func=lambda n: 1,
                priority=55,
                exclusive_with=["Werwolf"],
            ),
            avatar_gradient_from="#ca8a04",
            avatar_gradient_to="#a16207",
            avatar_border_color="#eab308",
            badge_emoji="🌕",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    def get_sichtbare_rolle_fuer(self, seher: "Role", kontext: SpielKontext) -> str:
        if kontext.runde % 2 == 0:
            return "Dorfbewohner"
        return "Werwolf"

    @property
    def is_group_action(self) -> bool:
        """Lupin stimmt mit dem Rudel ab."""
        return True

    @property
    def shared_phase_name(self) -> str:
        """Lupin teilt sich die werwolf_phase mit dem Rudel."""
        return "werwolf_phase"

    def is_active_on_first_night(self) -> bool:
        return False

    def is_active_on_every_night(self) -> bool:
        return False

    def get_ui_definition(self) -> "RollenUI":
        from ..base import RollenUI
        return RollenUI(
            title="Lupin - Passive Rolle",
            instructions="Du jagst mit den Wölfen. Deine Aura wechselt jede Nacht.",
            buttons=[],
            requires_target=False,
            can_skip=True,
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Lupin.

        Scholarly professor appearance with subtle wolf traits visible.
        Tattered robes, moon-influenced appearance with transitional features.
        """
        lupin_features = [
            # Scholarly robes (tattered, weathered)
            AppearanceFeature(
                feature_type="robes",
                geometry="box",
                position={"x": 0, "y": 1.0, "z": 0},
                scale={"x": 0.4, "y": 0.7, "z": 0.35},
                color_source="custom",
                custom_color="#5C4033",  # Brown robes
                roughness=0.85,
                description="Tattered professor robes",
            ),
            # Scarf/collar
            AppearanceFeature(
                feature_type="scarf",
                geometry="box",
                position={"x": 0, "y": 1.55, "z": 0.1},
                scale={"x": 0.35, "y": 0.1, "z": 0.22},
                color_source="custom",
                custom_color="#8B7355",
                description="Worn scarf",
            ),
            # Graying hair with wolfish texture
            AppearanceFeature(
                feature_type="hair",
                geometry="sphere",
                position={"x": 0, "y": 2.05, "z": -0.05},
                scale={"x": 0.28, "y": 0.15, "z": 0.25},
                color_source="custom",
                custom_color="#696969",  # Gray
                roughness=0.9,
                description="Graying wolfish hair",
            ),
            # Subtle wolf ears (can be hidden or visible)
            *create_wolf_ears(color="#696969", scale=0.6),  # Smaller, subtler
            # Amber/yellow eyes with subtle glow
            create_glowing_eyes(color="#DAA520", intensity=0.5),  # Goldenrod
            # Moon aura (subtle)
            AppearanceFeature(
                feature_type="moon_aura",
                geometry="sphere",
                position={"x": 0, "y": 1.5, "z": 0},
                scale={"x": 0.6, "y": 0.8, "z": 0.5},
                color_source="custom",
                custom_color="#F0E68C",  # Khaki (moonlight)
                opacity=0.12,
                emissive=True,
                emissive_intensity=0.15,
                animation="pulse",
                animation_speed=0.3,
                description="Moon aura",
            ),
            # Scars on face (wolf attack in past)
            AppearanceFeature(
                feature_type="scar_1",
                geometry="box",
                position={"x": 0.12, "y": 1.85, "z": 0.2},
                scale={"x": 0.08, "y": 0.012, "z": 0.01},
                rotation={"x": 0, "y": 0, "z": -25},
                color_source="custom",
                custom_color="#8B6969",
                description="Facial scar",
            ),
            AppearanceFeature(
                feature_type="scar_2",
                geometry="box",
                position={"x": 0.08, "y": 1.82, "z": 0.18},
                scale={"x": 0.06, "y": 0.012, "z": 0.01},
                rotation={"x": 0, "y": 0, "z": -20},
                color_source="custom",
                custom_color="#8B6969",
                description="Facial scar",
            ),
            # Subtle claws (partially hidden)
            AppearanceFeature(
                feature_type="subtle_claw_left",
                geometry="cone",
                position={"x": -0.35, "y": 0.55, "z": 0.1},
                scale={"x": 0.015, "y": 0.04, "z": 0.015},
                rotation={"x": 20, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#2a2a2a",
                description="Subtle claw",
            ),
            AppearanceFeature(
                feature_type="subtle_claw_right",
                geometry="cone",
                position={"x": 0.35, "y": 0.55, "z": 0.1},
                scale={"x": 0.015, "y": 0.04, "z": 0.015},
                rotation={"x": 20, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#2a2a2a",
                description="Subtle claw",
            ),
            # Book/wand in hand (professor)
            AppearanceFeature(
                feature_type="wand",
                geometry="cylinder",
                position={"x": 0.38, "y": 0.8, "z": 0.15},
                scale={"x": 0.02, "y": 0.2, "z": 0.02},
                rotation={"x": 15, "y": 0, "z": -30},
                color_source="custom",
                custom_color="#4a3520",
                description="Wand",
            ),
        ]

        return RollenModell(
            modell_id="lupin",
            anzeige_name="Lupin",
            beschreibung="Ein gelehrter Professor mit wolfsartigen Zügen",
            body=BodyModification(
                slouch_angle=5,  # Slightly tired posture
                height_multiplier=1.0,
                skin_texture="smooth",
            ),
            appearance_self_alive=lupin_features,
            appearance_others_alive=lupin_features,
            appearance_dead=create_death_marker(),
            seher_sicht="bad",  # Default, overridden by round logic
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.012,
                    sway_speed=0.4,
                    head_tilt_range=15,
                    breathing_visible=True,
                    blink_rate=2.5,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="moon_glow",
                    effect_type="glow",
                    glow_color="#F0E68C",
                    glow_intensity=0.5,
                    glow_pulse=True,
                ),
            ],
            sound_on_action="professor_growl.mp3",
        )
