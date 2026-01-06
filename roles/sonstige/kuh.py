"""
Kuh - Die mysteriöse Dorfkuh.

Die Kuh ist eine passive Rolle die jede Nacht für alle hörbar muht.
Sie bietet Milch an, die Dorfbewohner trinken können - aber mit 20%
Wahrscheinlichkeit ist die Milch giftig und tötet den Trinker!

DIESE ROLLE DEMONSTRIERT DAS DYNAMISCHE SYSTEM:
- Jeder sieht die Kuh als Kuh (auch für andere sichtbar)
- Nacht-Sound für alle
- Button den andere Spieler bekommen
- Globaler State auf andere Spieler
"""

import random
from typing import Optional, List, TYPE_CHECKING

from .. import RollenUI
from ..base import (
    AppearanceFeature,
    RollenModell,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
    StateTarget,
    VisualEffectConfig,
    GlobalStateDefinition,
    NachtEvent,
    UIButtonDefinition,
    set_spieler_state,
    get_spieler_state,
)
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Kuh(Role):
    """
    Die Kuh - Passive Dorf-Rolle mit Interaktion.

    Fähigkeiten:
    - Muht jede Nacht (alle hören es)
    - Bietet Milch an die Dorfbewohner trinken können
    - 20% Chance dass die Milch giftig ist
    - Jeder sieht die Kuh als "Kuh"

    Gewinnbedingung: Dorf gewinnt.
    """

    # Konstante für Gift-Wahrscheinlichkeit
    GIFT_CHANCE = 0.20

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder der Kuh."""
        return [
            StateField(
                "milch_gegeben_heute",
                StateType.BOOL,
                False,
                "Hat heute bereits Milch gegeben",
                persistent=False,  # Reset jeden Tag
            ),
            StateField(
                "anzahl_vergiftungen",
                StateType.INT,
                0,
                "Anzahl der Spieler die durch Milch gestorben sind",
            ),
        ]

    def global_state_definitions(self) -> List[GlobalStateDefinition]:
        """Definiert States die auf andere Spieler gesetzt werden."""
        return [
            GlobalStateDefinition(
                key="global.hat_milch_getrunken",
                name="Hat Milch getrunken",
                typ=StateType.BOOL,
                beschreibung="Der Spieler hat Milch von der Kuh getrunken",
                visual_config=VisualEffectConfig(
                    css_class="hat-milch",
                    icon="🥛",
                    tooltip="Hat Milch getrunken",
                    # Nur der Spieler selbst und Erzähler sehen es
                    show_to=lambda viewer, target: viewer.id == target.id
                    or viewer.ist_erzaehler,
                ),
                query_name="milchtrinker",
                defined_by="Kuh",
            ),
            GlobalStateDefinition(
                key="global.milchvergiftung",
                name="Milchvergiftung",
                typ=StateType.BOOL,
                beschreibung="Der Spieler wurde durch giftige Milch vergiftet",
                visual_config=VisualEffectConfig(
                    css_class="vergiftet",
                    icon="☠️",
                    animation="shake",
                    tooltip="Durch Milch vergiftet!",
                ),
                query_name="milchvergiftete",
                defined_by="Kuh",
            ),
        ]

    def get_nacht_events(self) -> List[NachtEvent]:
        """Kuh muht jede Nacht - alle hören es."""
        return [
            NachtEvent(
                event_id="kuh_muht",
                sound_file="audio/moo.mp3",
                text="Die Dorfkuh muht laut in der Nacht... Muuuuh!",
                animation="fade-in-out",
                phases=["nacht"],
                # Immer triggern wenn Kuh im Spiel
                trigger_condition=lambda kontext: True,
            ),
        ]

    def get_ui_buttons_for_others(self) -> List[UIButtonDefinition]:
        """
        Fügt einen "Milch trinken" Button für alle Dorfbewohner hinzu.
        """
        # Liste der Rollen die Milch trinken können (Dorf-Team)
        dorf_rollen = [
            "Dorfbewohner",
        ]

        return [
            UIButtonDefinition(
                button_id="milch_trinken",
                label="Milch trinken",
                action_type="milch_trinken",
                icon="fa-solid fa-glass-water",
                css_class="btn-info",
                tooltip="Trinke frische Milch von der Dorfkuh (Vorsicht: könnte giftig sein!)",
                requires_confirmation=True,
                # Nur Dorfbewohner können Milch trinken
                show_to=lambda spieler, kontext: (
                    spieler.rolle in dorf_rollen
                    and spieler.ist_am_leben
                    and not get_spieler_state(spieler, "global.hat_milch_getrunken")
                ),
                on_click=self._handle_milch_trinken,
            ),
        ]

    def _handle_milch_trinken(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Handler wenn ein Spieler Milch trinkt.

        20% Chance auf Vergiftung!
        """
        # Markiere dass Spieler Milch getrunken hat
        set_spieler_state(spieler, "global.hat_milch_getrunken", True)

        # 20% Chance auf Gift
        ist_giftig = random.random() < self.GIFT_CHANCE

        if ist_giftig:
            set_spieler_state(spieler, "global.milchvergiftung", True)
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Du trinkst die Milch... Sie schmeckt seltsam! "
                    "Dir wird schlecht - die Milch war vergiftet! ☠️"
                ),
                effekte={
                    "vergiftet": True,
                    "tod_naechste_nacht": True,
                    "todesursache": "milchvergiftung",
                },
                log_sichtbar_fuer="erzaehler",
            )
        else:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Du trinkst die frische Milch. Mmmmh, lecker! 🥛 "
                    "Du fühlst dich gestärkt."
                ),
                effekte={
                    "milch_getrunken": True,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

    def get_sichtbare_rolle(self, spieler: "Spieler") -> str:
        """Kuh sieht sich immer als Kuh."""
        return "Kuh"

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Kuh."""
        appearance_features = [
            AppearanceFeature(
                feature_type="cow_ear_left",
                geometry="box",
                position={"x": -0.2, "y": 1.9, "z": 0},
                scale={"x": 0.2, "y": 0.3, "z": 0.05},
                rotation={"x": 0, "y": 0, "z": -40},
                color_source="custom",
                custom_color="#8B4513",
                description="Floppy cow ear",
            ),
            AppearanceFeature(
                feature_type="accessory",
                geometry="box",
                position={"x": 0.25, "y": 1.0, "z": 0.15},
                scale={"x": 0.1, "y": 0.15, "z": 0.08},
                color_source="role",
                description="Role-specific accessory",
            ),
        ]

        return RollenModell(
            modell_id="kuh",
            anzeige_name="Kuh",
            beschreibung="Kuh appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=200,  # Hohe ID für Custom-Rolle
            name="Kuh",
            team=Team.DORF,
            kategorie=Kategorie.SONSTIGE,
            beschreibung=(
                "Du bist die Dorfkuh! Jede Nacht muhst du laut und alle "
                "hören es. Du bietest den Dorfbewohnern deine Milch an - "
                "aber Vorsicht: 20% der Milch ist giftig! Muhhhh! 🐄"
            ),
            icon="fa-solid fa-cow",
            farbe="#8B4513",  # Braun
            prioritaet=200,  # Niedrige Priorität (passiv)
            erzaehler_nacht="Die Kuh muht in der Nacht. Alle hören es.",
            erzaehler_tag="Die Kuh bietet ihre Milch an. Wer traut sich zu trinken?",
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#8B4513",
            avatar_gradient_to="#654321",
            avatar_border_color="#A0522D",
            badge_emoji="🐄",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        """Kuh hat keine aktive Aktion."""
        return AktionsTyp.KEINE

    @property
    def sichtbar_als(self) -> SichtTyp:
        """Kuh ist für alle als Dorf sichtbar."""
        return SichtTyp.DORF

    def is_active_on_first_night(self) -> bool:
        """Kuh ist passiv."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Kuh ist passiv."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Kuh hat kein eigenes Aktions-Panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Kuh - Passive Rolle",
            instructions=(
                "Du bist die Dorfkuh. Jede Nacht muhst du automatisch. "
                "Deine Milch wird den Dorfbewohnern angeboten."
            ),
            buttons=[],
            requires_target=False,
            can_skip=True,
        )

    def on_tag_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """Reset Milch-Status für neuen Tag."""
        self.set_state(spieler, "milch_gegeben_heute", False)
        return None
