"""
Rabe - Markiert Spieler für Extra-Stimmen.

Der Rabe markiert jede Nacht einen Spieler,
der am nächsten Tag 2 Extra-Stimmen gegen sich erhält.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Rabe(Role):
    """
    Rabe - Markierungs-Rolle.
    
    Fähigkeiten:
    - Markiert jede Nacht einen Spieler
    - Markierter erhält +2 Stimmen gegen sich
    
    Besonderheiten:
    - Kann Verdächtige schneller hinrichten
    - Kann auch Unschuldige in Gefahr bringen
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=73,
            name='Rabe',
            team=Team.DORF,
            kategorie=Kategorie.SPEZIAL,
            beschreibung=(
                'Du bist der Rabe. Jede Nacht markierst du einen Spieler. '
                'Dieser erhält am nächsten Tag automatisch 2 Extra-Stimmen '
                'gegen sich!'
            ),
            icon='fa-solid fa-crow',
            farbe='#1f2937',
            prioritaet=65,
            erzaehler_nacht=(
                'Der Rabe erwacht und markiert einen Spieler '
                '(+2 Stimmen gegen ihn morgen).'
            ),
            erzaehler_tag=(
                '{spieler} wurde vom Raben markiert und hat +2 Stimmen gegen sich!'
            ),
            hinweis_config=None,
        )
    
    def is_active_on_first_night(self) -> bool:
        """Rabe acts every night."""
        return True
    
    def is_active_on_every_night(self) -> bool:
        """Rabe acts every night."""
        return True
    
    def get_ui_definition(self) -> 'RollenUI':
        """Returns the UI definition for Rabe's action panel."""
        from ..base import RollenUI, UIButton
        return RollenUI(
            title="Rabe - Markieren",
            instructions="Markiere einen Spieler für 2 Extra-Stimmen morgen.",
            buttons=[
                UIButton(
                    label="Markieren",
                    action_type="manipulieren",
                    icon="fa-solid fa-crow",
                    css_class="btn-secondary"
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=True
        )
    
    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.MANIPULIEREN
    
    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Rabe markiert einen Spieler.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Der Rabe fliegt ruhelos, markiert aber niemanden.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst keine Toten markieren.",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du markierst {ziel.name}. Er wird morgen +2 Stimmen gegen sich haben!",
            ziel_spieler_id=ziel.id,
            effekte={
                "rabe_markiert": ziel.id,
                "extra_stimmen_gegen": 2,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
