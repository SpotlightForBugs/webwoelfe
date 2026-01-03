"""
Nutte - Übernachtet bei anderen Spielern.

Die Nutte besucht jede Nacht einen Spieler.
Sie entgeht Angriffen zuhause, stirbt aber wenn ihr Gastgeber stirbt.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Nutte(Role):
    """
    Nutte - Besuchsrolle mit Risiko.

    Fähigkeiten:
    - Besucht jede Nacht einen Spieler
    - Entgeht Angriffen auf ihr eigenes Haus
    - Stirbt wenn Gastgeber getötet wird

    Besonderheiten:
    - Risiko-Rolle
    - Kann bei Wolf übernachten und sterben
    - Aber auch sich vor Angriffen schützen

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=77,
            name="Nutte",
            team=Team.DORF,
            kategorie=Kategorie.SPEZIAL,
            beschreibung=(
                "Du bist die Nutte. Jede Nacht wählst du einen Spieler, "
                "bei dem du übernachtest. Wird dieser von Werwölfen getötet, "
                "stirbst auch du! Aber: Wirst du selbst gewählt, überlebst du "
                "(du bist ja nicht zuhause)."
            ),
            icon="fa-solid fa-house-user",
            farbe="#ec4899",
            nacht_aktiv=True,
            prioritaet=47,
            erzaehler_nacht=(
                "Die Nutte erwacht und wählt einen Spieler, " "bei dem sie übernachtet."
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.BESUCHEN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Nutte besucht einen Spieler und übernachtet dort.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du bleibst heute Nacht zuhause.",
                effekte={
                    "nutte_zuhause": True,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst keine Toten besuchen.",
            )

        # Speichern wo die Nutte übernachtet
        spieler.nutte_bei = ziel.id

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du übernachtest bei {ziel.name}. "
            f"Hoffentlich überlebt er die Nacht...",
            ziel_spieler_id=ziel.id,
            effekte={
                "nutte_besucht": ziel.id,
                "nicht_zuhause": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_angegriffen(
        self, spieler: "Spieler", angreifer_id: int, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn Nutte nicht zuhause ist, überlebt sie den Angriff.
        """
        nutte_bei = getattr(spieler, "nutte_bei", None)

        if nutte_bei is not None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du warst nicht zuhause - der Angriff geht ins Leere!",
                effekte={
                    "angriff_abgewehrt": True,
                    "nicht_zuhause": True,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return None  # Zuhause = normaler Angriff

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        gestorbener: "Spieler",
        todesursache: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn der Gastgeber stirbt, stirbt die Nutte mit.
        """
        nutte_bei = getattr(spieler, "nutte_bei", None)

        if nutte_bei is not None and gestorbener.id == nutte_bei:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du warst bei deinem Gastgeber als er starb - du stirbst mit!",
                effekte={
                    "nutte_stirbt_mit": True,
                    "todesursache": "gastgeber_tot",
                },
                log_sichtbar_fuer="alle",
            )

        return None
