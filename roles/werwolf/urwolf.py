"""
Urwolf - Kann Dorfbewohner infizieren.

Der Urwolf kann einmalig statt zu toeten
einen Dorfbewohner infizieren, der zum Werwolf wird.
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
    RollenUI,
    SpielKontext,
    StateField,
    StateType,
    StateVisualEffect,
    GlobalStateDefinition,
    set_spieler_state,
    # Factory functions
    create_wolf_ears,
    create_claws,
    create_fangs,
    create_glowing_eyes,
    create_tail,
    create_aura,
    create_death_marker,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Urwolf(Role):
    """
    Der Urwolf - Infektions-Werwolf.

    Faehigkeiten:
    - Jagt mit den Woelfen
    - Kann einmalig statt Toetung infizieren
    - Infizierte werden zu Werwoelfen

    Gewinnbedingung: Werwolf-Team gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Urwolfs."""
        return [
            StateField(
                "infektion_verfuegbar",
                StateType.BOOL,
                True,
                "Kann noch infizieren",
                icon="fa-solid fa-virus",
            ),
        ]

    def global_state_definitions(self) -> List[GlobalStateDefinition]:
        """Definiert den Infiziert-State der auf andere Spieler gesetzt wird."""
        return [
            GlobalStateDefinition(
                key="global.ist_infiziert",
                name="Infiziert",
                typ=StateType.BOOL,
                beschreibung="Spieler wurde vom Urwolf infiziert",
                visual_effect=StateVisualEffect.INFECTED,
                css_class="infiziert",
                icon="fa-solid fa-virus",
                query_name="infizierte",
                defined_by="Urwolf",
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=20,
            name="Urwolf",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Urwolf. Einmal pro Spiel kannst du statt zu töten "
                "einen Dorfbewohner infizieren. Er wird sofort zum Werwolf!"
            ),
            icon="fa-solid fa-virus",
            farbe="#7f1d1d",
            prioritaet=50,
            erzaehler_nacht=(
                "Der Urwolf jagt mit dem Rudel. Er kann einmalig "
                "ein Opfer infizieren statt zu töten."
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            distribution=DistributionConfig(
                min_players=12,
                count_func=lambda n: 1,
                priority=55,
                exclusive_with=["Werwolf"],
            ),
            avatar_gradient_from="#7f1d1d",
            avatar_gradient_to="#450a0a",
            avatar_border_color="#b91c1c",
            badge_emoji="fa-solid fa-paw",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.INFIZIEREN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def is_group_action(self) -> bool:
        """Urwolf stimmt mit dem Rudel ab."""
        return True

    def is_active_on_first_night(self) -> bool:
        return True

    def is_active_on_every_night(self) -> bool:
        return True

    def get_ui_definition(self) -> "RollenUI":
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Urwolf - Infizieren",
            instructions="Du kannst einmalig das Opfer infizieren statt zu töten.",
            buttons=[
                UIButton(
                    label="Infizieren",
                    action_type="urwolf_infizieren",
                    icon="fa-solid fa-virus",
                    css_class="btn-success",
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
        """Execute Urwolf infection action."""
        # Handle both prefixed and unprefixed action types
        if action_type in ("urwolf_infizieren", "infizieren"):
            if not self.get_state(spieler, "infektion_verfuegbar", True):
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht="Du hast deine Infektion bereits verbraucht!",
                )

            # Mark as used
            self.set_state(spieler, "infektion_verfuegbar", False)

            # The infection effect is applied to the werewolf victim
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du infizierst das Opfer! Es wird zum Werwolf werden.",
                effekte={
                    "urwolf_infiziert": True,
                    "todesursache_verhindert": True,
                    "verwandlung": "Werwolf",
                },
                state_updates={"urwolf.infektion_verfuegbar": False},
                log_sichtbar_fuer="werwolf",
            )
        # Delegate to parent for skip handling etc.
        return super().execute_action(action_type, spieler, targets, kontext)

    def on_nacht_aktion(
        self,
        spieler: "Spieler",
        ziel: Optional["Spieler"],
        kontext: SpielKontext,
        aktion: str = None,
    ) -> Optional[AktionsErgebnis]:
        """Legacy handler - routes to execute_action."""
        return self.execute_action(
            "urwolf_infizieren", spieler, [ziel] if ziel else [], kontext
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Urwolf.

        Ancient, primal wolf with infectious green glow and scarred features.
        """
        urwolf_features = [
            # Ancient wolf ears (larger, more primal)
            *create_wolf_ears(color="#4a0000", scale=1.2),
            # Longer, sharper claws
            *create_claws(color="#1a1a1a", count_per_hand=4),
            # Large fangs
            *create_fangs(color="#FFFEF0"),
            # Sickly green-red glowing eyes
            create_glowing_eyes(color="#88FF00", intensity=0.9),
            # Larger wolf tail
            create_tail("wolf", color="#4a0000"),
            # Infectious green aura
            create_aura(color="#00FF44", intensity=0.3, pulsing=True),
            # Infection pustules/marks
            AppearanceFeature(
                feature_type="infection_mark_1",
                geometry="sphere",
                position={"x": 0.2, "y": 1.3, "z": 0.15},
                scale={"x": 0.04, "y": 0.04, "z": 0.02},
                color_source="custom",
                custom_color="#00FF44",
                emissive=True,
                emissive_intensity=0.5,
                description="Infection mark",
            ),
            AppearanceFeature(
                feature_type="infection_mark_2",
                geometry="sphere",
                position={"x": -0.15, "y": 1.5, "z": 0.12},
                scale={"x": 0.03, "y": 0.03, "z": 0.015},
                color_source="custom",
                custom_color="#00FF44",
                emissive=True,
                emissive_intensity=0.4,
                description="Infection mark",
            ),
            # Scars on face
            AppearanceFeature(
                feature_type="scar",
                geometry="box",
                position={"x": -0.08, "y": 1.85, "z": 0.2},
                scale={"x": 0.12, "y": 0.01, "z": 0.01},
                rotation={"x": 0, "y": 0, "z": -20},
                color_source="custom",
                custom_color="#330000",
                description="Battle scar",
            ),
        ]

        return RollenModell(
            modell_id="urwolf",
            anzeige_name="Urwolf",
            beschreibung="Ein uralter, infektiöser Werwolf mit grünem Leuchten",
            body=BodyModification(
                slouch_angle=20,
                snout_length=0.4,
                claw_hands=True,
                skin_texture="fur",
                brow_ridge=0.5,
                height_multiplier=1.05,
            ),
            appearance_self_alive=urwolf_features,
            appearance_others_alive=urwolf_features,
            appearance_dead=create_death_marker(),
            seher_sicht="bad",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.025,
                    sway_speed=0.6,
                    head_tilt_range=20,
                    breathing_visible=True,
                    tail_wag=True,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="infection_glow",
                    effect_type="particle",
                    particle_type="magic",
                    particle_count=10,
                    particle_color="#00FF44",
                    particle_duration=1.0,
                ),
            ],
            sound_on_action="infection_hiss.mp3",
        )
