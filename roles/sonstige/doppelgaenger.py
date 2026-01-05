"""
Doppelgänger - Übernimmt Rolle eines Sterbenden.

Der Doppelgänger wählt ein Ziel. Stirbt dieses,
übernimmt er dessen Rolle und Team.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Doppelgaenger(Role):
    """
    Doppelgänger - Rollenübernahme bei Tod.

    Fähigkeiten:
    - Wählt in der ersten Nacht ein Ziel
    - Stirbt das Ziel, übernimmt er dessen Rolle
    - Team wechselt entsprechend

    Besonderheiten:
    - Ähnlich wie Wildes Kind
    - Aber: Aktive Übernahme
    - Kann zum Werwolf werden

    Gewinnbedingung: Abhängig von übernommener Rolle.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=93,
            name="Doppelgänger",
            team=Team.DORF,  # Startet als Dorf
            kategorie=Kategorie.SONSTIGE,
            beschreibung=(
                "Du bist der Doppelgänger. In der ersten Nacht wählst du "
                "einen Spieler. Stirbt dieser, übernimmst du seine Rolle "
                "und sein Team!"
            ),
            icon="fa-solid fa-clone",
            farbe="#6366f1",
            prioritaet=4,
            erzaehler_nacht=(
                "Der Doppelgänger erwacht (erste Nacht) und wählt sein Ziel."
            ),
            erzaehler_tag=(
                "Das Ziel des Doppelgängers ist tot! " "Er übernimmt dessen Rolle."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.WAEHLEN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_andere"

    def is_active_on_first_night(self) -> bool:
        """Doppelgänger acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Doppelgänger only acts on first night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Doppelgänger's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Doppelgänger - Ziel wählen",
            instructions="Wähle einen Spieler. Stirbt er, übernimmst du seine Rolle.",
            buttons=[
                UIButton(
                    label="Ziel wählen",
                    action_type="waehlen",
                    icon="fa-solid fa-clone",
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
        Doppelgänger wählt sein Ziel (erste Nacht).
        """
        if kontext.aktuelle_runde != 1:
            return None

        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst ein Ziel wählen!",
            )

        spieler.doppelgaenger_ziel_id = ziel.id

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du hast {ziel.name} als Ziel gewählt. "
            f"Stirbt er, übernimmst du seine Rolle!",
            ziel_spieler_id=ziel.id,
            effekte={
                "doppelgaenger_ziel": ziel.id,
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
        Wenn das Ziel stirbt, übernimmt der Doppelgänger die Rolle.
        """
        ziel_id = getattr(spieler, "doppelgaenger_ziel_id", None)

        if ziel_id is None:
            return None

        if gestorbener.id != ziel_id:
            return None

        # Bereits übernommen?
        if getattr(spieler, "doppelgaenger_uebernommen", False):
            return None

        spieler.doppelgaenger_uebernommen = True

        # Rolle des Gestorbenen ermitteln
        gestorbene_rolle = kontext.spieler_rollen.get(gestorbener.id, "Dorfbewohner")
        gestorbenes_team = kontext.spieler_teams.get(gestorbener.id, Team.DORF)

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Dein Ziel ist gestorben! Du übernimmst die Rolle: {gestorbene_rolle}!",
            effekte={
                "rolle_wechsel": gestorbene_rolle,
                "team_wechsel": gestorbenes_team.value,
                "doppelgaenger_uebernommen": True,
            },
            log_sichtbar_fuer="alle",
        )

    def berechne_aktuelles_team(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Team:
        """
        Team hängt von Übernahmestatus ab.
        """
        if getattr(spieler, "doppelgaenger_uebernommen", False):
            # Übernommenes Team aus Kontext holen
            return getattr(spieler, "neues_team", Team.DORF)
        return Team.DORF
