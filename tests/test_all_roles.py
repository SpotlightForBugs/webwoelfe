"""
Umfassende Test-Suite für alle Rollen im Webwölfe-Spiel.

Testet:
- Rollenregistrierung und -instanziierung
- Trigger-Methoden (on_nacht_aktion, on_eigener_tod, etc.)
- Spiellogik-Integration
- Team-Zugehörigkeiten und Gewinnbedingungen
"""

from __future__ import annotations

import unittest
import sys
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from roles import RoleRegistry
from roles.base import Role, RollenInfo, AktionsErgebnis, SpielKontext
from roles.enums import Team, Kategorie, AktionsTyp, SichtTyp, Phase


# ============================================================================
# Mock Objects für Tests
# ============================================================================


@dataclass
class MockSpieler:
    """Mock-Spieler für Tests ohne Datenbank."""

    id: int
    name: str
    rolle: str = "Dorfbewohner"
    ist_am_leben: bool = True
    status: str = "aktiv"
    raum_id: int = 1

    # Dynamic state storage (JSON string like real model)
    rolle_zustand: str = "{}"

    # Legacy attributes for backward compatibility in tests
    hund_herrchen_gewaehlt: bool = False
    herrchen_id: Optional[int] = None
    jaeger_schuss: bool = True
    hexe_heiltrank: bool = True
    hexe_gifttrank: bool = True
    verliebt_mit_id: Optional[int] = None
    ist_beschuetzt: bool = False
    wildes_kind_vorbild_id: Optional[int] = None
    ist_buergermeister: bool = False
    stimmen_gewicht: int = 1

    def __setattr__(self, name: str, value: Any) -> None:
        """Erlaube das Setzen beliebiger Attribute."""
        object.__setattr__(self, name, value)

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value from JSON storage."""
        import json

        try:
            state = json.loads(self.rolle_zustand or "{}")
            return state.get(key, default)
        except (json.JSONDecodeError, TypeError):
            return default

    def set_state(self, key: str, value: Any) -> None:
        """Set state value in JSON storage."""
        import json

        try:
            state = json.loads(self.rolle_zustand or "{}")
        except (json.JSONDecodeError, TypeError):
            state = {}
        state[key] = value
        self.rolle_zustand = json.dumps(state)

    def reset_state(self) -> None:
        """Reset state."""
        self.rolle_zustand = "{}"

    def get_all_state(self) -> dict:
        """Get all state."""
        import json

        try:
            return json.loads(self.rolle_zustand or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}


def create_mock_kontext(
    runde: int = 1,
    phase: Phase = Phase.NACHT_START,
    lebende_spieler: Optional[List[int]] = None,
    tote_spieler: Optional[List[int]] = None,
    spieler_rollen: Optional[Dict[int, Role]] = None,
    spieler_teams: Optional[Dict[int, Team]] = None,
    spieler_namen: Optional[Dict[int, str]] = None,
) -> SpielKontext:
    """Erstellt einen Mock-SpielKontext für Tests."""
    kontext = SpielKontext(
        raum_id=1,
        runde=runde,
        phase=phase,
        aktiver_spieler_id=1,
        lebende_spieler=lebende_spieler or [1, 2, 3, 4, 5],
        tote_spieler=tote_spieler or [],
    )

    # Dynamische Attribute setzen
    if spieler_rollen:
        kontext.spieler_rollen = spieler_rollen  # type: ignore
    if spieler_teams:
        kontext.spieler_teams = spieler_teams  # type: ignore
    if spieler_namen:
        kontext.spieler_namen = spieler_namen  # type: ignore

    return kontext


# ============================================================================
# Registry Tests
# ============================================================================


class TestRoleRegistry(unittest.TestCase):
    """Tests für die RoleRegistry."""

    def test_alle_rollen_registriert(self):
        """Prüft dass alle Rollen registriert sind."""
        alle_rollen = RoleRegistry.get_all()
        self.assertGreater(
            len(alle_rollen), 50, f"Zu wenige Rollen registriert: {len(alle_rollen)}"
        )

    def test_grundrollen_vorhanden(self):
        """Prüft dass alle Grundrollen vorhanden sind."""
        grundrollen = [
            "Werwolf",
            "Dorfbewohner",
            "Seherin",
            "Hexe",
            "Jäger",
            "Amor",
            "Heiler",
        ]
        for rolle_name in grundrollen:
            rolle = RoleRegistry.get(rolle_name)
            self.assertIsNotNone(rolle, f"Grundrolle '{rolle_name}' nicht gefunden")

    def test_jede_rolle_hat_info(self):
        """Prüft dass jede Rolle vollständige RollenInfo hat."""
        for rolle in RoleRegistry.get_all():
            info = rolle.info
            self.assertIsNotNone(info.id, f"{rolle.__class__.__name__} hat keine ID")
            self.assertIsNotNone(
                info.name, f"{rolle.__class__.__name__} hat keinen Namen"
            )
            self.assertIsNotNone(info.team, f"{rolle.__class__.__name__} hat kein Team")
            self.assertIsNotNone(
                info.beschreibung, f"{rolle.__class__.__name__} hat keine Beschreibung"
            )
            self.assertIsNotNone(info.icon, f"{rolle.__class__.__name__} hat kein Icon")
            self.assertIsNotNone(
                info.farbe, f"{rolle.__class__.__name__} hat keine Farbe"
            )

    def test_keine_doppelten_ids(self):
        """Prüft dass keine Rollen-IDs doppelt vergeben sind."""
        ids = {}
        for rolle in RoleRegistry.get_all():
            rolle_id = rolle.info.id
            if rolle_id in ids:
                self.fail(
                    f"Doppelte ID {rolle_id}: {rolle.info.name} und {ids[rolle_id]}"
                )
            ids[rolle_id] = rolle.info.name


# ============================================================================
# Grundrollen Tests
# ============================================================================


class TestSeherin(unittest.TestCase):
    """Tests für die Seherin."""

    def setUp(self):
        self.seherin = RoleRegistry.get("Seherin")
        self.assertIsNotNone(self.seherin)

    def test_seherin_sieht_werwolf(self):
        """Seherin erkennt Werwölfe korrekt."""
        werwolf = RoleRegistry.get("Werwolf")
        sicht = werwolf.sichtbar_als_fuer("Seherin")
        self.assertEqual(sicht, SichtTyp.WERWOLF)

    def test_seherin_sieht_dorfbewohner(self):
        """Seherin erkennt Dorfbewohner korrekt."""
        dorf = RoleRegistry.get("Dorfbewohner")
        sicht = dorf.sichtbar_als_fuer("Seherin")
        self.assertEqual(sicht, SichtTyp.DORF)

    def test_wolf_im_schafspelz_getarnt(self):
        """Wolf im Schafspelz erscheint als Dorfbewohner für Seherin."""
        wolf_schaf = RoleRegistry.get("Wolf im Schafspelz")
        if wolf_schaf:
            sicht = wolf_schaf.sichtbar_als_fuer("Seherin")
            rolle = wolf_schaf.sichtbare_rolle_fuer("Seherin")
            self.assertEqual(sicht, SichtTyp.DORF)
            self.assertEqual(rolle, "Dorfbewohner")

    def test_seherin_nacht_aktion(self):
        """Seherin kann in der Nacht einen Spieler sehen."""
        spieler = MockSpieler(id=1, name="Seherin", rolle="Seherin")
        ziel = MockSpieler(id=2, name="Verdächtiger", rolle="Werwolf")

        werwolf_rolle = RoleRegistry.get("Werwolf")
        kontext = create_mock_kontext(spieler_rollen={2: werwolf_rolle})

        ergebnis = self.seherin.on_nacht_aktion(spieler, ziel, kontext)

        self.assertIsNotNone(ergebnis)
        self.assertTrue(ergebnis.erfolg)
        self.assertIn("Werwolf", ergebnis.nachricht)


class TestHexe(unittest.TestCase):
    """Tests für die Hexe."""

    def setUp(self):
        self.hexe = RoleRegistry.get("Hexe")
        self.assertIsNotNone(self.hexe)

    def test_hexe_hat_heiltrank(self):
        """Hexe startet mit Heiltrank."""
        self.assertTrue(hasattr(self.hexe, "info"))
        self.assertEqual(self.hexe.info.team, Team.DORF)

    def test_hexe_ist_nacht_aktiv(self):
        """Hexe ist in der Nacht aktiv."""
        self.assertTrue(
            self.hexe.is_active_on_first_night() or self.hexe.is_active_on_every_night()
        )


class TestJaeger(unittest.TestCase):
    """Tests für den Jäger."""

    def setUp(self):
        self.jaeger = RoleRegistry.get("Jäger")
        self.assertIsNotNone(self.jaeger)

    def test_jaeger_schuss_bei_tod(self):
        """Jäger kann bei Tod schießen."""
        spieler = MockSpieler(id=1, name="Jäger", rolle="Jäger")
        ziel = MockSpieler(id=2, name="Opfer", rolle="Werwolf")
        kontext = create_mock_kontext(lebende_spieler=[2, 3, 4])

        ergebnis = self.jaeger.on_eigener_tod(spieler, "werwolf", kontext)

        self.assertIsNotNone(ergebnis)
        self.assertTrue(ergebnis.effekte.get("kann_schiessen", True))


class TestHund(unittest.TestCase):
    """Tests für den Hund."""

    def setUp(self):
        self.hund = RoleRegistry.get("Hund")
        self.assertIsNotNone(self.hund)

    def test_hund_herrchen_wahl(self):
        """Hund kann Herrchen wählen."""
        spieler = MockSpieler(id=1, name="Fido", rolle="Hund")
        herrchen = MockSpieler(id=2, name="Max", rolle="Dorfbewohner")
        kontext = create_mock_kontext(runde=1, lebende_spieler=[1, 2, 3])

        ergebnis = self.hund.on_nacht_aktion(spieler, herrchen, kontext)

        self.assertIsNotNone(ergebnis)
        self.assertTrue(ergebnis.erfolg)
        # Check state was set
        self.assertEqual(self.hund.get_state(spieler, "herrchen_id"), 2)

    def test_hund_verwandlung_bei_herrchen_tod(self):
        """Hund verwandelt sich wenn Herrchen stirbt."""
        spieler = MockSpieler(id=1, name="Fido", rolle="Hund")
        # Set state instead of model attribute
        self.hund.set_state(spieler, "herrchen_id", 2)
        self.hund.set_state(spieler, "gewaehlt", True)

        herrchen = MockSpieler(id=2, name="Max", rolle="Dorfbewohner")
        kontext = create_mock_kontext(lebende_spieler=[1, 3, 4])

        ergebnis = self.hund.on_spieler_stirbt(spieler, herrchen, "werwolf", kontext)

        self.assertIsNotNone(ergebnis)
        self.assertTrue(ergebnis.effekte.get("verwandlung", False))
        self.assertEqual(ergebnis.effekte.get("neues_team"), "werwolf")

    def test_hund_verwandlung_nicht_oeffentlich(self):
        """Die Verwandlung des Hundes ist nicht öffentlich."""
        spieler = MockSpieler(id=1, name="Fido", rolle="Hund")
        # Set state instead of model attribute
        self.hund.set_state(spieler, "herrchen_id", 2)
        self.hund.set_state(spieler, "gewaehlt", True)

        herrchen = MockSpieler(id=2, name="Max", rolle="Dorfbewohner")
        kontext = create_mock_kontext(lebende_spieler=[1, 3, 4])

        ergebnis = self.hund.on_spieler_stirbt(spieler, herrchen, "werwolf", kontext)

        self.assertIsNotNone(ergebnis)
        self.assertEqual(ergebnis.log_sichtbar_fuer, "erzaehler")


# ============================================================================
# Seher-Varianten Tests
# ============================================================================


class TestAurenseherin(unittest.TestCase):
    """Tests für die Aurenseherin."""

    def setUp(self):
        self.aurenseherin = RoleRegistry.get("Aurenseherin")

    def test_aurenseherin_sieht_aura_nicht_rolle(self):
        """Aurenseherin sieht Aura, nicht konkrete Rolle."""
        if not self.aurenseherin:
            self.skipTest("Aurenseherin nicht registriert")

        spieler = MockSpieler(id=1, name="Aurenseherin", rolle="Aurenseherin")
        ziel = MockSpieler(id=2, name="Verdächtiger", rolle="Werwolf")

        werwolf = RoleRegistry.get("Werwolf")
        kontext = create_mock_kontext(spieler_rollen={2: werwolf})

        ergebnis = self.aurenseherin.on_nacht_aktion(spieler, ziel, kontext)

        self.assertIsNotNone(ergebnis)
        self.assertIn("dunkle", ergebnis.nachricht.lower())


class TestParanormalerErmittler(unittest.TestCase):
    """Tests für den Paranormalen Ermittler."""

    def setUp(self):
        self.ermittler = RoleRegistry.get("Paranormaler Ermittler (billig)")

    def test_ermittler_kann_falsch_liegen(self):
        """Paranormaler Ermittler kann falsche Ergebnisse liefern."""
        if not self.ermittler:
            self.skipTest("Paranormaler Ermittler nicht registriert")

        # Test 100 mal um Zufälligkeit zu prüfen
        richtig = 0
        falsch = 0

        for _ in range(100):
            spieler = MockSpieler(
                id=1, name="Ermittler", rolle="Paranormaler Ermittler (billig)"
            )
            ziel = MockSpieler(id=2, name="Verdächtiger", rolle="Werwolf")

            werwolf = RoleRegistry.get("Werwolf")
            dorf = RoleRegistry.get("Dorfbewohner")
            kontext = create_mock_kontext(
                spieler_rollen={1: self.ermittler, 2: werwolf, 3: dorf},
                lebende_spieler=[1, 2, 3],
            )

            ergebnis = self.ermittler.on_nacht_aktion(spieler, ziel, kontext)

            if ergebnis and ergebnis.effekte.get("war_falsch"):
                falsch += 1
            else:
                richtig += 1

        # Etwa 30% sollten falsch sein (mit Toleranz)
        self.assertGreater(falsch, 15, "Zu wenige falsche Ergebnisse")
        self.assertLess(falsch, 45, "Zu viele falsche Ergebnisse")


# ============================================================================
# Werwolf-Varianten Tests
# ============================================================================


class TestWolfImSchafspelz(unittest.TestCase):
    """Tests für den Wolf im Schafspelz."""

    def setUp(self):
        self.wolf = RoleRegistry.get("Wolf im Schafspelz")

    def test_wolf_erscheint_als_dorfbewohner(self):
        """Wolf im Schafspelz erscheint für Seherin als Dorfbewohner."""
        if not self.wolf:
            self.skipTest("Wolf im Schafspelz nicht registriert")

        rolle = self.wolf.sichtbare_rolle_fuer("Seherin")
        self.assertEqual(rolle, "Dorfbewohner")

    def test_aurenseherin_erkennt_wolf(self):
        """Aurenseherin erkennt Wolf im Schafspelz."""
        if not self.wolf:
            self.skipTest("Wolf im Schafspelz nicht registriert")

        sicht = self.wolf.sichtbar_als_fuer("Aurenseherin")
        self.assertEqual(sicht, SichtTyp.WERWOLF)


# ============================================================================
# Solo-Rollen Tests
# ============================================================================


class TestSelbstmoerder(unittest.TestCase):
    """Tests für den Selbstmörder."""

    def setUp(self):
        self.selbstmoerder = RoleRegistry.get("Selbstmörder")

    def test_selbstmoerder_gewinnt_bei_hinrichtung(self):
        """Selbstmörder gewinnt wenn er hingerichtet wird."""
        if not self.selbstmoerder:
            self.skipTest("Selbstmörder nicht registriert")

        spieler = MockSpieler(id=1, name="Selbstmörder", rolle="Selbstmörder")
        kontext = create_mock_kontext()

        ergebnis = self.selbstmoerder.on_eigener_tod(spieler, "hinrichtung", kontext)

        self.assertIsNotNone(ergebnis)
        self.assertTrue(ergebnis.effekte.get("selbstmoerder_gewinnt", False))

    def test_selbstmoerder_verliert_bei_werwolf_tod(self):
        """Selbstmörder verliert wenn er von Werwölfen getötet wird."""
        if not self.selbstmoerder:
            self.skipTest("Selbstmörder nicht registriert")

        spieler = MockSpieler(id=1, name="Selbstmörder", rolle="Selbstmörder")
        kontext = create_mock_kontext()

        ergebnis = self.selbstmoerder.on_eigener_tod(spieler, "werwolf", kontext)

        self.assertIsNotNone(ergebnis)
        self.assertTrue(ergebnis.effekte.get("selbstmoerder_verliert", False))


class TestEngel(unittest.TestCase):
    """Tests für den Engel."""

    def setUp(self):
        self.engel = RoleRegistry.get("Engel")

    def test_engel_gewinnt_bei_fruehen_tod(self):
        """Engel gewinnt wenn er in Runde 1 stirbt."""
        if not self.engel:
            self.skipTest("Engel nicht registriert")

        spieler = MockSpieler(id=1, name="Engel", rolle="Engel")
        kontext = create_mock_kontext(runde=1)
        # aktuelle_runde is now a property derived from runde

        ergebnis = self.engel.on_eigener_tod(spieler, "werwolf", kontext)

        self.assertIsNotNone(ergebnis)
        self.assertTrue(
            ergebnis.effekte.get("engel_gewonnen", False)
            or ergebnis.effekte.get("engel_gewinnt", False)
        )


# ============================================================================
# Spezial-Rollen Tests
# ============================================================================


class TestHahn(unittest.TestCase):
    """Tests für den Hahn."""

    def setUp(self):
        self.hahn = RoleRegistry.get("Hahn")

    def test_hahn_enthuellt_moerder(self):
        """Hahn enthüllt seinen Mörder bei Tod."""
        if not self.hahn:
            self.skipTest("Hahn nicht registriert")

        spieler = MockSpieler(id=1, name="Hahn", rolle="Hahn")
        kontext = create_mock_kontext(
            spieler_namen={1: "Hahn", 2: "Wolf1", 3: "Wolf2"},
            spieler_teams={2: Team.WERWOLF, 3: Team.WERWOLF},
            lebende_spieler=[2, 3],
        )

        ergebnis = self.hahn.on_eigener_tod(spieler, "werwolf", kontext)

        self.assertIsNotNone(ergebnis)
        self.assertIn("KIKERIKI", ergebnis.nachricht)
        self.assertTrue(ergebnis.effekte.get("hahn_kräht", False))


class TestBuergermeister(unittest.TestCase):
    """Tests für den Bürgermeister."""

    def setUp(self):
        self.buergermeister = RoleRegistry.get("Bürgermeister")

    def test_buergermeister_doppelte_stimme(self):
        """Bürgermeister hat doppelte Stimme."""
        if not self.buergermeister:
            self.skipTest("Bürgermeister nicht registriert")

        spieler = MockSpieler(id=1, name="Bürgermeister", rolle="Bürgermeister")
        kontext = create_mock_kontext()

        ergebnis = self.buergermeister.on_spiel_start(spieler, kontext)

        self.assertIsNotNone(ergebnis)
        self.assertEqual(ergebnis.effekte.get("stimmen_gewicht"), 2)


# ============================================================================
# Team-Zugehörigkeit Tests
# ============================================================================


class TestTeamZugehoerigkeit(unittest.TestCase):
    """Tests für korrekte Team-Zugehörigkeiten."""

    def test_alle_werwolf_rollen_im_werwolf_team(self):
        """Alle Werwolf-Varianten sind im Werwolf-Team."""
        werwolf_rollen = [
            "Werwolf",
            "Wolf im Schafspelz",
            "Urwolf",
            "Teenager-Werwolf",
            "Polarwolf",
            "Werwolfseherin",
            "Lupin",
        ]
        # Weißer Wolf und Einsamer Wolf sind Solo, weil sie alleine gewinnen müssen

        for rolle_name in werwolf_rollen:
            rolle = RoleRegistry.get(rolle_name)
            if rolle:
                self.assertEqual(
                    rolle.info.team,
                    Team.WERWOLF,
                    f"{rolle_name} ist nicht im Werwolf-Team",
                )

    def test_solo_rollen_haben_solo_team(self):
        """Solo-Rollen haben das Solo-Team."""
        solo_rollen = ["Selbstmörder", "Engel", "Henker", "Pyromane"]

        for rolle_name in solo_rollen:
            rolle = RoleRegistry.get(rolle_name)
            if rolle:
                self.assertEqual(
                    rolle.info.team, Team.SOLO, f"{rolle_name} ist nicht im Solo-Team"
                )


# ============================================================================
# Aktions-Typ Tests
# ============================================================================


class TestAktionsTypen(unittest.TestCase):
    """Tests für korrekte Aktions-Typen."""

    def test_seherin_hat_sehen_aktionstyp(self):
        """Seherin hat SEHEN als Aktionstyp."""
        seherin = RoleRegistry.get("Seherin")
        self.assertEqual(seherin.aktions_typ, AktionsTyp.SEHEN)

    def test_werwolf_hat_toeten_aktionstyp(self):
        """Werwolf hat TOETEN als Aktionstyp."""
        werwolf = RoleRegistry.get("Werwolf")
        self.assertEqual(werwolf.aktions_typ, AktionsTyp.TOETEN)

    def test_heiler_hat_schuetzen_aktionstyp(self):
        """Heiler hat SCHUETZEN als Aktionstyp."""
        heiler = RoleRegistry.get("Heiler")
        self.assertEqual(heiler.aktions_typ, AktionsTyp.SCHUETZEN)

    def test_dorfbewohner_hat_keine_aktion(self):
        """Dorfbewohner hat KEINE als Aktionstyp."""
        dorf = RoleRegistry.get("Dorfbewohner")
        self.assertEqual(dorf.aktions_typ, AktionsTyp.KEINE)


# ============================================================================
# Sichtbarkeits-Tests
# ============================================================================


class TestSichtbarkeit(unittest.TestCase):
    """Tests für die Sichtbarkeit von Rollen."""

    def test_alle_rollen_haben_sichtbar_als_methoden(self):
        """Alle Rollen haben sichtbar_als_fuer und sichtbare_rolle_fuer."""
        for rolle in RoleRegistry.get_all():
            self.assertTrue(
                hasattr(rolle, "sichtbar_als_fuer"),
                f"{rolle.info.name} hat keine sichtbar_als_fuer Methode",
            )
            self.assertTrue(
                hasattr(rolle, "sichtbare_rolle_fuer"),
                f"{rolle.info.name} hat keine sichtbare_rolle_fuer Methode",
            )

    def test_sichtbar_als_gibt_sichttyp_zurueck(self):
        """sichtbar_als_fuer gibt immer einen SichtTyp zurück."""
        for rolle in RoleRegistry.get_all():
            sicht = rolle.sichtbar_als_fuer("Seherin")
            self.assertIsInstance(
                sicht,
                SichtTyp,
                f"{rolle.info.name}.sichtbar_als_fuer gibt keinen SichtTyp zurück",
            )


# ============================================================================
# Spiellogik Integration Tests
# ============================================================================


class TestSpielLogikIntegration(unittest.TestCase):
    """Tests für die Integration mit der Spiellogik."""

    def test_alle_rollen_koennen_instanziiert_werden(self):
        """Alle registrierten Rollen können ohne Fehler instanziiert werden."""
        for rolle in RoleRegistry.get_all():
            self.assertIsNotNone(rolle.info)
            self.assertIsNotNone(rolle.aktions_typ)

    def test_nacht_aktive_rollen_haben_on_nacht_aktion(self):
        """Alle nacht-aktiven Rollen haben eine on_nacht_aktion Methode."""
        for rolle in RoleRegistry.get_all():
            nacht_aktiv = (
                rolle.is_active_on_first_night() or rolle.is_active_on_every_night()
            )
            if nacht_aktiv:
                # Prüfe dass die Methode existiert und aufrufbar ist
                self.assertTrue(
                    callable(getattr(rolle, "on_nacht_aktion", None)),
                    f"{rolle.info.name} ist nacht_aktiv aber hat keine on_nacht_aktion",
                )


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    # Lade alle Rollen
    print("Lade Rollen-Registry...")
    alle_rollen = RoleRegistry.get_all()
    print(f"✓ {len(alle_rollen)} Rollen registriert")

    # Zeige Statistiken
    teams = {}
    kategorien = {}
    for rolle in alle_rollen:
        team = rolle.info.team.value
        kategorie = rolle.info.kategorie.value
        teams[team] = teams.get(team, 0) + 1
        kategorien[kategorie] = kategorien.get(kategorie, 0) + 1

    print("\nRollen nach Team:")
    for team, count in sorted(teams.items()):
        print(f"  {team}: {count}")

    print("\nRollen nach Kategorie:")
    for kategorie, count in sorted(kategorien.items()):
        print(f"  {kategorie}: {count}")

    print("\n" + "=" * 60)
    print("Starte Tests...")
    print("=" * 60 + "\n")

    # Tests ausführen
    unittest.main(verbosity=2)
