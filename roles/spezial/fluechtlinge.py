"""
Flüchtlinge - Gruppenrolle.

Alle Flüchtlinge kennen sich und müssen gemeinsam
bis zum Ende überleben um zu gewinnen.
"""
from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Fluechtlinge(Role):
    """
    Flüchtlinge - Solidaritäts-Gruppe.
    
    Fähigkeiten:
    - Alle Flüchtlinge kennen sich untereinander
    - Müssen alle überleben um zu gewinnen
    
    Besonderheiten:
    - Gruppenrolle (mehrere Spieler)
    - Sehen sich in der ersten Nacht
    - Zusätzliche Gewinnbedingung zum Dorf
    
    Gewinnbedingung: Dorf gewinnt UND alle Flüchtlinge leben.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=76,
            name='Flüchtlinge',
            team=Team.DORF,
            kategorie=Kategorie.SPEZIAL,
            beschreibung=(
                'Du bist ein Flüchtling. Alle Flüchtlinge kennen sich '
                'und halten zusammen. Ihr müsst bis zum Ende überleben '
                'um zu gewinnen!'
            ),
            icon='fa-solid fa-person-running',
            farbe='#0ea5e9',
            nacht_aktiv=True,
            prioritaet=10,
            erzaehler_nacht=(
                'Die Flüchtlinge erwachen und erkennen sich gegenseitig.'
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.PASSIV
    
    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.DORF
    
    def ist_nacht_aktiv(self, spieler: 'Spieler', kontext: SpielKontext) -> bool:
        """Nur in der ersten Nacht aktiv (zum Erkennen)."""
        return kontext.aktuelle_runde == 1
    
    def on_spiel_start(self, spieler: 'Spieler',
                       kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Flüchtlinge erkennen sich zu Spielbeginn.
        """
        # Alle anderen Flüchtlinge finden
        andere_fluechtlinge: List[int] = []
        for sid, rolle in kontext.spieler_rollen.items():
            if 'flüchtling' in rolle.lower() and sid != spieler.id:
                andere_fluechtlinge.append(sid)
        
        if andere_fluechtlinge:
            namen = [kontext.spieler_namen.get(sid, f"Spieler {sid}") 
                     for sid in andere_fluechtlinge]
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"Du erkennst deine Mitflüchtlinge: {', '.join(namen)}. "
                          f"Ihr müsst alle überleben!",
                effekte={
                    "fluechtlinge_erkannt": andere_fluechtlinge,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du bist allein... der einzige Flüchtling.",
            effekte={},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def pruefe_niederlage(self, spieler: 'Spieler',
                          kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Wenn ein Flüchtling stirbt, verlieren alle Flüchtlinge ihren Bonus.
        """
        # Diese Prüfung wird aufgerufen wenn ein Spieler stirbt
        if spieler.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ein Flüchtling ist gestorben! Die Gruppe hat ihr Ziel verfehlt.",
                effekte={
                    "fluechtlinge_gescheitert": True,
                },
                log_sichtbar_fuer="alle",
            )
        return None
