"""
Werwolfseherin - Werwolf mit Seher-Kräften.

Die Werwolfseherin jagt mit den Wölfen und kann
jede Nacht die Rolle eines Spielers sehen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Werwolfseherin(Role):
    """
    Werwolfseherin - Werwolf mit Seher-Fähigkeit.

    Fähigkeiten:
    - Jagt mit den Wölfen
    - Kann jede Nacht (nach dem Werwolf-Angriff) eine Rolle sehen

    Besonderheiten:
    - Sieht die tatsächliche Rolle
    - Aktiviert nach den Werwölfen (höhere Priorität)
    - Kann helfen, gefährliche Rollen zu identifizieren

    Gewinnbedingung: Werwölfe gewinnen.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=27,
            name="Werwolfseherin",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist die Werwolfseherin. Du bist ein Werwolf mit "
                "Seher-Kräften! Jede Nacht erfährst du die Rolle eines "
                "Spielers (nach dem Werwolf-Angriff)."
            ),
            icon="fa-solid fa-eye",
            farbe="#b91c1c",
            prioritaet=65,  # Nach Werwölfen
            erzaehler_nacht=(
                "Die Werwolfseherin erwacht nach den Werwölfen und "
                "erfährt die Rolle eines Spielers."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#b91c1c",
            avatar_gradient_to="#7f1d1d",
            avatar_border_color="#a78bfa",
            badge_emoji="👁️",
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import AktionsTyp

        return AktionsTyp.SEHEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"

    def is_active_on_first_night(self) -> bool:
        """Werwolfseherin acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Werwolfseherin acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Werwolfseherin's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Werwolfseherin - Rolle sehen",
            instructions="Wähle einen Spieler, um seine Rolle zu erfahren.",
            buttons=[
                UIButton(
                    label="Rolle sehen",
                    action_type="sehen",
                    icon="fa-solid fa-eye",
                    css_class="btn-info",
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
        Werwolfseherin sieht die Rolle eines Spielers.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du verzichtest auf deine Sehergabe diese Nacht.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst nur lebende Spieler betrachten.",
            )

        # Rolle des Ziels abrufen
        ziel_rolle = kontext.spieler_rollen.get(ziel.id, "Unbekannt")

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Deine dunkle Gabe zeigt: {ziel.name} ist {ziel_rolle}!",
            ziel_spieler_id=ziel.id,
            effekte={
                "rolle_gesehen": ziel_rolle,
                "seherin_ziel": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
