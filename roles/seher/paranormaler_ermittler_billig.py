"""
Paranormaler Ermittler (billig) - Unzuverlässige Visionen.

Der Paranormale Ermittler kann sehen wie die Seherin,
aber 30% seiner Ergebnisse sind falsch!
"""

from typing import Optional, TYPE_CHECKING
import random
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class ParanormalerErmittlerbillig(Role):
    """
    Paranormaler Ermittler (billig) - Unzuverlässige Seherin.

    Fähigkeiten:
    - Kann jede Nacht einen Spieler sehen (wie Seherin)
    - 30% Chance auf falsches Ergebnis!

    Besonderheiten:
    - Weiß nicht ob das Ergebnis stimmt
    - Muss selbst abschätzen ob er vertraut

    Gewinnbedingung: Dorf gewinnt.
    """

    FEHLERRATE = 0.30  # 30% falsche Ergebnisse

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=36,
            name="Paranormaler Ermittler (billig)",
            team=Team.DORF,
            kategorie=Kategorie.SEHER,
            beschreibung=(
                "Du bist der Paranormale Ermittler mit billiger Kristallkugel. "
                "Du kannst sehen wie die Seherin, aber die Ergebnisse sind zu "
                "30% falsch! Vertraue deinen Visionen nicht blind."
            ),
            icon="fa-solid fa-eye-slash",
            farbe="#a3a3a3",
            prioritaet=25,
            erzaehler_nacht=(
                "Der Paranormale Ermittler erwacht. Zeige ihm ein Ergebnis. "
                "ACHTUNG: 30% Chance dass du lügen musst! (Würfle heimlich)"
            ),
            erweiterung=Erweiterung.SONDEREDITION,

            # Visual Styling
            avatar_gradient_from="#a3a3a3",
            avatar_gradient_to="#737373",
            avatar_border_color="#d4d4d4",
            badge_emoji="🔮",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN
    
    @property
    def erlaubte_ziele(self) -> str:
        return "andere"
    
    def is_active_on_first_night(self) -> bool:
        """Paranormaler Ermittler acts on first night."""
        return True
    
    def is_active_on_every_night(self) -> bool:
        """Paranormaler Ermittler acts every night."""
        return True
    
    def get_ui_definition(self) -> 'RollenUI':
        """Returns the UI definition for Paranormaler Ermittler's action panel."""
        from ..base import RollenUI, UIButton
        return RollenUI(
            title="Paranormaler Ermittler (billig) - Sehen",
            instructions="Wähle einen Spieler. Achtung: 30% der Ergebnisse sind falsch!",
            buttons=[
                UIButton(
                    label="Vision",
                    action_type="sehen",
                    icon="fa-solid fa-eye-slash",
                    css_class="btn-info"
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False
        )

    def get_phase_name(self) -> str:
        """Gibt den Namen der Nacht-Phase zurück."""
        return "paranormal_billig_phase"

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Paranormaler Ermittler sieht einen Spieler - aber vielleicht falsch!
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst einen Spieler wählen.",
            )

        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel.",
            )

        # Hole die echte Rolle
        ziel_rolle = RoleRegistry.get(ziel.rolle)

        if ziel_rolle:
            echte_sicht = ziel_rolle.sichtbar_als_fuer("Seherin")
            rollen_name = ziel_rolle.sichtbare_rolle_fuer("Seherin")
        else:
            echte_sicht = SichtTyp.DORF
            rollen_name = ziel.rolle or "Unbekannt"

        # 30% Chance auf falsches Ergebnis
        ist_falsch = random.random() < self.FEHLERRATE

        gezeigt_rolle = rollen_name
        gezeigt_sicht = echte_sicht

        if ist_falsch:
            # Sammle alle aktiven Rollen im Spiel (außer der eigenen und der Ziel-Rolle)
            spieler_rollen = getattr(kontext, "spieler_rollen", {})
            lebende = kontext.lebende_spieler

            # Sammle die Rollen-Objekte der lebenden Spieler
            aktive_rollen = []
            for spieler_id in lebende:
                rolle_obj = spieler_rollen.get(spieler_id)
                if rolle_obj is None:
                    continue
                rolle_name = rolle_obj.info.name
                # Nicht die eigene Rolle und nicht die Rolle des Ziels
                if rolle_name != self.info.name and rolle_name != rollen_name:
                    aktive_rollen.append(rolle_obj)

            if aktive_rollen:
                # Wähle eine zufällige aktive Rolle aus dem Spiel
                zufalls_rolle_obj = random.choice(aktive_rollen)
                gezeigt_sicht = zufalls_rolle_obj.sichtbar_als_fuer("Seherin")
                gezeigt_rolle = zufalls_rolle_obj.sichtbare_rolle_fuer("Seherin")
            else:
                # Fallback: Zeige gegenteilige Sicht
                if echte_sicht == SichtTyp.WERWOLF:
                    gezeigt_sicht = SichtTyp.DORF
                    gezeigt_rolle = "Dorfbewohner"
                else:
                    gezeigt_sicht = SichtTyp.WERWOLF
                    gezeigt_rolle = "Werwolf"

        gezeigt_werwolf = gezeigt_sicht == SichtTyp.WERWOLF
        gezeigt_nachricht = (
            f"Deine Kristallkugel zeigt: {ziel.name} ist ein {gezeigt_rolle}! "
            f"({'Werwolf-Team' if gezeigt_werwolf else 'Dorf-Team'})"
        )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=gezeigt_nachricht,
            ziel_spieler_id=ziel.id,
            effekte={
                "gesehen": ziel.id,
                "gezeigte_rolle": gezeigt_rolle,
                "gezeigt_werwolf": gezeigt_werwolf,  # Was dem Spieler gezeigt wurde
                "echt_werwolf": echte_sicht
                == SichtTyp.WERWOLF,  # Die Wahrheit (für Erzähler)
                "war_falsch": ist_falsch,  # Ob es gelogen war (für Erzähler)
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
