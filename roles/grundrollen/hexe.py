"""
Hexe - Mächtige Rolle mit zwei Tränken.

Die Hexe kann einmal pro Spiel jemanden heilen
und einmal jemanden vergiften.
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
class Hexe(Role):
    """
    Die Hexe - Mächtige Rolle mit zwei Tränken.

    Fähigkeiten:
    - Heiltrank: Kann einmal pro Spiel das Werwolf-Opfer retten
    - Gifttrank: Kann einmal pro Spiel einen Spieler töten

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        return [
            StateField("heiltrank", StateType.BOOL, True, "Heiltrank verfügbar"),
            StateField("gifttrank", StateType.BOOL, True, "Gifttrank verfügbar"),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=4,
            name="Hexe",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist die Hexe. Du hast zwei Tränke: Einen Heiltrank, um das "
                "Werwolf-Opfer zu retten, und einen Gifttrank, um einen Spieler "
                "zu töten. Jeden Trank kannst du nur einmal verwenden."
            ),
            icon="fa-solid fa-flask",
            farbe="#d946ef",
            prioritaet=90,
            erzaehler_nacht=(
                "Die Hexe erwacht. Ich zeige ihr das Opfer der Werwölfe. "
                "Möchtest du es retten? Möchtest du jemanden vergiften?"
            ),
            erweiterung=Erweiterung.BASISSPIEL,
            # Visual Styling
            avatar_gradient_from="#d946ef",
            avatar_gradient_to="#a21caf",
            avatar_border_color="#f0abfc",
            badge_emoji="🧪",
            distribution=DistributionConfig(
                min_players=5,
                count_func=lambda n: 1,
                priority=90,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE  # Hexe hat mehrere Aktionen

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Hexe acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Hexe acts every night."""
        return True

    @property
    def requires_victim_info(self) -> bool:
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Hexe's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Hexe - Tränke verwenden",
            instructions="Du siehst das Opfer der Werwölfe. Willst du deine Tränke nutzen?",
            buttons=[
                UIButton(
                    label="Heilen",
                    action_type="heilen",
                    icon="fa-solid fa-heart-pulse",
                    css_class="btn-success",
                    requires_confirmation=False,
                ),
                UIButton(
                    label="Vergiften",
                    action_type="vergiften",
                    icon="fa-solid fa-skull-crossbones",
                    css_class="btn-danger",
                    requires_confirmation=True,
                ),
            ],
            requires_target=True,  # For poison
            allow_multiple_targets=False,
            can_skip=True,  # Can choose to do nothing
        )

    def get_phase_start_info(
        self, spieler: "Spieler", kontext: "SpielKontext"
    ) -> Optional[dict]:
        """Zeigt der Hexe das Werwolf-Opfer."""
        if kontext.werwolf_opfer_id:
            return {"werwolf_opfer_id": kontext.werwolf_opfer_id}
        return None

    def on_nacht_aktion(
        self,
        spieler: "Spieler",
        ziel: Optional["Spieler"],
        kontext: SpielKontext,
        aktion: str = None,
    ) -> Optional[AktionsErgebnis]:
        """
        Hexe verwendet einen Trank.
        """
        # Mapping legacy action names if necessary
        # UI uses "action_type": "heilen" or "vergiften"
        # app.py passes this as 'aktion'

        if aktion == "heilen" or aktion == "hexe_heilen":
            if not self.get_state(spieler, "heiltrank"):
                return AktionsErgebnis(False, "Du hast keinen Heiltrank mehr.")

            # Ziel ist das Werwolf-Opfer
            opfer_id = kontext.werwolf_opfer_id
            if not opfer_id:
                return AktionsErgebnis(False, "Es gibt kein Opfer zu heilen.")

            # Wenn Ziel übergeben wurde, muss es das Opfer sein
            if ziel and ziel.id != opfer_id:
                return AktionsErgebnis(False, "Du kannst nur das Werwolf-Opfer heilen.")

            self.set_state(spieler, "heiltrank", False)
            return AktionsErgebnis(
                True,
                "Du hast das Opfer geheilt.",
                ziel_spieler_id=opfer_id,
                effekte={
                    "heilen": True,
                    "hexe_heilen": True,
                    "heiltrank_verbraucht": True,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        elif (
            aktion == "vergiften"
            or aktion == "hexe_vergiften"
            or aktion == "toeten"
            or aktion == "hexe_toeten"
        ):
            if not self.get_state(spieler, "gifttrank"):
                return AktionsErgebnis(False, "Du hast keinen Gifttrank mehr.")

            if not ziel:
                return AktionsErgebnis(False, "Du musst ein Ziel wählen.")

            self.set_state(spieler, "gifttrank", False)
            return AktionsErgebnis(
                True,
                f"Du hast {ziel.name} vergiftet.",
                ziel_spieler_id=ziel.id,
                effekte={
                    "vergiften": True,
                    "hexe_vergiften": True,
                    "gifttrank_verbraucht": True,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Hexe."""
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
            modell_id="hexe",
            anzeige_name="Hexe",
            beschreibung="Hexe appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
