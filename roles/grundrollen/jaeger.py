"""
Jäger - Stirbt nicht kampflos.

Der Jäger kann bei seinem Tod einen letzten Schuss abfeuern
und einen beliebigen Spieler mit in den Tod reißen.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Jaeger(Role):
    """
    Der Jäger - Rache-Rolle.

    Fähigkeiten:
    - Wenn er stirbt, kann er einen anderen Spieler mit in den Tod reißen.

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        return [
            StateField("schuss", StateType.BOOL, True, "Schuss bereit"),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=5,
            name="Jäger",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist der Jäger. Wenn du stirbst, kannst du einen letzten "
                "Schuss abfeuern und einen Spieler deiner Wahl mit in den Tod reißen."
            ),
            icon="fa-solid fa-crosshairs",
            farbe="#f97316",
            prioritaet=100,
            erzaehler_nacht=("Der Jäger schläft. Er wird nur aktiv, wenn er stirbt."),
            erweiterung=Erweiterung.BASISSPIEL,
            # Visual Styling
            avatar_gradient_from="#f97316",
            avatar_gradient_to="#c2410c",
            avatar_border_color="#fb923c",
            badge_emoji="🔫",
            distribution=DistributionConfig(
                min_players=5,
                count_func=lambda n: 1,
                priority=10,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Jäger does not act on first night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Jäger does not act every night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Jäger's action panel (only when dead)."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Jäger - Letzter Schuss",
            instructions="Du stirbst! Wähle jemanden, den du mit in den Tod reißen willst.",
            buttons=[
                UIButton(
                    label="Schießen",
                    action_type="jaeger_schuss",
                    icon="fa-solid fa-crosshairs",
                    css_class="btn-danger",
                    requires_confirmation=True,
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn der Jäger stirbt, darf er noch schießen.
        """
        if self.get_state(spieler, "schuss"):
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Der Jäger greift zu seiner Waffe!",
                effekte={"trigger_jaeger_phase": True},
                log_sichtbar_fuer="alle",
            )
        return None

    def on_spieler_stirbt(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn der Jäger stirbt, wird seine Phase aktiviert.
        """
        if opfer.id == spieler.id and self.get_state(spieler, "schuss"):
            # Jäger stirbt -> Trigger Jäger-Phase
            # Das wird aktuell in app.py gehandhabt ("jaeger_phase")
            # Aber wir können hier Effekte zurückgeben
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Der Jäger greift zu seiner Waffe!",
                effekte={"trigger_jaeger_phase": True},
                log_sichtbar_fuer="alle",
            )
        return None
