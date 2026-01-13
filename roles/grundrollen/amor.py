"""
Amor - Der Gott der Liebe.

Amor verbindet zwei Spieler auf ewig -
stirbt einer, stirbt auch der andere.
"""

from typing import Optional, List, TYPE_CHECKING, Union
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
    RollenUI,
    StateField,
    StateType,
    StateVisualEffect,
    GlobalStateDefinition,
    get_spieler_state,
    set_spieler_state,
    DistributionConfig,
    # Factory functions
    create_wings,
    create_weapon,
    create_aura,
    create_heart_effect,
    create_halo,
    create_death_marker,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry
from logger import logger

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Amor(Role):
    """
    Amor - Verbindungs-Rolle.

    Fähigkeiten:
    - Erste Nacht: Wählt zwei Spieler die sich verlieben
    - Verliebte sterben zusammen
    - Verliebte gewinnen nur gemeinsam als Letztes Paar

    Gewinnbedingung: Dorf gewinnt ODER Verliebte überleben als Letzte.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder von Amor."""
        return [
            StateField(
                "hat_verkuppelt", StateType.BOOL, False, "Hat bereits Verliebte gewählt"
            ),
        ]

    def global_state_definitions(self) -> List[GlobalStateDefinition]:
        """Definiert den Verliebt-State der auf andere Spieler gesetzt wird."""
        return [
            GlobalStateDefinition(
                key="global.verliebt_mit_id",
                name="Verliebt",
                typ=StateType.PLAYER_ID,
                beschreibung="ID des Partners mit dem der Spieler verliebt ist",
                visual_effect=StateVisualEffect.HEART,
                css_class="verliebt-partner",
                icon="fa-solid fa-heart",
                query_name="verliebte",
                defined_by="Amor",
                # Dynamic visibility: Partners + Amor see lovers
                visible_to=["partner", "source_role"],  # Partners see each other, Amor sees all lovers
                reveals_role=True,  # Partners see each other's roles
                snapshot_role_on_set=True,  # Store role at time of amor's action
                snapshot_key="global.verliebt_rolle_snapshot",
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=7,
            name="Amor",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist Amor. In der ersten Nacht wählst du zwei Spieler aus, "
                "die sich unsterblich ineinander verlieben."
            ),
            icon="fa-solid fa-heart",
            farbe="#ec4899",
            prioritaet=5,
            erzaehler_nacht=(
                "Amor erwacht und verschießt seine Pfeile. Er wählt zwei Spieler, "
                "die sich ineinander verlieben."
            ),
            erweiterung=Erweiterung.BASISSPIEL,
            # Visual Styling
            avatar_gradient_from="#ec4899",
            avatar_gradient_to="#be185d",
            avatar_border_color="#f9a8d4",
            badge_emoji="fa-solid fa-heart",
            distribution=DistributionConfig(
                min_players=5,
                # 1 Amor ab 8 Spielern
                count_func=lambda n: max(1, n // 150),
                priority=5,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.VERLIEBEN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"  # Beide Verliebte müssen am Leben sein

    def is_active_on_first_night(self) -> bool:
        """Amor is only active on the first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Amor does not act every night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Amor's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Amor - Verliebte wählen",
            instructions="Wähle zwei Spieler, die sich verlieben sollen.",
            buttons=[
                UIButton(
                    label="Verlieben",
                    action_type="amor_verlieben",
                    icon="fa-solid fa-heart",
                    css_class="btn-primary",
                    requires_confirmation=True,
                )
            ],
            requires_target=True,
            allow_multiple_targets=True,  # Needs 2 targets
            min_targets=2,
            max_targets=2,
            can_skip=False,  # Must act
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Amor wählt in der ersten Nacht zwei Verliebte.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Wähle zwei Spieler, die sich verlieben sollen.",
            effekte={"warte_auf_verliebte_wahl": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_phase_start_info(
        self, spieler: "Spieler", kontext: "SpielKontext"
    ) -> Optional[dict]:
        """Zeigt Amor wen er verliebt hat."""
        logger.debug(f"Getting phase start info for Amor (Player: {spieler.name})")
        verliebt_mit_id = self.get_state(spieler, "verliebt_mit_id")
        if verliebt_mit_id:
            return {"verliebt_mit_id": verliebt_mit_id}
        return None

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: "SpielKontext"
    ) -> Optional[AktionsErgebnis]:
        """
        Legacy single-target handler. Use execute_action for multi-target.
        """
        logger.debug(f"Executing night action for Amor (Player: {spieler.name})")
        if self.get_state(spieler, "hat_verkuppelt"):
            return AktionsErgebnis(erfolg=False, nachricht="Du hast bereits gewählt.")

        # Single target not supported - needs execute_action with list
        return AktionsErgebnis(
            erfolg=False,
            nachricht="Amor muss zwei Spieler gleichzeitig wählen."
        )

    def execute_action(
        self,
        action_type: str,
        spieler: "Spieler",
        targets: List["Spieler"],
        kontext: "SpielKontext",
    ) -> Optional[AktionsErgebnis]:
        """
        Execute Amor actions dynamically with multi-target support.

        This replaces the hardcoded 'amor_verlieben' handler in app.py.

        Handles:
        - amor_verlieben: Connect two players as lovers
        """
        if action_type == "amor_verlieben":
            if len(targets) != 2:
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht=f"Amor muss genau 2 Spieler wählen, nicht {len(targets)}.",
                )
            return self.verlieben(spieler, targets[0], targets[1], kontext)

        return None

    def verlieben(
        self,
        spieler: "Spieler",
        ziel1: "Spieler",
        ziel2: "Spieler",
        kontext: SpielKontext,
    ) -> AktionsErgebnis:
        """
        Verbindet zwei Spieler als Verliebte.
        """
        # Prüfe Gültigkeit
        if ziel1.id == ziel2.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst zwei verschiedene Spieler wählen.",
            )

        if (
            ziel1.id not in kontext.lebende_spieler
            or ziel2.id not in kontext.lebende_spieler
        ):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Beide Spieler müssen am Leben sein.",
            )

        # Markiere Amor als hat verkuppelt
        self.set_state(spieler, "hat_verkuppelt", True)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel1.name} und {ziel2.name} haben sich verliebt!",
            effekte={},
            # Use generic updates instead of hardcoded 'verliebte' key
            multi_target_updates={
                ziel1.id: {"global.verliebt_mit_id": ziel2.id},
                ziel2.id: {"global.verliebt_mit_id": ziel1.id},
            },
            additional_logs=[
                {"text": f"Du bist verliebt in {ziel2.name}!", "sichtbar_fuer": str(ziel1.id)},
                {"text": f"Du bist verliebt in {ziel1.name}!", "sichtbar_fuer": str(ziel2.id)},
            ],
            log_sichtbar_fuer="erzaehler",
            private_infos={
                ziel1.id: {
                    # Generic overlay format - no hardcoded type needed
                    "overlay": {
                        "title": "Du bist verliebt!",
                        "subtitle": "Dein Seelenpartner ist:",
                        "highlight": f"{ziel2.name}",
                        "content": "Eure Schicksale sind verbunden. Stirbt einer, stirbt auch der andere!",
                        "icon_class": "fa-solid fa-heart",
                        "color": "#ec4899",
                        "gradient": "linear-gradient(135deg, #ff69b4 0%, #ff1493 50%, #c71585 100%)",
                        "animation": "heartbeat",
                    }
                },
                ziel2.id: {
                    "overlay": {
                        "title": "Du bist verliebt!",
                        "subtitle": "Dein Seelenpartner ist:",
                        "highlight": f"{ziel1.name}",
                        "content": "Eure Schicksale sind verbunden. Stirbt einer, stirbt auch der andere!",
                        "icon_class": "fa-solid fa-heart",
                        "color": "#ec4899",
                        "gradient": "linear-gradient(135deg, #ff69b4 0%, #ff1493 50%, #c71585 100%)",
                        "animation": "heartbeat",
                    }
                },
            },
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        opfer: "Spieler",
        todesursache: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob ein Verliebter stirbt und der andere folgen muss.
        """
        verliebt_mit = get_spieler_state(opfer, "global.verliebt_mit_id")

        if verliebt_mit and verliebt_mit in kontext.lebende_spieler:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"Der/Die Verliebte kann den Verlust nicht ertragen!",
                effekte={
                    "verliebter_stirbt_auch": verliebt_mit,
                    "todesursache": "gebrochenes_herz",
                },
                log_sichtbar_fuer="alle",
            )

        return None

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Verliebte gewinnen wenn sie die letzten Überlebenden sind.
        Deprecated: Used by legacy logic. New logic uses get_win_conditions.
        """
        return None

    def get_win_conditions(self) -> List["WinCondition"]:
        """Verliebte gewinnen wenn sie die letzten sind."""
        from ..base import WinCondition, get_spieler_state

        def check_lovers_win(spieler: "Spieler", kontext: SpielKontext) -> bool:
            # Hole alle Spieler-Objekte (langsam aber nötig für State-Check)
            from models import Spieler

            # Optimierung: Prüfe nur wenn wenige Spieler leben
            if (
                len(kontext.lebende_spieler) > 3
            ):  # Bei 3 (z.b. Wolf+Dorf+Amor) kann es spannend sein
                # Wenn noch viele leben, können Verliebte kaum gewonnen haben (außer alle sind tot bis auf 2)
                # Wir checken nur wenn lebende <= 3 oder so?
                # Nein, "Verliebte gewinnen wenn sie die letzten Überlebenden sind" -> max 2 lebende.
                pass

            if len(kontext.lebende_spieler) != 2:
                return False

            # Check ob die beiden Lebenden verliebt sind
            lebende_objs = Spieler.query.filter(
                Spieler.id.in_(kontext.lebende_spieler)
            ).all()
            if len(lebende_objs) != 2:
                return False

            s1, s2 = lebende_objs[0], lebende_objs[1]

            partner1 = get_spieler_state(s1, "global.verliebt_mit_id")
            partner2 = get_spieler_state(s2, "global.verliebt_mit_id")

            if partner1 == s2.id and partner2 == s1.id:
                # Prüfen ob ein Wolf dabei ist (damit es kein reiner Dorfsieg ist)
                # (Wobei reine Dorf-Verliebte auch als Dorf gewinnen können, aber "Verliebte Win" ist cooler)
                # Regel: Wenn Verliebte Good+Good sind, gewinnen sie mit Dorf.
                # Wenn Good+Evil oder Evil+Evil, gewinnen sie als Paar.

                from roles import RoleRegistry

                r1 = RoleRegistry.get(s1.rolle)
                r2 = RoleRegistry.get(s2.rolle)

                team1 = r1.info.team if r1 else Team.DORF
                team2 = r2.info.team if r2 else Team.DORF

                if team1 != team2 or team1 == Team.WERWOLF:
                    return True

            return False

        return [
            WinCondition(
                id="lovers_win",
                check_func=check_lovers_win,
                team_override=Team.VERLIEBTE,
                priority=20,  # Höher als Standard
                description="Die Verliebten haben gewonnen! Ihre Liebe hat alle überwunden.",
            )
        ]

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Amor.

        Features:
        - Angel wings
        - Bow and arrow weapon
        - Heart particles
        - Pink glowing aura
        - Cherub appearance
        """
        amor_features = [
            # Angel wings
            *create_wings("angel", color="#FFB6C1"),
            # Bow weapon
            *create_weapon("bow"),
            # Heart particle effect
            create_heart_effect(),
            # Pink romantic aura
            create_aura(color="#FF69B4", intensity=0.4, pulsing=True),
            # Cupid's quiver with arrows
            AppearanceFeature(
                feature_type="heart_quiver",
                geometry="cylinder",
                position={"x": 0.18, "y": 1.15, "z": -0.18},
                scale={"x": 0.06, "y": 0.35, "z": 0.06},
                rotation={"x": -10, "y": 0, "z": 8},
                color_source="custom",
                custom_color="#FF69B4",
                description="Heart arrow quiver",
            ),
            # Cupid's diaper/toga
            AppearanceFeature(
                feature_type="toga",
                geometry="box",
                position={"x": 0, "y": 0.9, "z": 0},
                scale={"x": 0.32, "y": 0.25, "z": 0.28},
                color_source="custom",
                custom_color="#FFFFFF",
                opacity=0.95,
                description="Cupid's toga",
            ),
            # Rosy cheeks effect
            AppearanceFeature(
                feature_type="blush_left",
                geometry="sphere",
                position={"x": -0.12, "y": 1.82, "z": 0.18},
                scale={"x": 0.05, "y": 0.03, "z": 0.02},
                color_source="custom",
                custom_color="#FFB6C1",
                opacity=0.5,
                description="Left cheek blush",
            ),
            AppearanceFeature(
                feature_type="blush_right",
                geometry="sphere",
                position={"x": 0.12, "y": 1.82, "z": 0.18},
                scale={"x": 0.05, "y": 0.03, "z": 0.02},
                color_source="custom",
                custom_color="#FFB6C1",
                opacity=0.5,
                description="Right cheek blush",
            ),
            # Curly hair indicator
            AppearanceFeature(
                feature_type="curly_hair",
                geometry="sphere",
                position={"x": 0, "y": 2.1, "z": -0.05},
                scale={"x": 0.28, "y": 0.15, "z": 0.25},
                color_source="custom",
                custom_color="#FFD700",
                roughness=0.8,
                description="Golden curly hair",
            ),
        ]

        return RollenModell(
            modell_id="amor",
            anzeige_name="Amor",
            beschreibung="Der Gott der Liebe mit Flügeln und Liebespfeilen",
            body=BodyModification(
                height_multiplier=0.9,  # Cherub - slightly smaller
                width_multiplier=0.95,
                skin_texture="smooth",
            ),
            appearance_self_alive=amor_features,
            appearance_others_alive=amor_features,
            appearance_dead=create_death_marker(),
            seher_sicht="good",
            animations={
                "idle": AnimationState(
                    state_name="idle",
                    sway_amplitude=0.02,
                    sway_speed=0.4,
                    bob_amplitude=0.02,  # Floating effect
                    bob_speed=0.5,
                    head_tilt_range=15,
                    look_around=True,
                    blink_rate=3.0,
                    breathing_visible=True,
                    wing_flutter=True,
                ),
                "aim": AnimationState(
                    state_name="aim",
                    sway_amplitude=0.0,
                    bob_amplitude=0.01,
                    wing_flutter=True,
                    gesture_chance=0.0,
                ),
            },
            hint_effects=[
                HintEffect3D(
                    effect_id="hearts",
                    effect_type="particle",
                    particle_type="hearts",
                    particle_count=10,
                    particle_color="#FF69B4",
                    particle_duration=2.0,
                ),
            ],
            sound_on_action="bow_draw.mp3",
            sound_ambient="romantic_harp.mp3",
        )
