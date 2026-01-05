"""
Floetenspieler - verzaubert alle Spieler.
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
    get_spieler_state,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Floetenspieler(Role):
    """
    Der Flötenspieler - Verzauberungs-Solo.

    Faehigkeiten:
    - Kann jede Nacht 2 Spieler verzaubern
    - Gewinnt wenn alle Lebenden verzaubert sind

    Gewinnbedingung: Alle Lebenden sind verzaubert.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Flötenspielers."""
        return [
            StateField(
                "verzauberte",
                StateType.PLAYER_IDS,
                [],
                "Liste verzauberter Spieler-IDs",
            ),
        ]

    def global_state_definitions(self) -> List[GlobalStateDefinition]:
        """Definiert den Verzaubert-State der auf andere Spieler gesetzt wird."""
        return [
            GlobalStateDefinition(
                key="global.ist_verzaubert",
                name="Verzaubert",
                typ=StateType.BOOL,
                beschreibung="Spieler wurde vom Flötenspieler verzaubert",
                visual_effect=StateVisualEffect.ENCHANTED,
                css_class="verzaubert",
                icon="🎵",
                query_name="verzauberte",
                defined_by="Floetenspieler",
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=101,
            name="Floetenspieler",
            team=Team.SOLO,
            kategorie=Kategorie.SOLO,
            beschreibung=(
                "Du bist der Floetenspieler. Jede Nacht verzauberst du "
                "2 Spieler mit deiner Floete. Du gewinnst wenn alle "
                "lebenden Spieler verzaubert sind!"
            ),
            icon="fa-solid fa-wand-magic-sparkles",
            farbe="#8b5cf6",
            prioritaet=70,
            erzaehler_nacht=(
                "Der Floetenspieler erwacht und waehlt 2 Spieler " "zum Verzaubern."
            ),
            erweiterung=Erweiterung.NEUMOND,

            # Visual Styling
            avatar_gradient_from="#8b5cf6",
            avatar_gradient_to="#5b21b6",
            avatar_border_color="#a78bfa",
            badge_emoji="🎵",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.VERZAUBERN

    def is_active_on_first_night(self) -> bool:
        """Flötenspieler acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Flötenspieler acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Flötenspieler's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Flötenspieler - Verzaubern",
            instructions="Wähle Spieler, um sie zu verzaubern.",
            buttons=[
                UIButton(
                    label="Verzaubern",
                    action_type="verzaubern",
                    icon="fa-solid fa-magic",
                    css_class="btn-primary",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Floetenspieler verzaubert Spieler.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du spielst leise vor dich hin.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        # Add to verzauberte list
        verzauberte = self.get_state(spieler, "verzauberte") or []
        if ziel.id not in verzauberte:
            verzauberte.append(ziel.id)
            self.set_state(spieler, "verzauberte", verzauberte)
            # Mark target as verzaubert (global state)
            set_spieler_state(ziel, "global.ist_verzaubert", True)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du verzauberst {ziel.name} mit deiner Melodie.",
            ziel_spieler_id=ziel.id,
            effekte={
                "verzaubert": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Gewinnt wenn alle Lebenden verzaubert sind.
        """
        verzauberte = self.get_state(spieler, "verzauberte") or []

        # Check if all living players are verzaubert
        for lebender_id in kontext.lebende_spieler:
            if lebender_id == spieler.id:
                continue  # Flötenspieler selbst zählt nicht
            if lebender_id not in verzauberte:
                return None  # Noch nicht alle verzaubert

        # Alle verzaubert!
        return Team.SOLO
