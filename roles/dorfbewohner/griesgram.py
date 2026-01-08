"""
Griesgram - Der ewige Nörgler.

Der Griesgram ist immer schlecht gelaunt und stimmt
bei jeder Hinrichtung automatisch mit JA.
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
class Griesgram(Role):
    """
    Griesgram - zwanghafte Abstimmungsrolle.

    Fähigkeiten:
    - Stimmt IMMER mit JA bei Hinrichtungen
    - Kann nicht anders abstimmen (Zwang)
    - Zählt trotzdem als normale Stimme

    Besonderheiten:
    - Passive Rolle (keine Nacht-Aktion)
    - Seine Stimme wird automatisch als JA gezählt
    - Kann strategisch genutzt werden um Werwölfe zu finden

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=16,
            name="Griesgram",
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist der Griesgram. Du bist immer schlecht gelaunt und "
                "stimmst IMMER mit JA bei Hinrichtungen - du kannst nicht "
                "anders! Deine Stimme zählt aber trotzdem."
            ),
            icon="fa-solid fa-face-angry",
            farbe="#6b7280",
            prioritaet=100,
            erzaehler_nacht=(
                "Der Griesgram wälzt sich mürrisch im Bett. "
                "Er freut sich schon auf die nächste Hinrichtung."
            ),
            erweiterung=Erweiterung.COMMUNITY,
            # Visual Styling
            avatar_gradient_from="#6b7280",
            avatar_gradient_to="#4b5563",
            avatar_border_color="#9ca3af",
            badge_emoji="😠",
        )

    def is_active_on_first_night(self) -> bool:
        """Griesgram is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Griesgram is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Griesgram's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Griesgram - Passive Rolle",
            instructions="Du bist immer dagegen. Deine Stimme ist automatisch NEIN.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def on_abstimmung(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Der Griesgram stimmt automatisch mit JA.

        Diese Methode wird aufgerufen wenn eine Abstimmung stattfindet.
        Der Griesgram hat keine Wahl - er muss mit JA stimmen.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{spieler.name} stimmt mürrisch mit JA. (Griesgram-Zwang)",
            effekte={
                "stimme": "ja",
                "stimme_fuer": ziel.id,
                "griesgram_zwang": True,  # Markiert dass dies automatisch war
            },
            log_sichtbar_fuer="alle",
        )

    @property
    def kann_abstimmung_aendern(self) -> bool:
        """
        Der Griesgram kann seine Abstimmung NICHT ändern.
        """
        return False

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Griesgram."""
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
            modell_id="griesgram",
            anzeige_name="Griesgram",
            beschreibung="Griesgram appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
