"""
Dieb - Wählt zwischen zwei Rollen.

Der Dieb sieht zu Beginn zwei übrige Rollen
und muss eine davon wählen.
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
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Dieb(Role):
    """
    Dieb - Rollenwahl zu Beginn.

    Fähigkeiten:
    - Sieht zu Beginn 2 übrige Rollen
    - Muss eine davon wählen
    - Muss Werwolf wählen wenn einer dabei ist

    Besonderheiten:
    - Erste Aktion im Spiel
    - Zwingende Werwolf-Wahl
    - Übernimmt dann die neue Rolle

    Gewinnbedingung: Abhängig von gewählter Rolle.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=96,
            name="Dieb",
            team=Team.DORF,  # Startet neutral
            kategorie=Kategorie.SONSTIGE,
            beschreibung=(
                "Du bist der Dieb. Zu Beginn siehst du zwei übrige Rollen "
                "und darfst dir eine aussuchen. Ist ein Werwolf dabei, "
                "musst du ihn wählen!"
            ),
            icon="fa-solid fa-mask",
            farbe="#1e293b",
            prioritaet=1,  # Erste Rolle!
            erzaehler_nacht=(
                "Der Dieb erwacht zuerst und sieht zwei Rollen. " "Er muss eine wählen."
            ),
            erweiterung=Erweiterung.BASISSPIEL,
            distribution=DistributionConfig(
                min_players=8,
                count_func=lambda n: 1,
                priority=100,
            ),
            # Visual Styling
            avatar_gradient_from="#1e293b",
            avatar_gradient_to="#0f172a",
            avatar_border_color="#334155",
            badge_emoji="🎭",
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.WAEHLEN

    def is_active_on_first_night(self) -> bool:
        """Dieb acts on first night (choosing role)."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Dieb only acts on first night."""
        return False

    def get_ui_definition(self) -> "RollenUI":
        """UI definition for Dieb using dynamic RoleAction, no skipping."""
        from ..base import RollenUI, RoleAction

        return RollenUI(
            title="Dieb - Rolle wählen",
            instructions=(
                "Du siehst zwei verbliebene Rollen. Ist ein Werwolf dabei, musst du ihn wählen."
            ),
            # Use action-driven API so backend handles selection without client targets
            actions=[
                RoleAction(
                    action_id="dieb_waehlen",
                    label="Rolle wählen",
                    handler="handle_dieb_waehlen",
                    action_type="waehlen",
                    icon="fa-solid fa-mask",
                    css_class="btn-primary",
                    requires_target=False,
                )
            ],
            # Legacy buttons left empty intentionally
            buttons=[],
            requires_target=False,
            allow_multiple_targets=False,
            can_skip=False,
        )

    def zeige_rollen(
        self, spieler: "Spieler", kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Zeigt dem Dieb die zwei verfügbaren Rollen.
        """
        # Die übrigen Rollen werden vom Spielleiter bestimmt
        uebrige_rollen: List[str] = getattr(kontext, "dieb_optionen", [])

        if len(uebrige_rollen) < 2:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Es gibt keine Rollen zur Auswahl!",
            )

        hat_werwolf = any("werwolf" in rolle.lower() for rolle in uebrige_rollen)

        hinweis = ""
        if hat_werwolf:
            hinweis = " ACHTUNG: Ein Werwolf ist dabei - du MUSST ihn wählen!"

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du siehst zwei Rollen: {uebrige_rollen[0]} und {uebrige_rollen[1]}.{hinweis}",
            effekte={
                "dieb_optionen": uebrige_rollen,
                "werwolf_pflicht": hat_werwolf,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def rolle_waehlen(
        self, spieler: "Spieler", wahl: int, kontext: SpielKontext
    ) -> AktionsErgebnis:
        """
        Dieb wählt eine der beiden Rollen (0 oder 1).
        """
        uebrige_rollen: List[str] = getattr(kontext, "dieb_optionen", [])

        if wahl not in [0, 1] or len(uebrige_rollen) < 2:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültige Wahl!",
            )

        gewaehlte_rolle = uebrige_rollen[wahl]
        andere_rolle = uebrige_rollen[1 - wahl]

        # Prüfen ob Werwolf dabei ist
        hat_werwolf = any("werwolf" in rolle.lower() for rolle in uebrige_rollen)
        ist_werwolf_wahl = "werwolf" in gewaehlte_rolle.lower()

        if hat_werwolf and not ist_werwolf_wahl:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du MUSST den Werwolf wählen!",
            )

        spieler.dieb_hat_gewaehlt = True

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du wirst zum {gewaehlte_rolle}!",
            effekte={
                "rolle_wechsel": gewaehlte_rolle,
                "dieb_hat_gewaehlt": True,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    # === Dynamic action handler used by RoleAction ===
    def handle_dieb_waehlen(self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext) -> AktionsErgebnis:
        """
        Dynamische Auswahl ohne Client-Targets:
        - Ermittelt zwei sinnvolle "übrige" Rollen aus der aktiven Rollenliste bzw. Registry
        - Erzwingt Werwolf-Wahl, wenn vorhanden
        - Wechselt die Rolle serverseitig direkt (keine app.py Hardcodes)
        """
        # 1) Versuche Optionen aus Kontext (falls später von Setup gesetzt)
        optionen: List[str] = getattr(kontext, "dieb_optionen", []) or []

        from models import Raum, Spieler as SpielerModel, db
        from roles import RoleRegistry

        # 2) Wenn nicht vorhanden: dynamisch ableiten
        if len(optionen) < 2:
            raum = db.session.get(Raum, kontext.raum_id)
            # Aktuell vergebene Rollen im Raum
            vergebene = [s.rolle for s in SpielerModel.query.filter_by(raum_id=kontext.raum_id).all() if s.rolle]
            # Kandidaten: alle registrierten Rollen, die nicht bereits vergeben sind
            kandidaten = [r for r in RoleRegistry.get_all_names() if r not in vergebene]

            # Stelle sinnvolle Default-Optionen sicher
            # Bevorzugt Werwolf + Dorfbewohner, falls verfügbar
            bevorzugt = []
            if "Werwolf" in kandidaten:
                bevorzugt.append("Werwolf")
            if "Dorfbewohner" in kandidaten:
                bevorzugt.append("Dorfbewohner")

            # Fülle ggf. auf 2 Optionen auf
            for name in kandidaten:
                if len(bevorzugt) >= 2:
                    break
                if name not in bevorzugt and name != spieler.rolle:
                    bevorzugt.append(name)

            optionen = bevorzugt[:2] if len(bevorzugt) >= 2 else (kandidaten[:2] if len(kandidaten) >= 2 else [spieler.rolle])

        # 3) Erzwinge Werwolf-Wahl wenn vorhanden
        if any("werwolf" in r.lower() for r in optionen):
            gewaehlte = next((r for r in optionen if "werwolf" in r.lower()), optionen[0])
        else:
            gewaehlte = optionen[0]

        # 4) Rolle sofort wechseln (ohne zentrale Hardcodes)
        alter_name = spieler.rolle or "Unbekannt"
        spieler.rolle = gewaehlte

        # Initialisiere State der neuen Rolle
        try:
            RoleRegistry.init_player_state(spieler)
        except Exception:
            pass

        db.session.commit()

        # 5) Ergebnis zurückgeben (UI/Log handled generisch)
        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du wirst zum {gewaehlte}!",
            effekte={
                "dieb_hat_gewaehlt": True,
                "alte_rolle": alter_name,
                "neue_rolle": gewaehlte,
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def get_modell_definition(self, spieler: "Spieler") -> RollenModell:
        """Village 3D appearance for Dieb."""
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
            modell_id="dieb",
            anzeige_name="Dieb",
            beschreibung="Dieb appearance with custom features",
            appearance_self_alive=appearance_features,
            appearance_others_alive=appearance_features,
            appearance_dead=[],
            seher_sicht="good",
        )
