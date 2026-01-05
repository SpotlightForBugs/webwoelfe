"""
Urwolf - Kann Dorfbewohner infizieren.

Der Urwolf kann einmalig statt zu toeten
einen Dorfbewohner infizieren, der zum Werwolf wird.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
    StateVisualEffect,
    GlobalStateDefinition,
    set_spieler_state,
)
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Urwolf(Role):
    """
    Der Urwolf - Infektions-Werwolf.

    Faehigkeiten:
    - Jagt mit den Woelfen
    - Kann einmalig statt Toetung infizieren
    - Infizierte werden zu Werwoelfen

    Gewinnbedingung: Werwolf-Team gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Urwolfs."""
        return [
            StateField("infektion", StateType.BOOL, True, "Kann noch infizieren"),
        ]

    def global_state_definitions(self) -> List[GlobalStateDefinition]:
        """Definiert den Infiziert-State der auf andere Spieler gesetzt wird."""
        return [
            GlobalStateDefinition(
                key="global.ist_infiziert",
                name="Infiziert",
                typ=StateType.BOOL,
                beschreibung="Spieler wurde vom Urwolf infiziert",
                visual_effect=StateVisualEffect.INFECTED,
                css_class="infiziert",
                icon="🦠",
                query_name="infizierte",
                defined_by="Urwolf",
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=20,
            name="Urwolf",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Urwolf. Einmal pro Spiel kannst du statt zu töten "
                "einen Dorfbewohner infizieren. Er wird sofort zum Werwolf!"
            ),
            icon="fa-solid fa-virus",
            farbe="#7f1d1d",
            prioritaet=50,
            erzaehler_nacht=(
                "Der Urwolf jagt mit dem Rudel. Er kann einmalig "
                "ein Opfer infizieren statt zu töten."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#7f1d1d",
            avatar_gradient_to="#450a0a",
            avatar_border_color="#b91c1c",
            badge_emoji="🐺",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.INFIZIEREN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    def is_active_on_first_night(self) -> bool:
        """Urwolf acts with the pack."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Urwolf acts with the pack."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Urwolf's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Urwolf - Infizieren",
            instructions="Du kannst einmalig das Opfer infizieren statt zu töten.",
            buttons=[
                UIButton(
                    label="Infizieren",
                    action_type="infizieren",
                    icon="fa-solid fa-virus",
                    css_class="btn-success",
                    requires_confirmation=True,
                )
            ],
            requires_target=False,  # Target is the victim of the pack
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Urwolf infiziert das Opfer des Rudels.
        """
        # Check if infection is available
        if not self.get_state(spieler, "infektion"):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deine Infektion bereits verbraucht!",
            )

        # Mark as used
        self.set_state(spieler, "infektion", False)

        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du infizierst das Opfer! Es wird nicht sterben, sondern zum Werwolf werden.",
            effekte={
                "urwolf_infiziert": True,
                "todesursache_verhindert": True,
            },
            log_sichtbar_fuer="werwolf",
        )
