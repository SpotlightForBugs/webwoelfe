"""
Wolfsjunge - Wird zum Werwolf wenn Vorbild stirbt.

Der Wolfsjunge waehlt in der ersten Nacht ein Vorbild.
Stirbt dieses, verwandelt er sich in einen Werwolf.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Wolfsjunge(Role):
    """
    Das Wolfsjunge (Wildes Kind) - Bedingte Verwandlung.

    Faehigkeiten:
    - Waehlt in der ersten Nacht ein Vorbild
    - Stirbt das Vorbild: Wird zum Werwolf
    - Solange Vorbild lebt: Teil des Dorfes

    Gewinnbedingung: Abhaengig von Verwandlung.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=24,
            name="Wolfsjunge",
            team=Team.DORF,  # Startet als Dorf
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist das Wolfsjunge. Du waehlst in der ersten Nacht "
                "ein Vorbild. Solange dein Vorbild lebt, gehoerst du zum "
                "Dorf. Stirbt es, wirst du zum Werwolf!"
            ),
            icon="fa-solid fa-child",
            farbe="#92400e",
            nacht_aktiv=True,
            prioritaet=7,
            erzaehler_nacht=(
                "Das Wolfsjunge erwacht (nur erste Nacht) und waehlt " "sein Vorbild."
            ),
        )

    @property
    def sichtbar_als(self) -> SichtTyp:
        # Sieht als Dorf aus, bis Verwandlung
        return SichtTyp.DORF

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wolfsjunge waehlt sein Vorbild in der ersten Nacht.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Waehle dein Vorbild.",
            effekte={"warte_auf_vorbild_wahl": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def vorbild_waehlen(
        self, spieler: "Spieler", vorbild: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Setzt das Vorbild.
        """
        if vorbild.id == spieler.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst dich nicht selbst als Vorbild waehlen.",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{vorbild.name} ist nun dein Vorbild.",
            ziel_spieler_id=vorbild.id,
            effekte={
                "vorbild": vorbild.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        opfer: "Spieler",
        todesursache: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """
        Prueft ob das Vorbild stirbt und Verwandlung ausloest.
        """
        vorbild_id = getattr(spieler, "vorbild_id", None)

        if vorbild_id and opfer.id == vorbild_id:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Das Vorbild des Wolfsjungen ist gestorben! "
                    "Es verwandelt sich in einen Werwolf!"
                ),
                effekte={
                    "verwandlung": True,
                    "neues_team": "werwolf",
                    "neue_rolle": "Werwolf",
                },
                log_sichtbar_fuer="erzaehler",
            )

        return None
