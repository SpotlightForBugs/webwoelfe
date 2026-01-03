"""
Gerber - Alle verlieren wenn er gehängt wird.

Der Gerber gewinnt wenn er gehängt wird.
Anders als Selbstmörder: Alle anderen verlieren!
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Gerber(Role):
    """
    Gerber - Destruktiver Sieg.

    Fähigkeiten:
    - Passive Rolle
    - Gewinnt wenn gehängt
    - Alle anderen verlieren dann!

    Besonderheiten:
    - Sehr gefährlich fürs Dorf
    - Muss sich verdächtig machen
    - Unterschied zu Selbstmörder: Fluch auf alle

    Gewinnbedingung: Wird gehängt (alle anderen verlieren).
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=92,
            name="Gerber",
            team=Team.SOLO,
            kategorie=Kategorie.SONSTIGE,
            beschreibung=(
                "Du bist der Gerber. Du gewinnst wenn du gehängt wirst! "
                "Aber anders als der Selbstmörder - wenn du gewinnst, "
                "verlieren ALLE anderen!"
            ),
            icon="fa-solid fa-face-angry",
            farbe="#78350f",
            nacht_aktiv=False,
            prioritaet=100,
            erzaehler_nacht=(
                "Der Gerber arbeitet an seinen stinkenden Fellen. "
                "Ein verbitterter Mann mit einem düsteren Plan."
            ),
            erzaehler_tag=(
                "ÜBERRASCHUNG! Der Gerber wurde gehängt und er lacht "
                "triumphierend! Sein Fluch verflucht das gesamte Dorf - "
                "ALLE verlieren außer ihm!"
            ),
            hinweis_config="Gerber",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.PASSIV

    @property
    def kann_hinweis_senden(self) -> bool:
        """Gerber kann Hinweise senden um sich verdächtig zu machen."""
        return True

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob der Gerber gehängt wird.
        """
        if opfer.id == spieler.id:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="FLUCH! Der Gerber wurde gehängt! "
                "Sein Fluch verflucht alle anderen - "
                "NUR der Gerber gewinnt, alle anderen verlieren!",
                effekte={
                    "gerber_gewonnen": True,
                    "spiel_ende": True,
                    "alle_verlieren": True,
                    "gewinner": "gerber",
                },
                log_sichtbar_fuer="alle",
            )

        return None

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Gerber gewinnt nur wenn gehängt.
        """
        if getattr(spieler, "gerber_gewonnen", False):
            return Team.SOLO
        return None
