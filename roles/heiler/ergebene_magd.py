"""
Ergebene Magd - Die Nachfolgerin.

Die Ergebene Magd übernimmt die Rolle einer
wichtigen verstorbenen Person.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
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
            name='Ergebene Magd',
            team=Team.DORF,
            kategorie=Kategorie.HEILER,
            beschreibung=(
                'Du bist die Ergebene Magd. Wenn eine wichtige Rolle '
                '(Seherin, Hexe, Jäger, Heiler, Amor) stirbt, übernimmst '
                'du ihre Identität und Fähigkeiten!'
            ),
            icon='fa-solid fa-broom',
            farbe='#14b8a6',
            nacht_aktiv=False,
            prioritaet=95,
            erzaehler_nacht=(
                'Die Ergebene Magd ruht im Hintergrund, bereit '
                'ihre Herrin zu ersetzen wenn nötig.'
            ),
            erzaehler_tag=(
                'Die Ergebene Magd tritt vor! Sie übernimmt die Rolle '
                'und Fähigkeiten der verstorbenen Rolle!'
            ),
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE
    
    def on_spieler_stirbt(self, spieler: 'Spieler', opfer: 'Spieler',
                          todesursache: str, kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Prüft ob eine wichtige Rolle stirbt und übernimmt sie.
        """
        # Prüfe ob bereits übernommen
        bereits_uebernommen = getattr(spieler, 'magd_hat_uebernommen', False)
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
