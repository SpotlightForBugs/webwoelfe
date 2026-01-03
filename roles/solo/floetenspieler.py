"""
Floetenspieler - Verzaubert alle Spieler.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Floetenspieler(Role):
    """
    Der Floetenspieler - Verzauberungs-Solo.

    Faehigkeiten:
    - Kann jede Nacht 2 Spieler verzaubern
    - Gewinnt wenn alle Lebenden verzaubert sind

    Gewinnbedingung: Alle Lebenden sind verzaubert.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=101,
            name="Floetenspieler",
            team=Team.SOLO,
            kategorie=Kategorie.SOLO,
            beschreibung=(
                "Du bist der Floetenspieler. Jede Nacht verzauberst du "
                "2 Spieler mit deiner Floete. Du gewinnst wenn alle "
                "lebenden Spieler verzaubert sind!"
            ),
            icon="fa-solid fa-wand-magic-sparkles",
            farbe="#8b5cf6",
            nacht_aktiv=True,
            prioritaet=70,
            erzaehler_nacht=(
                "Der Floetenspieler erwacht und waehlt 2 Spieler " "zum Verzaubern."
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.VERZAUBERN

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Floetenspieler verzaubert Spieler.
        """
        # Vereinfachte Version - normalerweise 2 Ziele
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du spielst leise vor dich hin.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du verzauberst {ziel.name} mit deiner Melodie.",
            ziel_spieler_id=ziel.id,
            effekte={
                "verzaubert": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Gewinnt wenn alle Lebenden verzaubert sind.
        """
        # Diese Logik muesste die verzauberten Spieler pruefen
        # Vereinfachte Version
        return None
