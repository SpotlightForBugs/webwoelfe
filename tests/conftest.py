"""
Shared test fixtures and helpers for Webwölfe test suite.

Eliminates MockSpieler/MockRaum duplication across test files.
Provides reusable factories, Flask app fixtures, and SpielKontext builders.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# MOCK OBJECTS
# =============================================================================


@dataclass
class MockSpieler:
    """
    Mock player object that mirrors models.Spieler without requiring Flask/SQLAlchemy.

    Supports the same get_state/set_state interface as the real model.
    """

    id: int
    name: str
    rolle: str = "Dorfbewohner"
    ist_am_leben: bool = True
    status: str = "aktiv"
    raum_id: int = 1
    ist_erzaehler: bool = False
    sitzplatz: Optional[int] = None
    rolle_zustand: str = "{}"

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value from JSON storage."""
        try:
            state = json.loads(self.rolle_zustand or "{}")
            return state.get(key, default)
        except (json.JSONDecodeError, TypeError):
            return default

    def set_state(self, key: str, value: Any) -> None:
        """Set state value in JSON storage."""
        try:
            state = json.loads(self.rolle_zustand or "{}")
        except (json.JSONDecodeError, TypeError):
            state = {}
        state[key] = value
        self.rolle_zustand = json.dumps(state)

    def get_all_state(self) -> dict:
        """Get all state values."""
        try:
            return json.loads(self.rolle_zustand or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def reset_state(self) -> None:
        """Reset all state."""
        self.rolle_zustand = "{}"

    def add_win_condition(self, condition_id: str) -> None:
        state = self.get_all_state()
        conditions = state.get("win_conditions", [])
        if condition_id not in conditions:
            conditions.append(condition_id)
            self.set_state("win_conditions", conditions)

    def remove_win_condition(self, condition_id: str) -> None:
        state = self.get_all_state()
        conditions = state.get("win_conditions", [])
        if condition_id in conditions:
            conditions.remove(condition_id)
            self.set_state("win_conditions", conditions)

    def has_win_condition(self, condition_id: str) -> bool:
        conditions = self.get_state("win_conditions", [])
        return condition_id in (conditions if conditions else [])

    def add_lose_condition(self, condition_id: str, context: dict = None) -> None:
        state = self.get_all_state()
        conditions = state.get("lose_conditions", {})
        conditions[condition_id] = context or {}
        self.set_state("lose_conditions", conditions)

    def remove_lose_condition(self, condition_id: str) -> None:
        state = self.get_all_state()
        conditions = state.get("lose_conditions", {})
        if condition_id in conditions:
            del conditions[condition_id]
            self.set_state("lose_conditions", conditions)

    def get_lose_conditions(self) -> dict:
        result = self.get_state("lose_conditions", {})
        return result if isinstance(result, dict) else {}

    # Allow arbitrary attribute setting (some roles set ad-hoc attributes)
    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)


@dataclass
class MockRaum:
    """
    Mock room object that mirrors models.Raum without requiring Flask/SQLAlchemy.
    """

    id: int = 1
    code: str = "TEST01"
    name: str = "Test Room"
    modus: str = "online"
    spiel_gestartet: bool = True
    aktuelle_phase: str = "nacht"
    runde: int = 1
    spiel_beendet: bool = False
    gewinner: Optional[str] = None
    phase_votes: str = "{}"
    timer_start: Optional[Any] = None
    timer_duration: int = 120
    spieler_anzahl: int = 8
    aktive_rollen: str = "{}"
    erzaehler_id: Optional[int] = None
    erzaehler_modus: str = "selbst"
    spieler: List[MockSpieler] = field(default_factory=list)


# =============================================================================
# FIXTURES - Mock objects
# =============================================================================


@pytest.fixture
def mock_spieler_factory():
    """Factory to create MockSpieler with auto-incrementing IDs."""
    _counter = [0]

    def _create(
        name: str = None,
        rolle: str = "Dorfbewohner",
        ist_am_leben: bool = True,
        id: int = None,
        raum_id: int = 1,
        ist_erzaehler: bool = False,
        sitzplatz: int = None,
    ) -> MockSpieler:
        _counter[0] += 1
        actual_id = id if id is not None else _counter[0]
        actual_name = name or f"Player-{actual_id}"
        return MockSpieler(
            id=actual_id,
            name=actual_name,
            rolle=rolle,
            ist_am_leben=ist_am_leben,
            raum_id=raum_id,
            ist_erzaehler=ist_erzaehler,
            sitzplatz=sitzplatz if sitzplatz is not None else actual_id,
        )

    return _create


@pytest.fixture
def mock_raum_factory():
    """Factory to create MockRaum instances."""
    _counter = [0]

    def _create(
        spieler: List[MockSpieler] = None,
        phase: str = "nacht",
        runde: int = 1,
        modus: str = "online",
        id: int = None,
    ) -> MockRaum:
        _counter[0] += 1
        actual_id = id if id is not None else _counter[0]
        return MockRaum(
            id=actual_id,
            code=f"TST{actual_id:03d}",
            spieler=spieler or [],
            aktuelle_phase=phase,
            runde=runde,
            modus=modus,
            spieler_anzahl=len(spieler) if spieler else 0,
        )

    return _create


