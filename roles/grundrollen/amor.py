"""
Amor - Der Gott der Liebe.

Amor verbindet zwei Spieler auf ewig -
stirbt einer, stirbt auch der andere.
"""

from typing import Optional, List, TYPE_CHECKING, Union
from ..base import (
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    RollenUI,
    StateField,
    StateType,
    StateVisualEffect,
    GlobalStateDefinition,
    get_spieler_state,
    set_spieler_state,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Amor(Role):
    """
    Amor - Verbindungs-Rolle.

    Fähigkeiten:
    - Erste Nacht: Wählt zwei Spieler die sich verlieben
    - Verliebte sterben zusammen
    - Verliebte gewinnen nur gemeinsam als Letztes Paar

    Gewinnbedingung: Dorf gewinnt ODER Verliebte überleben als Letzte.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder von Amor."""
        return [
            StateField(
                "hat_verkuppelt", StateType.BOOL, False, "Hat bereits Verliebte gewählt"
            ),
        ]

    def global_state_definitions(self) -> List[GlobalStateDefinition]:
        """Definiert den Verliebt-State der auf andere Spieler gesetzt wird."""
        return [
            GlobalStateDefinition(
                key="global.verliebt_mit_id",
                name="Verliebt",
                typ=StateType.PLAYER_ID,
                beschreibung="ID des Partners mit dem der Spieler verliebt ist",
                visual_effect=StateVisualEffect.HEART,
                css_class="verliebt-partner",
                icon="💕",
                query_name="verliebte",
                defined_by="Amor",
            ),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=7,
            name="Amor",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist Amor. In der ersten Nacht wählst du zwei Spieler, "
                "die sich unsterblich verlieben. Stirbt einer, stirbt auch "
                "der andere. Die Verliebten gewinnen nur gemeinsam!"
            ),
            icon="fa-solid fa-heart",
            farbe="#ec4899",
            prioritaet=5,  # Sehr früh in der Nacht
            erzaehler_nacht=(
                "Amor erwacht (nur erste Nacht) und zeigt auf zwei Spieler, "
                "die sich verlieben sollen. Beruehre beide leicht an der Schulter."
            ),
            erweiterung=Erweiterung.BASISSPIEL,
            distribution=DistributionConfig(
                min_players=8,
                # 1 Amor ab 8 Spielern
                count_func=lambda n: max(1, n // 150),
                priority=5,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.VERLIEBEN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"  # Beide Verliebte müssen am Leben sein

    def is_active_on_first_night(self) -> bool:
        """Amor is only active on the first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Amor does not act every night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Amor's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Amor - Verliebte wählen",
            instructions="Wähle zwei Spieler, die sich verlieben sollen.",
            buttons=[
                UIButton(
                    label="Verlieben",
                    action_type="armor_verlieben",
                    icon="fa-solid fa-heart",
                    css_class="btn-primary",
                    requires_confirmation=True,
                )
            ],
            requires_target=True,
            allow_multiple_targets=True,  # Needs 2 targets
            can_skip=False,  # Must act
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Amor wählt in der ersten Nacht zwei Verliebte.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Wähle zwei Spieler, die sich verlieben sollen.",
            effekte={"warte_auf_verliebte_wahl": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional[Union["Spieler", List["Spieler"]]], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """Dispatches the night action (verlieben)."""
        if isinstance(ziel, list) and len(ziel) == 2:
            return self.verlieben(spieler, ziel[0], ziel[1], kontext)
        return AktionsErgebnis(False, "Ungültige Anzahl an Zielen.")

    def verlieben(
        self,
        spieler: "Spieler",
        ziel1: "Spieler",
        ziel2: "Spieler",
        kontext: SpielKontext,
    ) -> AktionsErgebnis:
        """
        Verbindet zwei Spieler als Verliebte.
        """
        # Prüfe Gültigkeit
        if ziel1.id == ziel2.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst zwei verschiedene Spieler wählen.",
            )

        if (
            ziel1.id not in kontext.lebende_spieler
            or ziel2.id not in kontext.lebende_spieler
        ):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Beide Spieler müssen am Leben sein.",
            )

        # Setze Verliebte-Status auf beide Spieler (global state)
        set_spieler_state(ziel1, "global.verliebt_mit_id", ziel2.id)
        set_spieler_state(ziel2, "global.verliebt_mit_id", ziel1.id)

        # Markiere Amor als hat verkuppelt
        self.set_state(spieler, "hat_verkuppelt", True)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel1.name} und {ziel2.name} haben sich verliebt!",
            effekte={
                "verliebte": [ziel1.id, ziel2.id],
            },
            log_sichtbar_fuer="erzaehler",
            private_infos={
                ziel1.id: {
                    # Generic overlay format - no hardcoded type needed
                    "overlay": {
                        "title": "Du bist verliebt!",
                        "subtitle": "Dein Seelenpartner ist:",
                        "highlight": f"{ziel2.name} 💘",
                        "content": "Eure Schicksale sind verbunden. Stirbt einer, stirbt auch der andere!",
                        "icon": "💕",
                        "color": "#ec4899",
                        "gradient": "linear-gradient(135deg, #ff69b4 0%, #ff1493 50%, #c71585 100%)",
                        "animation": "heartbeat",
                    }
                },
                ziel2.id: {
                    "overlay": {
                        "title": "Du bist verliebt!",
                        "subtitle": "Dein Seelenpartner ist:",
                        "highlight": f"{ziel1.name} 💘",
                        "content": "Eure Schicksale sind verbunden. Stirbt einer, stirbt auch der andere!",
                        "icon": "💕",
                        "color": "#ec4899",
                        "gradient": "linear-gradient(135deg, #ff69b4 0%, #ff1493 50%, #c71585 100%)",
                        "animation": "heartbeat",
                    }
                }
            }
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        opfer: "Spieler",
        todesursache: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob ein Verliebter stirbt und der andere folgen muss.
        """
        verliebt_mit = get_spieler_state(opfer, "global.verliebt_mit_id")

        if verliebt_mit and verliebt_mit in kontext.lebende_spieler:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"Der/Die Verliebte kann den Verlust nicht ertragen!",
                effekte={
                    "verliebter_stirbt_auch": verliebt_mit,
                    "todesursache": "gebrochenes_herz",
                },
                log_sichtbar_fuer="alle",
            )

        return None

    def berechne_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[Team]:
        """
        Verliebte gewinnen wenn sie die letzten Überlebenden sind.
        Deprecated: Used by legacy logic. New logic uses get_win_conditions.
        """
        return None

    def get_win_conditions(self) -> List["WinCondition"]:
        """Verliebte gewinnen wenn sie die letzten sind."""
        from ..base import WinCondition, get_spieler_state

        def check_lovers_win(spieler: "Spieler", kontext: SpielKontext) -> bool:
            # Hole alle Spieler-Objekte (langsam aber nötig für State-Check)
            from models import Spieler
            
            # Optimierung: Prüfe nur wenn wenige Spieler leben
            if len(kontext.lebende_spieler) > 3: # Bei 3 (z.b. Wolf+Dorf+Amor) kann es spannend sein
                 # Wenn noch viele leben, können Verliebte kaum gewonnen haben (außer alle sind tot bis auf 2)
                 # Wir checken nur wenn lebende <= 3 oder so? 
                 # Nein, "Verliebte gewinnen wenn sie die letzten Überlebenden sind" -> max 2 lebende.
                 pass

            if len(kontext.lebende_spieler) != 2:
                return False

            # Check ob die beiden Lebenden verliebt sind
            lebende_objs = Spieler.query.filter(Spieler.id.in_(kontext.lebende_spieler)).all()
            if len(lebende_objs) != 2:
                return False
            
            s1, s2 = lebende_objs[0], lebende_objs[1]
            
            partner1 = get_spieler_state(s1, "global.verliebt_mit_id")
            partner2 = get_spieler_state(s2, "global.verliebt_mit_id")
            
            if partner1 == s2.id and partner2 == s1.id:
                # Prüfen ob ein Wolf dabei ist (damit es kein reiner Dorfsieg ist)
                # (Wobei reine Dorf-Verliebte auch als Dorf gewinnen können, aber "Verliebte Win" ist cooler)
                # Regel: Wenn Verliebte Good+Good sind, gewinnen sie mit Dorf.
                # Wenn Good+Evil oder Evil+Evil, gewinnen sie als Paar.
                
                from roles import RoleRegistry
                r1 = RoleRegistry.get(s1.rolle)
                r2 = RoleRegistry.get(s2.rolle)
                
                team1 = r1.info.team if r1 else Team.DORF
                team2 = r2.info.team if r2 else Team.DORF
                
                if team1 != team2 or team1 == Team.WERWOLF:
                    return True
                    
            return False

        return [
            WinCondition(
                id="lovers_win",
                check_func=check_lovers_win,
                team_override=Team.VERLIEBTE,
                priority=20,  # Höher als Standard
                description="Die Verliebten haben gewonnen! Ihre Liebe hat alle überwunden.",
            )
        ]
