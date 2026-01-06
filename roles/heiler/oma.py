"""
Oma - Die unantastbare Alte.

Die Oma kann nicht von Werwölfen getötet werden -
sie ist zu alt und schwach.
"""

from typing import Optional, TYPE_CHECKING
from ..base import RollenModell, AppearanceFeature, Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Oma(Role):
    """
    Oma - Werwolf-Immun-Rolle.

    Fähigkeiten:
    - Kann NICHT von Werwölfen getötet werden
    - Stirbt aber durch Hexe, Jäger, Hinrichtung

    Besonderheiten:
    - Passive Rolle (keine Nacht-Aktion)
    - Immunität gegen Werwolf-Angriffe
    - Kann das Spiel verlangsamen

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=64,
            name="Oma",
            team=Team.DORF,
            kategorie=Kategorie.HEILER,
            beschreibung=(
                "Du bist die Oma. Du bist alt und schwach - die Werwölfe "
                "verschonen dich aus Mitleid! Du kannst nicht von Wölfen "
                "getötet werden."
            ),
            icon="fa-solid fa-person-dress",
            farbe="#fda4af",
            prioritaet=100,
            erzaehler_nacht=(
                "Die Oma schnarcht leise in ihrem Bett. Die Werwölfe "
                "haben Mitleid mit der alten Frau."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#fda4af",
            avatar_gradient_to="#f43f5e",
            avatar_border_color="#fb7185",
            badge_emoji="👵",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Oma does not act on first night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Oma is passive and does not act at night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Oma's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Oma - Passive Rolle",
            instructions="Du bist immun gegen Werwolf-Angriffe.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_angegriffen(
        self, spieler: "Spieler", angreifer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Die Oma ist immun gegen Werwolf-Angriffe.
        """
        # Prüfe ob der Angreifer ein Werwolf ist
        angreifer_rolle = RoleRegistry.get(angreifer.rolle)

        if angreifer_rolle and angreifer_rolle.info.team == Team.WERWOLF:
            # Angriff wird geblockt!
            return AktionsErgebnis(
                erfolg=False,  # False = Angriff wird geblockt
                nachricht=(
                    "Die Werwölfe schauen die alte Oma an... "
                    "und drehen sich um. Sie ist zu alt für sie."
                ),
                effekte={
                    "angriff_geblockt": True,
                    "oma_verschont": True,
                },
                log_sichtbar_fuer="erzaehler",
            )

        # Andere Angriffe (Hexe, Jäger) funktionieren normal
        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Oma."""
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
            modell_id="oma",
            anzeige_name="Oma",
            beschreibung="Oma appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
