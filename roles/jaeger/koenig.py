"""
König - Doppelstimme bei Abstimmungen.

Der König hat doppeltes Stimmgewicht. Wenn er stirbt,
wählt das Dorf einen neuen König.
"""

from typing import Optional, TYPE_CHECKING
from ..base import RollenModell, Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
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
            prioritaet=95,
            erzaehler_nacht=(
                "Der König ruht auf seinem Thron. "
                "Seine Stimme wiegt schwerer als alle anderen."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#ca8a04",
            avatar_gradient_to="#a16207",
            avatar_border_color="#eab308",
            badge_emoji="👑",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """König does not act at night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """König is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for König's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="König - Passive Rolle",
            instructions="Deine Stimme zählt doppelt bei Abstimmungen.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

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

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Koenig."""
        return RollenModell(
            modell_id="koenig",
            anzeige_name="Koenig",
            beschreibung="Koenig appearance in Village 3D",
        )
