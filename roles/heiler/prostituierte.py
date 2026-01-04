"""
Prostituierte - Schutz durch Gesellschaft.

Die Prostituierte schläft jede Nacht bei jemandem
und schützt beide, aber verrät ihre Identität.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Prostituierte(Role):
    """
    Prostituierte - Schutz-mit-Risiko-Rolle.

    Fähigkeiten:
    - Wählt jede Nacht einen Spieler
    - Beide sind in dieser Nacht geschützt
    - Der Partner erfährt ihre Rolle

    Besonderheiten:
    - Gefährlich wenn Partner Werwolf ist
    - Partner weiß, wer sie ist
    - Gegenseitiger Schutz

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=63,
            name="Prostituierte",
            team=Team.DORF,
            kategorie=Kategorie.HEILER,
            beschreibung=(
                "Du bist die Prostituierte. Jede Nacht kannst du bei einem "
                "Spieler schlafen - ihr beide seid diese Nacht geschützt, "
                "aber er sieht deine Rolle!"
            ),
            icon="fa-solid fa-bed",
            farbe="#f43f5e",
            prioritaet=46,  # Vor Werwölfen
            erzaehler_nacht=(
                "Die Prostituierte erwacht und wählt einen Spieler für "
                "die Nacht. Beide sind geschützt, aber der Partner "
                "erfährt wer sie ist."
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SCHUETZEN

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    def is_active_on_first_night(self) -> bool:
        """Prostituierte acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Prostituierte acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Prostituierte's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Prostituierte - Bei jemandem schlafen",
            instructions="Wähle einen Spieler, bei dem du diese Nacht schläfst. Ihr beide seid geschützt, aber er erfährt deine Rolle.",
            buttons=[
                UIButton(
                    label="Besuchen",
                    action_type="schuetzen",
                    icon="fa-solid fa-bed",
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
        Prostituierte wählt ihren Partner für die Nacht.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du bleibst diese Nacht alleine zuhause.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel.",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=(
                f"Du verbringst die Nacht bei {ziel.name}. "
                f"Ihr seid beide geschützt - aber er weiß nun wer du bist!"
            ),
            ziel_spieler_id=ziel.id,
            effekte={
                "prostituierte_bei": ziel.id,
                "beide_geschuetzt": [spieler.id, ziel.id],
                "identitaet_enthuellt": True,
                "partner_weiss_rolle": ziel.id,
            },
            log_sichtbar_fuer="erzaehler",
        )
