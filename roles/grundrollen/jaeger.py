"""
Jäger - Stirbt nicht kampflos.

Der Jäger kann bei seinem Tod einen letzten Schuss abfeuern
und einen beliebigen Spieler mit in den Tod reißen.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Jaeger(Role):
    """
    Der Jäger - Todes-Trigger Rolle.
    
    Fähigkeiten:
    - Bei Tod: Kann einen Spieler erschießen (einmalig)
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=5,
            name="Jäger",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist der Jäger. Wenn du stirbst, kannst du einen letzten "
                "Schuss abfeuern und einen Spieler deiner Wahl mit in den Tod "
                "reißen!"
            ),
            icon="fa-solid fa-crosshairs",
            farbe="#b45309",
            nacht_aktiv=False,
            prioritaet=99,
            erzaehler_nacht=(
                "Der Jäger schläft mit seiner Flinte unter dem Kopfkissen. "
                "Bereit für seinen letzten Schuss."
            ),
            erzaehler_tag=(
                "Der Jäger ist gestorben! Mit zitternder Hand hebt er seine "
                "Flinte. Auf wen feuert er seinen letzten Schuss?"
            ),
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SCHIESSEN
    
    @property
    def kann_ziel_waehlen(self) -> bool:
        return False  # Nur bei Tod
    
    def on_eigener_tod(self, spieler: 'Spieler', todesursache: str,
                       kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Jäger stirbt und kann seinen Schuss abfeuern.
        """
        hat_schuss = getattr(spieler, 'jaeger_schuss', True)
        
        if not hat_schuss:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Der Jäger hat seinen Schuss bereits verwendet.",
            )
        
        # Markiere dass Schuss verfügbar ist - Zielwahl kommt separat
        return AktionsErgebnis(
            erfolg=True,
            nachricht=(
                "Der Jäger wurde getötet! Mit seinem letzten Atemzug "
                "greift er zur Flinte!"
            ),
            effekte={
                "jaeger_schuss_verfuegbar": True,
                "warte_auf_zielwahl": True,
            },
            log_sichtbar_fuer="alle",
        )
    
    def schiessen(self, spieler: 'Spieler', ziel: 'Spieler',
                  kontext: SpielKontext) -> AktionsErgebnis:
        """
        Jäger feuert seinen letzten Schuss.
        """
        hat_schuss = getattr(spieler, 'jaeger_schuss', True)
        
        if not hat_schuss:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Kein Schuss mehr verfügbar.",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Der Jäger erschießt {ziel.name} mit seinem letzten Schuss!",
            ziel_spieler_id=ziel.id,
            effekte={
                "erschossen": ziel.id,
                "schuss_verbraucht": True,
            },
            log_sichtbar_fuer="alle",
        )
