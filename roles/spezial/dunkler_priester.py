"""
Dunkler Priester - Böser Amor.

Der Dunkle Priester verkuppelt wie Amor zwei Spieler,
gehört aber selbst zu den Werwölfen.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    RollenModell,
    AppearanceFeature,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    DistributionConfig,
    StateField,
    StateType,
    GlobalStateDefinition,
    StateVisualEffect,
)
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

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Dunklen Priesters."""
        return [
            StateField(
                "hat_verkuppelt", StateType.BOOL, False, "Hat bereits Verliebte gewählt"
            ),
        ]

    def global_state_definitions(self) -> List[GlobalStateDefinition]:
        """Definiert den Verliebt-State der auf andere Spieler gesetzt wird."""
        return [
            GlobalStateDefinition(
                key="global.dunkle_liebe_mit_id",
                name="Dunkle Liebe",
                typ=StateType.PLAYER_ID,
                beschreibung="ID des Partners mit dem der Spieler durch dunkle Magie verliebt ist",
                visual_effect=StateVisualEffect.HEART,
                css_class="dunkle-liebe-partner",
                icon="🖤",
                query_name="dunkle_verliebte",
                defined_by="DunklerPriester",
                visible_to=["partner", "source_role"],
                reveals_role=True,
                snapshot_role_on_set=True,
                snapshot_key="global.dunkle_liebe_rolle_snapshot",
            ),
        ]

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
            erweiterung=Erweiterung.COMMUNITY,
            distribution=DistributionConfig(
                min_players=12,
                count_func=lambda n: 1,
                priority=25,
                exclusive_with=["Amor"],
            ),
            # Visual Styling
            avatar_gradient_from="#18181b",
            avatar_gradient_to="#09090b",
            avatar_border_color="#27272a",
            badge_emoji="🖤",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.VERLIEBEN

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
                    action_type="priester_verlieben",
                    icon="fa-solid fa-heart",
                    css_class="btn-danger",
                    requires_confirmation=True,
                )
            ],
            requires_target=True,
            allow_multiple_targets=True,
            min_targets=2,
            max_targets=2,
            can_skip=False,
        )

    def execute_action(
        self,
        action_type: str,
        spieler: "Spieler",
        targets: List["Spieler"],
        kontext: "SpielKontext",
    ) -> Optional[AktionsErgebnis]:
        """
        Execute Dunkler Priester actions dynamically with multi-target support.

        Handles:
        - priester_verlieben: Connect two players as dark lovers
        """
        if action_type == "priester_verlieben":
            if len(targets) != 2:
                return AktionsErgebnis(
                    erfolg=False,
                    nachricht=f"Du musst genau 2 Spieler wählen, nicht {len(targets)}.",
                )
            return self.verlieben(spieler, targets[0], targets[1], kontext)

        return None

    def verlieben(
        self,
        spieler: "Spieler",
        ziel1: "Spieler",
        ziel2: "Spieler",
        kontext: SpielKontext,
    ) -> AktionsErgebnis:
        """
        Verkuppelt zwei Spieler (wie Amor, aber dunkle Magie).
        """
        # Check if already matched
        if self.get_state(spieler, "hat_verkuppelt"):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast bereits zwei Spieler verkuppelt!",
            )

        if ziel1.id == ziel2.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst zwei verschiedene Spieler wählen!",
            )

        if (
            ziel1.id not in kontext.lebende_spieler
            or ziel2.id not in kontext.lebende_spieler
        ):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Beide Spieler müssen am Leben sein.",
            )

        # Mark as used
        self.set_state(spieler, "hat_verkuppelt", True)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Dunkle Magie verbindet {ziel1.name} und {ziel2.name}! "
            f"Sie sind nun verliebt und sterben gemeinsam.",
            effekte={
                "dunkle_liebe": True,
            },
            # Use multi_target_updates like Amor does
            multi_target_updates={
                ziel1.id: {"global.verliebt_mit_id": ziel2.id},
                ziel2.id: {"global.verliebt_mit_id": ziel1.id},
            },
            additional_logs=[
                {
                    "text": f"Du bist verliebt in {ziel2.name}! (Dunkle Liebe)",
                    "sichtbar_fuer": str(ziel1.id),
                },
                {
                    "text": f"Du bist verliebt in {ziel1.name}! (Dunkle Liebe)",
                    "sichtbar_fuer": str(ziel2.id),
                },
            ],
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for DunklerPriester."""
        appearance_features = [
            AppearanceFeature(
                feature_type="accessory",
                geometry="box",
                position={"x": 0.25, "y": 1.0, "z": 0.15},
                scale={"x": 0.1, "y": 0.15, "z": 0.08},
                color_source="role",
                description="Role-specific accessory",
            )
        ]

        return RollenModell(
            modell_id="dunklerpriester",
            anzeige_name="DunklerPriester",
            beschreibung="DunklerPriester appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="bad",
        )
