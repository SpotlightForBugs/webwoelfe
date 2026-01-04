"""
Wolf im Schafspelz - Erscheint als Dorfbewohner.

Der Wolf im Schafspelz erscheint für die normale
Seherin als Dorfbewohner, nur die Aurenseherin erkennt ihn.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class WolfimSchafspelz(Role):
    """
    Wolf im Schafspelz - Getarnter Werwolf.
    
    Fähigkeiten:
    - Jagt mit den Wölfen
    - Erscheint der Seherin als Dorfbewohner
    - Nur die Aurenseherin erkennt seine böse Aura
    
    Besonderheiten:
    - Perfekte Tarnung gegen normale Seherin
    - Aurenseherin sieht Böse Aura
    - Gefährlich für das Dorf
    
    Gewinnbedingung: Werwölfe gewinnen.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=23,
            name='Wolf im Schafspelz',
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                'Du bist der Wolf im Schafspelz. Für die Seherin erscheinst '
                'du als harmloser Dorfbewohner! Nur die Aurenseherin erkennt '
                'dein böses Herz.'
            ),
            icon='fa-brands fa-bluesky',
            farbe='#fef3c7',
            prioritaet=50,
            erzaehler_nacht=(
                'Der Wolf im Schafspelz erscheint der Seherin als Dorfbewohner!'
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN  # Jagt mit Wölfen
    
    @property
    def sichtbar_als(self) -> SichtTyp:
        """
        Erscheint als Dorf für normale Seherin!
        Aurenseherin sieht trotzdem Werwolf.
        """
        return SichtTyp.DORF  # Getarnt!
    
    def sichtbar_als_fuer(self, seher_rolle: str) -> SichtTyp:
        """Je nach Seher-Typ unterschiedliche Sichtbarkeit."""
        if 'aurenseherin' in seher_rolle.lower():
            return SichtTyp.WERWOLF  # Aurenseherin sieht die Wahrheit
        return SichtTyp.DORF  # Alle anderen sehen Dorf

    def sichtbare_rolle_fuer(self, seher_rolle: str) -> str:
        """Je nach Seher-Typ unterschiedliche Rollenanzeige."""
        if 'aurenseherin' in seher_rolle.lower():
            return self.info.name
        return 'Dorfbewohner'
