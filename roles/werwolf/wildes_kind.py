"""
Wildes Kind - Wird zum Werwolf wenn Vorbild stirbt.

Das Wilde Kind wählt in der ersten Nacht ein Vorbild.
Stirbt dieses, verwandelt es sich in einen Werwolf.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
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

    Gewinnbedingung: Abhängig von Verwandlung.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=25,
            name="Wildes Kind",
            team=Team.DORF,  # Startet als Dorf
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist das Wilde Kind. In der ersten Nacht wählst du "
                "ein Vorbild. Solange es lebt, bist du Dorfbewohner. "
                "Stirbt es, wirst du zum Werwolf!"
            ),
            icon="fa-solid fa-child",
            farbe="#92400e",
            prioritaet=6,
            erzaehler_nacht=(
                "Das Wilde Kind erwacht (erste Nacht) und wählt sein Vorbild."
            ),
            erzaehler_tag=(
                "Das Vorbild des Wilden Kindes ist gestorben - " "es wird zum Werwolf!"
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import AktionsTyp

        return AktionsTyp.WAEHLEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        # Erscheint als Dorf, bis Verwandlung
        return SichtTyp.DORF

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"

    def is_active_on_first_night(self) -> bool:
        """Wildes Kind acts only on first night to choose role model."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Wildes Kind does not act every night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Wildes Kind's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Wildes Kind - Vorbild wählen",
            instructions="Wähle dein Vorbild. Stirbt es, wirst du zum Werwolf.",
            buttons=[
                UIButton(
                    label="Vorbild wählen",
                    action_type="waehlen",
                    icon="fa-solid fa-child",
                    css_class="btn-primary",
                    requires_confirmation=True,
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
        Wildes Kind wählt sein Vorbild (erste Nacht).
        """
        if kontext.aktuelle_runde != 1:
            return None

        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst ein Vorbild wählen!",
            )

        # Vorbild speichern
        spieler.wildes_kind_vorbild_id = ziel.id

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du hast {ziel.name} als dein Vorbild gewählt. "
            f"Solange {ziel.name} lebt, gehörst du zum Dorf.",
            ziel_spieler_id=ziel.id,
            effekte={
                "vorbild_gewaehlt": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_spieler_stirbt(
        self, spieler: "Spieler", gestorbener_id: int, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn das Vorbild stirbt, verwandelt sich das Wilde Kind.
        """
        vorbild_id = getattr(spieler, "wildes_kind_vorbild_id", None)

        if vorbild_id is None:
            return None

        if gestorbener_id != vorbild_id:
            return None

        # Bereits verwandelt?
        if getattr(spieler, "wildes_kind_verwandelt", False):
            return None

        spieler.wildes_kind_verwandelt = True

        return AktionsErgebnis(
            erfolg=True,
            nachricht="Dein Vorbild ist tot! Die Wildheit übernimmt dich - "
            "du wirst zum WERWOLF!",
            effekte={
                "verwandlung": "werwolf",
                "team_wechsel": Team.WERWOLF.value,
                "wildes_kind_verwandelt": True,
            },
            log_sichtbar_fuer="alle",  # Wird verkündet
        )

    def berechne_aktuelles_team(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Team:
        """
        Team hängt von Verwandlungsstatus ab.
        """
        if getattr(spieler, "wildes_kind_verwandelt", False):
            return Team.WERWOLF
        return Team.DORF
