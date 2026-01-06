"""
Tanklastwagenfahrer - Der Überfahrer.

Einmal pro Spiel kann der Tanklastwagenfahrer
am Tag jemanden überfahren.
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
class Tanklastwagenfahrer(Role):
    """
    Tanklastwagenfahrer - Einmal-Tag-Kill.

    Fähigkeiten:
    - Einmal pro Spiel am Tag aktivierbar
    - Überfährt einen Spieler
    - Sofortiger Tod

    Besonderheiten:
    - Sehr direkt und effektiv
    - Keine Verteidigung möglich
    - Einmalig

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=54,
            name="Tanklastwagenfahrer",
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der Tanklastwagenfahrer. Einmal pro Spiel kannst du "
                "während des Tages jemanden überfahren - dieser Spieler "
                "stirbt sofort!"
            ),
            icon="fa-solid fa-truck",
            farbe="#64748b",
            prioritaet=92,
            erzaehler_nacht=(
                "Der Tanklastwagenfahrer parkt seinen Laster. "
                "Er wartet auf den richtigen Moment."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#64748b",
            avatar_gradient_to="#475569",
            avatar_border_color="#94a3b8",
            badge_emoji="🚛",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    def is_active_on_first_night(self) -> bool:
        """Tanklastwagenfahrer does not act at night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Tanklastwagenfahrer does not act at night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Tanklastwagenfahrer's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Tanklastwagenfahrer - Tagaktion",
            instructions="Du kannst einmal am Tag jemanden überfahren.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def ist_einmal_faehigkeit(self) -> bool:
        """Kann nur einmal überfahren."""
        return True

    def ist_tag_aktiv(self, spieler: "Spieler", kontext: SpielKontext) -> bool:
        """
        Nur aktiv wenn noch nicht gefahren.
        """
        return not getattr(spieler, "trucker_gefahren", False)

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def ueberfahren(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Überfährt einen Spieler - sofortiger Tod.
        """
        if getattr(spieler, "trucker_gefahren", False):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deinen Laster bereits benutzt!",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nur lebende Spieler überfahren!",
            )

        spieler.trucker_gefahren = True

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"HUUUP! Du überfährst {ziel.name} mit deinem Tanklaster!",
            ziel_spieler_id=ziel.id,
            effekte={
                "trucker_toetet": ziel.id,
                "trucker_gefahren": True,
                "todesursache": "ueberfahren",
            },
            log_sichtbar_fuer="alle",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Tanklastwagenfahrer."""
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
            modell_id="tanklastwagenfahrer",
            anzeige_name="Tanklastwagenfahrer",
            beschreibung="Tanklastwagenfahrer appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
