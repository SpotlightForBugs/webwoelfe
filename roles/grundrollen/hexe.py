"""
Hexe - Mächtige Rolle mit zwei Tränken.

Die Hexe kann einmal pro Spiel jemanden heilen
und einmal jemanden vergiften.
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
    create_witch_hat,
    create_potion_bottles,
    create_aura,
    create_book,
    create_death_marker,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Hexe(Role):
    """
    Die Hexe - Mächtige Rolle mit zwei Tränken.

    Fähigkeiten:
    - Heiltrank: Kann einmal pro Spiel das Werwolf-Opfer retten
    - Gifttrank: Kann einmal pro Spiel einen Spieler töten

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        return [
            StateField("heiltrank", StateType.BOOL, True, "Heiltrank verfügbar"),
            StateField("gifttrank", StateType.BOOL, True, "Gifttrank verfügbar"),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=4,
            name="Hexe",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist die Hexe. Du hast zwei Tränke: Einen Heiltrank, um das "
                "Werwolf-Opfer zu retten, und einen Gifttrank, um einen Spieler "
                "zu töten. Jeden Trank kannst du nur einmal verwenden."
            ),
            icon="fa-solid fa-flask",
            farbe="#d946ef",
            prioritaet=90,
            erzaehler_nacht=(
                "Die Hexe erwacht. Ich zeige ihr das Opfer der Werwölfe. "
                "Möchtest du es retten? Möchtest du jemanden vergiften?"
            ),
            erweiterung=Erweiterung.BASISSPIEL,
            # Visual Styling
            avatar_gradient_from="#d946ef",
            avatar_gradient_to="#a21caf",
            avatar_border_color="#f0abfc",
            badge_emoji="fas fa-flask",
            distribution=DistributionConfig(
                min_players=5,
                count_func=lambda n: 1,
                priority=90,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE  # Hexe hat mehrere Aktionen

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Hexe acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Hexe acts every night."""
        return True

    @property
    def requires_victim_info(self) -> bool:
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Hexe's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Hexe - Tränke verwenden",
            instructions="Du siehst das Opfer der Werwölfe. Willst du deine Tränke nutzen?",
            buttons=[
                UIButton(
                    label="Heilen",
                    action_type="heilen",
                    icon="fa-solid fa-heart-pulse",
                    css_class="btn-success",
                    requires_confirmation=False,
                ),
                UIButton(
                    label="Vergiften",
                    action_type="vergiften",
                    icon="fa-solid fa-skull-crossbones",
                    css_class="btn-danger",
                    requires_confirmation=True,
                ),
            ],
            requires_target=True,  # For poison
            allow_multiple_targets=False,
            allow_self_target=True,
            can_skip=True,  # Can choose to do nothing
        )

    def get_phase_start_info(
        self, spieler: "Spieler", kontext: "SpielKontext"
    ) -> Optional[dict]:
        """Zeigt der Hexe das Werwolf-Opfer."""
        if kontext.werwolf_opfer_id:
            return {"werwolf_opfer_id": kontext.werwolf_opfer_id}
        return None

    def on_nacht_aktion(
        self,
        spieler: "Spieler",
        ziel: Optional["Spieler"],
        kontext: SpielKontext,
        aktion: str = None,
    ) -> Optional[AktionsErgebnis]:
        """
        Hexe verwendet einen Trank.
        """
        # Mapping legacy action names if necessary
        # UI uses "action_type": "heilen" or "vergiften"
        # app.py passes this as 'aktion'

        if aktion == "heilen" or aktion == "hexe_heilen":
            if not self.get_state(spieler, "heiltrank"):
                return AktionsErgebnis(False, "Du hast keinen Heiltrank mehr.")

            # Ziel ist das Werwolf-Opfer
            opfer_id = kontext.werwolf_opfer_id
            if not opfer_id:
                return AktionsErgebnis(False, "Es gibt kein Opfer zu heilen.")

            # Wenn Ziel übergeben wurde, muss es das Opfer sein
            if ziel and ziel.id != opfer_id:
                return AktionsErgebnis(False, "Du kannst nur das Werwolf-Opfer heilen.")

            self.set_state(spieler, "heiltrank", False)
            return AktionsErgebnis(
                True,
                "Du hast das Opfer geheilt.",
                ziel_spieler_id=opfer_id,
                effekte={
                    "hexe_heilen": True,
                    "heiltrank_verbraucht": True,
                },
                multi_target_updates={opfer_id: {"global.ist_beschuetzt": True}},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        elif (
            aktion == "vergiften"
            or aktion == "hexe_vergiften"
            or aktion == "toeten"
            or aktion == "hexe_toeten"
        ):
            if not self.get_state(spieler, "gifttrank"):
                return AktionsErgebnis(False, "Du hast keinen Gifttrank mehr.")

            if not ziel:
                return AktionsErgebnis(False, "Du musst ein Ziel wählen.")

            self.set_state(spieler, "gifttrank", False)
            return AktionsErgebnis(
                True,
                f"Du hast {ziel.name} vergiftet.",
                ziel_spieler_id=ziel.id,
                effekte={
                    "toeten": ziel.id,
                    "todesursache": "hexentrank",
                    "hero_kill": True,
                    "hexe_vergiften": True,
                    "gifttrank_verbraucht": True,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        # Handle skip action
        elif aktion == "skip" or aktion == "nichts" or aktion is None:
            return AktionsErgebnis(
                True,
                "Du hast nichts getan.",
                effekte={"skip": True, "aktion_ausgefuehrt": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        # Unknown action - return error instead of None to prevent phase hang
        return AktionsErgebnis(
            False,
            f"Unbekannte Aktion: {aktion}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Hexe.

        Features:
        - Classic witch hat with brim
        - Two potion bottles on belt (green heal, purple poison)
        - Spell book
        - Dark mystical aura
        - Bubbling cauldron effect
        """
        # Check potion states for dynamic appearance
        has_heal = self.get_state(spieler, "heiltrank", True)
        has_poison = self.get_state(spieler, "gifttrank", True)

        # Dynamic potion colors based on availability
        potion_colors = []
        potion_positions = []
        if has_heal:
            potion_colors.append("#00FF88")  # Green heal
            potion_positions.append("left")
        if has_poison:
            potion_colors.append("#CC00FF")  # Purple poison
            potion_positions.append("right")

        hexe_features = [
            # Classic witch hat with brim
            *create_witch_hat(color="#1a1a1a", brim=True),
            # Spell book in left hand
            *create_book(color="#2a1a3a", glowing=True),
            # Dark mystical aura
            create_aura(color="#9900FF", intensity=0.3, pulsing=True),
            # Long dark robes
            AppearanceFeature(
                feature_type="robe",
                geometry="cone",
                position={"x": 0, "y": 0.7, "z": 0},
                scale={"x": 0.42, "y": 1.15, "z": 0.38},
                color_source="custom",
                custom_color="#1a0a1a",
                roughness=0.9,
                description="Dark witch robes",
            ),
            # Gnarled nose (subtle)
            AppearanceFeature(
                feature_type="witch_nose",
                geometry="cone",
                position={"x": 0, "y": 1.82, "z": 0.25},
                scale={"x": 0.03, "y": 0.06, "z": 0.04},
                rotation={"x": -30, "y": 0, "z": 0},
                color_source="skin",
                description="Witch nose",
            ),
        ]

        # Add potions based on what's available
        if potion_positions:
            hexe_features.extend(create_potion_bottles(potion_positions, potion_colors))

        # Add bubbling particles if any potion available
        if has_heal or has_poison:
            hexe_features.append(
                AppearanceFeature(
                    feature_type="potion_bubbles",
                    geometry="sphere",
                    position={"x": 0.35 if has_poison else -0.35, "y": 0.85, "z": 0.2},
                    scale={"x": 0.03, "y": 0.03, "z": 0.03},
                    color_source="custom",
                    custom_color="#CC00FF" if has_poison else "#00FF88",
                    emissive=True,
                    emissive_intensity=0.8,
                    opacity=0.7,
                    animation="float",
                    animation_speed=2.0,
                    particle_effect="magic",
                    particle_color="#CC00FF" if has_poison else "#00FF88",
                    particle_rate=5.0,
                    description="Bubbling potion effect",
                )
            )

        return RollenModell(
            modell_id="hexe",
            anzeige_name="Hexe",
            beschreibung="Eine mächtige Hexe mit Zaubertränken und Grimoire",
            body=BodyModification(
                height_multiplier=0.92,
                hunch_back=True,
                slouch_angle=8,
                skin_texture="smooth",
            ),
            appearance_self_alive=hexe_features,
            appearance_others_alive=hexe_features,
            appearance_dead=create_death_marker(),
            seher_sicht="good",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.015,
                    sway_speed=0.4,
                    head_tilt_range=12,
                    look_around=True,
                    blink_rate=2.0,
                    breathing_visible=True,
                    gesture_chance=0.1,
                ),
                "brewing": AnimationState(
                    state_name="brewing",
                    sway_amplitude=0.02,
                    bob_amplitude=0.01,
                    bob_speed=0.5,
                    gesture_chance=0.3,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="aura_glow",
                    effect_type="glow",
                    glow_color="#9900FF",
                    glow_intensity=0.8,
                    glow_pulse=True,
                ),
                HintEffect3D(
                    effect_id="suspicious_behavior",
                    effect_type="shake",
                    shake_intensity=0.05,
                    shake_duration=0.3,
                ),
            ],
            sound_on_action="potion_bubble.mp3",
            sound_ambient="cauldron_simmer.mp3",
        )
