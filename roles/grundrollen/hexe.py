"""
Hexe - Mächtige Rolle mit zwei Tränken.

Die Hexe kann einmal pro Spiel jemanden heilen
und einmal jemanden vergiften.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import (
    Role,
    RollenInfo,
    AktionsErgebnis,
    SpielKontext,
    StateField,
    StateType,
    DistributionConfig,
)
from ..enums import Team, Kategorie, AktionsTyp, Erweiterung
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Hexe(Role):
    """
    Die Hexe - Mächtige Rolle mit zwei Tränken.

    Fähigkeiten:
    - Heiltrank: Kann einmal pro Spiel das Werwolf-Opfer retten
    - Gifttrank: Kann einmal pro Spiel einen Spieler töten

    Gewinnbedingung: Dorf gewinnt.
    """

    def state_fields(self) -> List[StateField]:
        return [
            StateField("heiltrank", StateType.BOOL, True, "Heiltrank verfügbar"),
            StateField("gifttrank", StateType.BOOL, True, "Gifttrank verfügbar"),
        ]

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=4,
            name="Hexe",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist die Hexe. Du hast zwei Tränke: Einen Heiltrank, um das "
                "Werwolf-Opfer zu retten, und einen Gifttrank, um einen Spieler "
                "zu töten. Jeden Trank kannst du nur einmal verwenden."
            ),
            icon="fa-solid fa-flask",
            farbe="#d946ef",
            prioritaet=90,
            erzaehler_nacht=(
                "Die Hexe erwacht. Ich zeige ihr das Opfer der Werwölfe. "
                "Möchtest du es retten? Möchtest du jemanden vergiften?"
            ),
            erweiterung=Erweiterung.BASISSPIEL,
            # Visual Styling
            avatar_gradient_from="#d946ef",
            avatar_gradient_to="#a21caf",
            avatar_border_color="#f0abfc",
            badge_emoji="🧪",
            distribution=DistributionConfig(
                min_players=5,
                count_func=lambda n: 1,
                priority=90,
                exclusive_with=[],
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.KEINE  # Hexe hat mehrere Aktionen

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def is_active_on_first_night(self) -> bool:
        """Hexe acts on first night."""
        return True

    def is_active_on_every_night(self) -> bool:
        """Hexe acts every night."""
        return True

    def get_ui_definition(self) -> "RollenUI":
        """Returns the UI definition for Hexe's action panel."""
        from ..base import RollenUI, UIButton

        return RollenUI(
            title="Hexe - Tränke verwenden",
            instructions="Du siehst das Opfer der Werwölfe. Willst du deine Tränke nutzen?",
            buttons=[
                UIButton(
                    label="Heilen",
                    action_type="heilen",
                    icon="fa-solid fa-heart-pulse",
                    css_class="btn-success",
                    requires_confirmation=True,
                ),
                UIButton(
                    label="Vergiften",
                    action_type="vergiften",
                    icon="fa-solid fa-skull-crossbones",
                    css_class="btn-danger",
                    requires_confirmation=True,
                ),
            ],
            requires_target=True,  # For poison
            allow_multiple_targets=False,
            can_skip=True,  # Can choose to do nothing
        )

    def get_phase_start_info(
        self, spieler: "Spieler", kontext: "SpielKontext"
    ) -> Optional[dict]:
        """Zeigt der Hexe das Werwolf-Opfer."""
        if kontext.werwolf_opfer_id:
            return {"werwolf_opfer_id": kontext.werwolf_opfer_id}
        return None

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Hexe verwendet einen Trank.
        Aktionstyp muss im Kontext oder separat übergeben werden?
        Die Basis-Logik ruft on_nacht_aktion auf.
        Wir müssen wissen WELCHE Aktion (heilen/vergiften).

        Das wird aktuell über `aktion_typ` im `registriere_aktion` Aufruf in `app.py` gehandhabt.
        Aber `on_nacht_aktion` bekommt das nicht direkt.

        Workaround: Wir schauen in `kontext.aktionen_diese_runde`? Nein, das sind vergangene.

        Lösung: `app.py` ruft `on_nacht_aktion` auf. Wir müssen `aktion_typ` irgendwie bekommen.
        Aktuell wird `aktion_typ` in `app.py` verwendet um `registriere_aktion` zu rufen.
        Aber `on_nacht_aktion` hat keine `aktion_typ` Parameter.

        Wir können `aktion_typ` aus dem Kontext holen? Nein.

        Wir müssen `on_nacht_aktion` erweitern oder `Role` anpassen?
        Oder wir nutzen `ziel` um zu raten?

        Wenn `ziel` == `werwolf_opfer` -> Heilen? Nein, man kann auch Opfer vergiften (theoretisch).

        Wir brauchen `aktion_typ`.

        Da wir `app.py` nicht ändern wollen/können (oder doch?),
        können wir `aktion_typ` nicht einfach hinzufügen.

        ABER: `app.py` ruft `verarbeite_aktion` auf, welches `aktion_typ` hat.
        Und `verarbeite_aktion` ruft `rolle_obj.on_nacht_aktion(spieler, ziel, kontext)` auf.

        Wir müssen `on_nacht_aktion` in `base.py` ändern, um `aktion_typ` zu akzeptieren?
        Oder wir packen `aktion_typ` in `kontext`?

        In `app.py`:
        ```python
        kontext = SpielKontext(..., aktionen_diese_runde=aktionen_liste)
        ```
        Es gibt kein Feld für "aktuelle Aktion".

        Wir können `on_nacht_aktion` überladen oder kwargs nutzen?
        `def on_nacht_aktion(self, spieler, ziel, kontext, **kwargs):`

        Aber `base.py` definiert es fest.

        Lösung: Wir ändern `base.py` Signatur von `on_nacht_aktion` um `aktion` (str) aufzunehmen.
        Das ist sauber.
        """
        # TODO: Refactor base.py to include action_type in on_nacht_aktion
        # For now, we assume app.py handles the logic or we infer it.
        # But wait, app.py calls `rolle_obj.on_nacht_aktion(spieler, ziel, kontext)`.
        # It does NOT pass action_type.

        # This is a problem for Hexe who has 2 actions.
        # Most roles have 1 action defined by `aktions_typ`.

        # Hexe needs to know if it's heal or poison.
        # Maybe we can check `ziel`.
        # If `ziel` is None -> Heal? (No, heal needs target too, usually the victim).
        # Actually, heal target is implicit (the victim).

        # Let's look at `app.py` again.
        # `verarbeite_aktion` calls `rolle_obj.on_nacht_aktion`.

        # I will modify `base.py` to accept `aktion: str = None`.
        pass

    def on_nacht_aktion_with_type(
        self,
        spieler: "Spieler",
        ziel: Optional["Spieler"],
        kontext: SpielKontext,
        aktion: str,
    ) -> Optional[AktionsErgebnis]:
        """
        Spezielle Methode für Hexe, die den Aktionstyp benötigt.
        Wird von app.py aufgerufen wenn wir base.py anpassen.
        """
        if aktion == "heilen":
            if not self.get_state(spieler, "heiltrank"):
                return AktionsErgebnis(False, "Du hast keinen Heiltrank mehr.")

            # Ziel ist das Werwolf-Opfer
            opfer_id = kontext.werwolf_opfer_id
            if not opfer_id:
                return AktionsErgebnis(False, "Es gibt kein Opfer zu heilen.")

            # Wenn Ziel übergeben wurde, muss es das Opfer sein
            if ziel and ziel.id != opfer_id:
                return AktionsErgebnis(False, "Du kannst nur das Werwolf-Opfer heilen.")

            self.set_state(spieler, "heiltrank", False)
            return AktionsErgebnis(
                True,
                "Du hast das Opfer geheilt.",
                ziel_spieler_id=opfer_id,
                effekte={"heilen": True, "hexe_heilen": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        elif aktion == "vergiften":
            if not self.get_state(spieler, "gifttrank"):
                return AktionsErgebnis(False, "Du hast keinen Gifttrank mehr.")

            if not ziel:
                return AktionsErgebnis(False, "Du musst ein Ziel wählen.")

            self.set_state(spieler, "gifttrank", False)
            return AktionsErgebnis(
                True,
                f"Du hast {ziel.name} vergiftet.",
                ziel_spieler_id=ziel.id,
                effekte={"vergiften": True, "hexe_vergiften": True},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        return None
