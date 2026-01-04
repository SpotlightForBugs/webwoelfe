"""
Einsamer Wolf - Der Solo-Werwolf.

Der Einsame Wolf kennt die anderen Wölfe nicht
und jagt alleine. Er gewinnt nur als letzter Wolf.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class EinsamerWolf(Role):
    """
    Einsamer Wolf - Solo-Werwolf.
    
    Fähigkeiten:
    - Jagt alleine (nicht mit anderen Wölfen)
    - Kennt die anderen Wölfe nicht
    - Die anderen Wölfe kennen ihn nicht
    
    Besonderheiten:
    - Erscheint für Seherin als Werwolf
    - Gewinnt nur wenn er letzter Wolf ist
    
    Gewinnbedingung: Als letzter überlebender Werwolf gewinnen.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=30,
            name='Einsamer Wolf',
            team=Team.SOLO,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                'Du bist der Einsame Wolf. Du kennst die anderen Wölfe nicht '
                'und sie kennen dich nicht. Du tötest alleine und gewinnst nur, '
                'wenn DU der letzte Wolf bist!'
            ),
            icon='fa-solid fa-paw',
            farbe='#4c1d95',
            prioritaet=48,
            erzaehler_nacht=(
                'Der Einsame Wolf erwacht separat und wählt sein eigenes Opfer.'
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN
    
    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF
    
    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"  # Kann sich nicht selbst wählen
    
    def ist_nacht_aktiv(self, spieler: 'Spieler', kontext: SpielKontext) -> bool:
        """Einsamer Wolf jagt jede Nacht alleine."""
        return True
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Einsamer Wolf tötet sein Ziel alleine.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du schleichst durch die Nacht, findest aber kein Opfer.",
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
            nachricht=f"Du greifst {ziel.name} alleine an - ein einsamer Jäger!",
            ziel_spieler_id=ziel.id,
            effekte={
                "werwolf_opfer": ziel.id,
                "einzelangriff": True,
                "todesursache": "werwolf",
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def gewinnt_mit_woelfen(self) -> bool:
        """Einsamer Wolf gewinnt NICHT mit dem Rudel."""
        return False
