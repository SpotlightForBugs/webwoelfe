"""
Hexe - Maechtige Rolle mit zwei einmaligen Traenken.

Die Hexe kann einmal pro Spiel jemanden heilen
und einmal jemanden vergiften.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Hexe(Role):
    """
    Die Hexe - Dual-Action Rolle.

    Fähigkeiten:
    - Heiltrank: Rettet das Werwolf-Opfer (einmalig)
    - Gifttrank: Tötet einen beliebigen Spieler (einmalig)

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder der Hexe."""
        return [
            StateField("heiltrank", StateType.BOOL, True, "Hat noch Heiltrank"),
            StateField("gifttrank", StateType.BOOL, True, "Hat noch Gifttrank"),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=4,
            name="Hexe",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist die Hexe. Du hast einen Heiltrank (rettet das "
                "Werwolf-Opfer) und einen Gifttrank (tötet einen Spieler). "
                "Jeder Trank kann nur einmal verwendet werden!"
            ),
            icon="fa-solid fa-hat-wizard",
            farbe="#059669",
            prioritaet=60,
            erzaehler_nacht=(
                "Die Hexe erwacht. Zeige auf das Werwolf-Opfer. "
                "Frage: Heiltrank einsetzen? (Daumen hoch/runter) "
                "Gifttrank einsetzen? (Zeige auf Spieler oder schuettle Kopf)"
            ),
            erweiterung=Erweiterung.BASISSPIEL,
            distribution=DistributionConfig(
                min_players=6,
                # 1 Hexe ab 6 Spielern
                count_func=lambda n: max(1, n // 75),
                priority=60,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.HEILEN  # Primaere Aktion, Gift ist sekundaer

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Hexe acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Hexe acts every night (but only if she still has potions)."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Hexe's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Hexe - Tränke einsetzen",
            instructions="Du siehst das Werwolf-Opfer. Möchtest du Heiltrank oder Gifttrank einsetzen?",
            buttons=[
                UIButton(
                    label="Heiltrank",
                    action_type="heilen",
                    icon="fa-solid fa-flask",
                    css_class="btn-success",
                    requires_confirmation=True,
                ),
                UIButton(
                    label="Gifttrank",
                    action_type="vergiften",
                    icon="fa-solid fa-skull-crossbones",
                    css_class="btn-danger",
                    requires_confirmation=True,
                ),
            ],
            requires_target=False,  # Healing doesn't need target (uses werewolf victim)
            allow_multiple_targets=False,
            can_skip=True,  # Can choose not to use potions
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Hexe entscheidet über Heiltrank und Gifttrank.

        Die Aktion wird als Dictionary erwartet mit:
        - heilen: bool
        - vergiften: Optional[spieler_id]
        """
        effekte = {}

        # Prüfe Heiltrank
        hat_heiltrank = self.get_state(spieler, "heiltrank")

        if hat_heiltrank and kontext.werwolf_opfer_id:
            # Kann heilen - Entscheidung kommt über zusätzliche Daten
            effekte["kann_heilen"] = True
            effekte["werwolf_opfer"] = kontext.werwolf_opfer_id

        # Prüfe Gifttrank
        hat_gifttrank = self.get_state(spieler, "gifttrank")

        if hat_gifttrank:
            effekte["kann_vergiften"] = True

        return AktionsErgebnis(
            erfolg=True,
            nachricht="Die Hexe erwacht und sieht das Opfer der Werwoelfe.",
            effekte=effekte,
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_phase_start_info(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[dict]:
        """Zeigt der Hexe das Opfer an."""
        if kontext.werwolf_opfer_id:
            # Hole Opfer Namen
            opfer_name = kontext.spieler_namen.get(
                kontext.werwolf_opfer_id, "Unbekannt"
            )
            return {
                "opfer_name": opfer_name,
                "opfer_id": kontext.werwolf_opfer_id,
                "type": "werwolf_opfer",
            }
        return None

    def heilen(self, spieler: "Spieler", kontext: SpielKontext) -> AktionsErgebnis:
        """Setzt den Heiltrank ein."""
        if not self.get_state(spieler, "heiltrank"):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Der Heiltrank wurde bereits verwendet.",
            )

        if not kontext.werwolf_opfer_id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Es gibt kein Opfer zum Heilen.",
            )

        # Heiltrank verbrauchen
        self.set_state(spieler, "heiltrank", False)

        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du setzt den Heiltrank ein und rettest das Opfer!",
            ziel_spieler_id=kontext.werwolf_opfer_id,
            effekte={
                "geheilt": kontext.werwolf_opfer_id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def vergiften(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """Setzt den Gifttrank ein."""
        if not self.get_state(spieler, "gifttrank"):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Der Gifttrank wurde bereits verwendet.",
            )

        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel für Gift.",
            )

        # Gifttrank verbrauchen
        self.set_state(spieler, "gifttrank", False)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du vergiftest {ziel.name}!",
            ziel_spieler_id=ziel.id,
            effekte={
                "vergiftet": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
