"""
Gaukler - Der Platztauscher.

Einmal pro Spiel kann der Gaukler am Tag
zwei Spieler ihre Plätze tauschen lassen.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Gaukler(Role):
    """
    Gaukler - Einmal-Tag-Fähigkeit.
    
    Fähigkeiten:
    - Einmal pro Spiel am Tag aktivierbar
    - Lässt zwei Spieler Plätze tauschen
    - Alle Effekte wandern mit (Schutz, Markierungen, etc.)
    
    Besonderheiten:
    - Strategisch sehr wertvoll
    - Kann Amor-Verknüpfungen durcheinander bringen
    - Kann Werwolf-Angriffe umleiten
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=59,
            name='Gaukler',
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                'Du bist der Gaukler. Einmal pro Spiel kannst du während '
                'des Tages zwei Spieler ihre Plätze tauschen lassen - '
                'alle Effekte wechseln mit!'
            ),
            icon='fa-solid fa-masks-theater',
            farbe='#c026d3',
            prioritaet=90,
            erzaehler_nacht=(
                'Der Gaukler probt seine Tricks im Schlaf. '
                'Ein Meister der Verwirrung.'
            ),
            erweiterung=Erweiterung.SONDEREDITION,

            # Visual Styling
            avatar_gradient_from="#c026d3",
            avatar_gradient_to="#a21caf",
            avatar_border_color="#d946ef",
            badge_emoji="🎭",
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.MANIPULIEREN
    
    def is_active_on_first_night(self) -> bool:
        """Gaukler does not act at night."""
        return False
    
    def is_active_on_every_night(self) -> bool:
        """Gaukler does not act at night."""
        return False
    
    def get_ui_definition(self) -> 'RollenUI':
        """Returns the UI definition for Gaukler's action panel."""
        from ..base import RollenUI
        return RollenUI(
            title="Gaukler - Tagaktion",
            instructions="Du kannst einmal am Tag zwei Spieler ihre Plätze tauschen lassen.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True
        )
    
    def ist_einmal_faehigkeit(self) -> bool:
        """Gaukler kann nur einmal tauschen."""
        return True
    
    def ist_tag_aktiv(self, spieler: 'Spieler', kontext: SpielKontext) -> bool:
        """
        Nur aktiv wenn noch nicht getauscht.
        """
        return not getattr(spieler, 'gaukler_getauscht', False)
    
    @property
    def erlaubte_ziele(self) -> str:
        return "alle"  # Braucht zwei Ziele
    
    def plaetze_tauschen(self, spieler: 'Spieler', 
                         ziel1: 'Spieler', ziel2: 'Spieler',
                         kontext: SpielKontext) -> AktionsErgebnis:
        """
        Tauscht die Plätze von zwei Spielern.
        
        Alle sitzplatzbezogenen Effekte wandern mit:
        - Nachbar-Beziehungen ändern sich
        - Schutz-Markierungen bleiben bei den Spielern
        """
        if getattr(spieler, 'gaukler_getauscht', False):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deinen Trick bereits verwendet!",
            )
        
        if ziel1.id in kontext.tote_spieler or ziel2.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nur lebende Spieler tauschen!",
            )
        
        if ziel1.id == ziel2.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst zwei verschiedene Spieler wählen!",
            )
        
        spieler.gaukler_getauscht = True
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"HOKUSPOKUS! {ziel1.name} und {ziel2.name} tauschen Plätze!",
            effekte={
                "platztausch": [ziel1.id, ziel2.id],
                "gaukler_getauscht": True,
            },
            log_sichtbar_fuer="alle",
        )
