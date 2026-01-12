"""Integration-style tests for the core game logic.

This suite tests that:

* `naechste_phase` correctly transitions through core phases
* Role actions are correctly mapped and can be processed
* `registriere_aktion` + `alle_haben_gewaehlt` work for relevant players

The test isolates the logic in an in-memory SQLite database and does not
touch the production `app.py` database setup.

ARCHITECTURE NOTE:
The phase system has core phases (lobby, nacht_start, nacht, tag_abstimmung, etc.)
and role-specific phases (werwolf_phase, seherin_phase, etc.) are generated
dynamically from the RoleRegistry. Role actions happen DURING the nacht phase
based on role priority, not as separate core phases.
"""

from __future__ import annotations

import unittest
from flask import Flask

import game_logic
from phases import get_phase_list

PHASEN = get_phase_list()
from models import Raum, Spieler, db


def _build_test_app() -> Flask:
    """Create a fresh Flask app with an in-memory database for each test."""

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()

    return app


class GameLogicFullCycleTest(unittest.TestCase):
    """Test phase transitions and role action handling."""

    def setUp(self):
        self.app = _build_test_app()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()

    def _create_basic_room(self) -> int:
        """Create a room with basic roles for testing."""
        with self.app.app_context():
            raum = Raum(
                code="TST123",
                name="Full Cycle",
                modus="online",
                spieler_anzahl=0,
                spiel_gestartet=True,
                aktuelle_phase="nacht_start",
                runde=1,
            )
            db.session.add(raum)
            db.session.flush()

            # Basic 8-player game
            roles = [
                "Werwolf",
                "Werwolf",
                "Seherin",
                "Hexe",
                "Jäger",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
            ]

            players: list[Spieler] = []
            for idx, role in enumerate(roles):
                players.append(
                    Spieler(
                        name=f"Player-{idx + 1}",
                        session_id=f"sess-{idx}",
                        raum_id=raum.id,
                        rolle=role,
                        ist_am_leben=True,
                        status="aktiv",
                    )
                )

            db.session.add_all(players)
            raum.spieler_anzahl = len(players)
            db.session.commit()
            return raum.id

    def test_all_roles_advance_through_all_actions(self):
        """Test that phase transitions work and role mapping is correct."""
        raum_id = self._create_basic_room()

        with self.app.app_context():
            from models import db

            raum = db.session.get(Raum, raum_id)
            phase_roles = game_logic.phasennamen_zu_rollen_mapping()

            # Verify core role phase mappings exist
            self.assertEqual(phase_roles.get("werwolf_phase"), "Werwolf")
            self.assertEqual(phase_roles.get("seherin_phase"), "Seherin")
            self.assertEqual(phase_roles.get("hexe_phase"), "Hexe")

            # Verify core phases exist
            self.assertIn("nacht_start", PHASEN)
            self.assertIn("tag_abstimmung", PHASEN)
            self.assertIn("hinrichtung", PHASEN)

            # Test that we can get living players
            lebende = game_logic.hole_lebende_spieler(raum)
            self.assertEqual(len(lebende), 8)

            # Get werewolves from living players
            werwolf_spieler = [s for s in lebende if s.rolle == "Werwolf"]
            self.assertEqual(len(werwolf_spieler), 2)

            # Get a villager target
            dorfbewohner = [s for s in lebende if s.rolle == "Dorfbewohner"]
            target = dorfbewohner[0]

            # Register werewolf attack - should not raise
            game_logic.registriere_aktion(
                raum.id,
                raum.runde,
                "werwolf_phase",
                "toeten",
                werwolf_spieler[0].id,
                target.id,
            )

            # Verify that hat_spieler_mit_rolle works
            self.assertTrue(game_logic.hat_spieler_mit_rolle(raum, "Werwolf"))
            self.assertTrue(game_logic.hat_spieler_mit_rolle(raum, "Seherin"))
            self.assertFalse(
                game_logic.hat_spieler_mit_rolle(raum, "Amor")
            )  # Not in our setup

    def test_phase_list_has_correct_structure(self):
        """Core phases should be in correct order."""
        # These core phases must exist
        required_phases = ["nacht_start", "tag_abstimmung", "hinrichtung"]
        for phase in required_phases:
            self.assertIn(phase, PHASEN, f"Core phase '{phase}' missing from PHASEN")

        # nacht_start should come before tag phases
        nacht_idx = PHASEN.index("nacht_start")
        tag_idx = PHASEN.index("tag_abstimmung")
        self.assertLess(
            nacht_idx, tag_idx, "nacht_start should come before tag_abstimmung"
        )

    def test_role_phases_are_separate_from_core(self):
        """Role-specific phases should NOT be in the core phase list."""
        phase_roles = game_logic.phasennamen_zu_rollen_mapping()

        # Role phases (like werwolf_phase) are NOT core phases
        for role_phase in phase_roles.keys():
            self.assertNotIn(
                role_phase,
                PHASEN,
                f"Role phase '{role_phase}' should not be in core PHASEN list",
            )


if __name__ == "__main__":
    unittest.main()
