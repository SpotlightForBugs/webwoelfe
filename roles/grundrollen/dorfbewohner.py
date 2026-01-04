"""
Dorfbewohner - Die Basis-Rolle für das Dorf-Team.

Der Dorfbewohner hat keine speziellen Fähigkeiten,
aber seine Stimme in der Abstimmung ist entscheidend.
"""
from typing import Optional
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry


@RoleRegistry.register
class Dorfbewohner(Role):
    """
    Einfacher Dorfbewohner ohne spezielle Fähigkeiten.
    
    Gewinnbedingung: Alle Werwoelfe werden eliminiert.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=1,
            name="Dorfbewohner",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist ein einfacher Dorfbewohner. Hilf dem Dorf, die Werwoelfe "
                "zu entlarven! Du hast keine speziellen Fähigkeiten, aber deine "
                "Stimme zählt."
            ),
            icon="fa-solid fa-user",
            farbe="#6b7280",
            prioritaet=100,
            erzaehler_nacht=(
                "Der Dorfbewohner schläft friedlich. "
                "Er hat keine nächtlichen Fähigkeiten."
            ),
            erzaehler_tag=(
                "Der Dorfbewohner erwacht und hofft, die Woelfe zu entlarven. "
                "Seine Stimme ist seine einzige Waffe."
            ),
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE
