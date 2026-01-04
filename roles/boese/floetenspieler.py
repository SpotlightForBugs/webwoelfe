"""
Flötenspieler - Der Verzauberer.

Der Flötenspieler verzaubert jede Nacht zwei Spieler.
Er gewinnt wenn alle Lebenden verzaubert sind.
"""
from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Floetenspieler(Role):
    """
    Flötenspieler - Solo-Verzauberungsrolle.
    
    Fähigkeiten:
    - Verzaubert jede Nacht zwei Spieler
    - Verzauberte kennen sich untereinander
    - Gewinnt wenn alle Lebenden verzaubert sind
    
    Besonderheiten:
    - Solo-Rolle
    - Kann nicht sich selbst verzaubern
    - Verzauberung ist dauerhaft
    
    Gewinnbedingung: Alle Lebenden verzaubert.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=83,
            name='Flötenspieler',
            team=Team.SOLO,
            kategorie=Kategorie.BOESE,
            beschreibung=(
                'Du bist der Flötenspieler. Jede Nacht verzauberst du zwei '
                'Spieler. Du gewinnst wenn alle lebenden Spieler verzaubert sind!'
            ),
            icon='fa-solid fa-music',
            farbe='#84cc16',
            prioritaet=70,
            erzaehler_nacht=(
                'Der Flötenspieler erwacht und verzaubert zwei Spieler.'
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.MANIPULIEREN
    
    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.DORF  # Erscheint als harmlos
    
    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Flötenspieler verzaubert Spieler (braucht zwei Ziele).
        Diese Implementierung verzaubert ein Ziel pro Aufruf.
        """
        verzauberte: List[int] = getattr(spieler, 'floetenspieler_verzaubert', [])
        
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"Du spielst leise deine Flöte. {len(verzauberte)} Spieler verzaubert.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst keine Toten verzaubern.",
            )
        
        if ziel.id in verzauberte:
            return AktionsErgebnis(
                erfolg=False,
                nachricht=f"{ziel.name} ist bereits verzaubert!",
            )
        
        verzauberte.append(ziel.id)
        spieler.floetenspieler_verzaubert = verzauberte
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Deine Melodie verzaubert {ziel.name}! "
                      f"Insgesamt {len(verzauberte)} Spieler verzaubert.",
            ziel_spieler_id=ziel.id,
            effekte={
                "verzaubert": ziel.id,
                "anzahl_verzaubert": len(verzauberte),
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def pruefe_gewinn(self, spieler: 'Spieler',
                      kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Prüft ob alle Lebenden verzaubert sind.
        """
        verzauberte: List[int] = getattr(spieler, 'floetenspieler_verzaubert', [])
        
        # Alle lebenden Spieler außer Flötenspieler
        lebende = [sid for sid in kontext.spieler_rollen.keys() 
                   if sid not in kontext.tote_spieler and sid != spieler.id]
        
        alle_verzaubert = all(sid in verzauberte for sid in lebende)
        
        if alle_verzaubert and len(lebende) > 0:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="ALLE TANZEN! Der Flötenspieler hat gewonnen!",
                effekte={
                    "spiel_ende": True,
                    "gewinner": "floetenspieler",
                },
                log_sichtbar_fuer="alle",
            )
        
        return None
