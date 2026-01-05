"""
Zombie - Die Untoten.

Zombies infizieren jede Nacht einen Spieler.
Stirbt ein Infizierter, wird er zum Zombie.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Zombie(Role):
    """
    Zombie - Eigenständiges Team.

    Fähigkeiten:
    - Infiziert jede Nacht einen Spieler
    - Infizierte sterben normal, werden aber zum Zombie
    - Zombies kennen sich untereinander

    Besonderheiten:
    - Eigenes Team
    - Infektion ist geheim
    - Tote Infizierte werden sofort Zombies

    Gewinnbedingung: Zombie-Mehrheit unter Lebenden.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=84,
            name="Zombie",
            team=Team.ZOMBIE,
            kategorie=Kategorie.BOESE,
            beschreibung=(
                "Du bist ein Zombie! Jede Nacht infizierst du einen Spieler. "
                "Stirbt ein Infizierter, wird er zum Zombie. "
                "Ihr gewinnt bei Zombie-Mehrheit!"
            ),
            icon="fa-solid fa-biohazard",
            farbe="#4ade80",
            prioritaet=54,
            erzaehler_nacht=("Die Zombies erwachen und infizieren einen Spieler."),
            erzaehler_tag=None,
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.INFIZIEREN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.DORF  # Erscheinen normal

    def is_active_on_first_night(self) -> bool:
        """Zombie acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Zombie acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Zombie's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Zombie - Infizieren",
            instructions="Wähle einen Spieler, um ihn zu infizieren.",
            buttons=[
                UIButton(
                    label="Infizieren",
                    action_type="infizieren",
                    icon="fa-solid fa-biohazard",
                    css_class="btn-success",
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
        Zombie infiziert einen Spieler.
        """
        infizierte: List[int] = getattr(spieler, "zombie_infiziert", [])

        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"Du schleichst durch die Nacht. {len(infizierte)} infiziert.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Dieses Ziel ist bereits tot.",
            )

        # Prüfen ob schon infiziert oder Zombie
        ziel_team = kontext.spieler_teams.get(ziel.id, Team.DORF)
        if ziel_team == Team.ZOMBIE:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Dieses Opfer ist bereits ein Zombie!",
            )

        if ziel.id in infizierte:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Dieses Opfer ist bereits infiziert!",
            )

        infizierte.append(ziel.id)
        spieler.zombie_infiziert = infizierte

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du kratzt {ziel.name}... das Virus verbreitet sich. "
            f"Stirbt er, wird er zu einem von uns!",
            ziel_spieler_id=ziel.id,
            effekte={
                "zombie_infiziert": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_spieler_stirbt(
        self, spieler: "Spieler", gestorbener_id: int, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn ein Infizierter stirbt, wird er zum Zombie.
        """
        infizierte: List[int] = getattr(spieler, "zombie_infiziert", [])

        if gestorbener_id not in infizierte:
            return None

        return AktionsErgebnis(
            erfolg=True,
            nachricht="Ein Infizierter ist gestorben - er erhebt sich als ZOMBIE!",
            effekte={
                "zombie_verwandlung": gestorbener_id,
                "team_wechsel": Team.ZOMBIE.value,
                "untot": True,
            },
            log_sichtbar_fuer="alle",
        )

    def pruefe_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob Zombies in der Mehrheit sind.
        """
        lebende = [
            sid
            for sid in kontext.spieler_rollen.keys()
            if sid not in kontext.tote_spieler
        ]

        zombies = [
            sid for sid in lebende if kontext.spieler_teams.get(sid) == Team.ZOMBIE
        ]

        nicht_zombies = [sid for sid in lebende if sid not in zombies]

        if len(zombies) > len(nicht_zombies):
            return AktionsErgebnis(
                erfolg=True,
                nachricht="APOKALYPSE! Die Zombies haben übernommen!",
                effekte={
                    "spiel_ende": True,
                    "gewinner": "zombies",
                },
                log_sichtbar_fuer="alle",
            )

        return None
