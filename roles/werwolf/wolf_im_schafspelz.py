"""
Wolf im Schafspelz - Erscheint als Dorfbewohner.

Der Wolf im Schafspelz erscheint für die normale
Seherin als Dorfbewohner, nur die Aurenseherin erkennt ihn.
"""

from typing import Optional, TYPE_CHECKING
from roles.base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from roles.enums import Team, Kategorie, SichtTyp, Erweiterung
from roles.registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler
    from roles.enums import AktionsTyp
    from roles.base import RollenUI


@RoleRegistry.register
class WolfimSchafspelz(Role):
    """
    Wolf im Schafspelz - Getarnter Werwolf.

    Fähigkeiten:
    - Jagt mit den Wölfen
    - Erscheint der Seherin als Dorfbewohner
    - Nur die Aurenseherin erkennt seine böse Aura

    Besonderheiten:
    - Perfekte Tarnung gegen normale Seherin
    - Aurenseherin sieht Böse Aura
    - Gefährlich für das Dorf

    Gewinnbedingung: Werwölfe gewinnen.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=23,
            name="Wolf im Schafspelz",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Wolf im Schafspelz. Für die Seherin erscheinst "
                "du als harmloser Dorfbewohner! Nur die Aurenseherin erkennt "
                "dein böses Herz."
            ),
            icon="fa-brands fa-bluesky",
            farbe="#fef3c7",
            prioritaet=50,
            erzaehler_nacht=(
                "Der Wolf im Schafspelz jagt mit dem Rudel. "
                "Er erscheint der Seherin als Dorfbewohner."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#fef3c7",
            avatar_gradient_to="#d97706",
            avatar_border_color="#fcd34d",
            badge_emoji="🐑",
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from roles.enums import AktionsTyp

        return AktionsTyp.KEINE  # Jagt mit dem Rudel

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.DORF  # Das ist der Trick!

    def sichtbar_als_fuer(self, seher_rolle: str) -> SichtTyp:
        """
        Erscheint als Dorf für normale Seherin,
        aber als Werwolf für Aurenseherin.
        """
        if seher_rolle == "Aurenseherin":
            return SichtTyp.WERWOLF
        return SichtTyp.DORF

    def sichtbare_rolle_fuer(self, seher_rolle: str) -> str:
        """
        Erscheint als Dorfbewohner für normale Seherin.
        """
        if seher_rolle == "Seherin":
            return "Dorfbewohner"
        return self.info.name

    def is_active_on_first_night(self) -> bool:
        """Wolf im Schafspelz acts with the pack."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Wolf im Schafspelz acts with the pack."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Wolf im Schafspelz action panel."""
        from roles.base import RollenUI

        return RollenUI(
            title="Wolf im Schafspelz - Passive Rolle",
            instructions="Du jagst mit den Wölfen. Die Seherin sieht dich als Dorfbewohner.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for WolfimSchafspelz."""
        appearance_features = [
            AppearanceFeature(
                feature_type="sheep_wool",
                geometry="sphere",
                position={"x": 0, "y": 2.0, "z": 0},
                scale={"x": 0.35, "y": 0.3, "z": 0.3},
                color_source="custom",
                custom_color="#FFFACD",
                description="Fluffy sheep wool disguise",
            ),
            AppearanceFeature(
                feature_type="accessory",
                geometry="box",
                position={"x": 0.25, "y": 1.0, "z": 0.15},
                scale={"x": 0.1, "y": 0.15, "z": 0.08},
                color_source="role",
                description="Role-specific accessory",
            ),
        ]

        return RollenModell(
            modell_id="wolfimschafspelz",
            anzeige_name="WolfimSchafspelz",
            beschreibung="WolfimSchafspelz appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
