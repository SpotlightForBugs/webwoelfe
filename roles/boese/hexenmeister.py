"""
Hexenmeister - Der Verflucher.

Der Hexenmeister gehört zu den Wölfen und kann Spieler
verfluchen - werden diese angegriffen, werden sie zu Werwölfen.
"""

from typing import Optional, TYPE_CHECKING
from ..base import (
    RollenModell,
    AppearanceFeature,
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Hexenmeister(Role):
    """
    Hexenmeister - Werwolf mit Fluch-Fähigkeit.

    Fähigkeiten:
    - Gehört zum Werwolf-Team
    - Kann Spieler verfluchen
    - Verfluchte werden bei Werwolf-Angriff zu Werwölfen statt zu sterben

    Besonderheiten:
    - Fluch ist geheim
    - Nur ein aktiver Fluch
    - Strategische Rekrutierung

    Gewinnbedingung: Werwölfe gewinnen.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=82,
            name="Hexenmeister",
            team=Team.WERWOLF,
            kategorie=Kategorie.BOESE,
            beschreibung=(
                "Du bist der Hexenmeister. Du gehörst zu den Wölfen und hast "
                "einen Fluchzauber - der Verfluchte wird zum Werwolf wenn "
                "er angegriffen wird!"
            ),
            icon="fa-solid fa-hat-wizard",
            farbe="#4c1d95",
            prioritaet=68,
            erzaehler_nacht=(
                "Der Hexenmeister kann einen Spieler verfluchen "
                "oder den Fluch aufheben."
            ),
            erweiterung=Erweiterung.COMMUNITY,
            distribution=DistributionConfig(
                min_players=12,
                count_func=lambda n: 1,
                priority=55,
                exclusive_with=["Werwolf"],
            ),
            # Visual Styling
            avatar_gradient_from="#4c1d95",
            avatar_gradient_to="#2e1065",
            avatar_border_color="#6d28d9",
            badge_emoji="🧙‍♂️",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.MANIPULIEREN

    @property
    def sichtbar_als(self) -> SichtTyp:
        return SichtTyp.WERWOLF

    def is_active_on_first_night(self) -> bool:
        """Hexenmeister acts on the first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Hexenmeister acts every night until the curse is used."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Hexenmeister's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Hexenmeister - Verfluchen",
            instructions="Wähle einen Spieler, um ihn zu verfluchen (wird bei Angriff zum Werwolf).",
            buttons=[
                UIButton(
                    label="Verfluchen",
                    action_type="verfluchen",
                    icon="fa-solid fa-hat-wizard",
                    css_class="btn-primary",
                    requires_confirmation=True,
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
        Hexenmeister verflucht einen Spieler.
        """
        if ziel is None:
            aktueller_fluch = getattr(spieler, "hexenmeister_fluch", None)
            if aktueller_fluch:
                return AktionsErgebnis(
                    erfolg=True,
                    nachricht=f"Dein Fluch auf Spieler {aktueller_fluch} bleibt bestehen.",
                    effekte={},
                    log_sichtbar_fuer=f"spieler_{spieler.id}",
                )
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du verzichtest auf deinen Fluch diese Nacht.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id in kontext.tote_spieler:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du kannst keine Toten verfluchen.",
            )

        # Prüfen ob Ziel kein Werwolf ist
        ziel_team = kontext.spieler_teams.get(ziel.id, Team.DORF)
        if ziel_team == Team.WERWOLF:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Wölfe brauchen keinen Fluch - sie sind bereits Teil des Rudels!",
            )

        spieler.hexenmeister_fluch = ziel.id

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du verfluchst {ziel.name}! Wird er angegriffen, "
            f"erwacht er als Werwolf!",
            ziel_spieler_id=ziel.id,
            effekte={
                "verflucht": ziel.id,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Hexenmeister."""
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
            modell_id="hexenmeister",
            anzeige_name="Hexenmeister",
            beschreibung="Hexenmeister appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="bad",
        )
