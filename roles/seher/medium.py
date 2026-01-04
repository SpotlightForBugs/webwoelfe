"""
Medium - Kann mit Toten kommunizieren.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Medium(Role):
    """
    Das Medium - Kontakt zu den Toten.

    Fähigkeiten:
    - Kann jede Nacht die Rolle eines Toten erfahren

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=52,
            name="Medium",
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                "Du bist das Medium. Jede Nacht kannst du die Rolle "
                "eines verstorbenen Spielers erfahren."
            ),
            icon="fa-solid fa-ghost",
            farbe="#c084fc",
            prioritaet=25,
            erzaehler_nacht=(
                "Das Medium erwacht und wählt einen Toten. "
                "Flüster dem Medium die Rolle des Toten zu."
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN

    @property
    def erlaubte_ziele(self) -> str:
        return "tote"

    def is_active_on_first_night(self) -> bool:
        """Medium does not act on first night (no dead yet)."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Medium acts every night after first."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Medium's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Medium - Mit Toten sprechen",
            instructions="Wähle einen Toten, um seine Rolle zu erfahren.",
            buttons=[
                UIButton(
                    label="Geist befragen",
                    action_type="sehen",
                    icon="fa-solid fa-ghost",
                    css_class="btn-secondary",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Medium erfährt die Rolle eines Toten.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast diese Nacht keinen Toten befragt.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id not in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nur mit Toten sprechen.",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Der Geist von {ziel.name} flüstert: 'Ich war {ziel.rolle}'",
            ziel_spieler_id=ziel.id,
            effekte={
                "rolle_erfahren": ziel.rolle,
                "toter_befragt": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
