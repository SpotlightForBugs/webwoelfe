"""
Kleines Mädchen - Kann nachts blinzeln um Werwölfe zu sehen, riskiert aber entdeckt zu werden
"""
from typing import Optional, List, TYPE_CHECKING
import random
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class KleinesMaedchen(Role):
    """
    Kleines Mädchen
    
    Kann während der Werwolf-Phase blinzeln, um zu sehen wer die Werwölfe sind.
    Wird es dabei erwischt, wird es sofort von den Werwölfen getötet.
    Das Risiko erwischt zu werden ist zufällig (ca. 30%).
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=95,
            name='Kleines Mädchen',
            team=Team.DORF,
            kategorie=Kategorie.SONSTIGE,
            beschreibung='Du bist das Kleine Mädchen. Du darfst nachts blinzeln um die Werwölfe zu beobachten! Aber Vorsicht: Wirst du erwischt, stirbst du sofort!',
            icon='fa-solid fa-child-dress',
            farbe='#fbbf24',
            nacht_aktiv=True,
            prioritaet=50,
            erzaehler_nacht='Das Kleine Mädchen darf während der Werwolf-Phase blinzeln - auf eigene Gefahr!',
            erzaehler_tag=None,
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN
    
    @property
    def erlaubte_ziele(self) -> str:
        """Das Kleine Mädchen kann sich selbst wählen (blinzeln) oder nicht."""
        return "andere"
    
    def on_nacht_aktion(
        self,
        spieler: 'Spieler',
        ziel: Optional['Spieler'],
        kontext: SpielKontext,
        zusatz_info: Optional[str] = None
    ) -> AktionsErgebnis:
        """Das Kleine Mädchen blinzelt und sieht die Werwölfe - oder wird erwischt."""
        
        # ziel == spieler bedeutet "Nicht blinzeln"
        if ziel is None or ziel.id == spieler.id:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast dich entschieden, nicht zu blinzeln. Sicher ist sicher.",
                effekte={}
            )
        
        # Finde alle lebenden Werwölfe
        werwoelfe = []
        spieler_rollen = getattr(kontext, 'spieler_rollen', {})
        
        for spieler_id, rolle in spieler_rollen.items():
            if spieler_id in kontext.tote_spieler:
                continue
            team = getattr(rolle, 'info', None)
            if team and hasattr(team, 'team') and team.team == Team.WERWOLF:
                werwoelfe.append(spieler_id)
        
        # Risikoberechnung: ca. 30% Chance erwischt zu werden
        erwischt = random.random() < 0.30
        
        if erwischt:
            # Das Kleine Mädchen wird erwischt und stirbt
            return AktionsErgebnis(
                erfolg=True,
                nachricht="😱 Du hast geblinzelt und wurdest ERWISCHT! Die Werwölfe haben dich bemerkt!",
                effekte={
                    'tod': True,
                    'todesursache': 'Von Werwölfen erwischt beim Blinzeln',
                    'erwischt': True
                }
            )
        else:
            # Erfolgreich geblinzelt
            if werwoelfe:
                werwolf_namen = [str(wid) for wid in werwoelfe]
                return AktionsErgebnis(
                    erfolg=True,
                    nachricht=f"🔍 Du hast vorsichtig geblinzelt und {len(werwoelfe)} Werwolf/Werwölfe gesehen!",
                    effekte={
                        'gesehene_werwoelfe': werwoelfe,
                        'erwischt': False
                    }
                )
            else:
                return AktionsErgebnis(
                    erfolg=True,
                    nachricht="Du hast geblinzelt, aber keine Werwölfe gesehen...",
                    effekte={'erwischt': False}
                )
    