@pytest.fixture
def basic_8_player_game(mock_spieler_factory):
    """
    Standard 8-player game setup with core roles.
    Returns (raum, players_dict) where players_dict maps role -> MockSpieler.
    """
    players = [
        mock_spieler_factory(name="Alice", rolle="Werwolf", id=1),
        mock_spieler_factory(name="Bob", rolle="Werwolf", id=2),
        mock_spieler_factory(name="Charlie", rolle="Seherin", id=3),
        mock_spieler_factory(name="Diana", rolle="Hexe", id=4),
        mock_spieler_factory(name="Eve", rolle="Jäger", id=5),
        mock_spieler_factory(name="Frank", rolle="Dorfbewohner", id=6),
        mock_spieler_factory(name="Grace", rolle="Dorfbewohner", id=7),
        mock_spieler_factory(name="Henry", rolle="Dorfbewohner", id=8),
    ]
    raum = MockRaum(
        id=1,
        spieler=players,
        spieler_anzahl=8,
        aktuelle_phase="nacht_start",
        runde=1,
    )
    players_by_role = {}
    for p in players:
        if p.rolle not in players_by_role:
            players_by_role[p.rolle] = p
        else:
            # For roles with multiple players (e.g., Werwolf), store as list
            existing = players_by_role[p.rolle]
            if isinstance(existing, list):
                existing.append(p)
            else:
                players_by_role[p.rolle] = [existing, p]
    return raum, players, players_by_role


# =============================================================================
# FIXTURES - SpielKontext builder
# =============================================================================


@pytest.fixture
def make_kontext():
    """Factory to create SpielKontext from a list of MockSpieler."""
    from roles.base import SpielKontext
    from roles.enums import Phase

    def _create(
        lebende: List[MockSpieler] = None,
        tote: List[MockSpieler] = None,
        runde: int = 1,
        phase=Phase.NACHT,
        werwolf_opfer_id: int = None,
        aktiver_spieler_id: int = None,
        spieler_rollen: Dict[int, Any] = None,
        spieler_namen: Dict[int, str] = None,
        spieler_teams: Dict[int, Any] = None,
        aktionen_diese_runde: List[Dict[str, Any]] = None,
    ) -> SpielKontext:
        lebende = lebende or []
        tote = tote or []

        # Auto-populate spieler_rollen and spieler_namen from players
        auto_rollen = {}
        auto_namen = {}
        auto_teams = {}
        from roles import RoleRegistry

        for s in lebende + tote:
            role_obj = RoleRegistry.get(s.rolle)
            auto_rollen[s.id] = role_obj if role_obj else s.rolle
            auto_namen[s.id] = s.name
            if role_obj:
                auto_teams[s.id] = role_obj.info.team

        kontext = SpielKontext(
            raum_id=1,
            runde=runde,
            phase=phase,
            aktiver_spieler_id=aktiver_spieler_id or (lebende[0].id if lebende else 0),
            lebende_spieler=[s.id for s in lebende],
            tote_spieler=[s.id for s in tote],
            werwolf_opfer_id=werwolf_opfer_id,
            aktionen_diese_runde=aktionen_diese_runde or [],
            spieler_rollen=spieler_rollen
            if spieler_rollen is not None
            else auto_rollen,
            spieler_namen=spieler_namen if spieler_namen is not None else auto_namen,
            spieler_teams=spieler_teams if spieler_teams is not None else auto_teams,
        )
        return kontext

    return _create


# =============================================================================
# FIXTURES - Flask app with in-memory DB
# =============================================================================


@pytest.fixture
def test_app():
    """
    Create a Flask app with in-memory SQLite for integration tests.

    Usage:
        def test_something(test_app):
            with test_app.app_context():
                # DB operations here
    """
    from flask import Flask
    from models import db

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"

    db.init_app(app)
    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_db(test_app):
    """Provides the db session within app context."""
    from models import db

    with test_app.app_context():
        yield db
        db.session.rollback()


@pytest.fixture
def populated_game(test_app):
    """
    Creates a fully populated game in the test database.
    Returns (app, raum_id, player_ids_by_role).

    Uses real Raum and Spieler models with in-memory SQLite.
    """
    from models import Raum, Spieler, db

    with test_app.app_context():
        raum = Raum(
            code="TST001",
            name="Test Game",
            modus="online",
            spieler_anzahl=8,
            spiel_gestartet=True,
            aktuelle_phase="nacht_start",
            runde=1,
        )
        db.session.add(raum)
        db.session.flush()

        roles = [
            ("Alice", "Werwolf"),
            ("Bob", "Werwolf"),
            ("Charlie", "Seherin"),
            ("Diana", "Hexe"),
            ("Eve", "Jäger"),
            ("Frank", "Dorfbewohner"),
            ("Grace", "Dorfbewohner"),
            ("Henry", "Dorfbewohner"),
        ]

        player_ids = {}
        for idx, (name, rolle) in enumerate(roles):
            s = Spieler(
                name=name,
                session_id=f"sess-{idx}",
                raum_id=raum.id,
                rolle=rolle,
                ist_am_leben=True,
                status="aktiv",
                sitzplatz=idx,
            )
            db.session.add(s)
            db.session.flush()
            if rolle not in player_ids:
                player_ids[rolle] = []
            player_ids[rolle].append(s.id)

        db.session.commit()
        yield test_app, raum.id, player_ids


# =============================================================================
# HELPER FUNCTIONS (importable from conftest)
# =============================================================================


def kill_player(spieler: MockSpieler) -> None:
    """Mark a MockSpieler as dead."""
    spieler.ist_am_leben = False
    spieler.status = "tot"


def set_lovers(spieler1: MockSpieler, spieler2: MockSpieler) -> None:
    """Link two players as lovers."""
    spieler1.set_state("global.verliebt_mit_id", spieler2.id)
    spieler2.set_state("global.verliebt_mit_id", spieler1.id)


def init_role_state(spieler: MockSpieler) -> None:
    """Initialize a player's role state with defaults from the registry."""
    from roles import RoleRegistry

    role = RoleRegistry.get(spieler.rolle)
    if role:
        for sf in role.state_fields():
            key = role._state_key(sf.name)
            spieler.set_state(key, sf.default)
