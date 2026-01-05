"""
Henker - Will einen bestimmten Spieler toeten lassen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie
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

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} ist dein Ziel. Sorge dafuer, dass er gehaengt wird!",
            ziel_spieler_id=ziel.id,
            effekte={
                "henker_ziel": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prueft ob das Henker-Ziel gehaengt wird.
        """
        henker_ziel = getattr(spieler, "henker_ziel_id", None)

        if henker_ziel and opfer.id == henker_ziel:
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
        gewonnen = getattr(spieler, "henker_gewonnen", False)
        if gewonnen:
            return Team.SOLO
        return None
