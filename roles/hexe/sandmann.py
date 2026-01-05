"""
Sandmann - Der Schlafbringer.

Der Sandmann kann jede Nacht einen Spieler
einschläfern, sodass dieser seine Aktion verpasst.
"""
from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Sandmann(Role):
    """
    Sandmann - Blockierungs-Rolle.
    
    Fähigkeiten:
    - Kann jede Nacht einen Spieler einschläfern
    - Eingeschläferter Spieler kann keine Nacht-Aktion ausführen
    
    Besonderheiten:
    - Sehr frühe Priorität (vor allen anderen)
    - Kann Werwölfe blockieren
    - Kann auch Verbündete versehentlich blockieren
    
    Gewinnbedingung: Dorf gewinnt.
    """
    
    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=44,
            name='Sandmann',
            team=Team.DORF,
            kategorie=Kategorie.HEXE,
            beschreibung=(
                'Du bist der Sandmann. Jede Nacht kannst du einen Spieler '
                'einschläfern - dieser kann seine Nachtaktion nicht ausführen '
                'und verschläft die Phase!'
            ),
            icon='fa-solid fa-bed',
            farbe='#ddd6fe',
            prioritaet=15,  # Sehr früh, vor allen anderen!
            erzaehler_nacht=(
                'Der Sandmann erwacht ZUERST und wählt einen Spieler, '
                'der diese Nacht verschläft und seine Aktion nicht ausführen kann.'
            ),
            erweiterung=Erweiterung.SONDEREDITION,

            # Visual Styling
            avatar_gradient_from="#ddd6fe",
            avatar_gradient_to="#c4b5fd",
            avatar_border_color="#ede9fe",
            badge_emoji="💤",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.AUFWECKEN  # Ironischerweise schläfert er ein
    
    @property
    def erlaubte_ziele(self) -> str:
        return "andere"
    
    def is_active_on_first_night(self) -> bool:
        """Sandmann acts on first night."""
        return True
    
    def is_active_on_every_night(self) -> bool:
        """Sandmann acts every night."""
        return True
    
    def get_ui_definition(self) -> 'RollenUI':
        """Returns the UI definition for Sandmann's action panel."""
        from ..base import RollenUI, UIButton
        return RollenUI(
            title="Sandmann - Einschläfern",
            instructions="Wähle einen Spieler, der diese Nacht einschläft und seine Aktion nicht ausführen kann.",
            buttons=[
                UIButton(
                    label="Einschläfern",
                    action_type="einschlaefern",
                    icon="fa-solid fa-bed",
                    css_class="btn-info"
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=True
        )
    
    def on_nacht_aktion(self, spieler: 'Spieler', ziel: Optional['Spieler'],
                        kontext: SpielKontext) -> Optional[AktionsErgebnis]:
        """
        Sandmann schläfert einen Spieler ein.
        
        Der eingeschläferte Spieler:
        - Kann seine Nacht-Aktion nicht ausführen
        - Wird nicht von Werwölfen geweckt (wenn er Wolf ist)
        - Wird nicht von der Seherin gesehen (wenn er Seherin ist)
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast diese Nacht niemanden eingeschläfert.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )
        
        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel.",
            )
        
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} wird diese Nacht tief und fest schlafen...",
            ziel_spieler_id=ziel.id,
            effekte={
                "eingeschlaefert": ziel.id,
                "nacht_aktion_blockiert": True,
            },
            log_sichtbar_fuer="erzaehler",
        )
