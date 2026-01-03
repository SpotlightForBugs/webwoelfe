"""
Pyromane - Der Brandstifter (Solo).

Der Pyromane kann Häuser mit Benzin übergießen
und dann alle anzünden. Die Nachbarn sterben mit.
"""

from typing import Optional, List, TYPE_CHECKING
from ..base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from ..enums import Team, Kategorie, AktionsTyp
from ..registry import RoleRegistry

if TYPE_CHECKING:
    from models import Spieler


@RoleRegistry.register
class Pyromane(Role):
    """
    Pyromane - Solo-Killer mit Flächenschaden.

    Fähigkeiten:
    - Jede Nacht: Ein Haus mit Benzin übergießen
    - Einmal pro Spiel: Alle übergossenen Häuser anzünden
    - Feuer tötet auch Nachbarn

    Besonderheiten:
    - Solo-Rolle, gewinnt alleine
    - Strategie: Viele Häuser übergießen, dann zünden
    - Sehr mächtig bei vielen Zielen

    Gewinnbedingung: Pyromane als einziger übrig.
    """

    @property
    def info(self) -> RollenInfo:
        return RollenInfo(
            id=58,
            name="Pyromane",
            team=Team.SOLO,
            kategorie=Kategorie.JAEGER,
            beschreibung=(
                "Du bist der Pyromane. Jede Nacht kannst du ein Haus mit "
                "Benzin übergießen. Einmal pro Spiel kannst du alle "
                "übergossenen Häuser anzünden - das Feuer tötet auch die "
                "NACHBARN (links und rechts)!"
            ),
            icon="fa-solid fa-fire-flame-curved",
            farbe="#f97316",
            nacht_aktiv=True,
            prioritaet=75,
            erzaehler_nacht=(
                "Der Pyromane erwacht. Möchtest du ein Haus mit Benzin "
                "übergießen - oder alle übergossenen Häuser ANZÜNDEN?"
            ),
            erzaehler_tag=(
                "FEUER! Der Pyromane hat zugeschlagen! Die Flammen "
                "verschlingen die Opfer und breiten sich auf die "
                "Nachbarhäuser aus!"
            ),
            hinweis_config=None,
        )

    @property
    def aktions_typ(self) -> AktionsTyp:
        return AktionsTyp.TOETEN

    @property
    def erlaubte_ziele(self) -> str:
        return "lebende"

    def on_nacht_aktion(
        self, spieler: "Spieler", ziel: Optional["Spieler"], kontext: SpielKontext
    ) -> Optional[AktionsErgebnis]:
        """
        Pyromane kann übergießen oder anzünden.

        Aktion wird durch extra Parameter bestimmt:
        - "uebergiessen": Haus markieren
        - "anzuenden": Alle markierten Häuser anzünden
        """
        # Übergossene Häuser abrufen
        uebergossene: List[int] = getattr(spieler, "pyromane_uebergossen", [])
        kann_zuenden = not getattr(spieler, "pyromane_gezuendet", False)

        # Prüfen ob Ziel "anzuenden" ist (spezieller Wert)
        aktion = getattr(spieler, "pyromane_aktion", "uebergiessen")

        if aktion == "anzuenden":
            return self._anzuenden(spieler, uebergossene, kann_zuenden, kontext)
        else:
            return self._uebergiessen(spieler, ziel, uebergossene, kontext)

    def _uebergiessen(
        self,
        spieler: "Spieler",
        ziel: Optional["Spieler"],
        uebergossene: List[int],
        kontext: SpielKontext,
    ) -> AktionsErgebnis:
        """Übergießt ein Haus mit Benzin."""
        if ziel is None:
            return AktionsErgebnis(
                erfolg=True,
                nachricht=f"Du bereitest dich vor. Aktuell {len(uebergossene)} Häuser übergossen.",
                effekte={},
                log_sichtbar_fuer=f"spieler_{spieler.id}",
            )

        if ziel.id in uebergossene:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Dieses Haus ist bereits mit Benzin übergossen!",
            )

        uebergossene.append(ziel.id)
        spieler.pyromane_uebergossen = uebergossene

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"Du übergießt das Haus von {ziel.name} mit Benzin. "
            f"Insgesamt {len(uebergossene)} Häuser markiert.",
            ziel_spieler_id=ziel.id,
            effekte={
                "uebergossen": ziel.id,
                "anzahl_uebergossen": len(uebergossene),
            },
            log_sichtbar_fuer=f"spieler_{spieler.id}",
        )

    def _anzuenden(
        self,
        spieler: "Spieler",
        uebergossene: List[int],
        kann_zuenden: bool,
        kontext: SpielKontext,
    ) -> AktionsErgebnis:
        """Zündet alle übergossenen Häuser an."""
        if not kann_zuenden:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast dein Feuer bereits entfacht!",
            )

        if not uebergossene:
            return AktionsErgebnis(
                erfolg=False,
                nachricht="Du hast noch kein Haus übergossen!",
            )

        spieler.pyromane_gezuendet = True

        # Alle übergossenen Häuser + deren Nachbarn
        opfer_ids = set(uebergossene)

        # Nachbarn ermitteln für jedes übergossene Haus
        if hasattr(kontext, "sitzreihenfolge") and kontext.sitzreihenfolge:
            sitz = kontext.sitzreihenfolge
            for opfer_id in list(uebergossene):
                try:
                    idx = sitz.index(opfer_id)
                    links_idx = (idx - 1) % len(sitz)
                    rechts_idx = (idx + 1) % len(sitz)
                    opfer_ids.add(sitz[links_idx])
                    opfer_ids.add(sitz[rechts_idx])
                except (ValueError, IndexError):
                    pass

        # Tote entfernen
        opfer_ids = [oid for oid in opfer_ids if oid not in kontext.tote_spieler]

        return AktionsErgebnis(
            erfolg=True,
            nachricht=f"INFERNO! Du zündest {len(uebergossene)} Häuser an! "
            f"{len(opfer_ids)} Spieler verbrennen (inkl. Nachbarn)!",
            effekte={
                "feuer_toetet": list(opfer_ids),
                "pyromane_gezuendet": True,
                "todesursache": "verbrennung",
            },
            log_sichtbar_fuer="alle",
        )
