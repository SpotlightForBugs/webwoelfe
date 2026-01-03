"""
Selbstmörder 
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Selbstmoerder(Role):
    """
    Selbstmörder
    
    Du bist der Selbstmörder. Du gewinnst NUR wenn du vom Dorf g...
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=74,
            name='Selbstmörder',
            team=Team.SOLO,
            kategorie=Kategorie.SPEZIAL,
            beschreibung='Du bist der Selbstmörder. Du gewinnst NUR wenn du vom Dorf gehängt wirst! Versuche verdächtig zu wirken, ohne zu offensichtlich zu sein.',
            icon='fa-solid fa-skull',
            farbe='#374151',
            nacht_aktiv=False,
            prioritaet=100,
            erzaehler_nacht='Der Selbstmörder liegt wach und plant, wie er morgen möglichst verdächtig wirken kann.',
            erzaehler_tag='Der Selbstmörder erwacht mit einem finsteren Plan. Sein Ziel: Vom Dorf gehängt werden! Aber nicht zu offensichtlich...',
            hinweis_config='Selbstmörder',
        )
