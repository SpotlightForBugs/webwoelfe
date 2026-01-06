"""
Lupin - Der Werwolf mit wechselnder Identitaet.

Lupin verwandelt sich nur bei Vollmond. In geraden Runden
erscheint er der Seherin als Mensch, in ungeraden als Wolf.
"""

from typing import Optional, TYPE_CHECKING
from ..base import RollenModell, AppearanceFeature, Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, SichtTyp, Erweiterung, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Lupin(Role):
    """
    Lupin - Werwolf mit wechselnder Identitaet.

    Faehigkeiten:
    - Jagt mit den Woelfen
    - In geraden Runden erscheint er der Seherin als Mensch
    - In ungeraden Runden erscheint er als Werwolf

    Gewinnbedingung: Werwoelfe gewinnen.
    """

    # Speichert die aktuelle Runde fuer die Sichtbarkeit
    _aktuelle_runde: int = 1

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=26,
            name="Lupin",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist Lupin. Du verwandelst dich nur bei Vollmond - "
                "in geraden Runden bist du ein harmloser Mensch (erscheinst "
                "so fuer die Seherin), in ungeraden ein Wolf!"
            ),
            icon="fa-solid fa-moon",
            farbe="#ca8a04",
            prioritaet=50,
            erzaehler_nacht=(
                "Lupin ist in geraden Runden Mensch, in ungeraden Wolf. "
                "Die Seherin sieht entsprechend die aktuelle Form."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#ca8a04",
            avatar_gradient_to="#a16207",
            avatar_border_color="#eab308",
            badge_emoji="🌕",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE  # Jagt mit dem Rudel

    @property
    def sichtbar_als(self) -> SichtTyp:
        """
        Lupin erscheint in geraden Runden als Mensch, in ungeraden als Wolf.
        """
        # Wir brauchen Zugriff auf die aktuelle Runde
        # Da wir hier keinen Kontext haben, müssen wir das anders lösen
        # oder eine Standard-Rückgabe machen und die Logik in game_logic verschieben
        # Für jetzt: Standard Werwolf, die Logik muss in game_logic.py implementiert werden
        return SichtTyp.WERWOLF

    def get_sichtbare_rolle_fuer(self, seher: "Role", kontext: SpielKontext) -> str:
        """
        Spezielle Logik für Seherin:
        Gerade Runde = Mensch
        Ungerade Runde = Werwolf
        """
        if kontext.runde % 2 == 0:
            return "Dorfbewohner"
        return "Werwolf"

    def is_active_on_first_night(self) -> bool:
        """Lupin acts with the pack."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Lupin acts with the pack."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Lupin's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Lupin - Passive Rolle",
            instructions="Du jagst mit den Wölfen. Deine Aura wechselt jede Nacht.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Lupin."""
        appearance_features = [
            AppearanceFeature(
                feature_type="wolf_ear_left",
                geometry="cone",
                position={"x": -0.18, "y": 2.25, "z": -0.05},
                scale={"x": 0.12, "y": 0.2, "z": 0.1},
                rotation={"x": 0, "y": 0, "z": -15},
                color_source="role",
                description="Left wolf ear",
            ),
            AppearanceFeature(
                feature_type="wolf_ear_right",
                geometry="cone",
                position={"x": 0.18, "y": 2.25, "z": -0.05},
                scale={"x": 0.12, "y": 0.2, "z": 0.1},
                rotation={"x": 0, "y": 0, "z": 15},
                color_source="role",
                description="Right wolf ear",
            ),
            AppearanceFeature(
                feature_type="accessory",
                geometry="box",
                position={"x": 0.25, "y": 1.0, "z": 0.15},
                scale={"x": 0.1, "y": 0.15, "z": 0.08},
                color_source="role",
                description="Role-specific accessory",
            )
        ]
        
        return RollenModell(
            modell_id="lupin",
            anzeige_name="Lupin",
            beschreibung="Lupin appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="bad",
        )
