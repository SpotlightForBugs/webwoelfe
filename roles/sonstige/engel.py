"""
Engel - Gewinnt bei frühem Tod.

Der Engel gewinnt nur wenn er in der ersten Runde
stirbt. Danach wird er zum normalen Dorfbewohner.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext, RollenModell
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Engel(Role):
    """
    Engel - Sieg durch frühen Tod.

    Fähigkeiten:
    - Passive Rolle
    - Gewinnt bei Tod in Runde 1
    - Wird danach zum Dorfbewohner

    Besonderheiten:
    - Sehr riskante Rolle
    - Muss sich verdächtig machen
    - Nach Runde 1: Normales Dorf-Ziel

    Gewinnbedingung: Stirbt in Runde 1.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=99,
            name="Engel",
            team=Team.SOLO,
            kategorie=Kategorie.SONSTIGE,
            beschreibung=(
                "Du bist der Engel. Du gewinnst NUR wenn du in der ersten "
                "Runde (Tag oder Nacht) stirbst! Danach wirst du zum "
                "normalen Dorfbewohner."
            ),
            icon="fa-solid fa-feather",
            farbe="#fef3c7",
            prioritaet=100,
            erzaehler_nacht=(
                "Der Engel wartet sehnsüchtig auf seinen frühen Tod, "
                "um in den Himmel aufzusteigen."
            ),
            erzaehler_tag=(
                "Der Engel ist in der ersten Runde gestorben! "
                "Seine Flügel erstrahlen und er steigt siegreich "
                "in den Himmel auf!"
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            hinweis_config="Engel",
            # Visual Styling
            avatar_gradient_from="#fef3c7",
            avatar_gradient_to="#fde68a",
            avatar_border_color="#fef08a",
            badge_emoji="😇",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Engel is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Engel is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Engel's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Engel - Passive Rolle",
            instructions="Versuche in der ersten Runde zu sterben!",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    @property
    def kann_hinweis_senden(self) -> bool:
        """Engel kann Hinweise senden um sich verdächtig zu machen."""
        return True

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob der Engel in der ersten Runde stirbt.
        """
        aktuelle_runde = getattr(kontext, "aktuelle_runde", kontext.runde)
        if aktuelle_runde == 1:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="HALLELUJA! Der Engel ist in der ersten Runde gestorben! "
                "Er steigt in den Himmel auf und GEWINNT!",
                effekte={
                    "engel_gewonnen": True,
                    "spiel_ende": False,  # Spiel geht weiter, aber Engel gewinnt
                    "solo_gewinner": spieler.id,
                },
                log_sichtbar_fuer="alle",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht="Der Engel stirbt als einfacher Dorfbewohner...",
            effekte={},
            log_sichtbar_fuer="alle",
        )

    def on_tag_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Nach Runde 1 wird der Engel zum Dorfbewohner.
        """
        if kontext.aktuelle_runde > 1 and not getattr(
            spieler, "engel_verwandelt", False
        ):
            spieler.engel_verwandelt = True
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Deine Zeit als Engel ist vorbei. "
                "Du bist jetzt ein einfacher Dorfbewohner.",
                effekte={
                    "team_wechsel": Team.DORF.value,
                    "engel_zu_dorf": True,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return None

    def berechne_aktuelles_team(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Team:
        """
        Nach Runde 1: Team Dorf.
        """
        if kontext.aktuelle_runde > 1:
            return Team.DORF
        return Team.SOLO

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Engel."""
        return RollenModell(
            modell_id="engel",
            anzeige_name="Engel",
            beschreibung="Ein himmlischer Engel mit leuchtenden Flügeln",
        )
