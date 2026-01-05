"""
Teenager-Werwolf - Der rebellische Wolf.

Der Teenager-Werwolf ist ein normaler Werwolf, der sich
einmal pro Spiel weigern kann, beim Angriff mitzumachen.
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
class TeenagerWerwolf(Role):
    """
    Der Teenager-Werwolf

    Fähigkeiten:
    - Jagt mit den Woelfen
    - Kann einmal pro Spiel den Angriff verweigern

    Gewinnbedingung: Werwoelfe gewinnen.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des Teenager-Werwolfs."""
        return [
            StateField(
                "hat_verweigert", StateType.BOOL, False, "Hat bereits verweigert"
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=24,
            name="Teenager-Werwolf",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Teenager-Werwolf. Du jagst mit den Wölfen, "
                "aber einmal pro Spiel kannst du dich weigern, beim Angriff "
                "mitzumachen."
            ),
            icon="fa-solid fa-user-ninja",
            farbe="#b91c1c",
            prioritaet=50,
            erzaehler_nacht=(
                "Der Teenager-Werwolf erwacht mit den anderen. "
                "Er überlegt, ob er heute rebellieren soll."
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            # Visual Styling
            avatar_gradient_from="#b91c1c",
            avatar_gradient_to="#991b1b",
            avatar_border_color="#ef4444",
            badge_emoji="🧢",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Teenager-Werwolf acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Teenager-Werwolf acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Teenager-Werwolf's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Teenager-Werwolf - Mit Wölfen jagen",
            instructions="Wähle das Opfer oder verweigere einmal rebellisch den Angriff.",
            buttons=[
                UIButton(
                    label="Angreifen",
                    action_type="toeten",
                    icon="fa-solid fa-paw",
                    css_class="btn-danger",
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
        Teenager-Werwolf nimmt am Werwolf-Angriff teil oder verweigert.

        Die Verweigerung ist eine passive Faehigkeit - er waehlt einfach
        kein Opfer, aber die anderen Woelfe sehen das nicht.
        """
        # Pruefe ob schon verweigert wurde
        hat_verweigert = self.get_state(spieler, "hat_verweigert")

        if ziel is None:
            # Teenager verweigert den Angriff
            if hat_verweigert:
                return AktionsErgebnis(
                    erfolg=True,
                    nachricht="Du hast deine Verweigerung bereits genutzt.",
                    effekte={},
                    log_sichtbar_fuer=f"spieler_{spieler.id}",
                )

            # Verweigerung speichern
            self.set_state(spieler, "hat_verweigert", True)

            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du verweigerst diese Nacht den Angriff - rebellisch!",
                effekte={
                    "teenager_verweigert": True,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        # Normaler Werwolf-Angriff
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Die Woelfe haben {ziel.name} als Opfer gewaehlt.",
            ziel_spieler_id=ziel.id,
            effekte={
                "werwolf_opfer": ziel.id,
            },
            log_sichtbar_fuer="werwolf",
        )
