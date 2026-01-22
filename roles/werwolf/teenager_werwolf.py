"""
Teenager-Werwolf - Der rebellische Wolf.

Der Teenager-Werwolf ist ein normaler Werwolf, der sich
einmal pro Spiel weigern kann, beim Angriff mitzumachen.
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
    create_wolf_ears,
    create_claws,
    create_fangs,
    create_glowing_eyes,
    create_tail,
    create_death_marker,
    DistributionConfig,
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
        return [
            StateField(
                "hat_verweigert",
                StateType.BOOL,
                False,
                "Hat bereits verweigert",
                icon="fa-solid fa-hand",
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
                "Du bist der Teenager-Werwolf. Einmal pro Spiel kannst du dich weigern, "
                "beim nächtlichen Angriff mitzumachen. Das Opfer stirbt dann nicht!"
            ),
            icon="fa-solid fa-user-slash",
            farbe="#7f1d1d",
            prioritaet=50,
            erzaehler_nacht="Der Teenager-Werwolf kann einmal den Angriff verweigern.",
            erweiterung=Erweiterung.COMMUNITY,
            distribution=DistributionConfig(
                min_players=12,
                count_func=lambda n: 1,
                priority=50,
                exclusive_with=["Werwolf"],
            ),
            avatar_gradient_from="#7f1d1d",
            avatar_gradient_to="#450a0a",
            avatar_border_color="#b91c1c",
            badge_emoji="fa-solid fa-paw",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def is_group_action(self) -> bool:
        """Teenager-Werwolf stimmt mit dem Rudel ab."""
        return True

    @property
    def shared_phase_name(self) -> str:
        """Teenager-Werwolf teilt sich die werwolf_phase mit dem Rudel."""
        return "werwolf_phase"

    def is_active_on_first_night(self) -> bool:
        return True

    def is_active_on_every_night(self) -> bool:
        return True

    def get_ui_definition(self) -> "RollenUI":
        from ..base import RollenUI, UIButton
        return RollenUI(
            title="Teenager-Werwolf - Rebellieren",
            instructions="Du kannst einmal pro Spiel den Angriff des Rudels stoppen.",
            buttons=[
                UIButton(
                    label="Angriff verweigern",
                    action_type="teenager_verweigern",
                    icon="fa-solid fa-hand",
                    css_class="btn-warning",
                    requires_confirmation=True,
                )
            ],
            requires_target=False,
            can_skip=True,
        )

    def execute_action(
        self,
        action_type: str,
        spieler: "Spieler",
        targets: List["Spieler"],
        kontext: "SpielKontext",
    ) -> Optional[AktionsErgebnis]:
        # Handle both prefixed and unprefixed action types
        if action_type in ("teenager_verweigern", "verweigern"):
            if self.get_state(spieler, "hat_verweigert"):
                return AktionsErgebnis(erfolg=False, nachricht="Du hast bereits einmal rebelliert!")

            self.set_state(spieler, "hat_verweigert", True)
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du verweigerst den Angriff! Das Opfer wird verschont.",
                effekte={"angriff_verweigert": True},
                state_updates={"teenager_werwolf.hat_verweigert": True},
                log_sichtbar_fuer="werwolf",
            )
        # Delegate to parent for skip handling etc.
        return super().execute_action(action_type, spieler, targets, kontext)

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext, aktion: str = None
    ) -> Optional[AktionsErgebnis]:
        return self.execute_action("teenager_verweigern", spieler, [], kontext)

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Teenager-Werwolf.

        Young, rebellious werewolf with punk/emo styling.
        Hoodie, messy hair, earrings, attitude.
        """
        teen_wolf_features = [
            # Smaller wolf ears (younger)
            *create_wolf_ears(color="#4a2020", scale=0.9),
            # Shorter claws
            *create_claws(color="#2a2a2a", count_per_hand=2),
            # Smaller fangs (still growing)
            AppearanceFeature(
                feature_type="small_fang_left",
                geometry="cone",
                position={"x": -0.03, "y": 1.7, "z": 0.22},
                scale={"x": 0.015, "y": 0.03, "z": 0.015},
                rotation={"x": 170, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#FFFEF0",
                description="Small fang",
            ),
            AppearanceFeature(
                feature_type="small_fang_right",
                geometry="cone",
                position={"x": 0.03, "y": 1.7, "z": 0.22},
                scale={"x": 0.015, "y": 0.03, "z": 0.015},
                rotation={"x": 170, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#FFFEF0",
                description="Small fang",
            ),
            # Orange glowing eyes (rebellious)
            create_glowing_eyes(color="#FF6600", intensity=0.7),
            # Smaller tail
            create_tail("wolf", color="#4a2020"),
            # Messy emo/punk hair
            AppearanceFeature(
                feature_type="emo_hair",
                geometry="sphere",
                position={"x": 0, "y": 2.0, "z": 0.05},
                scale={"x": 0.3, "y": 0.18, "z": 0.28},
                color_source="custom",
                custom_color="#1a1a1a",  # Black hair
                roughness=0.9,
                description="Emo hair",
            ),
            # Hair bangs covering one eye
            AppearanceFeature(
                feature_type="hair_bang",
                geometry="box",
                position={"x": 0.1, "y": 1.9, "z": 0.2},
                scale={"x": 0.12, "y": 0.15, "z": 0.05},
                rotation={"x": 20, "y": 0, "z": -15},
                color_source="custom",
                custom_color="#1a1a1a",
                description="Hair bang",
            ),
            # Hoodie
            AppearanceFeature(
                feature_type="hoodie",
                geometry="box",
                position={"x": 0, "y": 1.15, "z": 0},
                scale={"x": 0.42, "y": 0.5, "z": 0.35},
                color_source="custom",
                custom_color="#2D2D2D",  # Dark gray
                description="Hoodie",
            ),
            # Hood part
            AppearanceFeature(
                feature_type="hood",
                geometry="sphere",
                position={"x": 0, "y": 1.65, "z": -0.15},
                scale={"x": 0.35, "y": 0.25, "z": 0.25},
                color_source="custom",
                custom_color="#2D2D2D",
                description="Hood (down)",
            ),
            # Ripped jeans
            AppearanceFeature(
                feature_type="jeans",
                geometry="box",
                position={"x": 0, "y": 0.55, "z": 0},
                scale={"x": 0.28, "y": 0.5, "z": 0.22},
                color_source="custom",
                custom_color="#2F4F4F",  # Dark slate gray
                description="Ripped jeans",
            ),
            # Ear piercing
            AppearanceFeature(
                feature_type="earring",
                geometry="sphere",
                position={"x": -0.22, "y": 1.85, "z": 0.05},
                scale={"x": 0.02, "y": 0.02, "z": 0.02},
                color_source="custom",
                custom_color="#C0C0C0",
                metallic=True,
                description="Ear piercing",
            ),
            # Sneakers
            AppearanceFeature(
                feature_type="sneaker_left",
                geometry="box",
                position={"x": -0.1, "y": 0.08, "z": 0.05},
                scale={"x": 0.1, "y": 0.08, "z": 0.18},
                color_source="custom",
                custom_color="#FF0000",  # Red sneakers
                description="Sneaker",
            ),
            AppearanceFeature(
                feature_type="sneaker_right",
                geometry="box",
                position={"x": 0.1, "y": 0.08, "z": 0.05},
                scale={"x": 0.1, "y": 0.08, "z": 0.18},
                color_source="custom",
                custom_color="#FF0000",
                description="Sneaker",
            ),
        ]

        return RollenModell(
            modell_id="teenager_werwolf",
            anzeige_name="Teenager-Werwolf",
            beschreibung="Ein rebellischer junger Werwolf mit Punk-Styling",
            body=BodyModification(
                height_multiplier=0.92,  # Shorter - teenager
                slouch_angle=10,
                snout_length=0.2,  # Smaller snout
                claw_hands=True,
                skin_texture="fur",
            ),
            appearance_self_alive=teen_wolf_features,
            appearance_others_alive=teen_wolf_features,
            appearance_dead=create_death_marker(),
            seher_sicht="bad",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.02,
                    sway_speed=0.6,
                    head_tilt_range=25,
                    breathing_visible=True,
                    gesture_chance=0.15,  # Fidgeting
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="rebel_flash",
                    effect_type="glow",
                    glow_color="#FF6600",
                    glow_intensity=0.6,
                    glow_pulse=True,
                ),
            ],
            sound_on_action="teen_growl.mp3",
        )
