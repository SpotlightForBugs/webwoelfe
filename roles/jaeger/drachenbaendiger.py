"""
Drachenbändiger - Der Drachenbeschützer.

Der Drachenbändiger hat einen Drachen, der jeden
tötet, der den Bändiger angreift. Funktioniert nur einmal.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Drachenbaendiger(Role):
    """
    Drachenbändiger - Passive Verteidigungsrolle.
    
    Fähigkeiten:
    - Hat einen schützenden Drachen
    - Wer den Drachenbändiger angreift, stirbt selbst
    - Funktioniert nur einmal!
    
    Besonderheiten:
    - Passiver Schutz, keine aktive Aktion nötig
    - Schützt nicht vor Hinrichtung
    - Der Drache "stirbt" nach einmaliger Nutzung
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=53,
            name='Drachenbändiger',
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                'Du bist der Drachenbändiger. Dein Drache beschützt dich - '
                'wer dich angreift, wird von deinem Drachen getötet! '
                'Funktioniert nur einmal.'
            ),
            icon='fa-solid fa-dragon',
            farbe='#7c3aed',
            nacht_aktiv=False,
            prioritaet=93,
            erzaehler_nacht=(
                'Der Drachenbändiger schläft friedlich, '
                'sein Drache wacht über ihn mit feurigem Atem.'
            ),
            erzaehler_tag=(
                'FEUER-ATEM! Der Drache des Drachenbändigers '
                'verbrennt seinen Angreifer zu Asche!'
            ),
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE
    
    def on_angegriffen(self, spieler: 'Spieler', angreifer_id: int,
                       kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Wenn der Drachenbändiger angegriffen wird,
        tötet der Drache den Angreifer und schützt den Bändiger.
        Funktioniert nur einmal!
        """
        # Prüfen ob Drache schon benutzt wurde
        if getattr(spieler, 'drache_benutzt', False):
            # Drache ist schon tot, kein Schutz mehr
            return None
        
        # Drache wird benutzt - Attribut setzen
        spieler.drache_benutzt = True
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Der Drache des Drachenbändigers hat den Angreifer getötet!",
            effekte={
                "drache_toetet": angreifer_id,
                "angriff_abgewehrt": True,
                "drache_benutzt": True,
                "kill_message": f"Der Drache von {spieler.name} hat seinen Angreifer verbrannt!",
            },
            log_sichtbar_fuer="alle",
        )
