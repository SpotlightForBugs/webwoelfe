"""
Heiler - Schützt Spieler vor nächtlichen Angriffen.

Der Heiler kann jede Nacht einen Spieler schützen,
aber nicht zweimal hintereinander denselben.
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
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Heiler(Role):
    """
    Der Heiler - Beschützer-Rolle.

    Fähigkeiten:
    - Kann jede Nacht einen Spieler vor Werwölfen schützen
    - Darf nicht zweimal hintereinander denselben Spieler schützen

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        return [
            StateField(
                "letztes_ziel_id",
                StateType.PLAYER_ID,
                None,
                "Zuletzt geschützter Spieler",
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=6,
            name="Heiler",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist der Heiler. Jede Nacht kannst du einen Spieler vor den "
                "Werwölfen schützen. Du darfst aber nicht zweimal hintereinander "
                "denselben Spieler schützen."
            ),
            icon="fa-solid fa-hand-holding-medical",
            farbe="#10b981",
            prioritaet=10,
            erzaehler_nacht=(
                "Der Heiler erwacht. Wen möchtest du diese Nacht vor den "
                "Werwölfen schützen?"
            ),
            erweiterung=Erweiterung.NEUMOND,
            # Visual Styling
            avatar_gradient_from="#10b981",
            avatar_gradient_to="#047857",
            avatar_border_color="#34d399",
            badge_emoji="🛡️",
            distribution=DistributionConfig(
                min_players=6,
                count_func=lambda n: 1,
                priority=10,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SCHUETZEN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Heiler acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Heiler acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Heiler's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Heiler - Spieler schützen",
            instructions="Wähle einen Spieler, den du vor den Werwölfen schützen möchtest.",
            buttons=[
                UIButton(
                    label="Schützen",
                    action_type="schuetzen",
                    icon="fa-solid fa-shield-halved",
                    css_class="btn-success",
                    requires_confirmation=True,
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Heiler schützt einen Spieler.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst einen Spieler wählen.",
            )

        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel.",
            )

        # Prüfe ob Ziel == letztes Ziel
        letztes_ziel_id = self.get_state(spieler, "letztes_ziel_id")
        if letztes_ziel_id == ziel.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nicht zweimal hintereinander denselben Spieler schützen.",
            )

        # Speichere neues Ziel
        self.set_state(spieler, "letztes_ziel_id", ziel.id)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du beschützt {ziel.name} in dieser Nacht.",
            ziel_spieler_id=ziel.id,
            effekte={
                "geschuetzt": ziel.id,
                "heiler_schutz": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Heiler."""
        appearance_features = [
            AppearanceFeature(
                feature_type="role_indicator",
                geometry="sphere",
                position={"x": 0, "y": 2.2, "z": 0.2},
                scale={"x": 0.12, "y": 0.12, "z": 0.12},
                color_source="role",
                description="Role indicator orb",
            )
        ]

        return RollenModell(
            modell_id="heiler",
            anzeige_name="Heiler",
            beschreibung="Heiler appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
