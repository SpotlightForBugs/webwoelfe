"""
Mordlustiger - Letzer Überlebender.

Der Mordlustige will als letzter überleben.
Jede Nacht kann er einen Spieler ermorden.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Mordlustiger(Role):
    """
    Mordlustiger - Solo-Killer.

    Fähigkeiten:
    - Kann jede Nacht einen Spieler ermorden
    - Unabhängig von Werwölfen

    Besonderheiten:
    - Solo-Rolle
    - Tötet zusätzlich zu Werwölfen
    - Sehr gefährlich für alle

    Gewinnbedingung: Als letzter überleben.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=78,
            name="Mordlustiger",
            team=Team.SOLO,
            kategorie=Kategorie.SPEZIAL,
            beschreibung=(
                "Du bist der Mordlustige. Du gewinnst, wenn du der letzte "
                "überlebende Spieler bist! Jede Nacht kannst du einen "
                "Spieler ermorden."
            ),
            icon="fa-solid fa-user-ninja",
            farbe="#7f1d1d",
            nacht_aktiv=True,
            prioritaet=49,
            erzaehler_nacht=(
                "Der Mordlustige erwacht und wählt sein nächtliches Opfer."
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.DORF  # Erscheint harmlos

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Mordlustiger tötet einen Spieler.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du lässt heute Nacht von deiner Mordlust ab...",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Dieses Ziel ist bereits tot.",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du schleichst zu {ziel.name} und begehst deinen Mord...",
            ziel_spieler_id=ziel.id,
            effekte={
                "mordlustiger_opfer": ziel.id,
                "todesursache": "mord",
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def pruefe_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob der Mordlustige der letzte Überlebende ist.
        """
        lebende = [
            sid
            for sid in kontext.spieler_rollen.keys()
            if sid not in kontext.tote_spieler
        ]

        if len(lebende) == 1 and spieler.id in lebende:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="DER LETZTE ÜBERLEBENDE! Der Mordlustige hat alle ermordet!",
                effekte={
                    "spiel_ende": True,
                    "gewinner": "mordlustiger",
                },
                log_sichtbar_fuer="alle",
            )

        return None
