"""
Chemielaborant - Explosion bei Tod.

Wenn der Chemielaborant stirbt, explodieren seine
Chemikalien und töten die Nachbarn.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    RollenModell,
    AppearanceFeature,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Chemielaborant(Role):
    """
    Chemielaborant - Passiver Todeseffekt.

    Fähigkeiten:
    - Passive Rolle (keine aktive Fähigkeit)
    - Bei Tod: Nachbarn sterben mit

    Besonderheiten:
    - Kann nicht verhindert werden
    - Ausnahme: Nachbar ist bei der Hure
    - Strategisch wichtige Position

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=75,
            name="Chemielaborant",
            team=Team.DORF,
            kategorie=Kategorie.SPEZIAL,
            beschreibung=(
                "Du bist der Chemielaborant. Wenn du stirbst, sterben "
                "deine beiden nächsten lebenden Nachbarn mit dir! Das kann "
                "nicht verhindert werden (Ausnahme: Nachbar ist bei der Hure)."
            ),
            icon="fa-solid fa-flask",
            farbe="#10b981",
            prioritaet=97,
            erzaehler_nacht=(
                "Der Chemielaborant experimentiert selbst im Schlaf. "
                "Ein gefährlicher Nachbar..."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#10b981",
            avatar_gradient_to="#047857",
            avatar_border_color="#34d399",
            badge_emoji="🧪",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Chemielaborant is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Chemielaborant is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Chemielaborant's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Chemielaborant - Passive Rolle",
            instructions="Bei Tod explodieren deine Chemikalien und töten Nachbarn.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_eigener_tod(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Bei Tod explodieren die Chemikalien und töten Nachbarn.
        """
        nachbarn_ids: List[int] = []

        # Nachbarn ermitteln (links und rechts in Sitzreihenfolge)
        if hasattr(kontext, "sitzreihenfolge") and kontext.sitzreihenfolge:
            sitz = kontext.sitzreihenfolge
            try:
                idx = sitz.index(spieler.id)

                # Nächsten lebenden Nachbarn links finden
                for i in range(1, len(sitz)):
                    links_idx = (idx - i) % len(sitz)
                    links_id = sitz[links_idx]
                    if links_id not in kontext.tote_spieler:
                        nachbarn_ids.append(links_id)
                        break

                # Nächsten lebenden Nachbarn rechts finden
                for i in range(1, len(sitz)):
                    rechts_idx = (idx + i) % len(sitz)
                    rechts_id = sitz[rechts_idx]
                    if (
                        rechts_id not in kontext.tote_spieler
                        and rechts_id not in nachbarn_ids
                    ):
                        nachbarn_ids.append(rechts_id)
                        break
            except (ValueError, IndexError):
                pass

        if not nachbarn_ids:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Die Chemikalien explodieren, aber niemand ist in der Nähe!",
                effekte={},
                log_sichtbar_fuer="alle",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"KABOOM! Die Explosion tötet {len(nachbarn_ids)} Nachbarn!",
            effekte={
                "explosion_toetet": nachbarn_ids,
                "todesursache": "explosion",
                "unverhinderbar": True,
            },
            log_sichtbar_fuer="alle",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Chemielaborant."""
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
            modell_id="chemielaborant",
            anzeige_name="Chemielaborant",
            beschreibung="Chemielaborant appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
