"""
Einsamer Wolf - Der Solo-Werwolf.

Der Einsame Wolf kennt die anderen Wölfe nicht
und jagt alleine. Er gewinnt nur als letzter Wolf.
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
)
from ..enums import Team, Kategorie, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class EinsamerWolf(Role):
    """
    Einsamer Wolf - Solo-Werwolf.

    Fähigkeiten:
    - Jagt alleine (nicht mit anderen Wölfen)
    - Kennt die anderen Wölfe nicht
    - Die anderen Wölfe kennen ihn nicht

    Besonderheiten:
    - Erscheint für Seherin als Werwolf
    - Gewinnt nur wenn er letzter Wolf ist

    Gewinnbedingung: Als letzter überlebender Werwolf gewinnen.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=30,
            name="Einsamer Wolf",
            team=Team.SOLO,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Einsame Wolf. Du kennst die anderen Wölfe nicht "
                "und sie kennen dich nicht. Du tötest alleine und gewinnst nur, "
                "wenn DU der letzte Wolf bist!"
            ),
            icon="fa-solid fa-paw",
            farbe="#4c1d95",
            prioritaet=48,
            erzaehler_nacht="Der Einsame Wolf erwacht separat und wählt sein eigenes Opfer.",
            erweiterung=Erweiterung.COMMUNITY,
            avatar_gradient_from="#4c1d95",
            avatar_gradient_to="#2e1065",
            avatar_border_color="#6d28d9",
            badge_emoji="🐺",
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import AktionsTyp

        return AktionsTyp.TOETEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"

    def is_active_on_first_night(self) -> bool:
        return True

    def is_active_on_every_night(self) -> bool:
        return True

    def get_ui_definition(self) -> "RollenUI":
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Einsamer Wolf - Alleine jagen",
            instructions="Wähle dein Opfer. Du jagst alleine.",
            buttons=[
                UIButton(
                    label="Angreifen",
                    action_type="einsamer_wolf_angriff",
                    icon="fa-solid fa-paw",
                    css_class="btn-danger",
                )
            ],
            requires_target=True,
            can_skip=True,
        )

    def execute_action(
        self,
        action_type: str,
        spieler: "Spieler",
        targets: List["Spieler"],
        kontext: "SpielKontext",
    ) -> Optional[AktionsErgebnis]:
        if action_type == "einsamer_wolf_angriff":
            if not targets:
                return AktionsErgebnis(
                    erfolg=True,
                    nachricht="Du schleichst durch die Nacht, findest aber kein Opfer.",
                )

            ziel = targets[0]
            if ziel.id in kontext.tote_spieler:
                return AktionsErgebnis(
                    erfolg=False, nachricht="Dieses Ziel ist bereits tot."
                )

            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"Du greifst {ziel.name} alleine an!",
                ziel_spieler_id=ziel.id,
                effekte={
                    "toeten": ziel.id,
                    "todesursache": "einsamer_wolf",
                },
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
            "einsamer_wolf_angriff", spieler, [ziel] if ziel else [], kontext
        )

    def gewinnt_mit_woelfen(self) -> bool:
        return False

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Einsamer Wolf.

        Dark purple/black solitary wolf with a haunted, lonely appearance.
        Scarred, weathered, with shadow aura.
        """
        einsamer_features = [
            # Dark wolf ears
            *create_wolf_ears(color="#2D1B4E", scale=1.05),
            # Dark claws
            *create_claws(color="#1a1a1a", count_per_hand=3),
            # Yellowed fangs (old warrior)
            *create_fangs(color="#F5F5DC"),
            # Purple/violet glowing eyes
            create_glowing_eyes(color="#9932CC", intensity=0.85),
            # Dark tail
            create_tail("wolf", color="#2D1B4E"),
            # Shadow aura
            create_aura(color="#4B0082", intensity=0.25, pulsing=False),
            # Battle scars
            AppearanceFeature(
                feature_type="scar_face",
                geometry="box",
                position={"x": 0.1, "y": 1.88, "z": 0.2},
                scale={"x": 0.15, "y": 0.015, "z": 0.01},
                rotation={"x": 0, "y": 0, "z": -15},
                color_source="custom",
                custom_color="#4a0020",
                description="Face scar",
            ),
            AppearanceFeature(
                feature_type="scar_shoulder",
                geometry="box",
                position={"x": -0.25, "y": 1.35, "z": 0.1},
                scale={"x": 0.02, "y": 0.12, "z": 0.01},
                rotation={"x": 0, "y": 0, "z": 25},
                color_source="custom",
                custom_color="#4a0020",
                description="Shoulder scar",
            ),
            # Torn ear
            AppearanceFeature(
                feature_type="torn_ear_notch",
                geometry="sphere",
                position={"x": 0.2, "y": 2.32, "z": -0.05},
                scale={"x": 0.03, "y": 0.03, "z": 0.03},
                color_source="custom",
                custom_color="#1a1a1a",  # Black notch in ear
                description="Torn ear notch",
            ),
            # Lone wolf marking on chest
            AppearanceFeature(
                feature_type="chest_marking",
                geometry="sphere",
                position={"x": 0, "y": 1.25, "z": 0.2},
                scale={"x": 0.1, "y": 0.08, "z": 0.02},
                color_source="custom",
                custom_color="#3D1B5E",
                opacity=0.6,
                description="Chest marking",
            ),
            # Shadow wisps
            AppearanceFeature(
                feature_type="shadow_wisp_1",
                geometry="cylinder",
                position={"x": -0.3, "y": 0.4, "z": -0.2},
                scale={"x": 0.04, "y": 0.2, "z": 0.04},
                rotation={"x": 15, "y": 0, "z": -20},
                color_source="custom",
                custom_color="#1a0a2e",
                opacity=0.4,
                animation="sway",
                animation_speed=0.3,
                description="Shadow wisp",
            ),
            AppearanceFeature(
                feature_type="shadow_wisp_2",
                geometry="cylinder",
                position={"x": 0.25, "y": 0.5, "z": -0.25},
                scale={"x": 0.03, "y": 0.18, "z": 0.03},
                rotation={"x": 10, "y": 0, "z": 15},
                color_source="custom",
                custom_color="#1a0a2e",
                opacity=0.35,
                animation="sway",
                animation_speed=0.4,
                description="Shadow wisp",
            ),
        ]

        return RollenModell(
            modell_id="einsamer_wolf",
            anzeige_name="Einsamer Wolf",
            beschreibung="Ein einsamer, vernarbter Wolf der Schatten",
            body=BodyModification(
                slouch_angle=18,
                snout_length=0.32,
                claw_hands=True,
                skin_texture="fur",
                skin_color_override="#2D1B3D",
                height_multiplier=1.02,
                brow_ridge=0.4,
            ),
            appearance_self_alive=einsamer_features,
            appearance_others_alive=einsamer_features,
            appearance_dead=create_death_marker(),
            seher_sicht="bad",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.01,
                    sway_speed=0.35,
                    head_tilt_range=12,
                    breathing_visible=True,
                    tail_wag=False,  # Too dignified
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="shadow_pulse",
                    effect_type="glow",
                    glow_color="#4B0082",
                    glow_intensity=0.5,
                    glow_pulse=True,
                ),
            ],
            sound_on_action="lone_howl.mp3",
        )
