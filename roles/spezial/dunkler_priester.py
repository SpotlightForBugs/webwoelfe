"""
Dunkler Priester - Böser Amor.

Der Dunkle Priester verkuppelt wie Amor zwei Spieler,
gehört aber selbst zu den Werwölfen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import RollenModell, Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class DunklerPriester(Role):
    """
    Dunkler Priester - Werwolf-Amor.

    Fähigkeiten:
    - Wählt in der ersten Nacht zwei Spieler die sich verlieben
    - Die Verliebten sterben zusammen
    - Gehört zum Werwolf-Team

    Besonderheiten:
    - Kann den Wölfen wichtige Dorf-Rollen sichern
    - Verliebte können problematisch sein wenn gemischt

    Gewinnbedingung: Werwölfe gewinnen.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=71,
            name="Dunkler Priester",
            team=Team.WERWOLF,
            kategorie=Kategorie.SPEZIAL,
            beschreibung=(
                "Du bist der Dunkle Priester. Wie Amor wählst du zwei "
                "Spieler die sich verlieben - aber du gehörst zu den "
                "Wölfen und gewinnst mit ihnen!"
            ),
            icon="fa-solid fa-church",
            farbe="#18181b",
            prioritaet=5,
            erzaehler_nacht=(
                "Der Dunkle Priester erwacht (erste Nacht) und wählt "
                "zwei Spieler zum Verlieben."
            ),
            erweiterung=Erweiterung.SONDEREDITION,

            # Visual Styling
            avatar_gradient_from="#18181b",
            avatar_gradient_to="#09090b",
            avatar_border_color="#27272a",
            badge_emoji="🖤",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.WAEHLEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Dunkler Priester acts on first night (matchmaking)."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Dunkler Priester only acts on first night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Dunkler Priester's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Dunkler Priester - Verlieben",
            instructions="Wähle zwei Spieler, die sich verlieben sollen.",
            buttons=[
                UIButton(
                    label="Verlieben",
                    action_type="waehlen",
                    icon="fa-solid fa-heart",
                    css_class="btn-danger",
                )
            ],
            requires_target=True,  # Need to select 2 players? UI handling for 2 targets might be tricky with standard flag.
            allow_multiple_targets=True,  # Set to True for 2 targets
            can_skip=False,
        )

    def verlieben(
        self,
        spieler: "Spieler",
        ziel1: "Spieler",
        ziel2: "Spieler",
        kontext: SpielKontext,
    ) -> AktionsErgebnis:
        """
        Verkuppelt zwei Spieler (wie Amor).
        """
        if getattr(spieler, "dunkler_priester_verkuppelt", False):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast bereits zwei Spieler verkuppelt!",
            )

        if ziel1.id == ziel2.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst zwei verschiedene Spieler wählen!",
            )

        spieler.dunkler_priester_verkuppelt = True

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Dunkle Magie verbindet {ziel1.name} und {ziel2.name}! "
            f"Sie sind nun verliebt und sterben gemeinsam.",
            effekte={
                "verliebt": [ziel1.id, ziel2.id],
                "dunkle_liebe": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )


    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Dunkler Priester."""
        return RollenModell(
            modell_id="dunkler_priester",
            anzeige_name="Dunkler Priester",
            beschreibung="Dunkler Priester appearance in Village 3D",
        )