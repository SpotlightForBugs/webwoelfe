"""
Wolfsjunge - Wird zum Werwolf wenn Vorbild stirbt.

Der Wolfsjunge waehlt in der ersten Nacht ein Vorbild.
Stirbt dieses, verwandelt er sich in einen Werwolf.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
)
from ..enums import Team, Kategorie, SichtTyp, Erweiterung, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Wolfsjunge(Role):
    """
    Das Wolfsjunge (Wildes Kind) - Bedingte Verwandlung.

    Faehigkeiten:
    - Waehlt in der ersten Nacht ein Vorbild
    - Stirbt das Vorbild: Wird zum Werwolf
    - Solange Vorbild lebt: Teil des Dorfes

    Gewinnbedingung: Abhaengig von Verwandlung.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Wolfsjungen."""
        return [
            StateField("vorbild_id", StateType.PLAYER_ID, None, "ID des Vorbilds"),
            StateField("verwandelt", StateType.BOOL, False, "Zum Werwolf verwandelt"),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=124,
            name="Wolfsjunge",
            team=Team.DORF,  # Startet als Dorf
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist das Wolfsjunge. Du wählst in der ersten Nacht ein "
                "Vorbild. Solange dein Vorbild lebt, gehörst du zum Dorf. "
                "Stirbt dein Vorbild, wirst du zum Werwolf!"
            ),
            icon="fa-solid fa-paw",
            farbe="#b91c1c",
            prioritaet=6,
            erzaehler_nacht=(
                "Das Wolfsjunge erwacht und sucht sich ein Vorbild. "
                "Es wird ihm folgen... bis in den Tod."
            ),
            erweiterung=Erweiterung.NEUMOND,

            # Visual Styling
            avatar_gradient_from="#b91c1c",
            avatar_gradient_to="#7f1d1d",
            avatar_border_color="#ef4444",
            badge_emoji="🐾",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.WAEHLEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        # Sieht als Dorf aus, bis Verwandlung
        return SichtTyp.DORF

    def is_active_on_first_night(self) -> bool:
        """Wolfsjunge acts only on first night to choose role model."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Wolfsjunge does not act every night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Wolfsjunge's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Wolfsjunge - Vorbild wählen",
            instructions="Wähle dein Vorbild. Stirbt es, wirst du zum Werwolf.",
            buttons=[
                UIButton(
                    label="Vorbild wählen",
                    action_type="waehlen",
                    icon="fa-solid fa-child",
                    css_class="btn-primary",
                    requires_confirmation=True,
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
        Wolfsjunge wählt sein Vorbild in der ersten Nacht.
        """
        if kontext.runde != 1:
            return None

        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst ein Vorbild wählen!",
            )

        if ziel.id == spieler.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst dich nicht selbst als Vorbild wählen.",
            )

        # Vorbild speichern
        self.set_state(spieler, "vorbild_id", ziel.id)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} ist nun dein Vorbild. Stirbt es, wirst du zum Werwolf.",
            ziel_spieler_id=ziel.id,
            effekte={
                "vorbild": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        opfer: "Spieler",
        todesursache: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """
        Prueft ob das Vorbild stirbt und Verwandlung ausloest.
        """
        vorbild_id = self.get_state(spieler, "vorbild_id")

        if vorbild_id and opfer.id == vorbild_id:
            # Markiere als verwandelt
            self.set_state(spieler, "verwandelt", True)

            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Das Vorbild des Wolfsjungen ist gestorben! "
                    "Es verwandelt sich in einen Werwolf!"
                ),
                effekte={
                    "verwandlung": True,
                    "neues_team": "werwolf",
                    "neue_rolle": "Werwolf",
                },
                log_sichtbar_fuer="erzaehler",
            )

        return None
