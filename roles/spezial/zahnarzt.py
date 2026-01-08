"""
Zahnarzt - Blockiert Abstimmungen.

Der Zahnarzt näht einem Spieler den Mund zu,
sodass dieser am nächsten Tag nicht abstimmen darf.
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
class Zahnarzt(Role):
    """
    Zahnarzt - Abstimmungs-Blocker.

    Fähigkeiten:
    - Blockiert jede Nacht die Stimme eines Spielers
    - Spieler kann noch sprechen, aber nicht abstimmen

    Besonderheiten:
    - Kann Wölfe am Abstimmen hindern
    - Kann aber auch wichtige Dorf-Stimmen blockieren

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=72,
            name="Zahnarzt",
            team=Team.DORF,
            kategorie=Kategorie.SPEZIAL,
            beschreibung=(
                "Du bist der Zahnarzt. Jede Nacht kannst du einem Spieler "
                "den Mund zunähen - er kann am nächsten Tag nicht abstimmen, "
                "nur sprechen!"
            ),
            icon="fa-solid fa-tooth",
            farbe="#ffffff",
            prioritaet=66,
            erzaehler_nacht=(
                "Der Zahnarzt erwacht und wählt einen Spieler, "
                "der morgen nicht abstimmen darf."
            ),
            erweiterung=Erweiterung.COMMUNITY,
            # Visual Styling
            avatar_gradient_from="#ffffff",
            avatar_gradient_to="#e5e7eb",
            avatar_border_color="#d1d5db",
            badge_emoji="🦷",
        )

    def is_active_on_first_night(self) -> bool:
        """Zahnarzt acts every night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Zahnarzt acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Zahnarzt's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Zahnarzt - Mund zunähen",
            instructions="Blockiere die Stimme eines Spielers für morgen.",
            buttons=[
                UIButton(
                    label="Blockieren",
                    action_type="blockieren",
                    icon="fa-solid fa-tooth",
                    css_class="btn-secondary",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=True,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.BLOCKIEREN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Zahnarzt näht einem Spieler den Mund zu.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du lässt deine Werkzeuge heute ruhen.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst bei Toten nichts nähen.",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du nähst {ziel.name} den Mund zu. Er darf morgen nicht abstimmen!",
            ziel_spieler_id=ziel.id,
            effekte={
                "zahnarzt_blockiert": ziel.id,
                "stimme_blockiert": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Zahnarzt."""
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
            modell_id="zahnarzt",
            anzeige_name="Zahnarzt",
            beschreibung="Zahnarzt appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
