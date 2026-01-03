"""Integration-style tests for the core game logic.

This suite builds a large room with every role that unlocks a dedicated
phase so we can assert that:

* `naechste_phase` does not skip any night/day steps when the matching role
  exists.
* `registriere_aktion` + `alle_haben_gewaehlt` can record inputs from all
  relevant players in heavy games.

The test isolates the logic in an in-memory SQLite database and does not
touch the production `app.py` database setup.
"""

from __future__ import annotations

import unittest
from flask import Flask

import game_logic
from game_logic import PHASEN
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
    """Walk through every phase with all matching roles present."""

    def setUp(self):
        self.app = _build_test_app()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()

    def _create_full_room(self) -> int:
        """Populate a room with one player for each mapped phase role."""

        phase_roles = game_logic.phasennamen_zu_rollen_mapping()

        # Minimum counts for roles that should appear as groups.
        special_counts = {
            "Zwei Schwestern": 2,
            "Drei Brüder": 3,
            "Freimaurer": 3,
            "Werwolf": 2,  # Keeps the wolf phase meaningful.
        }

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

            players: list[Spieler] = []

            for role in sorted(set(phase_roles.values())):
                count = special_counts.get(role, 1)
                for idx in range(count):
                    players.append(
                        Spieler(
                            name=f"{role}-{idx + 1}",
                            session_id=f"sess-{role}-{idx}",
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
        raum_id = self._create_full_room()
        expected_order = PHASEN[
            PHASEN.index("dieb_phase") : PHASEN.index("tag_ende") + 1
        ]

        with self.app.app_context():
            raum = Raum.query.get(raum_id)
            visited: list[str] = []
            phase_roles = game_logic.phasennamen_zu_rollen_mapping()

            # Ensure every mapped action belongs to a known phase and key role gates the wolf attack.
            self.assertTrue(set(phase_roles.keys()).issubset(set(PHASEN)))
            self.assertEqual(phase_roles.get("werwolf_phase"), "Werwolf")

            for _ in range(len(expected_order)):
                next_phase = game_logic.naechste_phase(raum)
                visited.append(next_phase)

                acting_role = phase_roles.get(next_phase)
                if acting_role:
                    actors = game_logic.hole_spieler_fuer_rolle(raum, acting_role)
                else:
                    actors = game_logic.hole_lebende_spieler(raum)

                # Register one action per actor to mimic a busy round.
                for actor in actors:
                    target_id = actors[0].id if actors else None
                    game_logic.registriere_aktion(
                        raum.id,
                        raum.runde,
                        next_phase,
                        "test_action",
                        actor.id,
                        target_id,
                    )

                self.assertTrue(
                    game_logic.alle_haben_gewaehlt(
                        raum, next_phase, acting_role if acting_role else None
                    )
                )

                if next_phase == "tag_ende":
                    break

        self.assertEqual(expected_order[: len(visited)], visited)
        self.assertEqual(raum.runde, 1)
        self.assertEqual(raum.aktuelle_phase, "tag_ende")


if __name__ == "__main__":
    unittest.main()
