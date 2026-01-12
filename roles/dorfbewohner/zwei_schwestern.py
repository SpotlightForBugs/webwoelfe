"""
Zwei Schwestern - Kennen sich gegenseitig.

Die zwei Schwestern erkennen sich in der ersten Nacht
und können sich jede Nacht kurz absprechen.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    RollenModell,
    AppearanceFeature,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    DistributionConfig,
)
from ..enums import Team, Kategorie, Erweiterung, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class ZweiSchwestern(Role):
    """
    Zwei Schwestern - Gruppen-Informationsrolle.

    Fähigkeiten:
    - Erkennen sich in der ersten Nacht
    - Können sich jede Nacht kurz absprechen

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=14,
            name="Zwei Schwestern",
            team=Team.DORF,
            kategorie=Kategorie.DORFBEWOHNER,
            beschreibung=(
                "Du bist eine der zwei Schwestern. In der ersten Nacht "
                "erkennt ihr euch gegenseitig. Danach könnt ihr über "
                "private Nachrichten kommunizieren."
            ),
            icon="fa-solid fa-user-group",
            farbe="#f472b6",
            prioritaet=8,
            erzaehler_nacht=(
                "Die zwei Schwestern erwachen und erkennen sich. "
                "Sie dürfen sich kurz absprechen."
            ),
            erweiterung=Erweiterung.CHARAKTERE,
            distribution=DistributionConfig(
                min_players=10,
                count_func=lambda n: 2,
                min_role_count=2,
                max_role_count=2,
                priority=35,
            ),
            # Visual Styling
            avatar_gradient_from="#f472b6",
            avatar_gradient_to="#db2777",
            avatar_border_color="#f9a8d4",
            badge_emoji="👭",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    @property
    def is_automatic_phase(self) -> bool:
        """
        Zwei Schwestern Phase ist automatisch - reine Info-Phase.
        Spieler sehen sich, können chatten, aber keine Aktionen ausführen.
        """
        return True

    def is_active_on_first_night(self) -> bool:
        """Zwei Schwestern act on first night (recognize each other)."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Zwei Schwestern only act on first night. After that they use private chat."""
        return False

    def erlaubt_private_nachrichten(self) -> bool:
        """Zwei Schwestern dürfen private Nachrichten schreiben."""
        return True
    
    def erlaubte_chat_partner(
        self, spieler: "Spieler", kontext: "SpielKontext"
    ) -> List["Spieler"]:
        """
        Zwei Schwestern dürfen nur mit ihrer Schwester chatten.
        
        Findet die andere Schwester basierend auf der Rolle.
        """
        from typing import List, TYPE_CHECKING
        if TYPE_CHECKING:
            from models import Spieler as SpielerType
        
        # Finde alle lebenden Spieler mit der Rolle "Zwei Schwestern"
        alle_schwestern = [
            s for s in kontext.lebende_spieler_objekte
            if s.rolle == "Zwei Schwestern" and s.id != spieler.id
        ]
        
        return alle_schwestern

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Zwei Schwestern action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Zwei Schwestern",
            instructions="Du erkennst deine Schwester! Ihr könnt euch ab jetzt über private Nachrichten absprechen.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_spiel_start(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Die zwei Schwestern erkennen sich.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Du erkennst deine Schwester.",
            effekte={"erkennt_schwestern": True},
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Schwestern dürfen sich kurz absprechen.
        """
        return AktionsErgebnis(
            erfolg=True,
            nachricht="Die Schwestern haben sich kurz abgesprochen.",
            effekte={"schwestern_absprache": True},
            log_sichtbar_fuer="erzaehler",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for ZweiSchwestern."""
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
            modell_id="zweischwestern",
            anzeige_name="ZweiSchwestern",
            beschreibung="ZweiSchwestern appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
