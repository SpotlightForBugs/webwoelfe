"""
Alter Mann - Zäh aber gefährlich für das Dorf.

Der Alte Mann überlebt den ersten Werwolf-Angriff,
aber wenn das Dorf ihn hängt, verlieren alle Spezialrollen ihre Kräfte.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    AppearanceFeature,
    RollenModell,
    AppearanceFeature,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class AlterMann(Role):
    """
    Der Alte Mann - Robuste Dorfrolle mit Risiko.

    Fähigkeiten:
    - Überlebt den ersten Werwolf-Angriff
    - Bei Hinrichtung: Alle Spezialrollen verlieren Fähigkeiten

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Alten Mannes."""
        return [
            StateField("leben", StateType.INT, 2, "Anzahl der verbleibenden Leben"),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=11,
            name="Alter Mann",
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist der Alte Mann. Du überlebst den ersten "
                "Werwolf-Angriff! Aber Vorsicht: Wirst du vom Dorf gehängt, "
                "verlieren alle Spezialrollen ihre Kräfte."
            ),
            icon="fa-solid fa-person-cane",
            farbe="#9ca3af",
            prioritaet=100,
            erzaehler_nacht=(
                "Der Alte Mann schläft tief und fest. Seine Weisheit "
                "schützt ihn vor dem ersten Angriff."
            ),
            erweiterung=Erweiterung.NEUMOND,
            # Visual Styling
            avatar_gradient_from="#9ca3af",
            avatar_gradient_to="#4b5563",
            avatar_border_color="#d1d5db",
            badge_emoji="👴",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        """Alter Mann hat keinen aktiven Nachtschutz."""
        return AktionsTyp.PASSIV

    def is_active_on_first_night(self) -> bool:
        """Alter Mann does not act at night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Alter Mann is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Alter Mann's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Alter Mann - Passive Rolle",
            instructions="Du bist zäh und überlebst den ersten Angriff.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_angegriffen(
        self, spieler: "Spieler", angreifer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Der Alte Mann überlebt den ersten Angriff.
        """
        leben = self.get_state(spieler, "leben")

        if leben > 1:
            # Leben reduzieren
            self.set_state(spieler, "leben", leben - 1)

            return AktionsErgebnis(
                erfolg=False,  # False = Angriff wird geblockt
                nachricht="Der Alte Mann überlebt den Angriff!",
                effekte={
                    "angriff_geblockt": True,
                },
                log_sichtbar_fuer="erzaehler",
            )

        return None  # Normaler Tod

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn der Alte Mann gehängt wird, verflucht er das Dorf.
        """
        if opfer.id == spieler.id:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Der Alte Mann wurde vom Dorf gehängt! "
                    "Vor Enttäuschung verflucht er das Dorf - "
                    "alle Spezialrollen verlieren ihre Fähigkeiten!"
                ),
                effekte={
                    "dorf_verflucht": True,
                    "spezialrollen_deaktiviert": True,
                },
                log_sichtbar_fuer="alle",
            )

        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for AlterMann."""
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
            modell_id="altermann",
            anzeige_name="AlterMann",
            beschreibung="AlterMann appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
