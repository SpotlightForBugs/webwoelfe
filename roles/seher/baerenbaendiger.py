"""
Bärenbändiger - Der Bär verrät die Wölfe.

Der Bär des Bärenbändigers brummt morgens,
wenn ein Werwolf neben ihm sitzt.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Baerenbaendiger(Role):
    """
    Bärenbändiger - Passive Informationsrolle.
    
    Fähigkeiten:
    - Bär brummt morgens wenn Werwolf neben ihm sitzt
    - ALLE hören das Brummen (öffentliche Info)
    - Nur der Bärenbändiger weiß, was es bedeutet
    
    Besonderheiten:
    - Keine aktive Nacht-Aktion
    - Nutzt das Nachbar-System (Sitzplätze)
    - Kann täuschen (andere denken vielleicht ER ist der Wolf)
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=37,
            name='Bärenbändiger',
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                'Du bist der Bärenbändiger. Dein Bär brummt morgens, wenn '
                'ein Werwolf neben dir sitzt! Alle hören das Brummen, aber '
                'nur du weißt was es bedeutet.'
            ),
            icon='fa-solid fa-paw',
            farbe='#78350f',
            prioritaet=86,
            erzaehler_nacht=(
                'Der Bär des Bärenbändigers schläft unruhig. '
                'Er spürt die Wölfe in der Nähe...'
            ),
            erzaehler_tag=(
                'GRRRR! Der Bär brummt! (Falls ein Werwolf neben '
                'dem Bärenbändiger sitzt)'
            ),
            erweiterung=Erweiterung.CHARAKTERE,

            # Visual Styling
            avatar_gradient_from="#78350f",
            avatar_gradient_to="#451a03",
            avatar_border_color="#92400e",
            badge_emoji="🐻",
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE
    
    def is_active_on_first_night(self) -> bool:
        """Bärenbändiger does not act at night."""
        return False
    
    def is_active_on_every_night(self) -> bool:
        """Bärenbändiger is passive at night."""
        return False
    
    def get_ui_definition(self) -> 'RollenUI':
        """Returns the UI definition for Bärenbändiger's action panel."""
        from ..base import RollenUI
        return RollenUI(
            title="Bärenbändiger - Passive Rolle",
            instructions="Dein Bär brummt morgens, wenn ein Werwolf neben dir sitzt.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True
        )
    
    def on_tag_start(self, spieler: 'Spieler', kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Prüft ob ein Werwolf neben dem Bärenbändiger sitzt.
        
        Diese Information wird am Morgen öffentlich bekannt gegeben.
        """
        # Hole die Nachbarn des Bärenbändigers
        nachbar_links = spieler.hole_nachbar_links()
        nachbar_rechts = spieler.hole_nachbar_rechts()
        
        nachbarn = []
        if nachbar_links:
            nachbarn.append(nachbar_links)
        if nachbar_rechts and (not nachbar_links or nachbar_rechts.id != nachbar_links.id):
            nachbarn.append(nachbar_rechts)
        
        # Prüfe ob ein Nachbar ein Werwolf ist
        werwolf_neben_baer = False
        
        for nachbar in nachbarn:
            ziel_rolle = RoleRegistry.get(nachbar.rolle)
            if ziel_rolle and ziel_rolle.info.team == Team.WERWOLF:
                werwolf_neben_baer = True
                break
        
        if werwolf_neben_baer:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "GRRRR! Der Bär des Bärenbändigers brummt laut! "
                    "Das bedeutet: Mindestens ein Werwolf sitzt direkt "
                    "neben dem Bärenbändiger!"
                ),
                effekte={
                    "baer_brummt": True,
                    "werwolf_neben_baer": True,
                },
                log_sichtbar_fuer="alle",  # Alle hören es!
            )
        else:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Der Bär ist heute ruhig. Kein Brummen.",
                effekte={
                    "baer_brummt": False,
                    "werwolf_neben_baer": False,
                },
                log_sichtbar_fuer="erzaehler",  # Nur Erzähler weiß es
            )
