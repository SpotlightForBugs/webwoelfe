"""
Wolfsjunge - Wird zum Werwolf wenn Vorbild stirbt.

Der Wolfsjunge waehlt in der ersten Nacht ein Vorbild.
Stirbt dieses, verwandelt er sich in einen Werwolf.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Wolfsjunge(Role):
    """
    Das Wolfsjunge (Wildes Kind) - Bedingte Verwandlung.

    Faehigkeiten:
    - Waehlt in der ersten Nacht ein Vorbild
    - Stirbt das Vorbild: Wird zum Werwolf
    - Solange Vorbild lebt: Teil des Dorfes

    Gewinnbedingung: Abhaengig von Verwandlung.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=124,
            name="Wolfsjunge",
            team=Team.DORF,  # Startet als Dorf
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist das Wolfsjunge. Du waehlst in der ersten Nacht "
                "ein Vorbild. Solange dein Vorbild lebt, gehoerst du zum "
                "Dorf. Stirbt es, wirst du zum Werwolf!"
            ),
            icon="fa-solid fa-child",
            farbe="#92400e",
            prioritaet=7,
            erzaehler_nacht=(
                "Das Wolfsjunge erwacht (nur erste Nacht) und waehlt " "sein Vorbild."
            ),
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import Team, Kategorie, SichtTyp, Erweiterung

        return AktionsTyp.WAEHLEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        # Sieht als Dorf aus, bis Verwandlung
        return SichtTyp.DORF

    def is_active_on_first_night(self) -> bool:
        """Wolfsjunge acts only on first night to choose role model."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Wolfsjunge does not act every night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Wolfsjunge's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Wolfsjunge - Vorbild wählen",
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
        Wolfsjunge wählt sein Vorbild in der ersten Nacht.
        """
        if kontext.runde != 1:
            return None

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

        # Vorbild speichern
        spieler.vorbild_id = ziel.id

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"{ziel.name} ist nun dein Vorbild. Stirbt es, wirst du zum Werwolf.",
            ziel_spieler_id=ziel.id,
            effekte={
                "vorbild": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_spieler_stirbt(
        self,
        spieler: "Spieler",
        opfer: "Spieler",
        todesursache: str,
        kontext: SpielKontext,
    ) -> Optional[AktionsErgebnis]:
        """
        Prueft ob das Vorbild stirbt und Verwandlung ausloest.
        """
        vorbild_id = getattr(spieler, "vorbild_id", None)

        if vorbild_id and opfer.id == vorbild_id:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=(
                    "Das Vorbild des Wolfsjungen ist gestorben! "
                    "Es verwandelt sich in einen Werwolf!"
                ),
                effekte={
                    "verwandlung": True,
                    "neues_team": "werwolf",
                    "neue_rolle": "Werwolf",
                },
                log_sichtbar_fuer="erzaehler",
            )

        return None
