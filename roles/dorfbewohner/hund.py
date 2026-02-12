"""
Hund - Der treue Begleiter mit dunkler Seite.

Der Hund wählt in der ersten Nacht sein Herrchen.
Stirbt das Herrchen, wird der Hund zum Werwolf!
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
from ..enums import Team, Kategorie, SichtTyp, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Hund(Role):
    """
    Hund

    Fähigkeiten:
    - Wählt in der ersten Nacht sein Herrchen
    - Stirbt das Herrchen: Wird zum Werwolf
    - Solange Herrchen lebt: Teil des Dorfes

    Besonderheiten:
    - Nur EINMAL aktiv (erste Nacht für Herrchen-Wahl)
    - Danach keine Nacht-Aktion mehr
    - Seherin sieht ihn als Dorf, bis Verwandlung

    Gewinnbedingung: Abhängig von Verwandlung.
    - Vor Verwandlung: Dorf gewinnt
    - Nach Verwandlung: Werwölfe gewinnen
    """

    def state_fields(self) -> List[StateField]:
        return [
            StateField("herrchen_id", StateType.PLAYER_ID, None, "ID des Herrchens"),
            StateField("gewaehlt", StateType.BOOL, False, "Herrchen bereits gewählt"),
            StateField("verwandelt", StateType.BOOL, False, "Zum Werwolf verwandelt"),
        ]

    def get_sichtbare_rolle(self, spieler: "Spieler") -> str:
        if self.get_state(spieler, "verwandelt"):
            return "Werhund"
        return "Hund"

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Comprehensive 3D appearance for Hund.

        IMPORTANT: The dog looks like an ACTUAL DOG - a quadruped animal!
        NOT a humanoid with dog ears!

        - Body is horizontal (quadruped stance)
        - Four legs
        - Dog head with snout, floppy ears
        - Wagging tail
        """
        is_transformed = self.get_state(spieler, "verwandelt")

        if is_transformed:
            # WERHUND - Werewolf-dog hybrid (more menacing, larger)
            werhund_features = [
                # Werewolf body (still quadruped but larger, more menacing)
                AppearanceFeature(
                    feature_type="body",
                    geometry="capsule",
                    position={"x": 0, "y": 0.8, "z": 0},
                    scale={"x": 0.5, "y": 0.4, "z": 0.9},
                    rotation={"x": 0, "y": 0, "z": 90},
                    color_source="custom",
                    custom_color="#2a1a0a",
                    roughness=0.9,
                    description="Wolf-dog body",
                ),
                # Head (wolf-like, larger)
                AppearanceFeature(
                    feature_type="head",
                    geometry="sphere",
                    position={"x": 0, "y": 1.1, "z": 0.6},
                    scale={"x": 0.3, "y": 0.28, "z": 0.35},
                    color_source="custom",
                    custom_color="#2a1a0a",
                    roughness=0.9,
                    description="Wolf-dog head",
                ),
                # Snout (longer, more wolf-like)
                AppearanceFeature(
                    feature_type="snout",
                    geometry="box",
                    position={"x": 0, "y": 1.0, "z": 0.85},
                    scale={"x": 0.12, "y": 0.1, "z": 0.25},
                    color_source="custom",
                    custom_color="#2a1a0a",
                    description="Wolf snout",
                ),
                # Pointed wolf ears (after transformation)
                AppearanceFeature(
                    feature_type="ear_left",
                    geometry="cone",
                    position={"x": -0.12, "y": 1.35, "z": 0.55},
                    scale={"x": 0.08, "y": 0.18, "z": 0.06},
                    rotation={"x": 15, "y": 0, "z": -15},
                    color_source="custom",
                    custom_color="#2a1a0a",
                    description="Pointed wolf ear",
                ),
                AppearanceFeature(
                    feature_type="ear_right",
                    geometry="cone",
                    position={"x": 0.12, "y": 1.35, "z": 0.55},
                    scale={"x": 0.08, "y": 0.18, "z": 0.06},
                    rotation={"x": 15, "y": 0, "z": 15},
                    color_source="custom",
                    custom_color="#2a1a0a",
                    description="Pointed wolf ear",
                ),
                # Glowing red eyes
                create_glowing_eyes(color="#FF2222", intensity=0.8),
                # Front left leg
                AppearanceFeature(
                    feature_type="front_leg_left",
                    geometry="cylinder",
                    position={"x": -0.18, "y": 0.35, "z": 0.35},
                    scale={"x": 0.08, "y": 0.4, "z": 0.08},
                    color_source="custom",
                    custom_color="#2a1a0a",
                    description="Front left leg",
                ),
                # Front right leg
                AppearanceFeature(
                    feature_type="front_leg_right",
                    geometry="cylinder",
                    position={"x": 0.18, "y": 0.35, "z": 0.35},
                    scale={"x": 0.08, "y": 0.4, "z": 0.08},
                    color_source="custom",
                    custom_color="#2a1a0a",
                    description="Front right leg",
                ),
                # Back left leg
                AppearanceFeature(
                    feature_type="back_leg_left",
                    geometry="cylinder",
                    position={"x": -0.18, "y": 0.35, "z": -0.35},
                    scale={"x": 0.08, "y": 0.4, "z": 0.08},
                    color_source="custom",
                    custom_color="#2a1a0a",
                    description="Back left leg",
                ),
                # Back right leg
                AppearanceFeature(
                    feature_type="back_leg_right",
                    geometry="cylinder",
                    position={"x": 0.18, "y": 0.35, "z": -0.35},
                    scale={"x": 0.08, "y": 0.4, "z": 0.08},
                    color_source="custom",
                    custom_color="#2a1a0a",
                    description="Back right leg",
                ),
                # Wolf tail (bushy, raised)
                AppearanceFeature(
                    feature_type="tail",
                    geometry="capsule",
                    position={"x": 0, "y": 1.0, "z": -0.7},
                    scale={"x": 0.1, "y": 0.35, "z": 0.1},
                    rotation={"x": -45, "y": 0, "z": 0},
                    color_source="custom",
                    custom_color="#2a1a0a",
                    animation="sway",
                    animation_speed=0.3,
                    description="Bushy wolf tail",
                ),
                # Fangs
                *create_fangs(color="#FFFEF0"),
                # Claws on paws
                AppearanceFeature(
                    feature_type="claw_front",
                    geometry="cone",
                    position={"x": 0, "y": 0.08, "z": 0.45},
                    scale={"x": 0.02, "y": 0.06, "z": 0.02},
                    rotation={"x": 15, "y": 0, "z": 0},
                    color_source="custom",
                    custom_color="#1a1a1a",
                    count=4,
                    count_arrangement="linear",
                    count_spacing=0.04,
                    description="Front claws",
                ),
            ]

            return RollenModell(
                modell_id="werhund",
                anzeige_name="Werhund",
                beschreibung="Ein verwandelter Hund - jetzt ein gefährlicher Werwolf",
                body=BodyModification(
                    height_multiplier=0.7,  # Lower to ground (quadruped)
                    width_multiplier=1.5,
                    skin_texture="fur",
                    claw_hands=True,
                ),
                appearance_self_alive=werhund_features,
                appearance_others_alive=werhund_features,
                appearance_dead=create_death_marker(),
                seher_sicht="bad",
                animations={
                    "idle": AnimationState(
                        state_name="idle",
                        sway_amplitude=0.02,
                        sway_speed=0.4,
                        breathing_visible=True,
                        tail_wag=True,
                    ),
                },
                hint_effects=[
                    HintEffect3D(
                        effect_id="growl",
                        effect_type="shake",
                        shake_intensity=0.05,
                        shake_duration=0.3,
                    ),
                ],
                sound_on_action="wolf_growl.mp3",
            )
        else:
            # NORMAL DOG - Friendly, floppy ears, wagging tail
            dog_features = [
                # Dog body (horizontal, quadruped)
                AppearanceFeature(
                    feature_type="body",
                    geometry="capsule",
                    position={"x": 0, "y": 0.7, "z": 0},
                    scale={"x": 0.4, "y": 0.35, "z": 0.7},
                    rotation={"x": 0, "y": 0, "z": 90},
                    color_source="custom",
                    custom_color="#8B4513",  # Brown
                    roughness=0.85,
                    description="Dog body",
                ),
                # Dog head
                AppearanceFeature(
                    feature_type="head",
                    geometry="sphere",
                    position={"x": 0, "y": 0.95, "z": 0.5},
                    scale={"x": 0.25, "y": 0.22, "z": 0.28},
                    color_source="custom",
                    custom_color="#8B4513",
                    roughness=0.85,
                    description="Dog head",
                ),
                # Dog snout
                AppearanceFeature(
                    feature_type="snout",
                    geometry="box",
                    position={"x": 0, "y": 0.88, "z": 0.72},
                    scale={"x": 0.1, "y": 0.08, "z": 0.18},
                    color_source="custom",
                    custom_color="#8B4513",
                    description="Dog snout",
                ),
                # Nose
                AppearanceFeature(
                    feature_type="nose",
                    geometry="sphere",
                    position={"x": 0, "y": 0.9, "z": 0.82},
                    scale={"x": 0.04, "y": 0.03, "z": 0.03},
                    color_source="custom",
                    custom_color="#1a1a1a",
                    description="Dog nose",
                ),
                # Floppy left ear
                AppearanceFeature(
                    feature_type="ear_left",
                    geometry="box",
                    position={"x": -0.15, "y": 1.05, "z": 0.45},
                    scale={"x": 0.12, "y": 0.2, "z": 0.06},
                    rotation={"x": 0, "y": 10, "z": -50},
                    color_source="custom",
                    custom_color="#6B3A0F",  # Darker brown
                    animation="sway",
                    animation_speed=0.3,
                    animation_amplitude=0.3,
                    description="Floppy ear left",
                ),
                # Floppy right ear
                AppearanceFeature(
                    feature_type="ear_right",
                    geometry="box",
                    position={"x": 0.15, "y": 1.05, "z": 0.45},
                    scale={"x": 0.12, "y": 0.2, "z": 0.06},
                    rotation={"x": 0, "y": -10, "z": 50},
                    color_source="custom",
                    custom_color="#6B3A0F",
                    animation="sway",
                    animation_speed=0.3,
                    animation_amplitude=0.3,
                    description="Floppy ear right",
                ),
                # Eyes (friendly, brown)
                AppearanceFeature(
                    feature_type="eye_left",
                    geometry="sphere",
                    position={"x": -0.08, "y": 1.0, "z": 0.68},
                    scale={"x": 0.04, "y": 0.04, "z": 0.02},
                    color_source="custom",
                    custom_color="#3D2314",
                    description="Left eye",
                ),
                AppearanceFeature(
                    feature_type="eye_right",
                    geometry="sphere",
                    position={"x": 0.08, "y": 1.0, "z": 0.68},
                    scale={"x": 0.04, "y": 0.04, "z": 0.02},
                    color_source="custom",
                    custom_color="#3D2314",
                    description="Right eye",
                ),
                # Front left leg
                AppearanceFeature(
                    feature_type="front_leg_left",
                    geometry="cylinder",
                    position={"x": -0.15, "y": 0.3, "z": 0.28},
                    scale={"x": 0.06, "y": 0.35, "z": 0.06},
                    color_source="custom",
                    custom_color="#8B4513",
                    description="Front left leg",
                ),
                # Front right leg
                AppearanceFeature(
                    feature_type="front_leg_right",
                    geometry="cylinder",
                    position={"x": 0.15, "y": 0.3, "z": 0.28},
                    scale={"x": 0.06, "y": 0.35, "z": 0.06},
                    color_source="custom",
                    custom_color="#8B4513",
                    description="Front right leg",
                ),
                # Back left leg
                AppearanceFeature(
                    feature_type="back_leg_left",
                    geometry="cylinder",
                    position={"x": -0.15, "y": 0.3, "z": -0.28},
                    scale={"x": 0.06, "y": 0.35, "z": 0.06},
                    color_source="custom",
                    custom_color="#8B4513",
                    description="Back left leg",
                ),
                # Back right leg
                AppearanceFeature(
                    feature_type="back_leg_right",
                    geometry="cylinder",
                    position={"x": 0.15, "y": 0.3, "z": -0.28},
                    scale={"x": 0.06, "y": 0.35, "z": 0.06},
                    color_source="custom",
                    custom_color="#8B4513",
                    description="Back right leg",
                ),
                # Wagging tail (curled up, happy)
                AppearanceFeature(
                    feature_type="tail",
                    geometry="cylinder",
                    position={"x": 0, "y": 0.85, "z": -0.55},
                    scale={"x": 0.05, "y": 0.25, "z": 0.05},
                    rotation={"x": -60, "y": 0, "z": 0},
                    color_source="custom",
                    custom_color="#8B4513",
                    animation="sway",
                    animation_speed=2.0,  # Fast wagging!
                    animation_amplitude=1.5,
                    description="Wagging tail",
                ),
                # Collar
                AppearanceFeature(
                    feature_type="collar",
                    geometry="torus",
                    position={"x": 0, "y": 0.9, "z": 0.4},
                    scale={"x": 0.15, "y": 0.02, "z": 0.15},
                    rotation={"x": 90, "y": 0, "z": 0},
                    color_source="custom",
                    custom_color="#CC0000",  # Red collar
                    description="Dog collar",
                ),
                # Collar tag
                AppearanceFeature(
                    feature_type="collar_tag",
                    geometry="sphere",
                    position={"x": 0, "y": 0.82, "z": 0.52},
                    scale={"x": 0.03, "y": 0.04, "z": 0.01},
                    color_source="custom",
                    custom_color="#FFD700",  # Gold tag
                    metallic=True,
                    description="Collar tag",
                ),
                # Paws (white/lighter)
                AppearanceFeature(
                    feature_type="paw_front_left",
                    geometry="sphere",
                    position={"x": -0.15, "y": 0.08, "z": 0.28},
                    scale={"x": 0.07, "y": 0.05, "z": 0.08},
                    color_source="custom",
                    custom_color="#D2B48C",  # Tan paws
                    description="Front left paw",
                ),
                AppearanceFeature(
                    feature_type="paw_front_right",
                    geometry="sphere",
                    position={"x": 0.15, "y": 0.08, "z": 0.28},
                    scale={"x": 0.07, "y": 0.05, "z": 0.08},
                    color_source="custom",
                    custom_color="#D2B48C",
                    description="Front right paw",
                ),
                AppearanceFeature(
                    feature_type="paw_back_left",
                    geometry="sphere",
                    position={"x": -0.15, "y": 0.08, "z": -0.28},
                    scale={"x": 0.07, "y": 0.05, "z": 0.08},
                    color_source="custom",
                    custom_color="#D2B48C",
                    description="Back left paw",
                ),
                AppearanceFeature(
                    feature_type="paw_back_right",
                    geometry="sphere",
                    position={"x": 0.15, "y": 0.08, "z": -0.28},
                    scale={"x": 0.07, "y": 0.05, "z": 0.08},
                    color_source="custom",
                    custom_color="#D2B48C",
                    description="Back right paw",
                ),
            ]

            return RollenModell(
                modell_id="hund",
                anzeige_name="Hund",
                beschreibung="Ein treuer, freundlicher Hund mit wedelndem Schwanz",
                body=BodyModification(
                    height_multiplier=0.6,  # Low to ground - it's a dog!
                    width_multiplier=1.3,
                    skin_texture="fur",
                ),
                appearance_self_alive=dog_features,
                appearance_others_alive=dog_features,
                appearance_dead=create_death_marker(),
                seher_sicht="good",
                animations={
                    "idle": AnimationState(
                        state_name="idle",
                        sway_amplitude=0.01,
                        sway_speed=0.5,
                        breathing_visible=True,
                        tail_wag=True,
                    ),
                    "excited": AnimationState(
                        state_name="excited",
                        sway_amplitude=0.03,
                        bob_amplitude=0.02,
                        bob_speed=3.0,
                        tail_wag=True,
                    ),
                },
                hint_effects=[
                    HintEffect3D(
                        effect_id="bark",
                        effect_type="shake",
                        shake_intensity=0.03,
                        shake_duration=0.2,
                    ),
                ],
                sound_on_action="dog_bark.mp3",
                sound_ambient="dog_panting.mp3",
            )

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=19,
            name="Hund",
            team=Team.DORF,  # Startet als Dorf
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist der treue Hund. Du wählst in der ersten Nacht ein "
                "Herrchen. Solange dein Herrchen lebt, gehörst du zum Dorf. "
                "Stirbt dein Herrchen, wechselst du zum Team der Werwölfe über!"
            ),
            icon="fa-solid fa-dog",
            farbe="#a16207",
            prioritaet=7,  # Früh in der Nacht, ähnlich wie Amor/Wildes Kind
            erzaehler_nacht=(
                "Der Hund erwacht und sucht sich ein Herrchen. "
                "Er wird ihm treu ergeben sein... bis in den Tod."
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            distribution=DistributionConfig(
                min_players=10,
                count_func=lambda n: 1,
                priority=30,
            ),
            # Visual Styling
            avatar_gradient_from="#a16207",
            avatar_gradient_to="#713f12",
            avatar_border_color="#ca8a04",
            badge_emoji="fas fa-dog",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.WAEHLEN

    @property
    def erlaubte_ziele(self) -> str:
        """Kann jeden anderen lebenden Spieler als Herrchen wählen."""
        return "andere"

    def is_active_on_first_night(self) -> bool:
        """Hund acts on first night (choosing master)."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Hund only acts on first night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Hund's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Hund - Herrchen wählen",
            instructions="Wähle dein Herrchen. Wenn es stirbt, wirst du zum Werwolf.",
            buttons=[
                UIButton(
                    label="Herrchen wählen",
                    action_type="waehlen",
                    icon="fa-solid fa-dog",
                    css_class="btn-primary",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Der Hund bereitet sich auf die Herrchen-Wahl vor.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Wähle in der ersten Nacht dein Herrchen.",
            effekte={"warte_auf_herrchen_wahl": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Hauptaktion: Herrchen wählen (nur erste Nacht).
        """
        # Prüfe ob noch aktiv (erste Runde)
        if kontext.runde != 1:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast bereits dein Herrchen gewählt.",
                effekte={"keine_aktion": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        # Wenn kein Ziel, warten auf Wahl
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Wähle dein Herrchen für dieses Spiel.",
                effekte={"warte_auf_herrchen_wahl": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        # Herrchen wählen
        return self.herrchen_waehlen(spieler, ziel, kontext)

    def herrchen_waehlen(
        self, spieler: "Spieler", herrchen: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Setzt das gewählte Herrchen.
        """
        # Validierung: Kann sich nicht selbst wählen
        if herrchen.id == spieler.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst dich nicht selbst als Herrchen wählen.",
            )

        # Validierung: Herrchen muss leben
        if herrchen.id not in kontext.lebende_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Das Herrchen muss am Leben sein.",
            )

        # Herrchen speichern
        self.set_state(spieler, "herrchen_id", herrchen.id)
        self.set_state(spieler, "gewaehlt", True)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{herrchen.name} ist nun dein Herrchen. Beschütze es mit deinem Leben!",
            ziel_spieler_id=herrchen.id,
            effekte={
                "event_typ": "hund_herrchen",
            },
            log_sichtbar_fuer="erzaehler",
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        opfer: "Spieler",
        kontext: SpielKontext,
        todesursache: str = "",
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob das Herrchen stirbt und löst Verwandlung aus.
        """
        herrchen_id = self.get_state(spieler, "herrchen_id")

        # Kein Herrchen gesetzt
        if herrchen_id is None:
            return None

        # Nicht das Herrchen
        if opfer.id != herrchen_id:
            return None

        # Hund selbst ist bereits tot
        if spieler.id not in kontext.lebende_spieler:
            return None

        # Das Herrchen stirbt! Verwandlung auslösen!
        self.set_state(spieler, "verwandelt", True)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=(
                f"Das Herrchen des Hundes ({opfer.name}) ist gestorben! "
                f"{spieler.name} der treue Hund verwandelt sich vor Trauer "
                f"in einen Werwolf!"
            ),
            effekte={
                "verwandlung": True,
                "neues_team": Team.WERWOLF.value,
                "ist_jetzt_werwolf": True,
                "event_typ": "hund_verwandelt",
            },
            log_sichtbar_fuer="erzaehler",
        )

    def berechne_aktuelles_team(self, spieler: "Spieler") -> Team:
        """
        Berechnet das aktuelle Team des Hundes.
        """
        herrchen_id = self.get_state(spieler, "herrchen_id")

        if herrchen_id is None:
            return Team.DORF

        if self.get_state(spieler, "verwandelt"):
            return Team.WERWOLF

        return Team.DORF

    def on_spiel_ende(
        self, spieler: "Spieler", gewinner_team: Team, kontext: SpielKontext
    ) -> bool:
        """
        Prüft ob der Hund gewonnen hat.
        """
        aktuelles_team = self.berechne_aktuelles_team(spieler)
        return aktuelles_team == gewinner_team
