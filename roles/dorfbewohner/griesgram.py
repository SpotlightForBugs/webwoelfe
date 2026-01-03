"""
Griesgram - Der ewige Nörgler.

Der Griesgram ist immer schlecht gelaunt und stimmt
bei jeder Hinrichtung automatisch mit JA.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Griesgram(Role):
    """
    Griesgram - Zwanghafte Abstimmungsrolle.
    
    Fähigkeiten:
    - Stimmt IMMER mit JA bei Hinrichtungen
    - Kann nicht anders abstimmen (Zwang)
    - Zählt trotzdem als normale Stimme
    
    Besonderheiten:
    - Passive Rolle (keine Nacht-Aktion)
    - Seine Stimme wird automatisch als JA gezählt
    - Kann strategisch genutzt werden um Werwölfe zu finden
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=16,
            name='Griesgram',
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                'Du bist der Griesgram. Du bist immer schlecht gelaunt und '
                'stimmst IMMER mit JA bei Hinrichtungen - du kannst nicht '
                'anders! Deine Stimme zählt aber trotzdem.'
            ),
            icon='fa-solid fa-face-angry',
            farbe='#6b7280',
            nacht_aktiv=False,
            prioritaet=100,
            erzaehler_nacht=(
                'Der Griesgram wälzt sich mürrisch im Bett. '
                'Selbst im Schlaf ist er schlecht gelaunt.'
            ),
            erzaehler_tag=(
                'Der Griesgram erwacht grantig. Er stimmt IMMER für eine '
                'Hinrichtung - egal wer vorgeschlagen wird!'
            ),
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE
    
    def on_abstimmung(self, spieler: 'Spieler', ziel: 'Spieler',
                      kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Der Griesgram stimmt automatisch mit JA.
        
        Diese Methode wird aufgerufen wenn eine Abstimmung stattfindet.
        Der Griesgram hat keine Wahl - er muss mit JA stimmen.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{spieler.name} stimmt mürrisch mit JA. (Griesgram-Zwang)",
            effekte={
                "stimme": "ja",
                "stimme_fuer": ziel.id,
                "griesgram_zwang": True,  # Markiert dass dies automatisch war
            },
            log_sichtbar_fuer="alle",
        )
    
    @property
    def kann_abstimmung_aendern(self) -> bool:
        """
        Der Griesgram kann seine Abstimmung NICHT ändern.
        """
        return False
