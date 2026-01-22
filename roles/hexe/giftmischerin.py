"""
Giftmischerin - Verzögerte Tötung.
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
class Giftmischerin(Role):
    """
    Die Giftmischerin - Verzögerte Tötung.

    Fähigkeiten:
    - Kann einmal einen Spieler vergiften
    - Vergifteter stirbt nach 2 Tagen

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=161,
            name="Giftmischerin",
            team=Team.DORF,
            kategorie=Kategorie.HEXE,
            beschreibung=(
                "Du bist die Giftmischerin. Du kannst einmal pro Spiel "
                "einen Spieler vergiften. Dieser stirbt nach 2 Tagen "
                "an dem langsam wirkenden Gift."
            ),
            icon="fa-solid fa-flask-vial",
            farbe="#84cc16",
            prioritaet=66,
            erzaehler_nacht=(
                "Die Giftmischerin erwacht. Möchte sie ihr Gift einsetzen?"
            ),
            erweiterung=Erweiterung.COMMUNITY,
            distribution=DistributionConfig(
                min_players=12,
                count_func=lambda n: 1,
                priority=30,
            ),
            # Visual Styling
            avatar_gradient_from="#84cc16",
            avatar_gradient_to="#4d7c0f",
            avatar_border_color="#a3e635",
            badge_emoji="fa-solid fa-flask",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.VERGIFTEN

    def is_active_on_first_night(self) -> bool:
        """Giftmischerin can act on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Giftmischerin acts every night until poison is used."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Giftmischerin's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Giftmischerin - Vergiften",
            instructions="Du kannst einmal pro Spiel einen Spieler vergiften. Dieser stirbt nach 2 Tagen.",
            buttons=[
                UIButton(
                    label="Vergiften",
                    action_type="vergiften",
                    icon="fa-solid fa-flask-vial",
                    css_class="btn-danger",
                    requires_confirmation=True,
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
        Giftmischerin vergiftet mit verzögerter Wirkung.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hebst dein Gift auf.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du hast {ziel.name} vergiftet. In 2 Tagen wird er sterben.",
            ziel_spieler_id=ziel.id,
            effekte={
                "vergiftet": ziel.id,
                "gift_countdown": 2,
                "gift_tod_runde": kontext.runde + 2,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Giftmischerin."""
        appearance_features = [
            AppearanceFeature(
                feature_type="witch_hat",
                geometry="cone",
                position={"x": 0, "y": 2.4, "z": 0},
                scale={"x": 0.3, "y": 0.5, "z": 0.3},
                color_source="custom",
                custom_color="#1a1a1a",
                description="Pointed witch hat",
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
            modell_id="giftmischerin",
            anzeige_name="Giftmischerin",
            beschreibung="Giftmischerin appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
