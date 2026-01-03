"""
Buddler - Der Grabenanthropöloge.

Der Buddler kann jede Nacht ein Grab untersuchen
und die Todesursache erfahren.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Buddler(Role):
    """
    Buddler - Toten-Informations-Rolle.
    
    Fähigkeiten:
    - Kann jede Nacht ein Grab ausgraben
    - Erfährt wie dieser Spieler gestorben ist
    
    Besonderheiten:
    - Ziel muss tot sein
    - Todesursache kann wichtige Hinweise geben
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=57,
            name='Buddler',
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                'Du bist der Buddler. Jede Nacht kannst du ein Grab ausgraben '
                'und erfährst die Todesursache des Spielers - Werwolf, '
                'Abstimmung, Gift oder Anderes.'
            ),
            icon='fa-solid fa-shovel',
            farbe='#78716c',
            nacht_aktiv=True,
            prioritaet=80,
            erzaehler_nacht=(
                'Der Buddler erwacht und wählt ein Grab. '
                'Flüstere ihm die Todesursache zu.'
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN
    
    @property
    def erlaubte_ziele(self) -> str:
        return "tote"
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Buddler untersucht ein Grab.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast diese Nacht kein Grab untersucht.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        if ziel.id not in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nur die Gräber von Toten untersuchen.",
            )
        
        # Die Todesursache wird als Attribut gespeichert
        # In der Praxis muss game_logic dies setzen
        todesursache = getattr(ziel, 'todesursache', 'unbekannt')
        
        todesursachen_text = {
            'werwolf': 'Werwolf-Bisse',
            'hexe': 'Vergiftung',
            'hinrichtung': 'Hinrichtung durch das Dorf',
            'jaeger': 'Schusswunde',
            'verbrennung': 'Feuer',
            'liebeskummer': 'Gebrochenes Herz',
        }
        
        text = todesursachen_text.get(todesursache, f'Unbekannte Ursache ({todesursache})')
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Das Grab von {ziel.name} zeigt: Tod durch {text}",
            ziel_spieler_id=ziel.id,
            effekte={
                "grab_untersucht": ziel.id,
                "todesursache": todesursache,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
