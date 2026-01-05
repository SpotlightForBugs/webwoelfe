"""
Urwolf - Kann Dorfbewohner infizieren.

Der Urwolf kann einmalig statt zu toeten
einen Dorfbewohner infizieren, der zum Werwolf wird.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Urwolf(Role):
    """
    Der Urwolf - Infektions-Werwolf.

    Faehigkeiten:
    - Jagt mit den Woelfen
    - Kann einmalig statt Toetung infizieren
    - Infizierte werden zu Werwoelfen

    Gewinnbedingung: Werwolf-Team gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=123,
            name="Urwolf",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Urwolf! Einmal pro Spiel kannst du statt "
                "zu toeten einen Dorfbewohner infizieren. Dieser wird "
                "zum Werwolf und erwacht in der naechsten Nacht mit euch."
            ),
            icon="fa-solid fa-virus",
            farbe="#7f1d1d",
            prioritaet=51,
            erzaehler_nacht=(
                "Der Urwolf hat die Moeglichkeit zu infizieren statt zu "
                "toeten. Moechte er seine Faehigkeit einsetzen?"
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.INFIZIEREN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    def is_active_on_first_night(self) -> bool:
        """Urwolf acts on first night with werwolves."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Urwolf acts every night with werwolves."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Urwolf's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Urwolf - Jagen oder Infizieren",
            instructions="Wähle das Opfer der Wölfe oder infiziere jemanden (einmalig).",
            buttons=[
                UIButton(
                    label="Angreifen",
                    action_type="toeten",
                    icon="fa-solid fa-paw",
                    css_class="btn-danger",
                ),
                UIButton(
                    label="Infizieren",
                    action_type="infizieren",
                    icon="fa-solid fa-virus",
                    css_class="btn-warning",
                    requires_confirmation=True,
                ),
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def infizieren(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Urwolf infiziert statt zu toeten.
        """
        kann_infizieren = getattr(spieler, "urwolf_infektion", True)

        if not kann_infizieren:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deine Infektions-Faehigkeit bereits verwendet.",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du hast {ziel.name} infiziert! Er wird zum Werwolf.",
            ziel_spieler_id=ziel.id,
            effekte={
                "infiziert": ziel.id,
                "urwolf_infektion_verbraucht": True,
                "wird_werwolf_in_runde": kontext.runde + 1,
            },
            log_sichtbar_fuer="werwolf",
        )
