"""
Wolfsjunge - Wird zum Werwolf wenn Vorbild stirbt.

Der Wolfsjunge waehlt in der ersten Nacht ein Vorbild.
Stirbt dieses, verwandelt er sich in einen Werwolf.
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
class Wolfsjunge(Role):
    """
    Das Wolfsjunge (Wildes Kind) - Bedingte Verwandlung.

    Faehigkeiten:
    - Waehlt in der ersten Nacht ein Vorbild
    - Stirbt das Vorbild: Wird zum Werwolf
    - Solange Vorbild lebt: Teil des Dorfes

    Gewinnbedingung: Abhaengig von Verwandlung.
    """

    def state_fields(self) -> List[StateField]:
        return [
            StateField(
                "vorbild_id", StateType.PLAYER_ID, None, "ID des Vorbilds", icon="👤"
            ),
            StateField(
                "verwandelt", StateType.BOOL, False, "Zum Werwolf verwandelt", icon="🐺"
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=124,
            name="Wolfsjunge",
            team=Team.DORF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist das Wolfsjunge. Du wählst in der ersten Nacht ein "
                "Vorbild. Solange dein Vorbild lebt, gehörst du zum Dorf. "
                "Stirbt dein Vorbild, wirst du zum Werwolf!"
            ),
            icon="fa-solid fa-paw",
            farbe="#b91c1c",
            prioritaet=6,
            erzaehler_nacht=(
                "Das Wolfsjunge erwacht und wählt sein Vorbild. "
                "Stirbt dieses, wird das Junge zum Werwolf."
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            distribution=DistributionConfig(
                min_players=10,
                count_func=lambda n: 1,
                priority=35,
            ),
            avatar_gradient_from="#a16207",
            avatar_gradient_to="#713f12",
            avatar_border_color="#ca8a04",
            badge_emoji="🐾",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.WAEHLEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.DORF

    def is_active_on_first_night(self) -> bool:
        return True

    def is_active_on_every_night(self) -> bool:
        return False

    def get_ui_definition(self) -> "RollenUI":
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Wolfsjunge - Vorbild wählen",
            instructions="Wähle dein Vorbild. Wenn es stirbt, wirst du zum Werwolf.",
            buttons=[
                UIButton(
                    label="Vorbild wählen",
                    action_type="wolfsjunge_waehlen",
                    icon="fa-solid fa-paw",
                    css_class="btn-primary",
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
        if action_type == "wolfsjunge_waehlen":
            if kontext.runde != 1:
                return AktionsErgebnis(
                    erfolg=False, nachricht="Du hast dein Vorbild bereits gewählt."
                )

            if not targets:
                return AktionsErgebnis(
                    erfolg=False, nachricht="Du musst ein Vorbild wählen!"
                )

            ziel = targets[0]
            if ziel.id == spieler.id:
                return AktionsErgebnis(
                    erfolg=False, nachricht="Du kannst dich nicht selbst wählen."
                )

            self.set_state(spieler, "vorbild_id", ziel.id)
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"{ziel.name} ist nun dein Vorbild!",
                ziel_spieler_id=ziel.id,
                effekte={"vorbild_gewaehlt": ziel.id},
                state_updates={"wolfsjunge.vorbild_id": ziel.id},
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
            "wolfsjunge_waehlen", spieler, [ziel] if ziel else [], kontext
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        gestorbener: "Spieler",
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        vorbild_id = self.get_state(spieler, "vorbild_id")
        if vorbild_id and gestorbener.id == vorbild_id:
            self.set_state(spieler, "verwandelt", True)
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Dein Vorbild ist tot! Du verwandelst dich in einen WERWOLF!",
                effekte={"verwandlung": "Werwolf", "team_wechsel": Team.WERWOLF.value},
                state_updates={"wolfsjunge.verwandelt": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Wolfsjunge.

        Before: Young boy/girl with wolf-like features (cute but feral)
        After: Young werewolf (smaller than adult wolves)
        """
        is_transformed = self.get_state(spieler, "verwandelt")

        if is_transformed:
            # TRANSFORMED - Young werewolf
            wolf_features = [
                *create_wolf_ears(color="#5C4033", scale=0.9),  # Slightly smaller ears
                *create_claws(color="#1a1a1a", count_per_hand=3),
                *create_fangs(color="#FFFEF0"),
                create_glowing_eyes(color="#FF6600", intensity=0.8),
                create_tail("wolf", color="#5C4033"),
                # Simple torn clothes remnant
                AppearanceFeature(
                    feature_type="torn_shirt",
                    geometry="box",
                    position={"x": 0, "y": 1.1, "z": 0},
                    scale={"x": 0.3, "y": 0.25, "z": 0.22},
                    color_source="custom",
                    custom_color="#4a4a4a",
                    roughness=0.9,
                    description="Torn shirt",
                ),
            ]

            return RollenModell(
                modell_id="wolfsjunge_wolf",
                anzeige_name="Wolfsjunge (Werwolf)",
                beschreibung="Ein junger Werwolf voller Wut",
                body=BodyModification(
                    height_multiplier=0.85,  # Smaller - young
                    slouch_angle=15,
                    snout_length=0.25,
                    claw_hands=True,
                    skin_texture="fur",
                ),
                appearance_self_alive=wolf_features,
                appearance_others_alive=wolf_features,
                appearance_dead=create_death_marker(),
                seher_sicht="bad",
                animations={
                    "idle": AnimationState(
                        state_name="idle",
                        sway_amplitude=0.02,
                        sway_speed=0.8,
                        breathing_visible=True,
                        tail_wag=True,
                    ),
                },
                hint_effects=[
                    HintEffect3D(
                        effect_id="young_rage",
                        effect_type="glow",
                        glow_color="#FF6600",
                        glow_intensity=0.8,
                    ),
                ],
                sound_on_action="young_wolf_howl.mp3",
            )
        else:
            # NOT TRANSFORMED - Young child with subtle wolf traits
            child_features = [
                # Messy hair with subtle wolf-like widow's peak
                AppearanceFeature(
                    feature_type="hair",
                    geometry="sphere",
                    position={"x": 0, "y": 1.95, "z": -0.03},
                    scale={"x": 0.28, "y": 0.15, "z": 0.25},
                    color_source="custom",
                    custom_color="#4a3520",
                    roughness=0.9,
                    description="Messy hair",
                ),
                # Simple child clothing
                AppearanceFeature(
                    feature_type="shirt",
                    geometry="box",
                    position={"x": 0, "y": 1.1, "z": 0},
                    scale={"x": 0.28, "y": 0.35, "z": 0.2},
                    color_source="custom",
                    custom_color="#5C7A3D",  # Forest green
                    description="Child's shirt",
                ),
                AppearanceFeature(
                    feature_type="pants",
                    geometry="box",
                    position={"x": 0, "y": 0.55, "z": 0},
                    scale={"x": 0.25, "y": 0.45, "z": 0.18},
                    color_source="custom",
                    custom_color="#4a3520",
                    description="Child's pants",
                ),
                # Subtle amber eyes (hint of wolf)
                AppearanceFeature(
                    feature_type="eye_glow",
                    geometry="sphere",
                    position={"x": 0, "y": 1.8, "z": 0.18},
                    scale={"x": 0.12, "y": 0.04, "z": 0.03},
                    color_source="custom",
                    custom_color="#CCAA00",
                    opacity=0.15,
                    emissive=True,
                    emissive_intensity=0.15,
                    description="Subtle amber eyes",
                ),
                # Paw print mark on cheek (birthmark)
                AppearanceFeature(
                    feature_type="paw_mark",
                    geometry="sphere",
                    position={"x": 0.12, "y": 1.78, "z": 0.18},
                    scale={"x": 0.03, "y": 0.03, "z": 0.01},
                    color_source="custom",
                    custom_color="#8B4513",
                    opacity=0.4,
                    description="Paw-shaped birthmark",
                ),
            ]

            return RollenModell(
                modell_id="wolfsjunge",
                anzeige_name="Wolfsjunge",
                beschreibung="Ein Kind mit versteckter wilder Seite",
                body=BodyModification(
                    height_multiplier=0.8,  # Child size
                    width_multiplier=0.85,
                    skin_texture="smooth",
                ),
                appearance_self_alive=child_features,
                appearance_others_alive=child_features,
                appearance_dead=create_death_marker(),
                seher_sicht="good",
                animations={
                    "idle": AnimationState(
                        state_name="idle",
                        sway_amplitude=0.015,
                        sway_speed=0.6,
                        head_tilt_range=25,
                        look_around=True,
                        blink_rate=3.5,
                        breathing_visible=True,
                    ),
                },
                hint_effects=[
                    HintEffect3D(
                        effect_id="feral_glance",
                        effect_type="transform",
                        rotate_to={"x": 0, "y": 25, "z": 0},
                    ),
                ],
            )
