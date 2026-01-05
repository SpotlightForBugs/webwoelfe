"""
Weisser Wolf - Solo-Werwolf.

Der Weisse Wolf jagt mit den Woelfen, aber kann
jede zweite Nacht auch einen Mitwerwolf toeten.
Er gewinnt nur alleine.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class WeisserWolf(Role):
    """
    Der Weisse Wolf - Solo-Werwolf.

    Faehigkeiten:
    - Jagt mit den Woelfen
    - Kann jede zweite Nacht einen Mitwerwolf toeten

    Gewinnbedingung: Als letzter ueberlebender Werwolf.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=21,
            name="Weißer Wolf",
            team=Team.SOLO,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Weisse Wolf! Du jagst mit den Woelfen, aber "
                "jede zweite Nacht kannst du zusaetzlich einen Mitwerwolf "
                "toeten. Du gewinnst nur alleine!"
            ),
            icon="fa-solid fa-paw",
            farbe="#f5f5f4",
            prioritaet=52,
            erzaehler_nacht=(
                "Der Weisse Wolf erwacht (jede zweite Nacht). "
                "Möchte er einen Mitwerwolf töten?"
            ),
            erweiterung=Erweiterung.GEMEINDE,
            # Visual Styling
            avatar_gradient_from="#f5f5f4",
            avatar_gradient_to="#d6d3d1",
            avatar_border_color="#e7e5e4",
            badge_emoji="🐺",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def erlaubte_ziele(self) -> str:
        return "andere_werwoelfe"

    def is_active_on_first_night(self) -> bool:
        """Weißer Wolf acts on second night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Weißer Wolf acts every second night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Weißer Wolf's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Weißer Wolf - Verrat",
            instructions="Du kannst einen Mitwerwolf töten (jede zweite Nacht).",
            buttons=[
                UIButton(
                    label="Töten",
                    action_type="toeten",
                    icon="fa-solid fa-skull",
                    css_class="btn-danger",
                    requires_confirmation=True,
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
        Weißer Wolf tötet einen Mitwerwolf.
        """
        if kontext.runde % 2 != 0:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du wartest auf die nächste Nacht...",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du verschonst deine Brüder heute Nacht.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        # Check if target is werewolf
        ziel_team = kontext.spieler_teams.get(ziel.id, Team.DORF)
        if ziel_team != Team.WERWOLF:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nur andere Werwölfe töten!",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du tötest {ziel.name}! Ein Konkurrent weniger...",
            ziel_spieler_id=ziel.id,
            effekte={
                "weisser_wolf_toetet": ziel.id,
                "todesursache": "werwolf",
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Gewinnt als letzter Ueberlebender oder letzter Werwolf.
        """
        if len(kontext.lebende_spieler) == 1 and spieler.id in kontext.lebende_spieler:
            return Team.SOLO
        return None
