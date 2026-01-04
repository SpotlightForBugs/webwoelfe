"""
Werwolf - Die Hauptrolle des Werwolf-Teams.

Werwölfe erkennen sich gegenseitig und wählen
jede Nacht gemeinsam ein Opfer aus.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Werwolf(Role):
    """
    Standard-Werwolf.

    Fähigkeiten:
    - Erkennt alle anderen Werwölfe
    - Wählt jede Nacht ein Opfer mit dem Rudel

    Gewinnbedingung: Werwölfe sind in Überzahl oder gleichauf.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=2,
            name="Werwolf",
            team=Team.WERWOLF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist ein Werwolf! Jede Nacht ermordest du gemeinsam mit "
                "deinen Werwolf-Gefährten einen Dorfbewohner. Bleibe unentdeckt!"
            ),
            icon="fa-solid fa-paw",
            farbe="#dc2626",
            prioritaet=50,
            erzaehler_nacht=(
                "Die Werwölfe erwachen, erkennen sich und wählen "
                "gemeinsam ein Opfer aus."
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
        return "andere"  # Kann sich nicht selbst töten

    @property
    def basis_hinweis_chance(self) -> float:
        return 0.15  # Höhere Chance für verdächtige Hinweise
    
    def is_active_on_first_night(self) -> bool:
        """Werwolf acts on first night."""
        return True
    
    def is_active_on_every_night(self) -> bool:
        """Werwolf acts every night."""
        return True
    
    def get_ui_definition(self) -> 'RollenUI':
        """Returns the UI definition for Werwolf's action panel."""
        from ..base import RollenUI, UIButton
        return RollenUI(
            title="Werwolf - Opfer wählen",
            instructions="Wähle gemeinsam mit den anderen Werwölfen ein Opfer.",
            buttons=[
                UIButton(
                    label="Töten",
                    action_type="toeten",
                    icon="fa-solid fa-paw",
                    css_class="btn-danger",
                    requires_confirmation=True
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False  # Must vote
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Werwolf-Aktion: Ziel zum Fressen auswählen.

        Hinweis: Die eigentliche Tötung passiert am Ende der Nacht,
        damit Hexe/Heiler noch eingreifen können.
        """
        # Check if already voted
        if self.has_voted_this_phase(spieler, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast bereits gewählt.",
            )

        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Die Werwölfe müssen ein Opfer wählen.",
            )

        # Check if target is valid (not self)
        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel gewählt.",
            )

        # Check if target is another werewolf
        from ..registry import RoleRegistry
        from game_logic import ist_werwolf_rolle

        if ist_werwolf_rolle(ziel.rolle):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst keinen anderen Werwolf wählen.",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Die Werwölfe haben {ziel.name} als Opfer gewählt.",
            ziel_spieler_id=ziel.id,
            effekte={"werwolf_opfer": ziel.id},
            log_sichtbar_fuer="werwolf",
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """Werwölfe erkennen sich in der ersten Nacht."""
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du erkennst deine Mitwölfe.",
            effekte={"erkennt_woelfe": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
