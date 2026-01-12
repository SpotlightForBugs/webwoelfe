"""
Werwolf - Die Hauptrolle des Werwolf-Teams.

Werwölfe erkennen sich gegenseitig und wählen
jede Nacht gemeinsam ein Opfer aus.
"""

from typing import Optional, TYPE_CHECKING, List
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
    # Factory functions
    create_wolf_ears,
    create_claws,
    create_fangs,
    create_glowing_eyes,
    create_tail,
    create_death_marker,
)
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Werwolf(Role):
    """
    Standard-Werwolf.

    Fähigkeiten:
    - Erkennt alle anderen Werwölfe
    - Wählt jede Nacht ein Opfer mit dem Rudel

    Gewinnbedingung: Werwölfe sind in Überzahl oder gleichauf.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=2,
            name="Werwolf",
            team=Team.WERWOLF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist ein Werwolf! Jede Nacht ermordest du gemeinsam mit "
                "deinen Werwolf-Gefährten einen Dorfbewohner. Bleibe unentdeckt!"
            ),
            icon="fa-solid fa-paw",
            farbe="#dc2626",
            prioritaet=50,
            erzaehler_nacht=(
                "Die Werwölfe erwachen, erkennen sich und wählen "
                "gemeinsam ein Opfer aus."
            ),
            erweiterung=Erweiterung.BASISSPIEL,
            # Visual Styling
            avatar_gradient_from="#b91c1c",
            avatar_gradient_to="#7f1d1d",
            avatar_border_color="#ef4444",
            badge_emoji="🐺",
            distribution=DistributionConfig(
                min_players=5,
                # ~20% Werwölfe, min 1
                count_func=lambda n: max(1, int(n * 0.20)),
                min_role_count=1,
                max_role_count=None,
                priority=50,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"  # Kann sich nicht selbst töten

    @property
    def basis_hinweis_chance(self) -> float:
        return 0.15  # Höhere Chance für verdächtige Hinweise

    @property
    def is_group_action(self) -> bool:
        """Werwölfe stimmen gemeinsam ab."""
        return True

    @property
    def shared_phase_name(self) -> str:
        """Alle Werwolf-Varianten teilen sich die werwolf_phase."""
        return "werwolf_phase"

    def is_active_on_first_night(self) -> bool:
        """Werwolf acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Werwolf acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Werwolf's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Werwolf - Opfer wählen",
            instructions="Wähle gemeinsam mit den anderen Werwölfen ein Opfer.",
            buttons=[
                UIButton(
                    label="Töten",
                    action_type="toeten",
                    icon="fa-solid fa-paw",
                    css_class="btn-danger",
                    requires_confirmation=True,
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,  # Must vote
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Werwolf-Aktion: Ziel zum Fressen auswählen.

        Hinweis: Die eigentliche Tötung passiert am Ende der Nacht,
        damit Hexe/Heiler noch eingreifen können.
        """
        # Check if already voted
        if self.has_voted_this_phase(spieler, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast bereits gewählt.",
            )

        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Die Werwölfe müssen ein Opfer wählen.",
            )

        # Check if target is valid (not self)
        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel gewählt.",
            )

        # Check if target is another werewolf
        from ..registry import RoleRegistry
        from game_logic import ist_werwolf_rolle

        if ist_werwolf_rolle(ziel.rolle):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst keinen anderen Werwolf wählen.",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Die Werwölfe haben {ziel.name} als Opfer gewählt.",
            ziel_spieler_id=ziel.id,
            effekte={"werwolf_opfer": ziel.id},
            log_sichtbar_fuer="werwolf",
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """Werwölfe erkennen sich in der ersten Nacht."""
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du erkennst deine Mitwölfe.",
            effekte={"erkennt_woelfe": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_win_conditions(self) -> List["WinCondition"]:
        """Werwölfe gewinnen wenn sie die Mehrheit stellen."""
        from ..base import WinCondition

        def check_werwolf_dominance(spieler: "Spieler", kontext: SpielKontext) -> bool:
            wolves = [
                uid
                for uid in kontext.lebende_spieler
                if kontext.spieler_teams.get(uid) == Team.WERWOLF
            ]
            villagers = [
                uid
                for uid in kontext.lebende_spieler
                if kontext.spieler_teams.get(uid) != Team.WERWOLF
            ]
            return len(wolves) >= len(villagers) and len(wolves) > 0

        return [
            WinCondition(
                id="werwolf_dominance",
                check_func=check_werwolf_dominance,
                team_override=Team.WERWOLF,
                priority=10,  # Standard Check
                description="Die Werwölfe sind in der Überzahl.",
            )
        ]

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Werwolf.

        Features:
        - Wolf ears (pointed, on head)
        - Sharp claws on hands
        - Fangs
        - Glowing red eyes
        - Wolf tail
        - Hunched posture
        - Fur texture
        """
        # Build complete wolf appearance
        wolf_features = [
            # Ears
            *create_wolf_ears(color="#8B0000", scale=1.0),
            # Claws on both hands
            *create_claws(color="#333333", count_per_hand=3),
            # Fangs
            *create_fangs(color="#FFFEF0"),
            # Glowing red eyes
            create_glowing_eyes(color="#FF2222", intensity=0.8),
            # Wolf tail
            create_tail("wolf", color="#8B0000"),
        ]

        # What Seher sees - subtle evil glow
        seher_features = [
            create_glowing_eyes(color="#FF0000", intensity=1.0),
            AppearanceFeature(
                feature_type="evil_aura",
                geometry="sphere",
                position={"x": 0, "y": 1.2, "z": 0},
                scale={"x": 0.7, "y": 1.4, "z": 0.7},
                color_source="custom",
                custom_color="#FF0000",
                opacity=0.1,
                emissive=True,
                emissive_intensity=0.3,
                visible_to_seher=True,
                visible_to_others=False,
                description="Evil aura visible to Seher",
            ),
        ]

        return RollenModell(
            modell_id="werwolf",
            anzeige_name="Werwolf",
            beschreibung="Ein blutrünstiger Werwolf mit glühenden Augen und scharfen Klauen",
            # Body modifications for wolf posture
            body=BodyModification(
                slouch_angle=15,
                snout_length=0.3,
                claw_hands=True,
                skin_texture="fur",
                brow_ridge=0.4,
            ),
            # What the werewolf sees when looking at themselves
            appearance_self_alive=wolf_features,
            # What others see - same features (werewolves are identifiable in 3D)
            appearance_others_alive=wolf_features,
            # What the Seher sees
            appearance_seher_view=seher_features,
            # Death appearance
            appearance_dead=create_death_marker(),
            # Animations
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.02,
                    sway_speed=0.8,
                    head_tilt_range=15,
                    look_around=True,
                    blink_rate=2.0,
                    breathing_visible=True,
                    tail_wag=True,
                ),
                "hunt": AnimationState(
                    state_name="hunt",
                    sway_amplitude=0.05,
                    sway_speed=1.5,
                    bob_amplitude=0.03,
                    bob_speed=2.0,
                    head_tilt_range=25,
                    gesture_chance=0.3,
                ),
            },
            # Hint effects for the hint system
            hint_effects=[
                HintEffect3D(
                    effect_id="eyes_glow_red",
                    effect_type="glow",
                    glow_color="#FF0000",
                    glow_intensity=1.5,
                    glow_pulse=True,
                ),
                HintEffect3D(
                    effect_id="shadow_pass",
                    effect_type="particle",
                    particle_type="shadow",
                    particle_count=15,
                    particle_color="#1a1a1a",
                    particle_duration=0.5,
                ),
            ],
            seher_sicht="bad",
            sound_on_action="growl.mp3",
            sound_on_death="wolf_death.mp3",
        )
