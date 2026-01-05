"""
Demoskopin - Die Meinungsforscherin.

Die Demoskopin erfährt am Anfang jeder Tagphase,
wer die meisten Stimmen bekommen würde.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Demoskopin(Role):
    """
    Demoskopin - Umfrage-Informationsrolle.
    
    Fähigkeiten:
    - Erfährt am Tag wer die meisten Stimmen bekommen würde
    - Basiert auf den bisherigen Abstimmungen/Stimmung
    - Kann Trends erkennen
    
    Besonderheiten:
    - Keine aktive Nacht-Aktion
    - Info ist nur für sie sichtbar
    - Hilfreich um Abstimmungen vorherzusagen
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=34,
            name='Demoskopin',
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                'Du bist die Demoskopin. Du kennst die Meinungsumfragen! '
                'Am Anfang jeder Tagphase erfährst du, wer die meisten '
                'Stimmen bekommen würde.'
            ),
            icon='fa-solid fa-chart-column',
            farbe='#06b6d4',
            prioritaet=85,
            erzaehler_nacht=(
                'Die Demoskopin analysiert auch nachts die Stimmung im Dorf.'
            ),
            erzaehler_tag=(
                'Die Demoskopin erfährt die aktuellen Umfragewerte. '
                '(Zeige ihr heimlich den beliebtesten Kandidaten)'
            ),
            erweiterung=Erweiterung.SONDEREDITION,

            # Visual Styling
            avatar_gradient_from="#06b6d4",
            avatar_gradient_to="#0891b2",
            avatar_border_color="#22d3ee",
            badge_emoji="📊",
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN
    
    def is_active_on_first_night(self) -> bool:
        """Demoskopin does not act at night."""
        return False
    
    def is_active_on_every_night(self) -> bool:
        """Demoskopin is passive at night."""
        return False
    
    def get_ui_definition(self) -> 'RollenUI':
        """Returns the UI definition for Demoskopin's action panel."""
        from ..base import RollenUI
        return RollenUI(
            title="Demoskopin - Passive Rolle",
            instructions="Du erfährst am Tag, wer die meisten Stimmen bekommen würde.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True
        )
    
    def on_tag_start(self, spieler: 'Spieler', kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Demoskopin erfährt den aktuellen Umfrage-Spitzenreiter.
        
        Die Berechnung basiert auf:
        - Bisherige Abstimmungsmuster
        - Spieler die oft verdächtigt wurden
        - "Stimmung" im Raum
        
        In der Praxis wird dies von der game_logic berechnet.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht=(
                "Die aktuellen Umfragewerte sind da! "
                "Der Erzähler zeigt dir, wer heute die meisten "
                "Stimmen bekommen würde."
            ),
            effekte={
                "umfrage_anfordern": True,
                # Die tatsächliche Berechnung erfolgt in game_logic
                # basierend auf bisherigen Abstimmungen
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
    
    def berechne_umfrage_spitzenreiter(self, kontext: SpielKontext) -> Optional[int]:
        """
        Berechnet den Spieler mit den meisten potentiellen Stimmen.
        
        Diese Methode wird von game_logic aufgerufen und berechnet
        basierend auf bisherigen Abstimmungen.
        
        Returns:
            Spieler-ID des Spitzenreiters oder None
        """
        # Die Berechnung sollte in game_logic erfolgen,
        # da dort Zugriff auf SpielAktion etc. besteht
        return None
