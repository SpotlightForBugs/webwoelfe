"""
Drachenbändiger - Der Drachenbeschützer.

Der Drachenbändiger hat einen Drachen, der jeden
tötet, der den Bändiger angreift. Funktioniert nur einmal.
"""

from typing import Optional, TYPE_CHECKING
from ..base import (
    RollenModell,
    AppearanceFeature,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Drachenbaendiger(Role):
    """
    Drachenbändiger - Passive Verteidigungsrolle.

    Fähigkeiten:
    - Hat einen schützenden Drachen
    - Wer den Drachenbändiger angreift, stirbt selbst
    - Funktioniert nur einmal!

    Besonderheiten:
    - Passiver Schutz, keine aktive Aktion nötig
    - Schützt nicht vor Hinrichtung
    - Der Drache "stirbt" nach einmaliger Nutzung

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=53,
            name="Drachenbändiger",
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der Drachenbändiger. Dein Drache beschützt dich - "
                "wer dich angreift, wird von deinem Drachen getötet! "
                "Funktioniert nur einmal."
            ),
            icon="fa-solid fa-dragon",
            farbe="#7c3aed",
            prioritaet=93,
            erzaehler_nacht=(
                "Der Drachenbändiger schläft friedlich, " "bewacht von seinem Drachen."
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            distribution=DistributionConfig(
                min_players=10,
                count_func=lambda n: 1,
                priority=35,
            ),
            # Visual Styling
            avatar_gradient_from="#7c3aed",
            avatar_gradient_to="#5b21b6",
            avatar_border_color="#8b5cf6",
            badge_emoji="fa-solid fa-dragon",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Drachenbändiger does not act on first night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Drachenbändiger is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Drachenbändiger's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Drachenbändiger - Passive Rolle",
            instructions="Dein Drache beschützt dich. Wer dich angreift, wird verbrannt (einmalig).",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_angegriffen(
        self, spieler: "Spieler", angreifer_id: int, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn der Drachenbändiger angegriffen wird,
        tötet der Drache den Angreifer und schützt den Bändiger.
        Funktioniert nur einmal!
        """
        # Prüfen ob Drache schon benutzt wurde
        if getattr(spieler, "drache_benutzt", False):
            # Drache ist schon tot, kein Schutz mehr
            return None

        # Drache wird benutzt - Attribut setzen
        spieler.drache_benutzt = True

        return AktionsErgebnis(
            erfolg=True,
            nachricht="Der Drache des Drachenbändigers hat den Angreifer getötet!",
            effekte={
                "drache_toetet": angreifer_id,
                "angriff_abgewehrt": True,
                "drache_benutzt": True,
                "kill_message": f"Der Drache von {spieler.name} hat seinen Angreifer verbrannt!",
            },
            log_sichtbar_fuer="alle",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Drachenbaendiger."""
        appearance_features = [
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
            modell_id="drachenbaendiger",
            anzeige_name="Drachenbaendiger",
            beschreibung="Drachenbaendiger appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
