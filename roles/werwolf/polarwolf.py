"""
Polarwolf - Immun gegen Sandmann und Jäger.

Der Polarwolf ist ein Werwolf mit Immunität gegen
bestimmte Effekte durch seine Kälteresistenz.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Polarwolf(Role):
    """
    Polarwolf - Werwolf mit Immunitäten.

    Fähigkeiten:
    - Jagt mit den Wölfen
    - Immun gegen Sandmann (kann nicht eingeschläfert werden)
    - Immun gegen Jäger (Schuss verfehlt)

    Besonderheiten:
    - Passiver Schutz
    - Kann weiterhin von Hexe, Hinrichtung etc. getötet werden

    Gewinnbedingung: Werwölfe gewinnen.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=22,
            name="Polarwolf",
            team=Team.WERWOLF,
            kategorie=Kategorie.WERWOLF,
            beschreibung=(
                "Du bist der Polarwolf. Du bist immun gegen die Kälte - "
                "der Sandmann kann dich nicht einschläfern und der Jäger "
                "verfehlt dich immer!"
            ),
            icon="fa-solid fa-snowflake",
            farbe="#e0f2fe",
            prioritaet=50,
            erzaehler_nacht=("Der Polarwolf ist immun gegen Sandmann und Jäger."),
            erzaehler_tag=None,
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> "AktionsTyp":
        from ..enums import AktionsTyp

        return AktionsTyp.TOETEN  # Jagt mit Wölfen

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    def is_active_on_first_night(self) -> bool:
        """Polarwolf acts on first night with werwolves."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Polarwolf acts every night with werwolves."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Polarwolf's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Polarwolf - Mit Wölfen jagen",
            instructions="Wähle das Opfer der Wölfe. Du bist immun gegen Sandmann und Jäger.",
            buttons=[
                UIButton(
                    label="Angreifen",
                    action_type="toeten",
                    icon="fa-solid fa-snowflake",
                    css_class="btn-danger",
                )
            ],
            requires_target=True,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def ist_immun_gegen(self, effekt_typ: str) -> bool:
        """
        Polarwolf ist immun gegen bestimmte Effekte.
        """
        immunitaeten = ["sandmann", "jaeger", "einschlaefern", "schuss"]
        return effekt_typ.lower() in immunitaeten

    def on_angegriffen(
        self, spieler: "Spieler", angreifer_id: int, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Polarwolf ist immun gegen Jäger-Schuss.
        """
        # Prüfen ob Angreifer ein Jäger ist
        angreifer_rolle = kontext.spieler_rollen.get(angreifer_id, "")

        if "jaeger" in angreifer_rolle.lower() or "jäger" in angreifer_rolle.lower():
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Der Schuss des Jägers verfehlt den Polarwolf in der Kälte!",
                effekte={
                    "angriff_abgewehrt": True,
                    "immunität_jaeger": True,
                },
                log_sichtbar_fuer="alle",
            )

        return None  # Andere Angriffe treffen normal
