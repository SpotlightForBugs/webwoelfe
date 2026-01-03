"""
Hure - Besucht andere Spieler und entgeht Angriffen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Hure(Role):
    """
    Die Hure - Naechtliche Besuche.

    Faehigkeiten:
    - Besucht jede Nacht einen Spieler
    - Entgeht Angriffen auf ihr eigenes Haus
    - Stirbt wenn sie bei einem Werwolf uebernachtet

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=191,
            name="Hure",
            team=Team.DORF,
            kategorie=Kategorie.SPEZIAL,
            beschreibung=(
                "Du bist die Hure. Jede Nacht besuchst du einen Spieler. "
                "Wirst du zuhause angegriffen, ueberlebst du. Aber wenn du "
                "bei einem Werwolf uebernachtest, stirbst du!"
            ),
            icon="fa-solid fa-heart",
            farbe="#f43f5e",
            nacht_aktiv=True,
            prioritaet=45,
            erzaehler_nacht=("Die Hure erwacht und waehlt bei wem sie uebernachtet."),
        )

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Hure besucht einen Spieler.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du bleibst diese Nacht zuhause.",
                effekte={"bleibt_zuhause": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        from ..registry import RoleRegistry

        ziel_rolle = RoleRegistry.get(ziel.rolle)

        ist_werwolf = False
        if ziel_rolle:
            ist_werwolf = ziel_rolle.info.team == Team.WERWOLF

        if ist_werwolf:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"Du besuchst {ziel.name}... ein Werwolf! Du stirbst!",
                ziel_spieler_id=ziel.id,
                effekte={
                    "besucht": ziel.id,
                    "stirbt_bei_werwolf": True,
                },
                log_sichtbar_fuer="erzaehler",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du uebernachtest bei {ziel.name}.",
            ziel_spieler_id=ziel.id,
            effekte={
                "besucht": ziel.id,
                "nicht_zuhause": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
