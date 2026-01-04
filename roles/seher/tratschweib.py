"""
Tratschweib - Die Klatschbase des Dorfes.

Das Tratschweib erfährt jede Nacht ob zwei
zufällige Spieler im gleichen Team sind.
"""
from typing import Optional, TYPE_CHECKING
import random
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Tratschweib(Role):
    """
    Tratschweib - Zufällige Team-Information.
    
    Fähigkeiten:
    - Erfährt jede Nacht zwei zufällige Spieler
    - Weiß ob sie im gleichen Team sind oder nicht
    
    Besonderheiten:
    - Keine Zielwahl (zufällig!)
    - Kann wichtige Verbindungen aufdecken
    - Information ist nur für sie sichtbar
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=35,
            name='Tratschweib',
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                'Du bist das Tratschweib. Du hörst alles! Jede Nacht erfährst '
                'du zwei zufällige Spieler und ob sie im gleichen Team sind '
                'oder nicht.'
            ),
            icon='fa-solid fa-comment-dots',
            farbe='#e11d48',
            prioritaet=24,
            erzaehler_nacht=(
                'Das Tratschweib erwacht. Wähle zwei zufällige Spieler und '
                'zeige ob sie im gleichen Team sind (Daumen hoch/runter).'
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN
    

    
    def is_active_on_first_night(self) -> bool:
        """Tratschweib acts on first night."""
        return True
    
    def is_active_on_every_night(self) -> bool:
        """Tratschweib acts every night."""
        return True
    
    def get_ui_definition(self) -> 'RollenUI':
        """Returns the UI definition for Tratschweib's action panel."""
        from ..base import RollenUI
        return RollenUI(
            title="Tratschweib - Zufällige Information",
            instructions="Du erfährst automatisch über zwei zufällige Spieler, ob sie im gleichen Team sind.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=False
        )
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Tratschweib erfährt über zwei zufällige Spieler.
        """
        # Brauche mindestens 2 andere lebende Spieler
        andere_spieler = [s for s in kontext.lebende_spieler if s != spieler.id]
        
        if len(andere_spieler) < 2:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Zu wenige Spieler für Tratsch...",
                effekte={"kein_tratsch": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        # Wähle zwei zufällige Spieler
        zufalls_spieler = random.sample(andere_spieler, 2)
        spieler1_id, spieler2_id = zufalls_spieler
        
        # Die tatsächliche Team-Prüfung muss von game_logic gemacht werden
        # da wir hier keinen direkten DB-Zugriff haben
        return AktionsErgebnis(
            erfolg=True,
            nachricht=(
                "Du hast heute Nacht einen interessanten Tratsch gehört! "
                "Der Erzähler zeigt dir zwei Spieler und ob sie im "
                "gleichen Team sind."
            ),
            effekte={
                "tratsch_spieler": [spieler1_id, spieler2_id],
                "erzaehler_muss_pruefen": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def prüfe_gleiches_team(self, spieler1: 'Spieler', spieler2: 'Spieler') -> bool:
        """
        Prüft ob zwei Spieler im gleichen Team sind.
        
        Wird von game_logic aufgerufen.
        """
        rolle1 = RoleRegistry.get(spieler1.rolle)
        rolle2 = RoleRegistry.get(spieler2.rolle)
        
        if not rolle1 or not rolle2:
            return False
        
        # Vergleiche die Teams
        return rolle1.info.team == rolle2.info.team
