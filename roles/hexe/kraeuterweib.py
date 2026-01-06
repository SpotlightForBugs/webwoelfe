"""
Kraeuterweib - Kann Spieler stumm machen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import (
    RollenModell,
    AppearanceFeature,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Kraeuterweib(Role):
    """
    Das Kräuterweib - Stummheits-Rolle.

    Fähigkeiten:
    - Kann jede Nacht einen Spieler stumm machen
    - Stumme Spieler dürfen am nächsten Tag nicht reden

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=41,
            name="Kräuterweib",
            team=Team.DORF,
            kategorie=Kategorie.HEXE,
            beschreibung=(
                "Du bist das Kräuterweib. Jede Nacht kannst du einem "
                "Spieler einen Stumm-Trank verabreichen. Dieser darf am "
                "nächsten Tag nicht sprechen."
            ),
            icon="fa-solid fa-leaf",
            farbe="#22c55e",
            prioritaet=65,
            erzaehler_nacht=(
                "Das Kräuterweib erwacht und wählt einen Spieler, "
                "der morgen stumm sein wird."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#22c55e",
            avatar_gradient_to="#15803d",
            avatar_border_color="#4ade80",
            badge_emoji="🌿",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.STUMM_MACHEN

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    def is_active_on_first_night(self) -> bool:
        """Kräuterweib acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Kräuterweib acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Kräuterweib's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Kräuterweib - Stumm machen",
            instructions="Wähle einen Spieler, der morgen stumm sein wird.",
            buttons=[
                UIButton(
                    label="Stumm machen",
                    action_type="stumm_machen",
                    icon="fa-solid fa-leaf",
                    css_class="btn-warning",
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
        Kräuterweib macht einen Spieler stumm.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast diese Nacht niemanden stumm gemacht.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} wird morgen stumm sein.",
            ziel_spieler_id=ziel.id,
            effekte={
                "stumm_gemacht": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Kraeuterweib."""
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
            modell_id="kraeuterweib",
            anzeige_name="Kraeuterweib",
            beschreibung="Kraeuterweib appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
