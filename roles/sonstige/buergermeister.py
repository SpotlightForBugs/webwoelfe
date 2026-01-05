"""
Bürgermeister - Doppelte Stimme bei Abstimmungen, kann Nachfolger bestimmen
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Buergermeister(Role):
    """
    Bürgermeister

    Die Stimme des Bürgermeisters zählt doppelt bei Abstimmungen.
    Wenn der Bürgermeister stirbt, kann er einen Nachfolger bestimmen,
    der sein Amt (und die doppelte Stimme) erbt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=97,
            name="Bürgermeister",
            team=Team.DORF,
            kategorie=Kategorie.SONSTIGE,
            beschreibung="Du bist der Bürgermeister. Deine Stimme zählt doppelt! Bei deinem Tod bestimmst du deinen Nachfolger, der deine Macht erbt.",
            icon="fa-solid fa-user-tie",
            farbe="#1e40af",
            prioritaet=95,
            erzaehler_nacht="Der Bürgermeister ruht in seinem Rathaus. Seine Stimme hat doppeltes Gewicht.",
            erzaehler_tag="Der Bürgermeister ist gefallen! Mit letzter Kraft zeigt er auf seinen Nachfolger, der das Amt und die doppelte Stimme erbt!",
            hinweis_config=None,
            erweiterung=Erweiterung.CHARAKTERE,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.WAEHLEN

    def is_active_on_first_night(self) -> bool:
        """Bürgermeister is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Bürgermeister is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Bürgermeister's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Bürgermeister - Passive Rolle",
            instructions="Deine Stimme zählt doppelt. Bei Tod wählst du einen Nachfolger.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """Bürgermeister-Status initialisieren."""
        spieler.ist_buergermeister = True
        spieler.stimmen_gewicht = 2

        return AktionsErgebnis(
            erfolg=True,
            nachricht="👔 Du bist der Bürgermeister! Deine Stimme zählt doppelt bei Abstimmungen.",
            effekte={"ist_buergermeister": True, "stimmen_gewicht": 2},
        )

    def on_abstimmung(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Die Stimme des Bürgermeisters zählt doppelt.
        """
        if not getattr(spieler, "ist_buergermeister", True):
            return None

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"👔 Du hast für {ziel.name} gestimmt. Deine Stimme zählt doppelt!",
            effekte={"stimmen_gewicht": 2, "ziel_id": ziel.id},
        )

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn der Bürgermeister stirbt, darf er einen Nachfolger wählen.
        Der Nachfolger erbt die doppelte Stimme.
        """
        # Sammle alle lebenden Spieler für die Nachfolger-Auswahl
        lebende_spieler = []
        for spieler_id in kontext.lebende_spieler:
            if spieler_id != spieler.id:
                lebende_spieler.append(spieler_id)

        if not lebende_spieler:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="💀 Der Bürgermeister ist gestorben. Es gibt niemanden der das Amt übernehmen könnte.",
                effekte={"amt_erloschen": True},
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht="💀 Du stirbst! Mit letzter Kraft darfst du deinen Nachfolger als Bürgermeister bestimmen!",
            effekte={
                "nachfolger_waehlen": True,
                "verfuegbare_nachfolger": lebende_spieler,
            },
        )

    def waehle_nachfolger(
        self, spieler: "Spieler", nachfolger: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Der sterbende Bürgermeister wählt seinen Nachfolger.
        Der Nachfolger erhält die doppelte Stimme.
        """
        # Übertrage Bürgermeister-Status
        nachfolger.ist_buergermeister = True
        nachfolger.stimmen_gewicht = 2

        # Entferne Status vom alten Bürgermeister
        spieler.ist_buergermeister = False
        spieler.stimmen_gewicht = 1

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"👔 {nachfolger.name} wurde zum neuen Bürgermeister ernannt! Seine Stimme zählt nun doppelt.",
            effekte={
                "neuer_buergermeister_id": nachfolger.id,
                "amt_uebertragen": True,
                "oeffentlich": True,  # Das Dorf erfährt wer der neue Bürgermeister ist
            },
        )
