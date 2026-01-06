"""
Putzfrau - Erfährt die Rolle jedes Verstorbenen und teilt es dem Dorf mit
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext, RollenModell
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Putzfrau(Role):
    """
    Putzfrau

    Wenn jemand stirbt, erfährt die Putzfrau automatisch dessen wahre Rolle.
    Diese Information wird dem Dorf öffentlich mitgeteilt.
    Eine passive Rolle ohne Nachtaktion.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=91,
            name="Putzfrau",
            team=Team.DORF,
            kategorie=Kategorie.SONSTIGE,
            beschreibung="Du bist die Putzfrau. Wenn jemand stirbt, räumst du auf und erfährst dabei seine wahre Rolle. Du teilst dein Wissen mit dem Dorf.",
            icon="fa-solid fa-spray-can-sparkles",
            farbe="#06b6d4",
            prioritaet=88,
            erzaehler_nacht="Die Putzfrau wischt durch die leeren Häuser und sammelt wertvolle Informationen.",
            erzaehler_tag="Die Putzfrau hat beim Aufräumen etwas gefunden! Sie enthüllt die wahre Rolle des Toten: {rolle}!",
            hinweis_config=None,
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#06b6d4",
            avatar_gradient_to="#0891b2",
            avatar_border_color="#22d3ee",
            badge_emoji="🧹",
        )

    @property
    def aktions_typ(self) -> Optional[AktionsTyp]:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Putzfrau is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Putzfrau is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Putzfrau's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Putzfrau - Passive Rolle",
            instructions="Du erfährst die Rolle von Toten, wenn du aufräumst.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_spieler_stirbt(
        self, spieler: "Spieler", gestorbener: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn jemand stirbt, erfährt die Putzfrau dessen Rolle.
        Diese Information wird öffentlich dem Dorf mitgeteilt.
        """
        # Wenn die Putzfrau selbst stirbt, kann sie nicht mehr aufräumen
        if gestorbener.id == spieler.id:
            return None

        # Finde die Rolle des Verstorbenen
        spieler_rollen = getattr(kontext, "spieler_rollen", {})
        rolle_obj = spieler_rollen.get(gestorbener.id)

        if rolle_obj:
            rollen_name = rolle_obj.info.name
        else:
            rollen_name = "Unbekannt"

        # Bestimme Team-Information
        if rolle_obj:
            team = (
                rolle_obj.info.team.value
                if hasattr(rolle_obj.info.team, "value")
                else str(rolle_obj.info.team)
            )
        else:
            team = "Unbekannt"

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"🧹 Beim Aufräumen des Hauses von {gestorbener.name} hast du entdeckt: Er/Sie war {rollen_name} (Team: {team})!",
            effekte={
                "rolle_enthuellt": True,
                "enthuellte_rolle": rollen_name,
                "enthuelltes_team": team,
                "enthuellter_spieler_id": gestorbener.id,
                "oeffentlich": True,  # Die Information ist öffentlich
            },
        )

    def on_tag_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Am Tagesbeginn kann die Putzfrau die Rollen der nachts Gestorbenen enthüllen.
        """
        # Prüfe ob es Tote in der letzten Nacht gab
        if not hasattr(kontext, "letzte_nacht_tote") or not kontext.letzte_nacht_tote:
            return None

        spieler_rollen = getattr(kontext, "spieler_rollen", {})
        enthuellungen = []

        for toter_id in kontext.letzte_nacht_tote:
            rolle_obj = spieler_rollen.get(toter_id)
            if rolle_obj:
                enthuellungen.append(
                    {"spieler_id": toter_id, "rolle": rolle_obj.info.name}
                )

        if enthuellungen:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"🧹 Die Putzfrau hat {len(enthuellungen)} Rolle(n) beim Aufräumen entdeckt!",
                effekte={"enthuellungen": enthuellungen, "oeffentlich": True},
            )

        return None

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Putzfrau."""
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
            modell_id="putzfrau",
            anzeige_name="Putzfrau",
            beschreibung="Putzfrau appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
