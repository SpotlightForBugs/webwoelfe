"""
Dorfbewohner - Die Basis-Rolle für das Dorf-Team.

Der Dorfbewohner hat keine speziellen Fähigkeiten,
aber seine Stimme in der Abstimmung ist entscheidend.
"""

from typing import Optional, List
from ..base import (
    RollenModell,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry


@RoleRegistry.register
class Dorfbewohner(Role):
    """
    Einfacher Dorfbewohner ohne spezielle Fähigkeiten.

    Gewinnbedingung: Alle Werwoelfe werden eliminiert.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=1,
            name="Dorfbewohner",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist ein einfacher Dorfbewohner. Hilf dem Dorf, die Werwoelfe "
                "zu entlarven! Du hast keine speziellen Fähigkeiten, aber deine "
                "Stimme zählt."
            ),
            icon="fa-solid fa-user",
            farbe="#6b7280",
            prioritaet=100,
            erweiterung=Erweiterung.BASISSPIEL,
            erzaehler_nacht=(
                "Der Dorfbewohner schläft friedlich. "
                "Er hat keine nächtlichen Fähigkeiten."
            ),
            erzaehler_tag=(
                "Der Dorfbewohner erwacht und hofft, die Woelfe zu entlarven. "
                "Seine Stimme ist seine einzige Waffe."
            ),
            # Visual Styling
            avatar_gradient_from="#0369a1",
            avatar_gradient_to="#075985",
            avatar_border_color="#0ea5e9",
            badge_emoji="🏠",
            distribution=DistributionConfig(
                min_players=0,
                count_func=lambda n: 0,  # Wird als Filler berechnet
                priority=100,
                exclusive_with=[],
                is_filler=True,
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Dorfbewohner does not act on the first night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Dorfbewohner does not act every night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        from ..base import RollenUI

        return RollenUI(
            title="Dorfbewohner - Schlafen",
            instructions="Du schläfst friedlich. Du hast keine nächtliche Aktion.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def get_win_conditions(self) -> List["WinCondition"]:
        """Dorf gewinnt wenn alle Werwölfe tot sind."""
        from ..base import WinCondition

        def check_dorf_win(spieler: "Spieler", kontext: SpielKontext) -> bool:
            wolves = [
                uid
                for uid in kontext.lebende_spieler
                if kontext.spieler_teams.get(uid) == Team.WERWOLF
            ]
            return len(wolves) == 0

        return [
            WinCondition(
                id="dorf_win",
                check_func=check_dorf_win,
                team_override=Team.DORF,
                priority=10,
                description="Alle Werwölfe wurden eliminiert.",
            )
        ]

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Dorfbewohner."""
        return RollenModell(
            modell_id="dorfbewohner",
            anzeige_name="Dorfbewohner",
            beschreibung="Dorfbewohner appearance in Village 3D",
        )
