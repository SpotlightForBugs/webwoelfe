"""
Kamikaze - Opfert sich um einen Werwolf zu toeten.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Kamikaze(Role):
    """
    Der Kamikaze - Selbstopfer.

    Fähigkeiten:
    - Kann sich einmal opfern um einen anderen Spieler zu töten
    - Beide sterben

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=71,
            name="Kamikaze",
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der Kamikaze. Du kannst dich einmal opfern und "
                "dabei einen anderen Spieler mit in den Tod reissen. "
                "Nutze diese Fähigkeit weise!"
            ),
            icon="fa-solid fa-bomb",
            farbe="#f97316",
            nacht_aktiv=True,
            prioritaet=90,
            erzaehler_nacht=(
                "Der Kamikaze erwacht. Möchte er sich opfern und "
                "jemanden mit in den Tod reissen?"
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.OPFERN

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Kamikaze opfert sich.
        """
        kann_opfern = getattr(spieler, "kamikaze_bombe", True)

        if not kann_opfern:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deine Bombe bereits gezündet.",
            )

        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du wartest auf den richtigen Moment.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du opferst dich und nimmst {ziel.name} mit!",
            ziel_spieler_id=ziel.id,
            effekte={
                "kamikaze_opfer": ziel.id,
                "selbst_geopfert": True,
                "kamikaze_bombe_verbraucht": True,
            },
            log_sichtbar_fuer="alle",
        )
