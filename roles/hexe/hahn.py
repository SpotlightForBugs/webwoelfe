"""
Hahn - Der krähende Verräter.

Der Hahn entlarvt seinen Mörder bei seinem Tod.
"""

from typing import Optional, TYPE_CHECKING
import random
from ..base import RollenModell, AppearanceFeature, Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Hahn(Role):
    """
    Hahn - Todes-Enthüllungs-Rolle.

    Fähigkeiten:
    - Keine aktive Fähigkeit
    - Bei Tod: Enthüllt wer ihn getötet hat

    Besonderheiten:
    - Passive Rolle (keine Nacht-Aktion)
    - Schreckt Werwölfe ab, ihn zu töten
    - Sehr mächtig gegen Werwölfe

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=45,
            name="Hahn",
            team=Team.DORF,
            kategorie=Kategorie.HEXE,
            beschreibung=(
                "Du bist der Hahn. Du krähst bei Sonnenaufgang! Wenn du "
                "stirbst, wird die Identität des Spielers, der dich "
                "getötet hat, enthüllt."
            ),
            icon="fa-solid fa-sun",
            farbe="#dc2626",
            prioritaet=96,
            erzaehler_nacht=(
                "Der Hahn schläft auf seinem Hühnerstall. "
                "Er wird jeden Mörder entlarven, der ihn tötet."
            ),
            erzaehler_tag=(
                "KIKERIKI! Der Hahn wurde getötet! Mit letzter Kraft "
                "verrät er seinen Mörder!"
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            # Visual Styling
            avatar_gradient_from="#dc2626",
            avatar_gradient_to="#991b1b",
            avatar_border_color="#ef4444",
            badge_emoji="🐓",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Hahn does not act on first night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Hahn is passive and does not act at night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Hahn's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Hahn - Passive Rolle",
            instructions="Wenn du stirbst, wird dein Mörder enthüllt.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Der Hahn entlarvt seinen Mörder.

        Die Todesursache gibt Hinweise auf den Mörder:
        - "werwolf": Die Werwölfe
        - "hexe": Die Hexe
        - "jaeger": Der Jäger
        - "hinrichtung": Das Dorf (keine Enthüllung)
        """
        # Bei Hinrichtung durch das Dorf keine Enthüllung
        if todesursache == "hinrichtung":
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "KIKERIKI! Der Hahn wurde vom Dorf gehängt. "
                    "Er konnte keinen einzelnen Mörder identifizieren."
                ),
                effekte={
                    "moerder_enthuellung": None,
                    "tod_durch_dorf": True,
                },
                log_sichtbar_fuer="alle",
            )

        spieler_namen = getattr(kontext, "spieler_namen", {})
        spieler_rollen = getattr(kontext, "spieler_rollen", {})
        lebende = getattr(kontext, "lebende_spieler", [])
        aktionen = getattr(kontext, "aktionen_diese_runde", [])

        def name_fuer(spieler_id: Optional[int]) -> str:
            if not spieler_id:
                return "Unbekannt"
            return spieler_namen.get(spieler_id, f"Spieler {spieler_id}")

        def finde_taeter_id(moerder_aktionen) -> Optional[int]:
            for aktion in aktionen:
                ziel_id = aktion.get("ziel_spieler_id") or aktion.get("ziel_id")
                if ziel_id != spieler.id:
                    continue
                aktion_typ = aktion.get("aktion_typ") or aktion.get("typ")
                if aktion_typ in moerder_aktionen:
                    return aktion.get("von_spieler_id") or aktion.get("spieler_id")
            return None

        def zufaelliger_werwolf_id() -> Optional[int]:
            if hasattr(kontext, "spieler_teams"):
                for sid in lebende:
                    if kontext.spieler_teams.get(sid) == Team.WERWOLF:
                        return random.choice(
                            [
                                lid
                                for lid in lebende
                                if kontext.spieler_teams.get(lid) == Team.WERWOLF
                            ]
                        )
                return None

            werwolf_ids = []
            for sid in lebende:
                rolle_name = spieler_rollen.get(sid)
                if not rolle_name:
                    continue
                rolle_obj = RoleRegistry.get(rolle_name)
                if rolle_obj and rolle_obj.info.team == Team.WERWOLF:
                    werwolf_ids.append(sid)
            return random.choice(werwolf_ids) if werwolf_ids else None

        moerder_id = None

        if todesursache == "werwolf":
            moerder_id = zufaelliger_werwolf_id()
            if moerder_id:
                nachricht = f"Einer meiner Mörder war {name_fuer(moerder_id)}!"
            else:
                nachricht = "Die Werwölfe haben den Hahn getötet!"
        elif todesursache == "hexe":
            moerder_id = finde_taeter_id({"vergiften", "hexe_toeten", "hexe"})
            if moerder_id:
                nachricht = f"{name_fuer(moerder_id)} hat den Hahn vergiftet!"
            else:
                nachricht = "Die Hexe hat den Hahn vergiftet!"
        elif todesursache == "jaeger":
            moerder_id = finde_taeter_id({"jaeger_schuss", "jaeger", "erschossen"})
            if moerder_id:
                nachricht = f"{name_fuer(moerder_id)} hat den Hahn erschossen!"
            else:
                nachricht = "Der Jäger hat den Hahn erschossen!"
        elif todesursache == "giftmischerin":
            moerder_id = finde_taeter_id({"giftmischerin", "vergiften"})
            if moerder_id:
                nachricht = f"{name_fuer(moerder_id)} hat den Hahn vergiftet!"
            else:
                nachricht = "Die Giftmischerin hat den Hahn vergiftet!"
        else:
            nachricht = f"Der Hahn wurde durch {todesursache} getötet!"

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"KIKERIKI! {nachricht}",
            effekte={
                "moerder_enthuellung": todesursache,
                "moerder_id": moerder_id,
                "hahn_kräht": True,
            },
            log_sichtbar_fuer="alle",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Hahn."""
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
            modell_id="hahn",
            anzeige_name="Hahn",
            beschreibung="Hahn appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
