"""
Kleines Mädchen - Kann nachts blinzeln um Werwölfe zu sehen, riskiert aber entdeckt zu werden
"""

from typing import Optional, List, TYPE_CHECKING
import random
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext, RollenModell
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class KleinesMaedchen(Role):
    """
    Kleines Mädchen

    Kann während der Werwolf-Phase blinzeln, um zu sehen, wer die Werwölfe sind.
    Wird es dabei erwischt, wird es sofort von den Werwölfen getötet.
    Das Risiko erwischt zu werden ist zufällig (ca. 30%).
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=95,
            name="Kleines Mädchen",
            team=Team.DORF,
            kategorie=Kategorie.SONSTIGE,
            beschreibung="Du bist das Kleine Mädchen. Du darfst nachts blinzeln um die Werwölfe zu beobachten! Aber Vorsicht: Wirst du erwischt, stirbst du sofort!",
            icon="fa-solid fa-child-dress",
            farbe="#fbbf24",
            prioritaet=50,
            erzaehler_nacht="Das Kleine Mädchen darf während der Werwolf-Phase blinzeln - auf eigene Gefahr!",
            erzaehler_tag=None,
            hinweis_config=None,
            erweiterung=Erweiterung.BASISSPIEL,

            # Visual Styling
            avatar_gradient_from="#fbbf24",
            avatar_gradient_to="#f59e0b",
            avatar_border_color="#fcd34d",
            badge_emoji="👧",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN

    @property
    def erlaubte_ziele(self) -> str:
        """Das Kleine Mädchen kann sich selbst wählen (blinzeln) oder nicht."""
        return "andere"

    def is_active_on_first_night(self) -> bool:
        """Kleines Mädchen acts every night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Kleines Mädchen acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for actions."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Kleines Mädchen - Blinzeln",
            instructions="Du kannst blinzeln um Werwölfe zu sehen (30% Risiko entdeckt zu werden).",
            buttons=[
                UIButton(
                    label="Blinzeln",
                    action_type="sehen",
                    icon="fa-solid fa-eye",
                    css_class="btn-warning",
                    requires_confirmation=True,
                )
            ],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_nacht_aktion(
        self,
        spieler: "Spieler",
        ziel: Optional["Spieler"],
        kontext: SpielKontext,
        zusatz_info: Optional[str] = None,
    ) -> AktionsErgebnis:
        """Das Kleine Mädchen blinzelt und sieht die Werwölfe - oder wird erwischt."""

        # NOTE: With new UI, calling this method implies "Blinzeln" was clicked.
        # Unless explicitly skipped which game logic shouldn't call this for?
        # We assume if called, it's an action.

        # Finde alle lebenden Werwölfe
        werwoelfe = []
        spieler_rollen = getattr(kontext, "spieler_rollen", {})

        for spieler_id, rolle in spieler_rollen.items():
            if spieler_id in kontext.tote_spieler:
                continue
            team = getattr(rolle, "info", None)
            if team and hasattr(team, "team") and team.team == Team.WERWOLF:
                werwoelfe.append(spieler_id)

        # Risikoberechnung: ca. 30% Chance erwischt zu werden
        erwischt = random.random() < 0.30

        if erwischt:
            # Das Kleine Mädchen wird erwischt und stirbt
            return AktionsErgebnis(
                erfolg=True,
                nachricht="😱 Du hast geblinzelt und wurdest ERWISCHT! Die Werwölfe haben dich bemerkt!",
                effekte={
                    "tod": True,
                    "todesursache": "Von Werwölfen erwischt beim Blinzeln",
                    "erwischt": True,
                },
            )
        else:
            # Erfolgreich geblinzelt
            if werwoelfe:
                werwolf_namen = [str(wid) for wid in werwoelfe]
                return AktionsErgebnis(
                    erfolg=True,
                    nachricht=f"🔍 Du hast vorsichtig geblinzelt und {len(werwoelfe)} Werwolf/Werwölfe gesehen!",
                    effekte={"gesehene_werwoelfe": werwoelfe, "erwischt": False},
                )
            else:
                return AktionsErgebnis(
                    erfolg=True,
                    nachricht="Du hast geblinzelt, aber keine Werwölfe gesehen...",
                    effekte={"erwischt": False},
                )

    def on_abstimmung(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird bei der Tagesabstimmung aufgerufen.
        Das Kleine Mädchen hat keine besonderen Fähigkeiten während der Abstimmung.
        """
        return None  # Keine besonderen Effekte

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird bei einer Hinrichtung aufgerufen.
        Das Kleine Mädchen hat keine besonderen Fähigkeiten bei Hinrichtungen.
        """
        return None  # Keine besonderen Effekte

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Kleines Mädchen."""
        return RollenModell(
            modell_id="kleines_maedchen",
            anzeige_name="Kleines Mädchen",
            beschreibung="Ein neugieriges kleines Mädchen",
        )
