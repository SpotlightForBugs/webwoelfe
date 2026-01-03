"""
Weisser Wolf - Solo-Werwolf.

Der Weisse Wolf jagt mit den Woelfen, aber kann
jede zweite Nacht auch einen Mitwerwolf toeten.
Er gewinnt nur alleine.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class WeisserWolf(Role):
    """
    Der Weisse Wolf - Solo-Werwolf.
    
    Faehigkeiten:
    - Jagt mit den Woelfen
    - Kann jede zweite Nacht einen Mitwerwolf toeten
    
    Gewinnbedingung: Als letzter ueberlebender Werwolf.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=21,
            name="Weißer Wolf",
            team=Team.SOLO,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Weisse Wolf! Du jagst mit den Woelfen, aber "
                "jede zweite Nacht kannst du zusaetzlich einen Mitwerwolf "
                "toeten. Du gewinnst nur alleine!"
            ),
            icon="fa-solid fa-paw",
            farbe="#f5f5f4",
            nacht_aktiv=True,
            prioritaet=52,
            erzaehler_nacht=(
                "Der Weisse Wolf erwacht (jede zweite Nacht). "
                "Moechte er einen Mitwerwolf toeten?"
            ),
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN
    
    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF
    
    @property
    def erlaubte_ziele(self) -> str:
        return "werwolf"  # Nur Mitwoelfe
    
    @property
    def basis_hinweis_chance(self) -> float:
        return 0.08  # Niedriger als normale Woelfe - unauffaelliger
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Weisser Wolf kann jede zweite Nacht einen Mitwolf toeten.
        """
        # Nur jede zweite Nacht aktiv
        if kontext.runde % 2 != 0:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Diese Nacht ruhst du.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast diese Nacht keinen Mitwolf getoetet.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du hast {ziel.name} heimlich getoetet!",
            ziel_spieler_id=ziel.id,
            effekte={
                "weisser_wolf_opfer": ziel.id,
                "todesursache": "weisser_wolf",
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def berechne_gewinn(self, spieler: 'Spieler', kontext: SpielKontext) -> Optional[Team]:
        """
        Gewinnt als letzter Ueberlebender oder letzter Werwolf.
        """
        if len(kontext.lebende_spieler) == 1 and spieler.id in kontext.lebende_spieler:
            return Team.SOLO
        return None
