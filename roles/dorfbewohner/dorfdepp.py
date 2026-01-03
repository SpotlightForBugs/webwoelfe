"""
Dorfdepp - Will gehängt werden.

Der Dorfdepp gewinnt, wenn er vom Dorf gehängt wird.
Er kann sich aktiv verdächtig machen.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Dorfdepp(Role):
    """
    Der Dorfdepp - Solo-Sieg durch Hinrichtung.

    Fähigkeiten:
    - Kann sich aktiv verdächtig machen (Hinweise senden)
    - Gewinnt wenn vom Dorf gehängt
    - Gewinnt MIT dem eigentlichen Gewinner

    Gewinnbedingung: Wird vom Dorf gehängt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=12,
            name="Dorfdepp",
            team=Team.SOLO,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist der Dorfdepp. Du gewinnst, wenn du vom Dorf "
                "gehängt wirst. Du gewinnst zusätzlich mit dem "
                "eigentlichen Gewinner."
            ),
            icon="fa-solid fa-face-grin-tongue",
            farbe="#f59e0b",
            nacht_aktiv=False,
            prioritaet=100,
            erzaehler_nacht=(
                "Der Dorfdepp schläft und träumt davon, endlich "
                "ernst genommen zu werden... oder auch nicht."
            ),
            erzaehler_tag=(
                "Der Dorfdepp stolpert durch den Tag. Sein Ziel: "
                "So verdächtig wie möglich wirken, ohne ein Werwolf zu sein!"
            ),
            hinweis_config="Dorfdepp",
        )

    @property
    def kann_hinweis_senden(self) -> bool:
        return True

    @property
    def verfuegbare_hinweise(self) -> List[str]:
        return ["stolpern", "nervös"]

    @property
    def hinweise_pro_tag(self) -> int:
        return 2

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob der Dorfdepp gehängt wird.
        """
        if opfer.id == spieler.id:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Der Dorfdepp wurde gehängt! "
                    "Er hat sein Ziel erreicht und gewinnt mit!"
                ),
                effekte={
                    "dorfdepp_gewonnen": True,
                },
                log_sichtbar_fuer="alle",
            )

        return None

    def on_spiel_ende(
        self, spieler: "Spieler", gewinner_team: Team, kontext: SpielKontext
    ) -> bool:
        """
        Dorfdepp gewinnt mit, wenn er gehängt wurde.
        """
        wurde_gehaengt = getattr(spieler, "dorfdepp_gewonnen", False)
        return wurde_gehaengt  # Gewinnt mit dem normalen Gewinner
