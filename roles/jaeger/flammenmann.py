"""
Flammenmann - Der Brandstifter.

Einmal pro Spiel kann der Flammenmann am Tag
sein Haus anzünden - die Nachbarn sterben.
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
class Flammenmann(Role):
    """
    Flammenmann - Einmal-Tag-Fähigkeit.

    Fähigkeiten:
    - Einmal pro Spiel am Tag aktivierbar
    - Zündet sein Haus an
    - Nachbarn links und rechts sterben mit

    Besonderheiten:
    - Stirbt selbst NICHT!
    - Mächtige aber riskante Fähigkeit
    - Einmalig

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=152,
            name="Flammenmann",
            team=Team.DORF,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der Flammenmann. Einmal pro Spiel kannst du "
                "während des Tages ein Haus anzünden - alle Spieler "
                "darin (Links und Rechts neben dir) sterben!"
            ),
            icon="fa-solid fa-fire",
            farbe="#ea580c",
            prioritaet=94,
            erzaehler_nacht=(
                "Der Flammenmann träumt von lodernden Flammen. "
                "Er kann nur am Tag aktiv werden."
            ),
            erweiterung=Erweiterung.COMMUNITY,
            distribution=DistributionConfig(
                min_players=12,
                count_func=lambda n: 1,
                priority=20,
            ),
            # Visual Styling
            avatar_gradient_from="#ea580c",
            avatar_gradient_to="#c2410c",
            avatar_border_color="#f97316",
            badge_emoji="🔥",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    def is_active_on_first_night(self) -> bool:
        """Flammenmann does not act at night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Flammenmann does not act at night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Flammenmann's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Flammenmann - Tagaktion",
            instructions="Du kannst einmal am Tag dein Haus anzünden und deine Nachbarn töten.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def ist_einmal_faehigkeit(self) -> bool:
        """Flammenmann kann nur einmal zünden."""
        return True

    def ist_tag_aktiv(self, spieler: "Spieler", kontext: SpielKontext) -> bool:
        """
        Nur aktiv wenn noch nicht gezündet.
        """
        return not getattr(spieler, "flammenmann_gezuendet", False)

    def anzuenden(self, spieler: "Spieler", kontext: SpielKontext) -> AktionsErgebnis:
        """
        Zündet das Haus an - Nachbarn sterben.

        Die Nachbarn werden über die Sitzreihenfolge ermittelt.
        """
        if getattr(spieler, "flammenmann_gezuendet", False):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast dein Feuer bereits benutzt!",
            )

        spieler.flammenmann_gezuendet = True

        # Nachbarn ermitteln (links und rechts in Sitzreihenfolge)
        # Das muss von game_logic über kontext.sitzreihenfolge gemacht werden
        nachbarn_ids = []

        if hasattr(kontext, "sitzreihenfolge") and kontext.sitzreihenfolge:
            sitz = kontext.sitzreihenfolge
            try:
                idx = sitz.index(spieler.id)
                # Links
                links_idx = (idx - 1) % len(sitz)
                # Rechts
                rechts_idx = (idx + 1) % len(sitz)

                # Nur lebende Nachbarn
                links_id = sitz[links_idx]
                rechts_id = sitz[rechts_idx]

                if links_id not in kontext.tote_spieler:
                    nachbarn_ids.append(links_id)
                if rechts_id not in kontext.tote_spieler and rechts_id != links_id:
                    nachbarn_ids.append(rechts_id)
            except (ValueError, IndexError):
                pass

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"FEUER! Die Flammen verschlingen {len(nachbarn_ids)} Nachbarn!",
            effekte={
                "flammen_toeten": nachbarn_ids,
                "flammenmann_gezuendet": True,
                "todesursache": "verbrennung",
            },
            log_sichtbar_fuer="alle",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Flammenmann."""
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
            modell_id="flammenmann",
            anzeige_name="Flammenmann",
            beschreibung="Flammenmann appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
