"""
Polarwolf - Immun gegen Sandmann und Jäger.

Der Polarwolf ist ein Werwolf mit Immunität gegen
bestimmte Effekte durch seine Kälteresistenz.
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
            erweiterung=Erweiterung.COMMUNITY,
            distribution=DistributionConfig(
                min_players=12,
                count_func=lambda n: 1,
                priority=55,
                exclusive_with=["Werwolf"],
            ),
            avatar_gradient_from="#e0f2fe",
            avatar_gradient_to="#0ea5e9",
            avatar_border_color="#38bdf8",
            badge_emoji="❄️",
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import AktionsTyp

        return AktionsTyp.KEINE

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def is_group_action(self) -> bool:
        """Polarwolf stimmt mit dem Rudel ab."""
        return True

    @property
    def shared_phase_name(self) -> str:
        """Polarwolf teilt sich die werwolf_phase mit dem Rudel."""
        return "werwolf_phase"

    def is_active_on_first_night(self) -> bool:
        return False

    def is_active_on_every_night(self) -> bool:
        return False

    def get_ui_definition(self) -> "RollenUI":
        from ..base import RollenUI

        return RollenUI(
            title="Polarwolf - Passive Rolle",
            instructions="Du jagst mit den Wölfen. Du bist immun gegen Kälte (Sandmann/Jäger).",
            buttons=[],
            requires_target=False,
            can_skip=True,
        )

    def on_angriff(
        self,
        spieler: "Spieler",
        angreifer: "Spieler",
        angriffstyp: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """Polarwolf is immune to hunter and sandman."""
        if angriffstyp in ["jaeger_schuss", "sandmann_schlaf"]:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Der Polarwolf ist immun gegen diesen Angriff!",
                effekte={"angriff_blockiert": True, "immunitaet": angriffstyp},
                log_sichtbar_fuer="erzaehler",
            )
        return None

    def ist_immun_gegen(self, effekt: str) -> bool:
        return effekt in ["sandmann_schlaf", "jaeger_schuss"]

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Polarwolf.

        Arctic white wolf with ice blue eyes, frost particles, thick white fur.
        """
        polarwolf_features = [
            # White wolf ears
            *create_wolf_ears(color="#F0F8FF", scale=1.1),  # AliceBlue
            # Ice-colored claws
            *create_claws(color="#ADD8E6", count_per_hand=3),  # LightBlue
            # White fangs with ice tint
            *create_fangs(color="#F0FFFF"),  # Azure
            # Ice blue glowing eyes
            create_glowing_eyes(color="#00BFFF", intensity=0.9),  # DeepSkyBlue
            # Thick white tail
            create_tail("wolf", color="#F5F5F5"),
            # Frost aura
            create_aura(color="#87CEEB", intensity=0.35, pulsing=True),  # SkyBlue
            # Thick fur ruff around neck
            AppearanceFeature(
                feature_type="fur_ruff",
                geometry="sphere",
                position={"x": 0, "y": 1.65, "z": -0.05},
                scale={"x": 0.45, "y": 0.25, "z": 0.4},
                color_source="custom",
                custom_color="#FFFAFA",  # Snow
                roughness=1.0,
                description="Thick fur ruff",
            ),
            # Frost particles floating around
            AppearanceFeature(
                feature_type="frost_particle_1",
                geometry="sphere",
                position={"x": 0.3, "y": 1.8, "z": 0.2},
                scale={"x": 0.03, "y": 0.03, "z": 0.03},
                color_source="custom",
                custom_color="#E0FFFF",
                opacity=0.7,
                emissive=True,
                emissive_intensity=0.4,
                animation="float",
                animation_speed=0.5,
                description="Frost particle",
            ),
            AppearanceFeature(
                feature_type="frost_particle_2",
                geometry="sphere",
                position={"x": -0.25, "y": 1.5, "z": 0.15},
                scale={"x": 0.025, "y": 0.025, "z": 0.025},
                color_source="custom",
                custom_color="#E0FFFF",
                opacity=0.6,
                emissive=True,
                emissive_intensity=0.3,
                animation="float",
                animation_speed=0.7,
                description="Frost particle",
            ),
            AppearanceFeature(
                feature_type="frost_particle_3",
                geometry="sphere",
                position={"x": 0.15, "y": 1.3, "z": 0.25},
                scale={"x": 0.02, "y": 0.02, "z": 0.02},
                color_source="custom",
                custom_color="#E0FFFF",
                opacity=0.5,
                emissive=True,
                emissive_intensity=0.3,
                animation="float",
                animation_speed=0.6,
                description="Frost particle",
            ),
            # Icy breath effect
            AppearanceFeature(
                feature_type="ice_breath",
                geometry="cone",
                position={"x": 0, "y": 1.7, "z": 0.35},
                scale={"x": 0.08, "y": 0.12, "z": 0.08},
                rotation={"x": 90, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#B0E0E6",
                opacity=0.3,
                particle_effect="magic",
                particle_color="#E0FFFF",
                particle_rate=5.0,
                description="Icy breath",
            ),
            # Frost on paws
            AppearanceFeature(
                feature_type="frost_paw_left",
                geometry="sphere",
                position={"x": -0.35, "y": 0.5, "z": 0.05},
                scale={"x": 0.08, "y": 0.04, "z": 0.08},
                color_source="custom",
                custom_color="#E0FFFF",
                opacity=0.5,
                emissive=True,
                emissive_intensity=0.2,
                description="Frost on paw",
            ),
            AppearanceFeature(
                feature_type="frost_paw_right",
                geometry="sphere",
                position={"x": 0.35, "y": 0.5, "z": 0.05},
                scale={"x": 0.08, "y": 0.04, "z": 0.08},
                color_source="custom",
                custom_color="#E0FFFF",
                opacity=0.5,
                emissive=True,
                emissive_intensity=0.2,
                description="Frost on paw",
            ),
        ]

        return RollenModell(
            modell_id="polarwolf",
            anzeige_name="Polarwolf",
            beschreibung="Ein majestätischer Polarwolf mit eisigem Atem",
            body=BodyModification(
                slouch_angle=12,
                snout_length=0.3,
                claw_hands=True,
                skin_texture="fur",
                skin_color_override="#F5F5F5",
                height_multiplier=1.03,
                width_multiplier=1.08,  # Thick arctic fur
            ),
            appearance_self_alive=polarwolf_features,
            appearance_others_alive=polarwolf_features,
            appearance_dead=create_death_marker(),
            seher_sicht="bad",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.012,
                    sway_speed=0.4,
                    head_tilt_range=15,
                    breathing_visible=True,
                    tail_wag=True,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="frost_glow",
                    effect_type="glow",
                    glow_color="#87CEEB",
                    glow_intensity=0.7,
                    glow_pulse=True,
                ),
                HintEffect3D(
                    effect_id="frost_breath",
                    effect_type="particle",
                    particle_type="magic",
                    particle_count=15,
                    particle_color="#E0FFFF",
                    particle_duration=1.5,
                ),
            ],
            sound_on_action="ice_howl.mp3",
            sound_ambient="cold_wind.mp3",
        )
