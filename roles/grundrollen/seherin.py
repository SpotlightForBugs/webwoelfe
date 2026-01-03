"""
Seherin - Die wichtigste Informationsrolle des Dorfes.

Die Seherin kann jede Nacht die wahre Identität
eines Spielers erfahren.
"""

from typing import Optional, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp, SichtTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Seherin(Role):
    """
    Die Seherin - Informationsrolle.

    Fähigkeiten:
    - Kann jede Nacht einen Spieler "sehen"
    - Erfährt ob das Ziel Werwolf oder Dorf ist

    Gewinnbedingung: Dorf gewinnt.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=3,
            name="Seherin",
            team=Team.DORF,
            kategorie=Kategorie.GRUNDROLLEN,
            beschreibung=(
                "Du bist die Seherin. Jede Nacht kannst du die wahre Identität "
                "eines Spielers erfahren - ob er ein Werwolf ist oder nicht."
            ),
            icon="fa-solid fa-eye",
            farbe="#7c3aed",
            nacht_aktiv=True,
            prioritaet=20,
            erzaehler_nacht=(
                "Die Seherin erwacht und zeigt auf einen Spieler. "
                "Du zeigst ihr mit Daumen hoch (Dorf) oder runter (Werwolf) "
                "die Zugehörigkeit."
            ),
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.SEHEN

    @property
    def erlaubte_ziele(self) -> str:
        return "andere"  # Kann sich nicht selbst sehen

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Seherin sieht die vollständige Rolle eines Spielers.

        Die Seherin erfährt:
        - Den genauen Rollennamen (z.B. "Hexe", "Werwolf", "Hund")
        - Das Team der Rolle (basierend auf sichtbar_als)

        Einige Rollen können sich tarnen (sichtbar_als != tatsächliches Team).

        WICHTIG: Das Ergebnis wird als SNAPSHOT gespeichert.
        Auch wenn sich die Rolle später ändert (z.B. Infektion),
        sieht die Seherin weiterhin das ursprüngliche Ergebnis.
        """
        if ziel is None:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du musst einen Spieler wählen.",
            )

        if not self.validate_ziel(spieler, ziel, kontext):
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Ungültiges Ziel.",
            )

        # Hole die Rolle des Ziels
        from ..registry import RoleRegistry

        ziel_rolle = RoleRegistry.get(ziel.rolle)

        if ziel_rolle:
            sicht = ziel_rolle.sichtbar_als_fuer(self.info.name)
            rollen_name = ziel_rolle.sichtbare_rolle_fuer(self.info.name)
            team = ziel_rolle.info.team
        else:
            # Fallback für unbekannte Rollen
            sicht = SichtTyp.DORF
            rollen_name = ziel.rolle or "Unbekannt"
            team = Team.DORF

        ist_werwolf = sicht == SichtTyp.WERWOLF
        enthuellung_typ = "boese" if ist_werwolf else "gut"

        # Speichere als SNAPSHOT - wichtig für spätere Rollenänderungen
        try:
            from models import SeherinEnthuellung, Raum

            raum = Raum.query.get(spieler.raum_id)
            if raum:
                SeherinEnthuellung.speichere_enthuellung(
                    seherin_id=spieler.id,
                    ziel_id=ziel.id,
                    raum_id=raum.id,
                    enthuellung_typ=enthuellung_typ,
                    rolle=rollen_name,
                    runde=raum.runde,
                )
        except Exception as e:
            # Fehler beim Speichern sollte die Aktion nicht blockieren
            print(f"Warnung: Konnte Seherin-Enthüllung nicht speichern: {e}")

        # Nachricht mit vollständiger Rolleninformation
        if ist_werwolf:
            nachricht = f"{ziel.name} ist ein {rollen_name}! (Werwolf-Team)"
        else:
            nachricht = f"{ziel.name} ist ein {rollen_name}. (Dorf-Team)"

        return AktionsErgebnis(
            erfolg=True,
            nachricht=nachricht,
            ziel_spieler_id=ziel.id,
            effekte={
                "gesehen": ziel.id,
                "rolle": rollen_name,
                "ist_werwolf": ist_werwolf,
                "sicht_typ": sicht.value,
                "team": team.value,
                "snapshot": True,  # Markiert dass dies ein Snapshot ist
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )
