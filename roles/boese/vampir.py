"""
Vampir - Der Blutsauger.

Vampire verwandeln jede zweite Nacht einen Spieler
in einen Vampir. Sie gewinnen bei Vampir-Mehrheit.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Vampir(Role):
    """
    Vampir - Eigenständiges Team.
    
    Fähigkeiten:
    - Erwacht jede zweite Nacht
    - Kann einen Spieler in einen Vampir verwandeln
    - Vampire kennen sich untereinander
    
    Besonderheiten:
    - Eigenes Team (nicht Dorf, nicht Wölfe)
    - Verwandlung statt Tötung
    - Gewinnt bei Vampir-Mehrheit
    
    Gewinnbedingung: Mehr Vampire als andere Lebende.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=81,
            name='Vampir',
            team=Team.VAMPIR,
            kategorie=Kategorie.BOESE,
            beschreibung=(
                'Du bist ein Vampir! Jede zweite Nacht kannst du einen '
                'Spieler in einen Vampir verwandeln. Ihr gewinnt, wenn '
                'mehr Vampire als andere leben!'
            ),
            icon='fa-solid fa-tooth',
            farbe='#7c2d12',
            nacht_aktiv=True,
            prioritaet=53,
            erzaehler_nacht=(
                'Die Vampire erwachen (jede zweite Nacht) und wählen '
                'einen Spieler zur Verwandlung.'
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.INFIZIEREN
    
    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.DORF  # Erscheinen als harmlos für Seherin
    
    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_keine_vampire"
    
    def ist_nacht_aktiv(self, spieler: 'Spieler', kontext: SpielKontext) -> bool:
        """Vampire erwachen nur jede zweite Nacht."""
        return kontext.aktuelle_runde % 2 == 0  # Gerade Runden
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Vampir verwandelt einen Spieler.
        """
        if not self.ist_nacht_aktiv(spieler, kontext):
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du schläfst in deiner Gruft. Nächste Nacht wirst du jagen.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du verzichtest auf die Jagd diese Nacht.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Tote können nicht verwandelt werden.",
            )
        
        # Prüfen ob schon Vampir
        ziel_team = kontext.spieler_teams.get(ziel.id, Team.DORF)
        if ziel_team == Team.VAMPIR:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Dieses Opfer ist bereits ein Vampir!",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du beißt {ziel.name}! In der nächsten Nacht wird "
                      f"er als Vampir erwachen!",
            ziel_spieler_id=ziel.id,
            effekte={
                "vampir_gebissen": ziel.id,
                "team_wechsel": Team.VAMPIR.value,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def pruefe_gewinn(self, spieler: 'Spieler',
                      kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Prüft ob Vampire in der Mehrheit sind.
        """
        lebende = [sid for sid in kontext.spieler_rollen.keys() 
                   if sid not in kontext.tote_spieler]
        
        vampire = [sid for sid in lebende 
                   if kontext.spieler_teams.get(sid) == Team.VAMPIR]
        
        nicht_vampire = [sid for sid in lebende if sid not in vampire]
        
        if len(vampire) > len(nicht_vampire):
            return AktionsErgebnis(
                erfolg=True,
                nachricht="DIE NACHT BRICHT HEREIN! Die Vampire haben gewonnen!",
                effekte={
                    "spiel_ende": True,
                    "gewinner": "vampire",
                },
                log_sichtbar_fuer="alle",
            )
        
        return None
