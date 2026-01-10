"""
Sündenbock - Stirbt bei Unentschieden in Abstimmungen, darf dann bestimmen wer nicht abstimmen darf
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    AppearanceFeature,
    Role,
    RollenInfo,
    RollenModell,
    AktionsErgebnis,
    SpielKontext,
    RollenModell,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Suendenbock(Role):
    """
    Sündenbock

    Wenn es bei einer Abstimmung ein Unentschieden gibt, stirbt der Sündenbock
    anstelle der anderen. Als Ausgleich darf er bestimmen, wer in der nächsten
    Runde nicht abstimmen darf.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=98,
            name="Sündenbock",
            team=Team.DORF,
            kategorie=Kategorie.SONSTIGE,
            beschreibung="Du bist der Sündenbock. Wenn es bei einer Abstimmung ein Unentschieden gibt, stirbst DU anstelle der anderen! Versuche das zu verhindern.",
            icon="fa-solid fa-person-falling",
            farbe="#a8a29e",
            prioritaet=100,
            erzaehler_nacht="Der Sündenbock ahnt, dass er heute vielleicht für die Unentschlossenheit anderer sterben wird.",
            erzaehler_tag="UNENTSCHIEDEN bei der Abstimmung! Das Dorf kann sich nicht einigen - also muss der Sündenbock sterben!",
            hinweis_config=None,
            erweiterung=Erweiterung.NEUMOND,
            distribution=DistributionConfig(
                min_players=10,
                count_func=lambda n: 1,
                priority=25,
            ),
            # Visual Styling
            avatar_gradient_from="#a8a29e",
            avatar_gradient_to="#78716c",
            avatar_border_color="#d6d3d1",
            badge_emoji="🐐",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE

    def is_active_on_first_night(self) -> bool:
        """Sündenbock is passive."""
        return False

    def is_active_on_every_night(self) -> bool:
        """Sündenbock is passive."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Sündenbock's action panel."""
        from ..base import RollenUI

        return RollenUI(
            title="Sündenbock - Passive Rolle",
            instructions="Du stirbst bei Unentschieden, darfst dann aber jemanden blockieren.",
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=True,
        )

    def on_abstimmung(
        self, spieler: "Spieler", ziel: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird bei der Abstimmung aufgerufen.
        Die Logik für Unentschieden wird im Game-Loop geprüft.
        """
        # Der Sündenbock kann normal abstimmen
        return None

    def on_hinrichtung(
        self, spieler: "Spieler", opfer: "Spieler", kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wird bei einer Hinrichtung aufgerufen.
        Wenn es ein Unentschieden gab, wird der Sündenbock stattdessen hingerichtet.
        """
        # Prüfe ob es ein Unentschieden gab (wird im Kontext gesetzt)
        unentschieden = getattr(kontext, "abstimmung_unentschieden", False)

        if unentschieden and opfer.id == spieler.id:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="⚖️ Das Dorf konnte sich nicht einigen! Als Sündenbock musst DU sterben!",
                effekte={
                    "tod": True,
                    "todesursache": "Unentschieden bei Abstimmung",
                    "suendenbock_gestorben": True,
                    "darf_waehlen_wer_nicht_abstimmt": True,
                },
            )
        return None

    def on_eigener_tod(
        self, spieler: "Spieler", todesursache: str, kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Wenn der Sündenbock durch Unentschieden stirbt, darf er bestimmen
        wer in der nächsten Runde nicht abstimmen darf.
        """
        # Nur wenn durch Unentschieden gestorben
        if todesursache != "Unentschieden bei Abstimmung":
            return None

        # Sammle alle lebenden Spieler für die Auswahl
        lebende_spieler = []
        spieler_rollen = getattr(kontext, "spieler_rollen", {})
        for spieler_id in spieler_rollen.keys():
            if spieler_id not in kontext.tote_spieler and spieler_id != spieler.id:
                lebende_spieler.append(spieler_id)

        return AktionsErgebnis(
            erfolg=True,
            nachricht="🔇 Du stirbst für die Unentschlossenheit der anderen! Aber du darfst bestimmen, wer morgen NICHT abstimmen darf!",
            effekte={
                "waehle_blockierte_spieler": True,
                "verfuegbare_ziele": lebende_spieler,
            },
        )

    def waehle_blockierte_spieler(
        self, spieler: "Spieler", blockierte_ids: List[int], kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Der Sündenbock wählt, welche Spieler in der nächsten Runde
        nicht abstimmen dürfen.
        """
        if not blockierte_ids:
            return AktionsErgebnis(
                erfolg=True,
                nachricht="Du hast niemanden vom Abstimmen ausgeschlossen.",
                effekte={},
            )

        # Markiere die gewählten Spieler als blockiert
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"🚫 Du hast {len(blockierte_ids)} Spieler vom Abstimmen in der nächsten Runde ausgeschlossen!",
            effekte={
                "abstimmung_blockiert": blockierte_ids,
                "blockiert_fuer_runde": getattr(kontext, "aktuelle_runde", 1) + 1,
            },
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Suendenbock."""
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
            modell_id="suendenbock",
            anzeige_name="Suendenbock",
            beschreibung="Suendenbock appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
