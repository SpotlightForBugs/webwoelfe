"""
Jesus - Der Auferstandene.

Jesus kann nach seinem Tod wieder auferstehen
und weiterspielen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Jesus(Role):
    """
    Jesus - Auferstehungs-Rolle.

    Fähigkeiten:
    - Kann einmalig nach 3 Tagen auferstehen
    - Auferstehung geschieht automatisch

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=17,
            name="Jesus",
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist Jesus. Wenn du stirbst, kannst du einmalig "
                "nach 3 Tagen auferstehen und weiterspielen! "
                "Die Auferstehung geschieht automatisch."
            ),
            icon="fa-solid fa-cross",
            farbe="#fbbf24",
            nacht_aktiv=False,
            prioritaet=97,
            erzaehler_nacht=(
                "Jesus ruht friedlich. Der Tod ist für ihn "
                "nur ein vorübergehender Zustand."
            ),
            erzaehler_tag=(
                "Falls Jesus vor 3 Tagen gestorben ist: Ein Wunder geschieht! "
                "Jesus erhebt sich und kehrt triumphierend ins Spiel zurück!"
            ),
        )

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Jesus startet den Auferstehungs-Timer.
        """
        kann_auferstehen = getattr(spieler, "jesus_auferstehung", True)

        if not kann_auferstehen:
            return None

        return AktionsErgebnis(
            erfolg=True,
            nachricht="Jesus ist gestorben... aber er wird wiederkommen!",
            effekte={
                "auferstehung_in_runden": 3,
                "auferstehung_runde": kontext.runde + 3,
            },
            log_sichtbar_fuer="erzaehler",
        )

    def on_tag_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob Jesus auferstehen sollte.
        """
        auferstehung_runde = getattr(spieler, "auferstehung_runde", None)

        if auferstehung_runde and kontext.runde >= auferstehung_runde:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Ein Wunder geschieht! Jesus ist nach 3 Tagen "
                    "von den Toten auferstanden!"
                ),
                effekte={
                    "auferstehung": True,
                    "jesus_auferstehung_verbraucht": True,
                },
                log_sichtbar_fuer="alle",
            )

        return None
