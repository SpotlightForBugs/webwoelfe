"""
Henker - Will einen bestimmten Spieler toeten lassen.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext, StateField, StateType
from ..enums import Team, Kategorie, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Henker(Role):
    """
    Der Henker - Ziel-basierter Solo.

    Faehigkeiten:
    - Waehlt zu Spielbeginn ein Ziel
    - Gewinnt wenn das Ziel gehaengt wird

    Gewinnbedingung: Ziel wird vom Dorf gehaengt.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Henkers."""
        return [
            StateField("ziel_id", StateType.PLAYER_ID, None, "ID des Ziels"),
            StateField("gewonnen", StateType.BOOL, False, "Hat gewonnen"),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=102,
            name="Henker",
            team=Team.SOLO,
            kategorie=Kategorie.SOLO,
            beschreibung=(
                "Du bist der Henker. Du waehlst zu Beginn ein Ziel. "
                "Dein Ziel: Dafuer sorgen, dass dieses Ziel vom Dorf "
                "gehaengt wird! Dann gewinnst du."
            ),
            icon="fa-solid fa-gavel",
            farbe="#525252",
            prioritaet=6,
            erzaehler_nacht=(
                "Der Henker erwacht (nur erste Nacht) und waehlt sein Ziel."
            ),
        )

    def is_active_on_first_night(self) -> bool:
        """Henker acts on first night (choosing target)."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Henker only acts on first night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Henker's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Henker - Ziel wählen",
            instructions="Wähle dein Ziel. Du gewinnst, wenn es gehängt wird.",
            buttons=[
                UIButton(
                    label="Ziel wählen",
                    action_type="waehlen",
                    icon="fa-solid fa-gavel",
                    css_class="btn-danger",
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
        Henker waehlt sein Ziel zu Beginn.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Waehle dein Ziel.",
            effekte={"warte_auf_henker_ziel": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def ziel_waehlen(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Setzt das Henker-Ziel.
        """
        if ziel.id == spieler.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst dich nicht selbst waehlen.",
            )

        self.set_state(spieler, "ziel_id", ziel.id)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} ist dein Ziel. Sorge dafuer, dass er gehaengt wird!",
            ziel_spieler_id=ziel.id,
            effekte={},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prueft ob das Henker-Ziel gehaengt wird.
        """
        henker_ziel = self.get_state(spieler, "ziel_id")

        if henker_ziel and opfer.id == henker_ziel:
            self.set_state(spieler, "gewonnen", True)
            return AktionsErgebnis(
                erfolg=True,
                nachricht=("Das Ziel des Henkers wurde gehaengt! Der Henker gewinnt!"),
                effekte={
                    "henker_gewonnen": True,
                },
                log_sichtbar_fuer="alle",
            )

        return None

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Gewinnt wenn Ziel gehaengt wurde.
        """
        gewonnen = self.get_state(spieler, "gewonnen")
        if gewonnen:
            return Team.SOLO
        return None
