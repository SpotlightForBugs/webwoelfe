"""
Aurenseherin - Sieht die Aura statt die konkrete Rolle.
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
class Aurenseherin(Role):
    """
    Die Aurenseherin - Alternative Informationsrolle.

    Fähigkeiten:
    - Sieht ob ein Spieler "gut" oder "böse" ist
    - Kann durch manche Tarnungen durchschauen

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=51,
            name="Aurenseherin",
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                "Du bist die Aurenseherin. Du siehst nicht die konkrete "
                "Rolle, sondern ob jemand eine gute oder böse Aura hat."
            ),
            icon="fa-solid fa-circle-radiation",
            farbe="#a78bfa",
            prioritaet=22,
            erzaehler_nacht=(
                "Die Aurenseherin erwacht und wählt einen Spieler. "
                "Zeige: Goldenes Licht (gut) oder dunkler Schatten (böse)."
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            # Visual Styling
            avatar_gradient_from="#a78bfa",
            avatar_gradient_to="#7c3aed",
            avatar_border_color="#c4b5fd",
            badge_emoji="✨",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    def is_active_on_first_night(self) -> bool:
        """Aurenseherin acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Aurenseherin acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Aurenseherin's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Aurenseherin - Aura sehen",
            instructions="Wähle einen Spieler, um seine Aura zu sehen (gut oder böse).",
            buttons=[
                UIButton(
                    label="Aura sehen",
                    action_type="sehen",
                    icon="fa-solid fa-circle-radiation",
                    css_class="btn-info",
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
        Aurenseherin sieht die Aura eines Spielers.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst einen Spieler wählen.",
            )

        from ..registry import RoleRegistry

        ziel_rolle = RoleRegistry.get(ziel.rolle)

        if ziel_rolle:
            team = ziel_rolle.info.team
            ist_boese = team in [Team.WERWOLF, Team.SOLO]
        else:
            ist_boese = False

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} hat eine {'dunkle' if ist_boese else 'helle'} Aura.",
            ziel_spieler_id=ziel.id,
            effekte={
                "aura_gesehen": ziel.id,
                "ist_boese": ist_boese,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Aurenseherin."""
        appearance_features = [
            AppearanceFeature(
                feature_type="mystical_aura",
                geometry="sphere",
                position={"x": 0, "y": 1.5, "z": 0},
                scale={"x": 0.6, "y": 0.8, "z": 0.5},
                color_source="role",
                description="Mystical aura effect",
            )
        ]

        return RollenModell(
            modell_id="aurenseherin",
            anzeige_name="Aurenseherin",
            beschreibung="Aurenseherin appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
