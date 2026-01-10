"""
Buddler - Der Grabenanthropöloge.

Der Buddler kann jede Nacht ein Grab untersuchen
und die Todesursache erfahren.
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
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Buddler(Role):
    """
    Buddler - Toten-Informations-Rolle.

    Fähigkeiten:
    - Kann jede Nacht ein Grab ausgraben
    - Erfährt wie dieser Spieler gestorben ist

    Besonderheiten:
    - Ziel muss tot sein
    - Todesursache kann wichtige Hinweise geben

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=57,
            name="Buddler",
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der Buddler. Jede Nacht kannst du ein Grab ausgraben "
                "und erfährst die Todesursache des Spielers - Werwolf, "
                "Abstimmung, Gift oder Anderes."
            ),
            icon="fa-solid fa-shovel",
            farbe="#78716c",
            prioritaet=80,
            erzaehler_nacht=(
                "Der Buddler erwacht und wählt ein Grab. "
                "Flüstere ihm die Todesursache zu."
            ),
            erweiterung=Erweiterung.COMMUNITY,
            distribution=DistributionConfig(
                min_players=12,
                count_func=lambda n: 1,
                priority=20,
            ),
            # Visual Styling
            avatar_gradient_from="#78716c",
            avatar_gradient_to="#57534e",
            avatar_border_color="#a8a29e",
            badge_emoji="⛏️",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN

    @property
    def erlaubte_ziele(self) -> str:
        return "tote"

    def is_active_on_first_night(self) -> bool:
        """Buddler does not act on first night (no dead yet)."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Buddler acts every night after first."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Buddler's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Buddler - Grab untersuchen",
            instructions="Wähle das Grab eines Toten, um die Todesursache zu erfahren.",
            buttons=[
                UIButton(
                    label="Grab untersuchen",
                    action_type="sehen",
                    icon="fa-solid fa-shovel",
                    css_class="btn-secondary",
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
        Buddler untersucht ein Grab.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast diese Nacht kein Grab untersucht.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id not in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nur die Gräber von Toten untersuchen.",
            )

        # Die Todesursache wird als Attribut gespeichert
        # In der Praxis muss game_logic dies setzen
        todesursache = getattr(ziel, "todesursache", "unbekannt")

        todesursachen_text = {
            "werwolf": "Werwolf-Bisse",
            "hexe": "Vergiftung",
            "hinrichtung": "Hinrichtung durch das Dorf",
            "jaeger": "Schusswunde",
            "verbrennung": "Feuer",
            "liebeskummer": "Gebrochenes Herz",
        }

        text = todesursachen_text.get(
            todesursache, f"Unbekannte Ursache ({todesursache})"
        )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Das Grab von {ziel.name} zeigt: Tod durch {text}",
            ziel_spieler_id=ziel.id,
            effekte={
                "grab_untersucht": ziel.id,
                "todesursache": todesursache,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Buddler."""
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
            modell_id="buddler",
            anzeige_name="Buddler",
            beschreibung="Buddler appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
