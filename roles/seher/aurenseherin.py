"""
Aurenseherin - Sieht die Aura statt die konkrete Rolle.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Aurenseherin(Role):
    """
    Die Aurenseherin - Alternative Informationsrolle.

    Fähigkeiten:
    - Sieht ob ein Spieler "gut" oder "böse" ist
    - Kann durch manche Tarnungen durchschauen

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=51,
            name="Aurenseherin",
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                "Du bist die Aurenseherin. Du siehst nicht die konkrete "
                "Rolle, sondern ob jemand eine gute oder böse Aura hat."
            ),
            icon="fa-solid fa-circle-radiation",
            farbe="#a78bfa",
            nacht_aktiv=True,
            prioritaet=22,
            erzaehler_nacht=(
                "Die Aurenseherin erwacht und wählt einen Spieler. "
                "Zeige: Goldenes Licht (gut) oder dunkler Schatten (böse)."
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Aurenseherin sieht die Aura eines Spielers.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst einen Spieler wählen.",
            )

        from ..registry import RoleRegistry

        ziel_rolle = RoleRegistry.get(ziel.rolle)

        if ziel_rolle:
            team = ziel_rolle.info.team
            ist_boese = team in [Team.WERWOLF, Team.SOLO]
        else:
            ist_boese = False

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} hat eine {'dunkle' if ist_boese else 'helle'} Aura.",
            ziel_spieler_id=ziel.id,
            effekte={
                "aura_gesehen": ziel.id,
                "ist_boese": ist_boese,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
