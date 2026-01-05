"""
Lupin - Der Werwolf mit wechselnder Identitaet.

Lupin verwandelt sich nur bei Vollmond. In geraden Runden
erscheint er der Seherin als Mensch, in ungeraden als Wolf.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Lupin(Role):
    """
    Lupin - Werwolf mit wechselnder Identitaet.

    Faehigkeiten:
    - Jagt mit den Woelfen
    - In geraden Runden erscheint er der Seherin als Mensch
    - In ungeraden Runden erscheint er als Werwolf

    Gewinnbedingung: Werwoelfe gewinnen.
    """

    # Speichert die aktuelle Runde fuer die Sichtbarkeit
    _aktuelle_runde: int = 1

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=26,
            name="Lupin",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist Lupin. Du verwandelst dich nur bei Vollmond - "
                "in geraden Runden bist du ein harmloser Mensch (erscheinst "
                "so fuer die Seherin), in ungeraden ein Wolf!"
            ),
            icon="fa-solid fa-moon",
            farbe="#ca8a04",
            prioritaet=50,
            erzaehler_nacht=(
                "Lupin ist in geraden Runden Mensch, in ungeraden Wolf. "
                "Die Seherin sieht entsprechend die aktuelle Form."
            ),
            erweiterung=Erweiterung.SONDEREDITION,
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import Team, Kategorie, SichtTyp, Erweiterung

        return AktionsTyp.TOETEN

    @property
    def sichtbar_als(self) -> SichtTyp:
        """In geraden Runden Mensch, in ungeraden Wolf."""
        # Die Runde wird beim Nacht-Start gesetzt
        if self._aktuelle_runde % 2 == 0:
            return SichtTyp.DORF  # Gerade Runde = Mensch
        return SichtTyp.WERWOLF  # Ungerade Runde = Wolf

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Lupin acts on first night with werwolves."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Lupin acts every night with werwolves."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Lupin's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Lupin - Mit Wölfen jagen",
            instructions="Wähle das Opfer der Wölfe. Deine Form wechselt jede Runde.",
            buttons=[
                UIButton(
                    label="Angreifen",
                    action_type="toeten",
                    icon="fa-solid fa-moon",
                    css_class="btn-danger",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def on_nacht_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """Speichert die aktuelle Runde fuer die Sichtbarkeit."""
        self._aktuelle_runde = kontext.runde

        ist_wolf = kontext.runde % 2 != 0
        form_text = "Wolf" if ist_wolf else "Mensch"

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Diese Nacht bist du in deiner {form_text}-Form.",
            effekte={
                "lupin_ist_wolf": ist_wolf,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Lupin nimmt am Werwolf-Angriff teil wie ein normaler Wolf.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Die Woelfe muessen ein Opfer waehlen.",
            )

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Die Woelfe haben {ziel.name} als Opfer gewaehlt.",
            ziel_spieler_id=ziel.id,
            effekte={
                "werwolf_opfer": ziel.id,
            },
            log_sichtbar_fuer="werwolf",
        )
