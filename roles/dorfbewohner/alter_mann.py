"""
Alter Mann - Zäh aber gefährlich für das Dorf.

Der Alte Mann überlebt den ersten Werwolf-Angriff,
aber wenn das Dorf ihn hängt, verlieren alle Spezialrollen ihre Kräfte.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class AlterMann(Role):
    """
    Der Alte Mann - Robuste Dorfrolle mit Risiko.

    Fähigkeiten:
    - Überlebt den ersten Werwolf-Angriff
    - Bei Hinrichtung: Alle Spezialrollen verlieren Fähigkeiten

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=11,
            name="Alter Mann",
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist der Alte Mann. Du überlebst den ersten "
                "Werwolf-Angriff! Aber Vorsicht: Wirst du vom Dorf gehängt, "
                "verlieren alle Spezialrollen ihre Fähigkeiten."
            ),
            icon="fa-solid fa-person-cane",
            farbe="#78716c",
            prioritaet=98,
            erzaehler_nacht=(
                "Der Alte Mann schläft tief. Seine zähe Haut hat "
                "schon manchen Biss überstanden."
            ),
            erweiterung=Erweiterung.NEUMOND,
            erzaehler_tag=(
                "Der Alte Mann erwacht. Falls er von Woelfen angegriffen "
                "wurde, hat er überlebt! Aber Vorsicht: Hängt das Dorf ihn, "
                "verlieren alle Spezialrollen ihre Kräfte."
            ),
        )

    def is_active_on_first_night(self) -> bool:
        """Alter Mann does not act at night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Alter Mann is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Alter Mann's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Alter Mann - Passive Rolle",
            instructions="Du bist zäh und überlebst den ersten Angriff.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_angegriffen(
        self, spieler: "Spieler", angreifer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Der Alte Mann überlebt den ersten Angriff.
        """
        leben = getattr(spieler, "alter_mann_leben", 2)

        if leben > 1:
            return AktionsErgebnis(
                erfolg=False,  # False = Angriff wird geblockt
                nachricht="Der Alte Mann überlebt den Angriff!",
                effekte={
                    "alter_mann_leben": leben - 1,
                    "angriff_geblockt": True,
                },
                log_sichtbar_fuer="erzaehler",
            )

        return None  # Normaler Tod

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn der Alte Mann gehängt wird, verflucht er das Dorf.
        """
        if opfer.id == spieler.id:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Der Alte Mann wurde vom Dorf gehängt! "
                    "Vor Enttäuschung verflucht er das Dorf - "
                    "alle Spezialrollen verlieren ihre Fähigkeiten!"
                ),
                effekte={
                    "dorf_verflucht": True,
                    "spezialrollen_deaktiviert": True,
                },
                log_sichtbar_fuer="alle",
            )

        return None
