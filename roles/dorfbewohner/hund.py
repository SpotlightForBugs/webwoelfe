"""
Hund - Der treue Begleiter mit dunkler Seite.

Der Hund wählt in der ersten Nacht sein Herrchen.
Stirbt das Herrchen, wird der Hund zum Werwolf!
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    AppearanceFeature,
    RollenModell,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
    RollenModell,
    AppearanceFeature,
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
        """Definiert die Zustandsfelder des Hundes."""
        return [
            StateField("herrchen_id", StateType.PLAYER_ID, None, "ID des Herrchens"),
            StateField("gewaehlt", StateType.BOOL, False, "Herrchen bereits gewählt"),
            StateField("verwandelt", StateType.BOOL, False, "Zum Werwolf verwandelt"),
        ]

    def get_sichtbare_rolle(self, spieler: "Spieler") -> str:
        """
        Der Hund sieht sich als "Hund" oder "Werhund" je nach Verwandlung.

        - Vor Verwandlung: "Hund"
        - Nach Verwandlung: "Werhund" (behält Hund-Identität, aber mit Wolf-Aspekt)
        """
        if self.get_state(spieler, "verwandelt"):
            return "Werhund"
        return "Hund"

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """
        Dynamische Modell-Auswahl basierend auf Verwandlungsstatus.

        - Vor Verwandlung: hund (normaler Hund)
        - Nach Verwandlung: werhund (Wolf-Hund Hybrid)
        """
        # Dog ears (floppy, not pointy like wolf)
        dog_ears = [
            AppearanceFeature(
                feature_type="dog_ear_left",
                geometry="box",
                position={"x": -0.2, "y": 2.0, "z": 0},
                scale={"x": 0.15, "y": 0.25, "z": 0.08},
                rotation={"x": 0, "y": 0, "z": -30},
                color_source="custom",
                custom_color="#8B4513",
                description="Floppy dog ear",
            ),
            AppearanceFeature(
                feature_type="dog_ear_right",
                geometry="box",
                position={"x": 0.2, "y": 2.0, "z": 0},
                scale={"x": 0.15, "y": 0.25, "z": 0.08},
                rotation={"x": 0, "y": 0, "z": 30},
                color_source="custom",
                custom_color="#8B4513",
                description="Floppy dog ear",
            ),
        ]

        # Wolf ears (pointy) for when transformed
        wolf_ears = [
            AppearanceFeature(
                feature_type="wolf_ear_left",
                geometry="cone",
                position={"x": -0.18, "y": 2.25, "z": -0.05},
                scale={"x": 0.12, "y": 0.2, "z": 0.1},
                rotation={"x": 0, "y": 0, "z": -15},
                color_source="custom",
                custom_color="#8B4513",
                description="Wolf ear after transformation",
            ),
            AppearanceFeature(
                feature_type="wolf_ear_right",
                geometry="cone",
                position={"x": 0.18, "y": 2.25, "z": -0.05},
                scale={"x": 0.12, "y": 0.2, "z": 0.1},
                rotation={"x": 0, "y": 0, "z": 15},
                color_source="custom",
                custom_color="#8B4513",
                description="Wolf ear after transformation",
            ),
        ]

        # Claws appear after transformation
        wolf_claws = [
            AppearanceFeature(
                feature_type="claws",
                geometry="cone",
                count=6,
                position={"x": 0, "y": 0.52, "z": 0.08},
                scale={"x": 0.025, "y": 0.08, "z": 0.02},
                rotation={"x": -10, "y": 0, "z": 0},
                color_source="custom",
                custom_color="#888888",
                description="Sharp claws after transformation",
            ),
        ]

        # Check transformation state
        is_transformed = self.get_state(spieler, "verwandelt")

        if is_transformed:
            # After transformation: looks like a werewolf to everyone
            appearance = wolf_ears + wolf_claws
            return RollenModell(
                modell_id="werhund",
                anzeige_name="Werhund",
                beschreibung="Ein Hund der zum Werwolf wurde",
                appearance_self_alive=appearance,
                appearance_others_alive=appearance,
                appearance_dead=[],
                seher_sicht="bad",  # Now seen as bad by Seher
            )
        else:
            # Before transformation: looks like a dog
            appearance = dog_ears
            return RollenModell(
                modell_id="hund",
                anzeige_name="Hund",
                beschreibung="Ein treuer Hund",
                appearance_self_alive=appearance,
                appearance_others_alive=appearance,
                appearance_dead=[],
                seher_sicht="good",  # Seen as good by Seher
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
            # Visual Styling
            avatar_gradient_from="#a16207",
            avatar_gradient_to="#713f12",
            avatar_border_color="#ca8a04",
            badge_emoji="🐕",
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
        todesursache: str,
        kontext: SpielKontext,
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
