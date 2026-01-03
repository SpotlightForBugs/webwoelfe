"""
König - Doppelstimme bei Abstimmungen.

Der König hat doppeltes Stimmgewicht. Wenn er stirbt,
wählt das Dorf einen neuen König.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Koenig(Role):
    """
    König - Passive Abstimmungsrolle.

    Fähigkeiten:
    - Stimme zählt doppelt bei Abstimmungen
    - Bei Tod wird ein neuer König gewählt

    Besonderheiten:
    - Sehr einflussreich bei Abstimmungen
    - Der neue König übernimmt die Fähigkeit

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=56,
            name="König",
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der König. Deine Stimme zählt doppelt bei "
                "allen Abstimmungen! Aber wenn du stirbst, darf das Dorf "
                "einen neuen König wählen."
            ),
            icon="fa-solid fa-chess-king",
            farbe="#ca8a04",
            nacht_aktiv=False,
            prioritaet=95,
            erzaehler_nacht=(
                "Der König ruht auf seinem Thron. "
                "Seine Stimme wiegt schwerer als alle anderen."
            ),
            erzaehler_tag=(
                "Der König ist gefallen! Sein Erbe muss bestimmt werden - "
                "das Dorf wählt einen neuen König mit doppelter Stimme!"
            ),
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.PASSIV

    def get_stimm_gewicht(self, spieler: "Spieler", kontext: SpielKontext) -> int:
        """
        König hat doppeltes Stimmgewicht.
        """
        return 2

    def on_abstimmung(
        self, spieler: "Spieler", kandidat_id: int, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Königs Stimme zählt doppelt - wird von game_logic beachtet.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Deine königliche Stimme zählt doppelt!",
            effekte={
                "stimm_gewicht": 2,
                "extra_stimmen": 1,  # Eine zusätzliche Stimme
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_eigener_tod(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Bei Tod des Königs wird ein neuer gewählt.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Der König ist tot! Das Dorf muss einen neuen König wählen.",
            effekte={
                "koenig_wahl_erforderlich": True,
                "thronfolge": True,
            },
            log_sichtbar_fuer="alle",
        )
