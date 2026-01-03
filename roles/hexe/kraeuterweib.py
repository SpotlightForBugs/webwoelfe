"""
Kraeuterweib - Kann Spieler stumm machen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Kraeuterweib(Role):
    """
    Das Kräuterweib - Stummheits-Rolle.

    Fähigkeiten:
    - Kann jede Nacht einen Spieler stumm machen
    - Stumme Spieler dürfen am nächsten Tag nicht reden

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=41,
            name="Kräuterweib",
            team=Team.DORF,
            kategorie=Kategorie.HEXE,
            beschreibung=(
                "Du bist das Kräuterweib. Jede Nacht kannst du einem "
                "Spieler einen Stumm-Trank verabreichen. Dieser darf am "
                "nächsten Tag nicht sprechen."
            ),
            icon="fa-solid fa-leaf",
            farbe="#22c55e",
            nacht_aktiv=True,
            prioritaet=65,
            erzaehler_nacht=(
                "Das Kräuterweib erwacht und wählt einen Spieler, "
                "der morgen stumm sein wird."
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.STUMM_MACHEN

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Kräuterweib macht einen Spieler stumm.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast diese Nacht niemanden stumm gemacht.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} wird morgen stumm sein.",
            ziel_spieler_id=ziel.id,
            effekte={
                "stumm_gemacht": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
