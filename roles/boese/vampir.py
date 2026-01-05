"""
Vampir - Der Blutsauger.

Vampire verwandeln jede zweite Nacht einen Spieler
in einen Vampir. Sie gewinnen bei Vampir-Mehrheit.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Vampir(Role):
    """
    Vampir - Eigenständiges Team.

    Fähigkeiten:
    - Erwacht jede zweite Nacht
    - Kann einen Spieler in einen Vampir verwandeln
    - Vampire kennen sich untereinander

    Besonderheiten:
    - Eigenes Team (nicht Dorf, nicht Wölfe)
    - Verwandlung statt Tötung
    - Gewinnt bei Vampir-Mehrheit

    Gewinnbedingung: Mehr Vampire als andere Lebende.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=81,
            name="Vampir",
            team=Team.VAMPIR,
            kategorie=Kategorie.BOESE,
            beschreibung=(
                "Du bist ein Vampir! Jede zweite Nacht kannst du einen "
                "Spieler in einen Vampir verwandeln. Ihr gewinnt, wenn "
                "mehr Vampire als andere leben!"
            ),
            icon="fa-solid fa-tooth",
            farbe="#7c2d12",
            prioritaet=53,
            erzaehler_nacht=(
                "Die Vampire erwachen (jede zweite Nacht) und wählen "
                "einen Spieler zur Verwandlung."
            ),
            erzaehler_tag=None,
            hinweis_config=None,
        erweiterung=Erweiterung.SONDEREDITION,
            )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.INFIZIEREN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.DORF  # Erscheinen als harmlos für Seherin

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende_keine_vampire"

    def is_active_on_first_night(self) -> bool:
        """Vampir starts acting on second night."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Vampir is active (periodically). Checks round in on_nacht_aktion."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Vampir's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Vampir - Verwandeln",
            instructions="Wähle einen Spieler, um ihn zu verwandeln (nur gerade Runden).",
            buttons=[
                UIButton(
                    label="Verwandeln",
                    action_type="verwandeln",
                    icon="fa-solid fa-tooth",
                    css_class="btn-danger",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Vampir verwandelt einen Spieler.
        """
        # Nur jede zweite Nacht (gerade Runden)
        # Assuming runden start at 1? Or 0?
        # Vampir desc: "Jede zweite Nacht". Usually night 2, 4, 6...
        if kontext.runde % 2 != 0:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du schläfst in deiner Gruft. Nächste Nacht wirst du jagen.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du verzichtest auf die Jagd diese Nacht.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Tote können nicht verwandelt werden.",
            )

        # Prüfen ob schon Vampir
        ziel_team = kontext.spieler_teams.get(ziel.id, Team.DORF)
        if ziel_team == Team.VAMPIR:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Dieses Opfer ist bereits ein Vampir!",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du beißt {ziel.name}! In der nächsten Nacht wird "
            f"er als Vampir erwachen!",
            ziel_spieler_id=ziel.id,
            effekte={
                "vampir_gebissen": ziel.id,
                "team_wechsel": Team.VAMPIR.value,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def pruefe_gewinn(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Prüft ob Vampire in der Mehrheit sind.
        """
        lebende = [
            sid
            for sid in kontext.spieler_rollen.keys()
            if sid not in kontext.tote_spieler
        ]

        vampire = [
            sid for sid in lebende if kontext.spieler_teams.get(sid) == Team.VAMPIR
        ]

        nicht_vampire = [sid for sid in lebende if sid not in vampire]

        if len(vampire) > len(nicht_vampire):
            return AktionsErgebnis(
                erfolg=True,
                nachricht="DIE NACHT BRICHT HEREIN! Die Vampire haben gewonnen!",
                effekte={
                    "spiel_ende": True,
                    "gewinner": "vampire",
                },
                log_sichtbar_fuer="alle",
            )

        return None
