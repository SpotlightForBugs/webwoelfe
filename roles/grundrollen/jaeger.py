"""
Jäger - Stirbt nicht kampflos.

Der Jäger kann bei seinem Tod einen letzten Schuss abfeuern
und einen beliebigen Spieler mit in den Tod reißen.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext, StateField, StateType
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Jaeger(Role):
    """
    Der Jäger - Todes-Trigger Rolle.

    Fähigkeiten:
    - Bei Tod: Kann einen Spieler erschießen (einmalig)

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Jägers."""
        return [
            StateField("schuss", StateType.BOOL, True, "Hat noch einen Schuss"),
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
                "Schuss abfeuern und einen Spieler deiner Wahl mit in den Tod "
                "reißen!"
            ),
            icon="fa-solid fa-crosshairs",
            farbe="#b45309",
            prioritaet=99,
            erzaehler_nacht=(
                "Der Jäger schläft mit seiner Flinte unter dem Kopfkissen. "
                "Bereit für seinen letzten Schuss."
            ),
            erzaehler_tag=(
                "Der Jäger ist gestorben! Mit zitternder Hand hebt er seine "
                "Flinte. Auf wen feuert er seinen letzten Schuss?"
            ),
            erweiterung=Erweiterung.BASISSPIEL,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SCHIESSEN

    def is_active_on_first_night(self) -> bool:
        """Jaeger does not act on first night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Jaeger does not act every night - only on death."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Jaeger's action panel (when dying)."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Jäger - Letzter Schuss",
            instructions="Du wurdest getötet! Wähle ein Ziel für deinen letzten Schuss.",
            buttons=[
                UIButton(
                    label="Schießen",
                    action_type="schiessen",
                    icon="fa-solid fa-crosshairs",
                    css_class="btn-danger",
                    requires_confirmation=True,
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=True,  # Can choose not to shoot
        )

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Jäger stirbt und kann seinen Schuss abfeuern.
        """
        hat_schuss = self.get_state(spieler, "schuss")

        if not hat_schuss:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Der Jäger hat seinen Schuss bereits verwendet.",
            )

        # Markiere dass Schuss verfügbar ist - Zielwahl kommt separat
        return AktionsErgebnis(
            erfolg=True,
            nachricht=(
                "Der Jäger wurde getötet! Mit seinem letzten Atemzug "
                "greift er zur Flinte!"
            ),
            effekte={
                "jaeger_schuss_verfuegbar": True,
                "warte_auf_zielwahl": True,
            },
            log_sichtbar_fuer="alle",
        )

    def schiessen(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Jäger feuert seinen letzten Schuss.
        """
        hat_schuss = self.get_state(spieler, "schuss")

        if not hat_schuss:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Kein Schuss mehr verfügbar.",
            )

        # Schuss verbrauchen
        self.set_state(spieler, "schuss", False)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Der Jäger erschießt {ziel.name} mit seinem letzten Schuss!",
            ziel_spieler_id=ziel.id,
            effekte={
                "erschossen": ziel.id,
            },
            log_sichtbar_fuer="alle",
        )
