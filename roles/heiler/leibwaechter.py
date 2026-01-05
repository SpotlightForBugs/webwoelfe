"""
Leibwächter - Kann sich für einen anderen opfern.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Leibwaechter(Role):
    """
    Der Leibwächter - Selbstopfer für Schutz.

    Fähigkeiten:
    - Wählt jede Nacht jemanden zum Beschützen
    - Wenn Schützling angegriffen wird: Stirbt an seiner Stelle

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=61,
            name="Leibwächter",
            team=Team.DORF,
            kategorie=Kategorie.HEILER,
            beschreibung=(
                "Du bist der Leibwächter. Du wählst jede Nacht jemanden "
                "zum Beschützen. Wird dieser angegriffen, stirbst du an "
                "seiner Stelle!"
            ),
            icon="fa-solid fa-shield-halved",
            farbe="#0ea5e9",
            prioritaet=54,
            erzaehler_nacht=("Der Leibwächter erwacht und wählt seinen Schützling."),
            erweiterung=Erweiterung.SONDEREDITION,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SCHUETZEN

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    def is_active_on_first_night(self) -> bool:
        """Leibwächter acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Leibwächter acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Leibwächter's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Leibwächter - Schützen",
            instructions="Wähle einen Spieler, den du mit deinem Leben beschützt.",
            buttons=[
                UIButton(
                    label="Beschützen",
                    action_type="schuetzen",
                    icon="fa-solid fa-shield-halved",
                    css_class="btn-primary",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Leibwächter wählt seinen Schützling.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst jemanden beschützen.",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du beschützt {ziel.name} mit deinem Leben.",
            ziel_spieler_id=ziel.id,
            effekte={
                "leibwaechter_schuetzt": ziel.id,
                "opfert_sich_fuer": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
