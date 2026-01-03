"""
Prinz - Immun gegen Hinrichtung.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Prinz(Role):
    """
    Der Prinz - Immunität gegen Hinrichtung.
    
    Fähigkeiten:
    - Kann nicht vom Dorf gehängt werden (einmalig)
    - Bei Versuch wird Rolle enthüllt
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=70,
            name="Prinz",
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der Prinz. Wenn das Dorf versucht dich zu "
                "hängen, wird deine Rolle enthüllt und du überlebst. "
                "Dies funktioniert nur einmal!"
            ),
            icon="fa-solid fa-crown",
            farbe="#eab308",
            nacht_aktiv=False,
            prioritaet=98,
            erzaehler_tag=(
                "Der Prinz kann nicht gehängt werden! Seine Identität "
                "wird enthüllt."
            ),
        )
    
    def on_hinrichtung(self, spieler: 'Spieler', opfer: 'Spieler',
                       kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Prinz überlebt die erste Hinrichtung.
        """
        if opfer.id == spieler.id:
            return AktionsErgebnis(
                erfolg=False,  # Hinrichtung schlaegt fehl
                nachricht=(
                    "Das Dorf versucht den Prinzen zu hängen, aber sein "
                    "königliches Blut schützt ihn! Er überlebt und seine "
                    "Identität ist nun bekannt."
                ),
                effekte={
                    "hinrichtung_verhindert": True,
                    "rolle_enthuellt": True,
                    "prinz_schutz_verbraucht": True,
                },
                log_sichtbar_fuer="alle",
            )
        
        return None
