"""
Aurenseherin - Sieht die Aura statt die konkrete Rolle.
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
    create_pointed_hat,
    create_aura,
    create_robe,
    create_death_marker,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Aurenseherin(Role):
    """
    Die Aurenseherin - Alternative Informationsrolle.

    Fähigkeiten:
    - Sieht ob ein Spieler "gut" oder "böse" ist
    - Kann durch manche Tarnungen durchschauen

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=51,
            name="Aurenseherin",
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                "Du bist die Aurenseherin. Du siehst nicht die konkrete "
                "Rolle, sondern ob jemand eine gute oder böse Aura hat."
            ),
            icon="fa-solid fa-circle-radiation",
            farbe="#a78bfa",
            prioritaet=22,
            erzaehler_nacht="Die Aurenseherin sieht die Aura eines Spielers.",
            erweiterung=Erweiterung.CHARAKTERE,
            distribution=DistributionConfig(
                min_players=10,
                count_func=lambda n: 1,
                priority=45,
                exclusive_with=["Seherin"],
            ),
            avatar_gradient_from="#a78bfa",
            avatar_gradient_to="#7c3aed",
            avatar_border_color="#c4b5fd",
            badge_emoji="✨",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    def is_active_on_first_night(self) -> bool:
        return True

    def is_active_on_every_night(self) -> bool:
        return True

    def get_ui_definition(self) -> "RollenUI":
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Aurenseherin - Aura sehen",
            instructions="Wähle einen Spieler, um seine Aura zu sehen.",
            buttons=[
                UIButton(
                    label="Aura sehen",
                    action_type="aurenseherin_sehen",
                    icon="fa-solid fa-circle-radiation",
                    css_class="btn-info",
                )
            ],
            requires_target=True,
            can_skip=False,
        )

    def execute_action(
        self,
        action_type: str,
        spieler: "Spieler",
        targets: List["Spieler"],
        kontext: "SpielKontext",
    ) -> Optional[AktionsErgebnis]:
        if action_type == "aurenseherin_sehen":
            if not targets:
                return AktionsErgebnis(
                    erfolg=False, nachricht="Du musst einen Spieler wählen."
                )

            ziel = targets[0]
            ziel_rolle = RoleRegistry.get(ziel.rolle)

            ist_boese = False
            if ziel_rolle:
                team = ziel_rolle.info.team
                ist_boese = team in [Team.WERWOLF, Team.SOLO]

            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"{ziel.name} hat eine {'dunkle 🌑' if ist_boese else 'helle ☀️'} Aura.",
                ziel_spieler_id=ziel.id,
                effekte={"aura_gesehen": ziel.id, "ist_boese": ist_boese},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        return None

    def on_nacht_aktion(
        self,
        spieler: "Spieler",
        ziel: Optional["Spieler"],
        kontext: SpielKontext,
        aktion: str = None,
    ) -> Optional[AktionsErgebnis]:
        return self.execute_action(
            "aurenseherin_sehen", spieler, [ziel] if ziel else [], kontext
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Aurenseherin.

        Ethereal mystic with glowing eyes, flowing robes, surrounded by
        swirling colored auras representing good and evil.
        """
        aurenseherin_features = [
            # Flowing mystical robes (purple/violet)
            create_robe(color="#7C3AED"),
            # Pointed mystic hood
            AppearanceFeature(
                feature_type="mystic_hood",
                geometry="sphere",
                position={"x": 0, "y": 2.0, "z": -0.08},
                scale={"x": 0.32, "y": 0.22, "z": 0.28},
                color_source="custom",
                custom_color="#5B21B6",
                description="Mystic hood",
            ),
            # Glowing white-purple eyes
            AppearanceFeature(
                feature_type="glowing_eyes",
                geometry="sphere",
                position={"x": 0, "y": 1.88, "z": 0.2},
                scale={"x": 0.12, "y": 0.05, "z": 0.04},
                color_source="custom",
                custom_color="#E9D5FF",
                emissive=True,
                emissive_intensity=0.9,
                animation="pulse",
                animation_speed=0.5,
                description="Glowing aura-reading eyes",
            ),
            # Multi-colored aura (representing ability to see auras)
            create_aura(color="#A78BFA", intensity=0.35, pulsing=True),
            # Golden aura particles (good)
            AppearanceFeature(
                feature_type="good_aura_particle_1",
                geometry="sphere",
                position={"x": 0.35, "y": 1.6, "z": 0.15},
                scale={"x": 0.04, "y": 0.04, "z": 0.04},
                color_source="custom",
                custom_color="#FFD700",
                opacity=0.7,
                emissive=True,
                emissive_intensity=0.6,
                animation="float",
                animation_speed=0.6,
                description="Good aura particle",
            ),
            AppearanceFeature(
                feature_type="good_aura_particle_2",
                geometry="sphere",
                position={"x": 0.2, "y": 1.3, "z": 0.2},
                scale={"x": 0.03, "y": 0.03, "z": 0.03},
                color_source="custom",
                custom_color="#FFD700",
                opacity=0.6,
                emissive=True,
                emissive_intensity=0.5,
                animation="float",
                animation_speed=0.8,
                description="Good aura particle",
            ),
            # Dark aura particles (evil)
            AppearanceFeature(
                feature_type="dark_aura_particle_1",
                geometry="sphere",
                position={"x": -0.3, "y": 1.5, "z": 0.1},
                scale={"x": 0.04, "y": 0.04, "z": 0.04},
                color_source="custom",
                custom_color="#4A0080",
                opacity=0.6,
                emissive=True,
                emissive_intensity=0.4,
                animation="float",
                animation_speed=0.5,
                description="Dark aura particle",
            ),
            AppearanceFeature(
                feature_type="dark_aura_particle_2",
                geometry="sphere",
                position={"x": -0.18, "y": 1.2, "z": 0.18},
                scale={"x": 0.035, "y": 0.035, "z": 0.035},
                color_source="custom",
                custom_color="#4A0080",
                opacity=0.5,
                emissive=True,
                emissive_intensity=0.3,
                animation="float",
                animation_speed=0.7,
                description="Dark aura particle",
            ),
            # Mystical pendant
            AppearanceFeature(
                feature_type="pendant",
                geometry="sphere",
                position={"x": 0, "y": 1.35, "z": 0.2},
                scale={"x": 0.05, "y": 0.06, "z": 0.03},
                color_source="custom",
                custom_color="#C4B5FD",
                emissive=True,
                emissive_intensity=0.5,
                metallic=True,
                description="Aura pendant",
            ),
            # Flowing sleeves
            AppearanceFeature(
                feature_type="sleeve_left",
                geometry="cone",
                position={"x": -0.35, "y": 0.9, "z": 0},
                scale={"x": 0.15, "y": 0.4, "z": 0.15},
                rotation={"x": 0, "y": 0, "z": 25},
                color_source="custom",
                custom_color="#7C3AED",
                animation="sway",
                animation_speed=0.3,
                description="Flowing sleeve",
            ),
            AppearanceFeature(
                feature_type="sleeve_right",
                geometry="cone",
                position={"x": 0.35, "y": 0.9, "z": 0},
                scale={"x": 0.15, "y": 0.4, "z": 0.15},
                rotation={"x": 0, "y": 0, "z": -25},
                color_source="custom",
                custom_color="#7C3AED",
                animation="sway",
                animation_speed=0.3,
                description="Flowing sleeve",
            ),
        ]

        return RollenModell(
            modell_id="aurenseherin",
            anzeige_name="Aurenseherin",
            beschreibung="Eine Mystikerin die Auren lesen kann",
            body=BodyModification(
                height_multiplier=0.98,
                skin_texture="smooth",
            ),
            appearance_self_alive=aurenseherin_features,
            appearance_others_alive=aurenseherin_features,
            appearance_dead=create_death_marker(),
            seher_sicht="good",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.015,
                    sway_speed=0.4,
                    breathing_visible=True,
                    gesture_chance=0.1,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="aura_vision",
                    effect_type="glow",
                    glow_color="#A78BFA",
                    glow_intensity=0.8,
                    glow_pulse=True,
                ),
                HintEffect3D(
                    effect_id="aura_particles",
                    effect_type="particle",
                    particle_type="magic",
                    particle_count=12,
                    particle_color="#E9D5FF",
                    particle_duration=1.2,
                ),
            ],
            sound_on_action="mystical_chime.mp3",
        )
