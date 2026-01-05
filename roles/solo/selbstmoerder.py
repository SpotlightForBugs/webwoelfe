"""
Selbstmörder - Will vom Dorf gehängt werden.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext, StateField, StateType, HinweisConfig
from ..enums import Team, Kategorie
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Selbstmoerder(Role):
    """
    Der Selbstmörder - Solo-Sieg durch Hinrichtung.

    Fähigkeiten:
    - Kann sich aktiv verdächtig machen (Hinweise senden)
    - Gewinnt NUR wenn vom Dorf gehängt
    - Gewinnt nicht wenn von Wölfen getötet

    Gewinnbedingung: Wird vom Dorf gehängt.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Selbstmörders."""
        return [
            StateField("gewonnen", StateType.BOOL, False, "Hat gewonnen (wurde gehängt)"),
        ]

    def get_hinweis_config(self) -> HinweisConfig:
        """Selbstmörder kann aktiv Hinweise senden."""
        return HinweisConfig(
            kann_senden=True,
            verfuegbare_hinweise=["selbst_verdaechtigung", "nervoes", "stolpern", "blick_abwenden"],
            hinweise_pro_tag=3,
            basis_chance=0.0,
            beschreibung="Mache dich verdächtig und lass dich hängen!",
        )

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=100,
            name="Selbstmoerder",
            team=Team.SOLO,
            kategorie=Kategorie.SOLO,
            beschreibung=(
                "Du bist der Selbstmörder. Dein Ziel: Vom Dorf gehängt "
                "werden! Du gewinnst nur so - stirbst du durch Wölfe, "
                "verlierst du. Mache dich verdächtig!"
            ),
            icon="fa-solid fa-skull",
            farbe="#78716c",
            prioritaet=100,
            hinweis_config="Selbstmörder",
        )

    def is_active_on_first_night(self) -> bool:
        """Selbstmörder is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Selbstmörder is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Selbstmörder's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Selbstmörder - Passive Rolle",
            instructions="Mache dich verdächtig und lass dich hängen!",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob der Selbstmörder gehängt wird.
        """
        if opfer.id == spieler.id:
            self.set_state(spieler, "gewonnen", True)
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Der Selbstmörder hat es geschafft! Er wurde vom Dorf "
                    "gehängt und hat sein Ziel erreicht! Er gewinnt alleine!"
                ),
                effekte={
                    "spiel_ende": True,
                    "gewinner": "selbstmoerder",
                },
                log_sichtbar_fuer="alle",
            )

        return None

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Gewinnt nur wenn gehängt.
        """
        wurde_gehaengt = self.get_state(spieler, "gewonnen")
        if wurde_gehaengt:
            return Team.SOLO
        return None
