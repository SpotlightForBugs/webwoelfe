"""
Tonks - Die Metamorphmagin.

Tonks kann einmal pro Spiel ihre Rolle mit einem
zufälligen toten Spieler tauschen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import RollenModell, AppearanceFeature, Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry
import random

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Tonks(Role):
    """
    Tonks - Rollentausch-Rolle.

    Fähigkeiten:
    - Kann einmal pro Spiel Rolle mit totem Spieler tauschen
    - Übernimmt alle Fähigkeiten der neuen Rolle
    - Tausch ist zufällig (kann nicht wählen welchen Toten)

    Besonderheiten:
    - Nur EINMAL pro Spiel nutzbar
    - Muss mindestens einen toten Spieler geben
    - Kann auch gefährliche Rollen bekommen (z.B. Werwolf!)

    Gewinnbedingung: Abhängig von der neuen Rolle.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=18,
            name="Tonks",
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist Tonks, ein Metamorphmagus! Einmal pro Spiel kannst "
                "du deine Rolle mit einem zufälligen toten Spieler tauschen "
                "und seine Fähigkeiten übernehmen. Vorsicht: Du könntest auch "
                "zum Werwolf werden!"
            ),
            icon="fa-solid fa-masks-theater",
            farbe="#a855f7",
            prioritaet=75,
            erzaehler_nacht=(
                "Tonks erwacht. Möchte sie ihre Gestalt wandeln und "
                "die Rolle eines Toten annehmen?"
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#a855f7",
            avatar_gradient_to="#7e22ce",
            avatar_border_color="#c084fc",
            badge_emoji="🎭",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.VERWANDELN

    def is_active_on_first_night(self) -> bool:
        """Tonks can act on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Tonks can act every night until ability is used."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Tonks' action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Tonks - Rollentausch",
            instructions="Du kannst einmalig deine Rolle mit einem Toten tauschen.",
            buttons=[
                UIButton(
                    label="Tauschen (Zufällig)",
                    action_type="verwandeln",
                    icon="fa-solid fa-shuffle",
                    css_class="btn-warning",
                    requires_confirmation=True,
                )
            ],
            requires_target=False,  # Random target logic handled inside action
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Tonks entscheidet ob sie ihre Fähigkeit einsetzen möchte.

        Wenn sie JA wählt, wird ein zufälliger toter Spieler ausgewählt
        und Tonks übernimmt dessen Rolle.
        """
        tausch_verwendet = getattr(spieler, "tonks_tausch_verwendet", False)

        if tausch_verwendet:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast deinen Rollentausch bereits verwendet.",
                effekte={"keine_aktion": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if len(kontext.tote_spieler) == 0:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Es gibt keine toten Spieler zum Tauschen.",
            )

        # Wenn kein explizites Ziel, warten auf Entscheidung
        # (ziel wird hier als "JA ich will tauschen" interpretiert)
        return AktionsErgebnis(
            erfolg=True,
            nachricht=(
                "Möchtest du deine Rolle mit einem zufälligen toten "
                "Spieler tauschen? Dies ist einmalig und unwiderruflich!"
            ),
            effekte={"warte_auf_tausch_entscheidung": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def rollentausch_durchfuehren(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Führt den zufälligen Rollentausch durch.

        Args:
            spieler: Tonks
            kontext: Spielkontext mit Liste der toten Spieler

        Returns:
            Ergebnis mit der neuen Rolle
        """
        tausch_verwendet = getattr(spieler, "tonks_tausch_verwendet", False)

        if tausch_verwendet:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast deinen Rollentausch bereits verwendet.",
            )

        if len(kontext.tote_spieler) == 0:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Es gibt keine toten Spieler zum Tauschen.",
            )

        # Wähle zufälligen toten Spieler
        toter_spieler_id = random.choice(kontext.tote_spieler)

        # Die tatsächliche Rolle wird über die Effekte gesetzt
        # und muss von der game_logic verarbeitet werden
        return AktionsErgebnis(
            erfolg=True,
            nachricht=(
                "Du verwandelst dich! Deine neue Rolle wird dir gleich " "offenbart..."
            ),
            ziel_spieler_id=toter_spieler_id,
            effekte={
                "rollentausch": True,
                "tonks_tausch_verwendet": True,
                "tausch_mit_spieler": toter_spieler_id,
                # Die neue Rolle wird von game_logic gesetzt
            },
            log_sichtbar_fuer="erzaehler",
        )

    def on_spiel_ende(
        self, spieler: "Spieler", gewinner_team: Team, kontext: SpielKontext
    ) -> bool:
        """
        Tonks gewinnt mit dem Team ihrer aktuellen Rolle.

        Nach einem Rollentausch gewinnt sie mit dem neuen Team.
        """
        # Wenn sie die Rolle getauscht hat, wird die Gewinnbedingung
        # von der neuen Rolle bestimmt (über spieler.rolle)
        tausch_verwendet = getattr(spieler, "tonks_tausch_verwendet", False)

        if tausch_verwendet:
            # Hole die neue Rolle und prüfe deren Gewinnbedingung
            from ..registry import RoleRegistry

            neue_rolle = RoleRegistry.get(spieler.rolle)
            if neue_rolle:
                return neue_rolle.on_spiel_ende(spieler, gewinner_team, kontext)

        # Ohne Tausch: Dorf gewinnt
        return gewinner_team == Team.DORF

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Tonks."""
        appearance_features = [
            AppearanceFeature(
                feature_type="mystical_aura",
                geometry="sphere",
                position={"x": 0, "y": 1.5, "z": 0},
                scale={"x": 0.6, "y": 0.8, "z": 0.5},
                color_source="role",
                description="Mystical aura effect",
            )
        ]
        
        return RollenModell(
            modell_id="tonks",
            anzeige_name="Tonks",
            beschreibung="Tonks appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
