"""
Ergebene Magd - Die Nachfolgerin.

Die Ergebene Magd übernimmt die Rolle einer
wichtigen verstorbenen Person.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


# Wichtige Rollen die übernommen werden können
WICHTIGE_ROLLEN = ["Seherin", "Hexe", "Jäger", "Heiler", "Amor"]


@RoleRegistry.register
class ErgebeneMagd(Role):
    """
    Ergebene Magd - Rollen-Übernahme-Rolle.

    Fähigkeiten:
    - Wenn wichtige Rolle stirbt: Übernimmt deren Fähigkeiten
    - Wird zur neuen Seherin/Hexe/etc.

    Besonderheiten:
    - Passive Rolle (keine eigene Aktion)
    - Übernimmt ALLE Fähigkeiten inklusive Ressourcen
    - Nur für erste wichtige Rolle die stirbt

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=162,
            name="Ergebene Magd",
            team=Team.DORF,
            kategorie=Kategorie.HEILER,
            beschreibung=(
                "Du bist die Ergebene Magd. Wenn eine wichtige Rolle "
                "(Seherin, Hexe, Jäger, Heiler, Amor) stirbt, übernimmst "
                "du ihre Identität und Fähigkeiten!"
            ),
            icon="fa-solid fa-broom",
            farbe="#14b8a6",
            prioritaet=100,
            erzaehler_nacht=(
                "Die Ergebene Magd schläft. Sie wartet auf ihre Bestimmung."
            ),
            erweiterung=Erweiterung.SONDEREDITION,

            # Visual Styling
            avatar_gradient_from="#14b8a6",
            avatar_gradient_to="#0f766e",
            avatar_border_color="#2dd4bf",
            badge_emoji="🧹",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Ergebene Magd does not act on first night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Ergebene Magd is passive and does not act at night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Ergebene Magd's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Ergebene Magd - Passive Rolle",
            instructions="Du wartest darauf, eine wichtige Rolle zu übernehmen.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        opfer: "Spieler",
        todesursache: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob eine wichtige Rolle stirbt und übernimmt sie.
        """
        # Prüfe ob bereits übernommen
        bereits_uebernommen = getattr(spieler, "magd_hat_uebernommen", False)
        if bereits_uebernommen:
            return None

        # Prüfe ob es eine wichtige Rolle ist
        if opfer.rolle not in WICHTIGE_ROLLEN:
            return None

        # Magd übernimmt die Rolle!
        return AktionsErgebnis(
            erfolg=True,
            nachricht=(
                f"Die Ergebene Magd tritt aus dem Schatten! "
                f"Sie übernimmt die Rolle der verstorbenen {opfer.rolle}!"
            ),
            effekte={
                "magd_uebernimmt": True,
                "neue_rolle": opfer.rolle,
                "von_rolle": opfer.rolle,
                "magd_hat_uebernommen": True,
            },
            log_sichtbar_fuer="erzaehler",
        )
