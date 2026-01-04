"""
Hexe - Maechtige Rolle mit zwei einmaligen Traenken.

Die Hexe kann einmal pro Spiel jemanden heilen
und einmal jemanden vergiften.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Hexe(Role):
    """
    Die Hexe - Dual-Action Rolle.
    
    Fähigkeiten:
    - Heiltrank: Rettet das Werwolf-Opfer (einmalig)
    - Gifttrank: Tötet einen beliebigen Spieler (einmalig)
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=4,
            name="Hexe",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist die Hexe. Du hast einen Heiltrank (rettet das "
                "Werwolf-Opfer) und einen Gifttrank (tötet einen Spieler). "
                "Jeder Trank kann nur einmal verwendet werden!"
            ),
            icon="fa-solid fa-hat-wizard",
            farbe="#059669",
            prioritaet=60,
            erzaehler_nacht=(
                "Die Hexe erwacht. Zeige auf das Werwolf-Opfer. "
                "Frage: Heiltrank einsetzen? (Daumen hoch/runter) "
                "Gifttrank einsetzen? (Zeige auf Spieler oder schuettle Kopf)"
            ),
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.HEILEN  # Primaere Aktion, Gift ist sekundaer
    
    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Hexe entscheidet über Heiltrank und Gifttrank.
        
        Die Aktion wird als Dictionary erwartet mit:
        - heilen: bool
        - vergiften: Optional[spieler_id]
        """
        effekte = {}
        nachrichten = []
        
        # Prüfe Heiltrank
        hat_heiltrank = getattr(spieler, 'hexe_heiltrank', True)
        
        if hat_heiltrank and kontext.werwolf_opfer_id:
            # Kann heilen - Entscheidung kommt über zusätzliche Daten
            effekte['kann_heilen'] = True
            effekte['werwolf_opfer'] = kontext.werwolf_opfer_id
        
        # Prüfe Gifttrank
        hat_gifttrank = getattr(spieler, 'hexe_gifttrank', True)
        
        if hat_gifttrank:
            effekte['kann_vergiften'] = True
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Die Hexe erwacht und sieht das Opfer der Werwoelfe.",
            effekte=effekte,
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def heilen(self, spieler: 'Spieler', kontext: SpielKontext) -> AktionsErgebnis:
        """Setzt den Heiltrank ein."""
        if not getattr(spieler, 'hexe_heiltrank', True):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Der Heiltrank wurde bereits verwendet.",
            )
        
        if not kontext.werwolf_opfer_id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Es gibt kein Opfer zum Heilen.",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du setzt den Heiltrank ein und rettest das Opfer!",
            ziel_spieler_id=kontext.werwolf_opfer_id,
            effekte={
                "geheilt": kontext.werwolf_opfer_id,
                "heiltrank_verbraucht": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def vergiften(self, spieler: 'Spieler', ziel: 'Spieler',
                  kontext: SpielKontext) -> AktionsErgebnis:
        """Setzt den Gifttrank ein."""
        if not getattr(spieler, 'hexe_gifttrank', True):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Der Gifttrank wurde bereits verwendet.",
            )
        
        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel für Gift.",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du vergiftest {ziel.name}!",
            ziel_spieler_id=ziel.id,
            effekte={
                "vergiftet": ziel.id,
                "gifttrank_verbraucht": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
