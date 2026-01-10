"""
Rabe - Markiert Spieler für Extra-Stimmen.

Der Rabe markiert jede Nacht einen Spieler,
der am nächsten Tag 2 Extra-Stimmen gegen sich erhält.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    AppearanceFeature,
    RollenModell,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
    StateVisualEffect,
    GlobalStateDefinition,
    set_spieler_state,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Rabe(Role):
    """
    Rabe

    Fähigkeiten:
    - Markiert jede Nacht einen Spieler
    - Markierter erhält +2 Stimmen gegen sich

    Besonderheiten:
    - Kann Verdächtige schneller hinrichten
    - Kann auch Unschuldige in Gefahr bringen

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Raben."""
        return [
            StateField(
                "markiert_id", StateType.PLAYER_ID, None, "Aktuell markierter Spieler"
            ),
        ]

    def global_state_definitions(self) -> List[GlobalStateDefinition]:
        """Definiert den Markiert-State der auf andere Spieler gesetzt wird."""
        return [
            GlobalStateDefinition(
                key="global.rabe_markiert",
                name="Vom Raben markiert",
                typ=StateType.BOOL,
                beschreibung="Spieler wurde vom Raben markiert (+2 Stimmen gegen sich)",
                visual_effect=StateVisualEffect.MARKED,
                css_class="rabe-markiert",
                icon="🐦‍⬛",
                query_name="markierte",
                defined_by="Rabe",
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=73,
            name="Rabe",
            team=Team.DORF,
            kategorie=Kategorie.SPEZIAL,
            beschreibung=(
                "Du bist der Rabe. Jede Nacht markierst du einen Spieler. "
                "Dieser erhält am nächsten Tag automatisch 2 Extra-Stimmen "
                "gegen sich!"
            ),
            icon="fa-solid fa-crow",
            farbe="#1f2937",
            prioritaet=65,
            erzaehler_nacht=(
                "Der Rabe erwacht und markiert einen Spieler "
                "(+2 Stimmen gegen ihn morgen)."
            ),
            erzaehler_tag=(
                "{spieler} wurde vom Raben markiert und hat +2 Stimmen gegen sich!"
            ),
            erweiterung=Erweiterung.GEMEINDE,
            distribution=DistributionConfig(
                min_players=10,
                count_func=lambda n: 1,
                priority=30,
            ),
            hinweis_config=None,
            # Visual Styling
            avatar_gradient_from="#1f2937",
            avatar_gradient_to="#030712",
            avatar_border_color="#374151",
            badge_emoji="🐦‍⬛",
        )

    def is_active_on_first_night(self) -> bool:
        """Rabe acts every night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Rabe acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Rabe's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Rabe - Markieren",
            instructions="Markiere einen Spieler für 2 Extra-Stimmen morgen.",
            buttons=[
                UIButton(
                    label="Markieren",
                    action_type="manipulieren",
                    icon="fa-solid fa-crow",
                    css_class="btn-secondary",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=True,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.MANIPULIEREN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Rabe markiert einen Spieler.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Der Rabe fliegt ruhelos, markiert aber niemanden.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst keine Toten markieren.",
            )

        # Speichere Markierung im State
        self.set_state(spieler, "markiert_id", ziel.id)
        # Setze globalen Status auf Ziel
        set_spieler_state(ziel, "global.rabe_markiert", True)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du markierst {ziel.name}. Er wird morgen +2 Stimmen gegen sich haben!",
            ziel_spieler_id=ziel.id,
            effekte={
                "extra_stimmen_gegen": 2,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Rabe."""
        appearance_features = [
            AppearanceFeature(
                feature_type="wings",
                geometry="box",
                position={"x": 0, "y": 1.3, "z": -0.2},
                scale={"x": 0.8, "y": 0.5, "z": 0.1},
                color_source="custom",
                custom_color="#FFFFFF",
                description="Angel wings",
            )
        ]

        return RollenModell(
            modell_id="rabe",
            anzeige_name="Rabe",
            beschreibung="Rabe appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
