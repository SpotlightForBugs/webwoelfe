"""
Weisser Wolf - Solo-Werwolf.

Der Weisse Wolf jagt mit den Woelfen, aber kann
jede zweite Nacht auch einen Mitwerwolf toeten.
Er gewinnt nur alleine.
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
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class WeisserWolf(Role):
    """
    Der Weisse Wolf - Solo-Werwolf.

    Faehigkeiten:
    - Jagt mit den Woelfen
    - Kann jede zweite Nacht einen Mitwerwolf toeten

    Gewinnbedingung: Als letzter ueberlebender Werwolf.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=21,
            name="Weißer Wolf",
            team=Team.SOLO,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Weisse Wolf! Du jagst mit den Woelfen, aber "
                "jede zweite Nacht kannst du zusaetzlich einen Mitwerwolf "
                "toeten. Du gewinnst nur alleine!"
            ),
            icon="fa-solid fa-paw",
            farbe="#f5f5f4",
            prioritaet=52,
            erzaehler_nacht=(
                "Der Weisse Wolf erwacht (jede zweite Nacht). "
                "Möchte er einen Mitwerwolf töten?"
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            distribution=DistributionConfig(
                min_players=15,
                count_func=lambda n: 1,
                priority=50,
                exclusive_with=["Werwolf"],
            ),
            avatar_gradient_from="#f5f5f4",
            avatar_gradient_to="#d6d3d1",
            avatar_border_color="#e7e5e4",
            badge_emoji="🐺",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def erlaubte_ziele(self) -> str:
        return "andere_werwoelfe"

    def is_active_on_first_night(self) -> bool:
        return False

    def is_active_on_every_night(self) -> bool:
        return True

    def get_ui_definition(self) -> "RollenUI":
        from ..base import RollenUI, UIButton
        return RollenUI(
            title="Weißer Wolf - Verrat",
            instructions="Du kannst einen Mitwerwolf töten (jede zweite Nacht).",
            buttons=[
                UIButton(
                    label="Töten",
                    action_type="weisser_wolf_toeten",
                    icon="fa-solid fa-skull",
                    css_class="btn-danger",
                    requires_confirmation=True,
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
        if action_type == "weisser_wolf_toeten":
            if kontext.runde % 2 != 0:
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht="Du kannst nur jede zweite Nacht zuschlagen.",
                )

            if not targets:
                return AktionsErgebnis(
                    erfolg=True,
                    nachricht="Du verschonst deine Brüder heute Nacht.",
                )

            ziel = targets[0]
            ziel_team = kontext.spieler_teams.get(ziel.id, Team.DORF)
            if ziel_team != Team.WERWOLF:
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht="Du kannst nur andere Werwölfe töten!",
                )

            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"Du tötest {ziel.name}! Ein Konkurrent weniger...",
                ziel_spieler_id=ziel.id,
                effekte={
                    "toeten": ziel.id,
                    "todesursache": "weisser_wolf",
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        return None

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext, aktion: str = None
    ) -> Optional[AktionsErgebnis]:
        return self.execute_action("weisser_wolf_toeten", spieler, [ziel] if ziel else [], kontext)

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        if len(kontext.lebende_spieler) == 1 and spieler.id in kontext.lebende_spieler:
            return Team.SOLO
        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Weißer Wolf.

        Majestic white/silver wolf with ice-blue eyes, pristine fur.
        """
        weisser_wolf_features = [
            # White wolf ears
            *create_wolf_ears(color="#E8E8E8", scale=1.1),
            # Silver claws
            *create_claws(color="#C0C0C0", count_per_hand=3),
            # White fangs
            *create_fangs(color="#FFFFFF"),
            # Ice blue glowing eyes
            create_glowing_eyes(color="#66CCFF", intensity=0.8),
            # White fluffy tail
            create_tail("wolf", color="#F5F5F5"),
            # Frost aura
            create_aura(color="#AADDFF", intensity=0.25, pulsing=True),
            # Silver mane/ruff
            AppearanceFeature(
                feature_type="mane",
                geometry="sphere",
                position={"x": 0, "y": 1.7, "z": -0.1},
                scale={"x": 0.4, "y": 0.25, "z": 0.35},
                color_source="custom",
                custom_color="#E8E8E8",
                roughness=0.9,
                description="Silver mane ruff",
            ),
            # Frost particles on breath
            AppearanceFeature(
                feature_type="frost_breath",
                geometry="sphere",
                position={"x": 0, "y": 1.75, "z": 0.3},
                scale={"x": 0.08, "y": 0.05, "z": 0.08},
                color_source="custom",
                custom_color="#CCFFFF",
                opacity=0.4,
                emissive=True,
                emissive_intensity=0.3,
                particle_effect="magic",
                particle_color="#CCFFFF",
                particle_rate=3.0,
                description="Frost breath",
            ),
        ]

        return RollenModell(
            modell_id="weisser_wolf",
            anzeige_name="Weißer Wolf",
            beschreibung="Ein majestätischer weißer Wolf mit eisblauem Blick",
            body=BodyModification(
                slouch_angle=12,
                snout_length=0.3,
                claw_hands=True,
                skin_texture="fur",
                skin_color_override="#F0F0F0",
                height_multiplier=1.02,
            ),
            appearance_self_alive=weisser_wolf_features,
            appearance_others_alive=weisser_wolf_features,
            appearance_dead=create_death_marker(),
            seher_sicht="bad",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.015,
                    sway_speed=0.5,
                    head_tilt_range=18,
                    breathing_visible=True,
                    tail_wag=True,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="frost_glow",
                    effect_type="glow",
                    glow_color="#AADDFF",
                    glow_intensity=0.6,
                    glow_pulse=True,
                ),
            ],
            sound_on_action="wolf_howl_cold.mp3",
        )
