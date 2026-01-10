"""
Prostituierte - Schutz durch Gesellschaft.

Die Prostituierte schläft jede Nacht bei jemandem
und schützt beide, aber verrät ihre Identität.
"""

from typing import Optional, TYPE_CHECKING
from ..base import (
    RollenModell,
    AppearanceFeature,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Prostituierte(Role):
    """
    Prostituierte - Schutz-mit-Risiko-Rolle.

    Fähigkeiten:
    - Wählt jede Nacht einen Spieler
    - Beide sind in dieser Nacht geschützt
    - Der Partner erfährt ihre Rolle

    Besonderheiten:
    - Gefährlich wenn Partner Werwolf ist
    - Partner weiß, wer sie ist
    - Gegenseitiger Schutz

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=63,
            name="Prostituierte",
            team=Team.DORF,
            kategorie=Kategorie.HEILER,
            beschreibung=(
                "Du bist die Prostituierte. Jede Nacht kannst du bei einem "
                "Spieler schlafen - ihr beide seid diese Nacht geschützt, "
                "aber er sieht deine Rolle!"
            ),
            icon="fa-solid fa-bed",
            farbe="#f43f5e",
            prioritaet=46,  # Vor Werwölfen
            erzaehler_nacht=(
                "Die Prostituierte erwacht und wählt einen Spieler für " "die Nacht."
            ),
            erweiterung=Erweiterung.COMMUNITY,
            distribution=DistributionConfig(
                min_players=10,
                count_func=lambda n: 1,
                priority=25,
            ),
            # Visual Styling
            avatar_gradient_from="#f43f5e",
            avatar_gradient_to="#be123c",
            avatar_border_color="#fb7185",
            badge_emoji="💋",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SCHUETZEN

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    def is_active_on_first_night(self) -> bool:
        """Prostituierte acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Prostituierte acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Prostituierte's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Prostituierte - Bei jemandem schlafen",
            instructions="Wähle einen Spieler, bei dem du diese Nacht schläfst. Ihr beide seid geschützt, aber er erfährt deine Rolle.",
            buttons=[
                UIButton(
                    label="Besuchen",
                    action_type="schuetzen",
                    icon="fa-solid fa-bed",
                    css_class="btn-primary",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prostituierte wählt ihren Partner für die Nacht.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du bleibst diese Nacht alleine zuhause.",
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
            nachricht=(
                f"Du verbringst die Nacht bei {ziel.name}. "
                f"Ihr seid beide geschützt - aber er weiß nun wer du bist!"
            ),
            ziel_spieler_id=ziel.id,
            effekte={
                "prostituierte_bei": ziel.id,
                "partner_weiss_rolle": ziel.id,
            },
            multi_target_updates={
                spieler.id: {"global.ist_beschuetzt": True},
                ziel.id: {"global.ist_beschuetzt": True},
                # Identität enthüllen via Private Info handled below/elsewhere?
                # Actually, "partner_weiss_rolle" might be handled by UI/Logs?
                # Let's verify if we need to send a private message here.
            },
            private_infos={
                ziel.id: {
                    "nachricht": f"{spieler.name} hat die Nacht bei dir verbracht. Sie ist die Prostituierte!",
                    "alert_type": "warning",
                }
            },
            log_sichtbar_fuer="erzaehler",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Prostituierte."""
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
            modell_id="prostituierte",
            anzeige_name="Prostituierte",
            beschreibung="Prostituierte appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
