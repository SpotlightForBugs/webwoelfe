"""
Freimaurer - Geheime Loge im Dorf.

Die Freimaurer erkennen sich gegenseitig und wissen,
dass sie auf der gleichen Seite stehen.
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
from ..enums import Team, Kategorie, Erweiterung, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Freimaurer(Role):
    """
    Freimaurer - Gruppen-Vertrauensrolle.

    Fähigkeiten:
    - Erkennen sich alle in der ersten Nacht
    - Wissen wem sie vertrauen können

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=15,
            name="Freimaurer",
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist ein Freimaurer. In der ersten Nacht erkennen "
                "sich alle Freimaurer gegenseitig. Ihr wisst, dass ihr "
                "auf der gleichen Seite steht."
            ),
            icon="fa-solid fa-building-columns",
            farbe="#3b82f6",
            prioritaet=9,
            erzaehler_nacht=("Die Freimaurer erwachen und erkennen sich gegenseitig."),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#3b82f6",
            avatar_gradient_to="#1d4ed8",
            avatar_border_color="#60a5fa",
            badge_emoji="🏛️",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Freimaurer act on first night (recognize each other)."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Freimaurer only act on first night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Freimaurer action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Freimaurer - Erkennen",
            instructions="Du erkennst die anderen Freimaurer.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Die Freimaurer erkennen sich.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du erkennst deine Logen-Brüder.",
            effekte={"erkennt_freimaurer": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Freimaurer."""
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
            modell_id="freimaurer",
            anzeige_name="Freimaurer",
            beschreibung="Freimaurer appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
