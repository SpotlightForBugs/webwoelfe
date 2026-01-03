"""
Tanklastwagenfahrer - Der Überfahrer.

Einmal pro Spiel kann der Tanklastwagenfahrer
am Tag jemanden überfahren.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Tanklastwagenfahrer(Role):
    """
    Tanklastwagenfahrer - Einmal-Tag-Kill.

    Fähigkeiten:
    - Einmal pro Spiel am Tag aktivierbar
    - Überfährt einen Spieler
    - Sofortiger Tod

    Besonderheiten:
    - Sehr direkt und effektiv
    - Keine Verteidigung möglich
    - Einmalig

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=54,
            name="Tanklastwagenfahrer",
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der Tanklastwagenfahrer. Einmal pro Spiel kannst du "
                "während des Tages jemanden überfahren - dieser Spieler "
                "stirbt sofort!"
            ),
            icon="fa-solid fa-truck",
            farbe="#64748b",
            nacht_aktiv=False,
            prioritaet=92,
            erzaehler_nacht=(
                "Der Tanklastwagenfahrer parkt seinen Laster. "
                "Er wartet auf den richtigen Moment."
            ),
            erzaehler_tag=(
                "HUUUP! Der Tanklastwagenfahrer startet seinen Motor "
                "und überfährt sein Ziel! Keine Chance zu überleben!"
            ),
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    def ist_einmal_faehigkeit(self) -> bool:
        """Kann nur einmal überfahren."""
        return True

    def ist_tag_aktiv(self, spieler: "Spieler", kontext: SpielKontext) -> bool:
        """
        Nur aktiv wenn noch nicht gefahren.
        """
        return not getattr(spieler, "trucker_gefahren", False)

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def ueberfahren(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Überfährt einen Spieler - sofortiger Tod.
        """
        if getattr(spieler, "trucker_gefahren", False):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deinen Laster bereits benutzt!",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nur lebende Spieler überfahren!",
            )

        spieler.trucker_gefahren = True

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"HUUUP! Du überfährst {ziel.name} mit deinem Tanklaster!",
            ziel_spieler_id=ziel.id,
            effekte={
                "trucker_toetet": ziel.id,
                "trucker_gefahren": True,
                "todesursache": "ueberfahren",
            },
            log_sichtbar_fuer="alle",
        )
