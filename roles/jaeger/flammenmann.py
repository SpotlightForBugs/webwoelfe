"""
Flammenmann - Der Brandstifter.

Einmal pro Spiel kann der Flammenmann am Tag
sein Haus anzünden - die Nachbarn sterben.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Flammenmann(Role):
    """
    Flammenmann - Einmal-Tag-Fähigkeit.
    
    Fähigkeiten:
    - Einmal pro Spiel am Tag aktivierbar
    - Zündet sein Haus an
    - Nachbarn links und rechts sterben mit
    
    Besonderheiten:
    - Stirbt selbst NICHT!
    - Mächtige aber riskante Fähigkeit
    - Einmalig
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=152,
            name='Flammenmann',
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                'Du bist der Flammenmann. Einmal pro Spiel kannst du '
                'während des Tages ein Haus anzünden - alle Spieler '
                'darin (Links und Rechts neben dir) sterben!'
            ),
            icon='fa-solid fa-fire',
            farbe='#ea580c',
            nacht_aktiv=False,
            prioritaet=94,
            erzaehler_nacht=(
                'Der Flammenmann träumt von lodernden Flammen. '
                'Er wartet auf den richtigen Moment.'
            ),
            erzaehler_tag=(
                'FEUER! Der Flammenmann zündet sein Haus an! '
                'Die Flammen greifen auf die Nachbarhäuser über - '
                'alle Nachbarn sterben!'
            ),
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN
    
    def ist_einmal_faehigkeit(self) -> bool:
        """Flammenmann kann nur einmal zünden."""
        return True
    
    def ist_tag_aktiv(self, spieler: 'Spieler', kontext: SpielKontext) -> bool:
        """
        Nur aktiv wenn noch nicht gezündet.
        """
        return not getattr(spieler, 'flammenmann_gezuendet', False)
    
    def anzuenden(self, spieler: 'Spieler', 
                  kontext: SpielKontext) -> AktionsErgebnis:
        """
        Zündet das Haus an - Nachbarn sterben.
        
        Die Nachbarn werden über die Sitzreihenfolge ermittelt.
        """
        if getattr(spieler, 'flammenmann_gezuendet', False):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast dein Feuer bereits benutzt!",
            )
        
        spieler.flammenmann_gezuendet = True
        
        # Nachbarn ermitteln (links und rechts in Sitzreihenfolge)
        # Das muss von game_logic über kontext.sitzreihenfolge gemacht werden
        nachbarn_ids = []
        
        if hasattr(kontext, 'sitzreihenfolge') and kontext.sitzreihenfolge:
            sitz = kontext.sitzreihenfolge
            try:
                idx = sitz.index(spieler.id)
                # Links
                links_idx = (idx - 1) % len(sitz)
                # Rechts
                rechts_idx = (idx + 1) % len(sitz)
                
                # Nur lebende Nachbarn
                links_id = sitz[links_idx]
                rechts_id = sitz[rechts_idx]
                
                if links_id not in kontext.tote_spieler:
                    nachbarn_ids.append(links_id)
                if rechts_id not in kontext.tote_spieler and rechts_id != links_id:
                    nachbarn_ids.append(rechts_id)
            except (ValueError, IndexError):
                pass
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"FEUER! Die Flammen verschlingen {len(nachbarn_ids)} Nachbarn!",
            effekte={
                "flammen_toeten": nachbarn_ids,
                "flammenmann_gezuendet": True,
                "todesursache": "verbrennung",
            },
            log_sichtbar_fuer="alle",
        )
