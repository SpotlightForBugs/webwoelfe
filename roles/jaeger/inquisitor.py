"""
Inquisitor - Der Richter.

Einmal pro Spiel kann der Inquisitor am Tag einen Spieler
verhören - ist es ein Werwolf, stirbt er sofort.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Inquisitor(Role):
    """
    Inquisitor - Einmal-Tag-Fähigkeit.

    Fähigkeiten:
    - Einmal pro Spiel am Tag aktivierbar
    - Verhört einen Spieler
    - Ist es ein Werwolf, stirbt er sofort
    - Ist es kein Werwolf, passiert nichts

    Besonderheiten:
    - Sehr mächtig gegen Werwölfe
    - Risikofrei für den Verhörten wenn unschuldig
    - Einmalig

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=55,
            name="Inquisitor",
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der Inquisitor. Einmal pro Spiel kannst du während "
                "des Tages einen Spieler verhören - gesteht er nicht "
                "(Werwolf), stirbt er sofort!"
            ),
            icon="fa-solid fa-scale-balanced",
            farbe="#1e3a8a",
            prioritaet=91,
            erzaehler_nacht=(
                "Der Inquisitor schärft sein Schwert der Gerechtigkeit im Schlaf."
            ),
            erzaehler_tag=(
                'Der Inquisitor tritt vor! "Im Namen der Wahrheit - GESTEHE!" '
                "Ist das Ziel ein Werwolf, stirbt es auf der Stelle!"
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    def is_active_on_first_night(self) -> bool:
        """Inquisitor does not act at night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Inquisitor does not act at night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Inquisitor's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Inquisitor - Tagaktion",
            instructions="Du kannst einmal am Tag einen Spieler verhören. Werwölfe sterben sofort.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def ist_einmal_faehigkeit(self) -> bool:
        """Inquisitor kann nur einmal verhören."""
        return True

    def ist_tag_aktiv(self, spieler: "Spieler", kontext: SpielKontext) -> bool:
        """
        Nur aktiv wenn noch nicht verhört.
        """
        return not getattr(spieler, "inquisitor_verhoert", False)

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def verhoeren(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Verhört einen Spieler - Werwölfe sterben sofort.
        """
        if getattr(spieler, "inquisitor_verhoert", False):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast dein Verhör bereits durchgeführt!",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nur lebende Spieler verhören!",
            )

        spieler.inquisitor_verhoert = True

        # Prüfen ob Ziel ein Werwolf ist
        ziel_team = kontext.spieler_teams.get(ziel.id, Team.DORF)

        if ziel_team == Team.WERWOLF:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"SCHULDIG! {ziel.name} ist ein Werwolf und stirbt!",
                ziel_spieler_id=ziel.id,
                effekte={
                    "inquisitor_toetet": ziel.id,
                    "inquisitor_verhoert": True,
                    "todesursache": "inquisition",
                },
                log_sichtbar_fuer="alle",
            )
        else:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"{ziel.name} besteht das Verhör - kein Werwolf.",
                effekte={
                    "inquisitor_verhoert": True,
                    "verhoer_bestanden": ziel.id,
                },
                log_sichtbar_fuer="alle",
            )
