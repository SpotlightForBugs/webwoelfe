"""
Heiler - Schützt Spieler vor nächtlichen Angriffen.

Der Heiler kann jede Nacht einen Spieler schützen,
aber nicht zweimal hintereinander denselben.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext, StateField, StateType
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Heiler(Role):
    """
    Der Heiler - Schutz-Rolle.

    Fähigkeiten:
    - Kann jede Nacht einen Spieler schützen
    - Nicht zweimal hintereinander denselben Spieler

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Heilers."""
        return [
            StateField("letztes_ziel", StateType.PLAYER_ID, None, "Zuletzt geschützter Spieler"),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=6,
            name="Heiler",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist der Heiler. Jede Nacht kannst du einen Spieler vor "
                "dem Werwolf-Angriff schützen. Du darfst nicht zweimal "
                "hintereinander denselben Spieler schützen!"
            ),
            icon="fa-solid fa-heart-pulse",
            farbe="#10b981",
            prioritaet=55,
            erzaehler_nacht=(
                "Der Heiler erwacht und zeigt auf den Spieler, den er diese "
                "Nacht beschützen möchte. Nicht denselben wie letzte Nacht!"
            ),
            erweiterung=Erweiterung.NEUMOND,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SCHUETZEN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Heiler acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Heiler acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Heiler's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Heiler - Spieler schützen",
            instructions="Wähle einen Spieler, den du diese Nacht schützen möchtest. Du kannst nicht zweimal hintereinander denselben Spieler schützen.",
            buttons=[
                UIButton(
                    label="Schützen",
                    action_type="schuetzen",
                    icon="fa-solid fa-heart-pulse",
                    css_class="btn-success",
                    requires_confirmation=False,
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,  # Must act
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Heiler schützt einen Spieler.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst jemanden zum Schützen wählen.",
            )

        # Prüfe ob es das gleiche Ziel wie letzte Nacht ist
        letztes_ziel = self.get_state(spieler, "letztes_ziel")

        if letztes_ziel == ziel.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht=(
                    "Du kannst nicht zweimal hintereinander denselben "
                    "Spieler schützen!"
                ),
            )

        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel.",
            )

        # Speichere das aktuelle Ziel für die nächste Runde
        self.set_state(spieler, "letztes_ziel", ziel.id)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du beschützt {ziel.name} diese Nacht.",
            ziel_spieler_id=ziel.id,
            effekte={
                "geschuetzt": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
