"""
Werwolfseherin - Werwolf mit Seher-Kräften.

Die Werwolfseherin jagt mit den Wölfen und kann
jede Nacht die Rolle eines Spielers sehen.
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
from ..enums import Team, Kategorie, SichtTyp, Erweiterung, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Werwolfseherin(Role):
    """
    Werwolfseherin - Werwolf mit Seher-Fähigkeit.

    Fähigkeiten:
    - Jagt mit den Wölfen
    - Kann jede Nacht (nach dem Werwolf-Angriff) eine Rolle sehen

    Besonderheiten:
    - Sieht die tatsächliche Rolle
    - Aktiviert nach den Werwölfen (höhere Priorität)
    - Kann helfen, gefährliche Rollen zu identifizieren

    Gewinnbedingung: Werwölfe gewinnen.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=27,
            name="Werwolfseherin",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist die Werwolfseherin. Du bist ein Werwolf mit "
                "Seher-Kräften! Jede Nacht erfährst du die Rolle eines "
                "Spielers (nach dem Werwolf-Angriff)."
            ),
            icon="fa-solid fa-eye",
            farbe="#b91c1c",
            prioritaet=65,  # Nach Werwölfen
            erzaehler_nacht=(
                "Die Werwolfseherin erwacht nach den Werwölfen und "
                "erfährt die Rolle eines Spielers."
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            distribution=DistributionConfig(
                min_players=12,
                count_func=lambda n: 1,
                priority=55,
                exclusive_with=["Werwolf"],
            ),
            # Visual Styling
            avatar_gradient_from="#b91c1c",
            avatar_gradient_to="#7f1d1d",
            avatar_border_color="#ef4444",
            badge_emoji="fa-solid fa-eye",
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import AktionsTyp

        return AktionsTyp.SEHEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    @property
    def is_group_action(self) -> bool:
        """Werwolfseherin stimmt mit dem Rudel ab."""
        return True

    @property
    def shared_phase_name(self) -> str:
        """Werwolfseherin teilt sich die werwolf_phase mit dem Rudel."""
        return "werwolf_phase"

    def is_active_on_first_night(self) -> bool:
        """Werwolfseherin acts every night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Werwolfseherin acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Werwolfseherin's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Werwolfseherin - Sehen",
            instructions="Wähle einen Spieler, um seine Rolle zu erfahren.",
            buttons=[
                UIButton(
                    label="Sehen",
                    action_type="sehen",
                    icon="fa-solid fa-eye",
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
        Werwolfseherin sieht die Rolle eines Spielers.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast diese Nacht niemanden beobachtet.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        # Rolle ermitteln
        ziel_rolle = RoleRegistry.get(ziel.rolle)
        if ziel_rolle:
            rollen_name = ziel_rolle.info.name
        else:
            rollen_name = ziel.rolle or "Unbekannt"

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Deine Vision zeigt: {ziel.name} ist ein {rollen_name}!",
            ziel_spieler_id=ziel.id,
            effekte={
                "gesehen": ziel.id,
                "rolle": rollen_name,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Werwolfseherin."""
        appearance_features = [
            AppearanceFeature(
                feature_type="wolf_ear_left",
                geometry="cone",
                position={"x": -0.18, "y": 2.25, "z": -0.05},
                scale={"x": 0.12, "y": 0.2, "z": 0.1},
                rotation={"x": 0, "y": 0, "z": -15},
                color_source="role",
                description="Left wolf ear",
            ),
            AppearanceFeature(
                feature_type="wolf_ear_right",
                geometry="cone",
                position={"x": 0.18, "y": 2.25, "z": -0.05},
                scale={"x": 0.12, "y": 0.2, "z": 0.1},
                rotation={"x": 0, "y": 0, "z": 15},
                color_source="role",
                description="Right wolf ear",
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
            modell_id="werwolfseherin",
            anzeige_name="Werwolfseherin",
            beschreibung="Werwolfseherin appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="bad",
        )
