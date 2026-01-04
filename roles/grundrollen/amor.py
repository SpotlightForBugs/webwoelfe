"""
Amor - Der Gott der Liebe.

Amor verbindet zwei Spieler auf ewig - 
stirbt einer, stirbt auch der andere.
"""
from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Amor(Role):
    """
    Amor - Verbindungs-Rolle.
    
    Fähigkeiten:
    - Erste Nacht: Wählt zwei Spieler die sich verlieben
    - Verliebte sterben zusammen
    - Verliebte gewinnen nur gemeinsam als Letztes Paar
    
    Gewinnbedingung: Dorf gewinnt ODER Verliebte überleben als Letzte.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=7,
            name="Amor",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist Amor. In der ersten Nacht wählst du zwei Spieler, "
                "die sich unsterblich verlieben. Stirbt einer, stirbt auch "
                "der andere. Die Verliebten gewinnen nur gemeinsam!"
            ),
            icon="fa-solid fa-heart",
            farbe="#ec4899",
            prioritaet=5,  # Sehr früh in der Nacht
            erzaehler_nacht=(
                "Amor erwacht (nur erste Nacht) und zeigt auf zwei Spieler, "
                "die sich verlieben sollen. Beruehre beide leicht an der Schulter."
            ),
            erweiterung=Erweiterung.BASISSPIEL,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.VERLIEBEN
    

    def on_spiel_start(self, spieler: 'Spieler', kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Amor wählt in der ersten Nacht zwei Verliebte.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Wähle zwei Spieler, die sich verlieben sollen.",
            effekte={"warte_auf_verliebte_wahl": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def verlieben(self, spieler: 'Spieler', ziel1: 'Spieler', ziel2: 'Spieler',
                  kontext: SpielKontext) -> AktionsErgebnis:
        """
        Verbindet zwei Spieler als Verliebte.
        """
        # Prüfe Gültigkeit
        if ziel1.id == ziel2.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst zwei verschiedene Spieler wählen.",
            )
        
        if ziel1.id not in kontext.lebende_spieler or ziel2.id not in kontext.lebende_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Beide Spieler müssen am Leben sein.",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel1.name} und {ziel2.name} haben sich verliebt!",
            effekte={
                "verliebte": [ziel1.id, ziel2.id],
                "amor_aktion_abgeschlossen": True,
            },
            log_sichtbar_fuer="erzaehler",
        )
    
    def on_spieler_stirbt(self, spieler: 'Spieler', opfer: 'Spieler',
                          todesursache: str, kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Prüft ob ein Verliebter stirbt und der andere folgen muss.
        """
        verliebt_mit = getattr(opfer, 'verliebt_mit_id', None)
        
        if verliebt_mit and verliebt_mit in kontext.lebende_spieler:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"Der/Die Verliebte kann den Verlust nicht ertragen!",
                effekte={
                    "verliebter_stirbt_auch": verliebt_mit,
                    "todesursache": "gebrochenes_herz",
                },
                log_sichtbar_fuer="alle",
            )
        
        return None
    
    def berechne_gewinn(self, spieler: 'Spieler', kontext: SpielKontext) -> Optional[Team]:
        """
        Verliebte gewinnen wenn sie die letzten Überlebenden sind.
        """
        verliebt_mit = getattr(spieler, 'verliebt_mit_id', None)
        
        if verliebt_mit:
            # Prüfe ob nur noch die Verliebten leben
            if (len(kontext.lebende_spieler) == 2 and 
                spieler.id in kontext.lebende_spieler and 
                verliebt_mit in kontext.lebende_spieler):
                return Team.VERLIEBTE
        
        return None
