"""
Seherlehrling - Wird zur Seherin wenn die Original-Seherin stirbt.
"""

from typing import Optional, TYPE_CHECKING
from ..base import RollenModell, AppearanceFeature, Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Seherlehrling(Role):
    """
    Der Seherlehrling - Nachfolger der Seherin.

    Fähigkeiten:
    - Keine aktiven Fähigkeiten zu Beginn
    - Wenn Seherin stirbt: Übernimmt ihre Fähigkeit

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=50,
            name="Seherlehrling",
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                "Du bist der Seherlehrling. Du hast noch keine Fähigkeiten, "
                "aber wenn die Seherin stirbt, übernimmst du ihre Gabe "
                "und kannst selbst sehen."
            ),
            icon="fa-solid fa-eye-low-vision",
            farbe="#8b5cf6",  # Wird aktiv wenn Seherin stirbt
            prioritaet=21,
            erzaehler_nacht=("Der Seherlehrling schläft. Noch lernt er..."),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#8b5cf6",
            avatar_gradient_to="#6d28d9",
            avatar_border_color="#a78bfa",
            badge_emoji="🎓",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN

    def is_active_on_first_night(self) -> bool:
        """Seherlehrling does not act until Seherin dies."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Seherlehrling is passive until activated."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Seherlehrling's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Seherlehrling",
            instructions="Du übernimmst die Sehergabe, wenn die Seherin stirbt.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        opfer: "Spieler",
        todesursache: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob die Seherin stirbt und der Lehrling übernimmt.
        """
        if opfer.rolle == "Seherin":
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Die Seherin ist tot! Der Seherlehrling übernimmt "
                    "ihre Gabe und wird zur neuen Seherin."
                ),
                effekte={
                    "wird_seherin": True,
                    "nacht_aktiv": True,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Seherlehrling."""
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
            modell_id="seherlehrling",
            anzeige_name="Seherlehrling",
            beschreibung="Seherlehrling appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
