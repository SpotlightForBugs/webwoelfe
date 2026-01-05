"""
Wildes Kind - Wird zum Werwolf wenn Vorbild stirbt.

Das Wilde Kind wählt in der ersten Nacht ein Vorbild.
Stirbt dieses, verwandelt es sich in einen Werwolf.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
)
from ..enums import Team, Kategorie, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class WildesKind(Role):
    """
    Wildes Kind - Bedingte Verwandlungsrolle.

    Fähigkeiten:
    - Wählt in der ersten Nacht ein Vorbild
    - Solange Vorbild lebt: Dorfbewohner
    - Stirbt Vorbild: Wird zum Werwolf

    Besonderheiten:
    - Startet im Dorf-Team
    - Team wechselt bei Verwandlung
    - Nach Verwandlung: Jagt mit den Wölfen

    Gewinnbedingung: Abhängig von der Verwandlung.
    """

    def state_fields(self) -> List[StateField]:
        """Definiert die Zustandsfelder des wilden Kindes."""
        return [
            StateField("vorbild_id", StateType.PLAYER_ID, None, "ID des Vorbilds"),
            StateField("verwandelt", StateType.BOOL, False, "Zum Werwolf verwandelt"),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=25,
            name="Wildes Kind",
            team=Team.DORF,  # Startet als Dorf
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist das Wilde Kind. Du wählst in der ersten Nacht ein "
                "Vorbild. Solange dein Vorbild lebt, gehörst du zum Dorf. "
                "Stirbt dein Vorbild, wirst du zum Werwolf!"
            ),
            icon="fa-solid fa-child-reaching",
            farbe="#a16207",
            prioritaet=6,  # Sehr früh
            erzaehler_nacht=(
                "Das Wilde Kind erwacht und wählt sein Vorbild. "
                "Stirbt dieses, wird das Kind zum Werwolf."
            ),
            erweiterung=Erweiterung.NEUMOND,
            # Visual Styling
            avatar_gradient_from="#a16207",
            avatar_gradient_to="#713f12",
            avatar_border_color="#ca8a04",
            badge_emoji="🐾",
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import AktionsTyp

        return AktionsTyp.WAEHLEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        """
        Erscheint als Dorfbewohner, bis es verwandelt ist.
        """
        # Wir brauchen Zugriff auf den State
        # Da wir hier keinen Spieler haben, geben wir Standard zurück
        # Die Logik muss in get_sichtbare_rolle_fuer implementiert werden
        return SichtTyp.DORF

    def get_sichtbare_rolle_fuer(self, seher: "Role", kontext: SpielKontext) -> str:
        """
        Spezielle Logik für Seherin:
        Vor Verwandlung = Dorfbewohner
        Nach Verwandlung = Werwolf
        """
        # Wir brauchen den Spieler um den State zu prüfen
        # Das ist hier schwierig ohne Spieler-Objekt
        # Aber die Basis-Klasse ruft dies auf dem Role-Objekt auf
        # Wir müssen das Role-Objekt mit dem Spieler verknüpfen oder
        # die Methode muss den Spieler als Argument bekommen (was sie nicht tut in base.py)
        # TODO: Refactor base.py to pass target player to get_sichtbare_rolle_fuer
        return "Dorfbewohner"  # Fallback

    def is_active_on_first_night(self) -> bool:
        """Wildes Kind acts on first night (choosing role model)."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Wildes Kind only acts on first night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Wildes Kind's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Wildes Kind - Vorbild wählen",
            instructions="Wähle dein Vorbild. Wenn es stirbt, wirst du zum Werwolf.",
            buttons=[
                UIButton(
                    label="Vorbild wählen",
                    action_type="waehlen",
                    icon="fa-solid fa-paw",
                    css_class="btn-primary",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wildes Kind wählt sein Vorbild.
        """
        if kontext.runde != 1:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast dein Vorbild bereits gewählt.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst ein Vorbild wählen!",
            )

        if ziel.id == spieler.id:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst dich nicht selbst als Vorbild wählen.",
            )

        self.set_state(spieler, "vorbild_id", ziel.id)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} ist nun dein Vorbild. Beschütze es, oder deine wilde Seite erwacht!",
            ziel_spieler_id=ziel.id,
            effekte={
                "vorbild_gewaehlt": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        gestorbener: "Spieler",
        todesursache: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn das Vorbild stirbt, wird das Wilde Kind zum Werwolf.
        """
        vorbild_id = self.get_state(spieler, "vorbild_id")

        if vorbild_id and gestorbener.id == vorbild_id:
            self.set_state(spieler, "verwandelt", True)
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Dein Vorbild ist tot! Deine Wut verwandelt dich in einen WERWOLF!",
                effekte={
                    "wildes_kind_verwandlung": True,
                    "team_wechsel": Team.WERWOLF.value,
                },
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return None
