"""
Wildes Kind - Wird zum Werwolf wenn Vorbild stirbt.

Das Wilde Kind wählt in der ersten Nacht ein Vorbild.
Stirbt dieses, verwandelt es sich in einen Werwolf.
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
    create_aura,
    create_death_marker,
    DistributionConfig,
)
from ..enums import Team, Kategorie, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class WildesKind(Role):
    """
    Wildes Kind - Bedingte Verwandlungsrolle.

    Fähigkeiten:
    - Wählt in der ersten Nacht ein Vorbild
    - Solange Vorbild lebt: Dorfbewohner
    - Stirbt Vorbild: Wird zum Werwolf

    Besonderheiten:
    - Startet im Dorf-Team
    - Team wechselt bei Verwandlung
    - Nach Verwandlung: Jagt mit den Wölfen

    Gewinnbedingung: Abhängig von der Verwandlung.
    """

    def state_fields(self) -> List[StateField]:
        return [
            StateField(
                "vorbild_id",
                StateType.PLAYER_ID,
                None,
                "ID des Vorbilds",
                icon="fa-solid fa-user",
            ),
            StateField(
                "verwandelt",
                StateType.BOOL,
                False,
                "Zum Werwolf verwandelt",
                icon="fa-solid fa-paw",
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=25,
            name="Wildes Kind",
            team=Team.DORF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist das Wilde Kind. Du wählst in der ersten Nacht ein "
                "Vorbild. Solange dein Vorbild lebt, gehörst du zum Dorf. "
                "Stirbt dein Vorbild, wirst du zum Werwolf!"
            ),
            icon="fa-solid fa-child-reaching",
            farbe="#a16207",
            prioritaet=6,
            erzaehler_nacht=(
                "Das Wilde Kind erwacht und wählt sein Vorbild. "
                "Stirbt dieses, wird das Kind zum Werwolf."
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
            badge_emoji="fa-solid fa-paw",
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import AktionsTyp
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
            title="Wildes Kind - Vorbild wählen",
            instructions="Wähle dein Vorbild. Wenn es stirbt, wirst du zum Werwolf.",
            buttons=[
                UIButton(
                    label="Vorbild wählen",
                    action_type="wildes_kind_waehlen",
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
        # Handle both prefixed and unprefixed action types
        if action_type in ("wildes_kind_waehlen", "waehlen"):
            if kontext.runde != 1:
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht="Du hast dein Vorbild bereits gewählt.",
                )

            if not targets:
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht="Du musst ein Vorbild wählen!",
                )

            ziel = targets[0]
            if ziel.id == spieler.id:
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht="Du kannst dich nicht selbst als Vorbild wählen.",
                )

            self.set_state(spieler, "vorbild_id", ziel.id)

            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"{ziel.name} ist nun dein Vorbild!",
                ziel_spieler_id=ziel.id,
                effekte={"vorbild_gewaehlt": ziel.id},
                state_updates={"wildes_kind.vorbild_id": ziel.id},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        # Delegate to parent for skip handling etc.
        return super().execute_action(action_type, spieler, targets, kontext)

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext, aktion: str = None
    ) -> Optional[AktionsErgebnis]:
        """Direct handling - don't call execute_action to avoid recursion."""
        if kontext.runde != 1:
            return AktionsErgebnis(erfolg=False, nachricht="Du hast dein Vorbild bereits gewählt.")
        if not ziel:
            return AktionsErgebnis(erfolg=False, nachricht="Du musst ein Vorbild wählen!")
        if ziel.id == spieler.id:
            return AktionsErgebnis(erfolg=False, nachricht="Du kannst dich nicht selbst wählen.")
        self.set_state(spieler, "vorbild_id", ziel.id)
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} ist nun dein Vorbild!",
            ziel_spieler_id=ziel.id,
            effekte={"vorbild_gewaehlt": ziel.id},
            state_updates={"wildes_kind.vorbild_id": ziel.id},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        gestorbener: "Spieler",
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """Wenn das Vorbild stirbt, wird das Wilde Kind zum Werwolf."""
        vorbild_id = self.get_state(spieler, "vorbild_id")

        if vorbild_id and gestorbener.id == vorbild_id:
            self.set_state(spieler, "verwandelt", True)
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Dein Vorbild ist tot! Deine Wut verwandelt dich in einen WERWOLF!",
                effekte={
                    "verwandlung": "Werwolf",
                    "team_wechsel": Team.WERWOLF.value,
                },
                state_updates={"wildes_kind.verwandelt": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Wildes Kind.

        Before transformation: Feral child (Mowgli-like) with wild hair, animal skins
        After transformation: Full werewolf with remnants of wild child appearance
        """
        is_transformed = self.get_state(spieler, "verwandelt")

        if is_transformed:
            # TRANSFORMED - Full werewolf with wild child remnants
            transformed_features = [
                *create_wolf_ears(color="#5C4033", scale=1.1),
                *create_claws(color="#1a1a1a", count_per_hand=4),
                *create_fangs(color="#FFFEF0"),
                create_glowing_eyes(color="#FFAA00", intensity=0.9),
                create_tail("wolf", color="#5C4033"),
                # Torn animal skin loincloth remnant
                AppearanceFeature(
                    feature_type="loincloth",
                    geometry="box",
                    position={"x": 0, "y": 0.85, "z": 0},
                    scale={"x": 0.35, "y": 0.2, "z": 0.3},
                    color_source="custom",
                    custom_color="#8B4513",
                    roughness=0.9,
                    description="Torn loincloth",
                ),
                # Wild tangled hair
                AppearanceFeature(
                    feature_type="wild_hair",
                    geometry="sphere",
                    position={"x": 0, "y": 2.15, "z": -0.1},
                    scale={"x": 0.35, "y": 0.2, "z": 0.3},
                    color_source="custom",
                    custom_color="#3D2314",
                    roughness=1.0,
                    description="Wild tangled hair",
                ),
                # Rage aura
                create_aura(color="#FF4400", intensity=0.4, pulsing=True),
            ]

            return RollenModell(
                modell_id="wildes_kind_wolf",
                anzeige_name="Wildes Kind (Werwolf)",
                beschreibung="Das wilde Kind hat sich in einen wütenden Werwolf verwandelt",
                body=BodyModification(
                    slouch_angle=18,
                    snout_length=0.35,
                    claw_hands=True,
                    skin_texture="fur",
                    height_multiplier=1.0,
                ),
                appearance_self_alive=transformed_features,
                appearance_others_alive=transformed_features,
                appearance_dead=create_death_marker(),
                seher_sicht="bad",
                animations={
                    "idle": AnimationState(
                        state_name="idle",
                        sway_amplitude=0.025,
                        sway_speed=0.8,
                        head_tilt_range=25,
                        breathing_visible=True,
                        tail_wag=True,
                    ),
                },
                hint_effects=[
                    HintEffect3D(
                        effect_id="rage_glow",
                        effect_type="glow",
                        glow_color="#FF4400",
                        glow_intensity=1.0,
                        glow_pulse=True,
                    ),
                ],
                sound_on_action="angry_howl.mp3",
            )
        else:
            # NOT TRANSFORMED - Feral child / Mowgli appearance
            child_features = [
                # Wild messy hair
                AppearanceFeature(
                    feature_type="wild_hair",
                    geometry="sphere",
                    position={"x": 0, "y": 2.0, "z": -0.05},
                    scale={"x": 0.32, "y": 0.18, "z": 0.28},
                    color_source="custom",
                    custom_color="#3D2314",  # Dark brown
                    roughness=1.0,
                    description="Wild messy hair",
                ),
                # Hair strand left
                AppearanceFeature(
                    feature_type="hair_strand_left",
                    geometry="cylinder",
                    position={"x": -0.18, "y": 1.9, "z": 0.05},
                    scale={"x": 0.04, "y": 0.15, "z": 0.04},
                    rotation={"x": 0, "y": 0, "z": -30},
                    color_source="custom",
                    custom_color="#3D2314",
                    description="Hair strand",
                ),
                # Hair strand right
                AppearanceFeature(
                    feature_type="hair_strand_right",
                    geometry="cylinder",
                    position={"x": 0.18, "y": 1.9, "z": 0.05},
                    scale={"x": 0.04, "y": 0.15, "z": 0.04},
                    rotation={"x": 0, "y": 0, "z": 30},
                    color_source="custom",
                    custom_color="#3D2314",
                    description="Hair strand",
                ),
                # Animal skin loincloth
                AppearanceFeature(
                    feature_type="loincloth",
                    geometry="box",
                    position={"x": 0, "y": 0.75, "z": 0},
                    scale={"x": 0.32, "y": 0.25, "z": 0.28},
                    color_source="custom",
                    custom_color="#8B4513",
                    roughness=0.9,
                    description="Animal skin loincloth",
                ),
                # Bare chest with dirt/mud marks
                AppearanceFeature(
                    feature_type="mud_mark_1",
                    geometry="sphere",
                    position={"x": 0.1, "y": 1.2, "z": 0.15},
                    scale={"x": 0.05, "y": 0.03, "z": 0.02},
                    color_source="custom",
                    custom_color="#5C4033",
                    opacity=0.6,
                    description="Mud mark",
                ),
                AppearanceFeature(
                    feature_type="mud_mark_2",
                    geometry="sphere",
                    position={"x": -0.08, "y": 1.35, "z": 0.12},
                    scale={"x": 0.04, "y": 0.025, "z": 0.02},
                    color_source="custom",
                    custom_color="#5C4033",
                    opacity=0.5,
                    description="Mud mark",
                ),
                # Leaf/twig in hair
                AppearanceFeature(
                    feature_type="twig",
                    geometry="cylinder",
                    position={"x": 0.15, "y": 2.05, "z": 0.1},
                    scale={"x": 0.015, "y": 0.12, "z": 0.015},
                    rotation={"x": 30, "y": 45, "z": 20},
                    color_source="custom",
                    custom_color="#228B22",
                    description="Twig in hair",
                ),
                # Bare feet (no shoes)
                AppearanceFeature(
                    feature_type="foot_left",
                    geometry="box",
                    position={"x": -0.1, "y": 0.05, "z": 0.05},
                    scale={"x": 0.08, "y": 0.05, "z": 0.15},
                    color_source="skin",
                    description="Bare foot",
                ),
                AppearanceFeature(
                    feature_type="foot_right",
                    geometry="box",
                    position={"x": 0.1, "y": 0.05, "z": 0.05},
                    scale={"x": 0.08, "y": 0.05, "z": 0.15},
                    color_source="skin",
                    description="Bare foot",
                ),
                # Subtle wild eyes (yellow tint)
                AppearanceFeature(
                    feature_type="eye_glow",
                    geometry="sphere",
                    position={"x": 0, "y": 1.85, "z": 0.2},
                    scale={"x": 0.15, "y": 0.05, "z": 0.05},
                    color_source="custom",
                    custom_color="#CCAA00",
                    opacity=0.2,
                    emissive=True,
                    emissive_intensity=0.2,
                    description="Feral eye hint",
                ),
            ]

            return RollenModell(
                modell_id="wildes_kind",
                anzeige_name="Wildes Kind",
                beschreibung="Ein verwildertes Kind das im Wald aufwuchs",
                body=BodyModification(
                    height_multiplier=0.85,  # Smaller - it's a child
                    width_multiplier=0.9,
                    skin_texture="smooth",
                ),
                appearance_self_alive=child_features,
                appearance_others_alive=child_features,
                appearance_dead=create_death_marker(),
                seher_sicht="good",
                animations={
                    "idle": AnimationState(
                        state_name="idle",
                        sway_amplitude=0.02,
                        sway_speed=0.7,
                        head_tilt_range=30,
                        look_around=True,
                        blink_rate=3.5,
                        breathing_visible=True,
                        gesture_chance=0.15,
                    ),
                },
                hint_effects=[
                    HintEffect3D(
                        effect_id="wild_glance",
                        effect_type="transform",
                        rotate_to={"x": 0, "y": 30, "z": 0},
                    ),
                ],
                sound_on_action="child_growl.mp3",
            )
