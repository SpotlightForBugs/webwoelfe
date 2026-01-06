"""
Jesus - Der Auferstandene.

Jesus kann nach seinem Tod wieder auferstehen
und weiterspielen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import RollenModell, Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, Erweiterung, AktionsTyp
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
            prioritaet=97,
            erzaehler_nacht=(
                "Jesus ruht friedlich. Der Tod ist für ihn "
                "nur ein vorübergehender Zustand."
            ),
            erzaehler_tag=(
                "Falls Jesus vor 3 Tagen gestorben ist: Ein Wunder geschieht! "
                "Jesus erhebt sich und kehrt triumphierend ins Spiel zurück!"
            ),
            erweiterung=Erweiterung.SONDEREDITION,

            # Visual Styling
            avatar_gradient_from="#fbbf24",
            avatar_gradient_to="#d97706",
            avatar_border_color="#fcd34d",
            badge_emoji="✝️",
        )

    def is_active_on_first_night(self) -> bool:
        """Jesus is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Jesus is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Jesus' action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Jesus - Passive Rolle",
            instructions="Du stehst nach 3 Tagen wieder auf.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
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


    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Jesus."""
        return RollenModell(
            modell_id="jesus",
            anzeige_name="Jesus",
            beschreibung="Jesus appearance in Village 3D",
        )