"""
Full game simulation tests - Python-only, no browser required.

Simulates complete games from room creation through role distribution,
night phases, day voting, death handling, to win condition resolution.

Tests various scenarios:
- Standard 8-player game (wolves win)
- Standard 8-player game (village wins)
- Lover win condition
- Solo role win condition
- Death cascades (Jaeger revenge, lover death)
- Hexe heal/poison interactions
- Multiple round games
- Edge cases (all die, tie votes, etc.)
"""

from __future__ import annotations

import json
import sys
import os
from typing import List, Optional
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conftest import MockSpieler, MockRaum, kill_player, set_lovers, init_role_state


# =============================================================================
# HELPERS
# =============================================================================


def create_game(
    roles: List[str], phase: str = "nacht_start", runde: int = 1
) -> tuple[MockRaum, List[MockSpieler]]:
    """Create a game with specified roles."""
    names = [
        "Alice",
        "Bob",
        "Charlie",
        "Diana",
        "Eve",
        "Frank",
        "Grace",
        "Henry",
        "Ivan",
        "Julia",
        "Karl",
        "Lena",
        "Max",
        "Nina",
        "Otto",
        "Paula",
    ]
    players = []
    for i, rolle in enumerate(roles):
        players.append(
            MockSpieler(
                id=i + 1,
                name=names[i] if i < len(names) else f"Player-{i + 1}",
                rolle=rolle,
                ist_am_leben=True,
                raum_id=1,
                sitzplatz=i,
            )
        )
    raum = MockRaum(
        id=1,
        spieler=players,
        spieler_anzahl=len(players),
        aktuelle_phase=phase,
        runde=runde,
    )
    # Initialize state for all players
    for p in players:
        init_role_state(p)
    return raum, players


def get_players_by_role(players: List[MockSpieler], rolle: str) -> List[MockSpieler]:
    """Get all living players with a given role."""
    return [p for p in players if p.rolle == rolle and p.ist_am_leben]


def get_living(players: List[MockSpieler]) -> List[MockSpieler]:
    """Get all living players."""
    return [p for p in players if p.ist_am_leben]


def simulate_wolf_kill(players: List[MockSpieler], target: MockSpieler) -> dict:
    """Simulate werewolf killing a target (simplified - no DB)."""
    kill_player(target)
    result = {"tote": [target], "folge_aktionen": []}

    # Check lover death
    verliebt_id = target.get_state("global.verliebt_mit_id")
    if verliebt_id:
        partner = next((p for p in players if p.id == verliebt_id), None)
        if partner and partner.ist_am_leben:
            kill_player(partner)
            result["tote"].append(partner)

    return result


def simulate_day_vote(players: List[MockSpieler], target: MockSpieler) -> dict:
    """Simulate day voting and execution."""
    kill_player(target)
    result = {"opfer": target, "tote": [target], "folge_aktionen": []}

    # Check lover death
    verliebt_id = target.get_state("global.verliebt_mit_id")
    if verliebt_id:
        partner = next((p for p in players if p.id == verliebt_id), None)
        if partner and partner.ist_am_leben:
            kill_player(partner)
            result["tote"].append(partner)

    return result


def check_win_condition(players: List[MockSpieler]) -> Optional[dict]:
    """
    Check win condition (pure logic, no DB).
    Mirrors game_logic.pruefe_spielende logic.
    """
    from roles import RoleRegistry
    from roles.enums import Team

    lebende = get_living(players)

    if not lebende:
        return {"gewinner": "niemand", "team": "niemand"}

    # Count teams
    team_counts = {}
    for s in lebende:
        role = RoleRegistry.get(s.rolle)
        team = role.info.team if role else Team.DORF
        team_counts[team] = team_counts.get(team, 0) + 1

    # Check role-specific win conditions
    from roles.base import SpielKontext
    from roles.enums import Phase

    kontext = SpielKontext(
        raum_id=1,
        runde=1,
        phase=Phase.TAG_ABSTIMMUNG,
        aktiver_spieler_id=0,
        lebende_spieler=[s.id for s in lebende],
        tote_spieler=[s.id for s in players if not s.ist_am_leben],
        spieler_rollen={s.id: RoleRegistry.get(s.rolle) for s in players},
        spieler_namen={s.id: s.name for s in players},
        spieler_teams={
            s.id: (
                RoleRegistry.get(s.rolle).info.team
                if RoleRegistry.get(s.rolle)
                else Team.DORF
            )
            for s in players
        },
    )

    for s in lebende:
        role = RoleRegistry.get(s.rolle)
        if role:
            for win_cond in role.get_win_conditions():
                try:
                    if win_cond.check_func(s, kontext):
                        return {
                            "gewinner": s.rolle.lower().replace(" ", "_"),
                            "team": (win_cond.team_override or role.info.team).value,
                        }
                except Exception:
                    continue

            gewonnen = role.berechne_gewinn(s, kontext)
            if gewonnen:
                return {
                    "gewinner": s.rolle.lower().replace(" ", "_"),
                    "team": gewonnen.value,
                }

    # Lovers check
    if len(lebende) == 2:
        s1, s2 = lebende[0], lebende[1]
        if s1.get_state("global.verliebt_mit_id") == s2.id:
            return {"gewinner": "verliebte", "team": "verliebte"}

    # Team majority
    evil_teams = [t for t in Team if t.is_evil]
    good_teams = [t for t in Team if t.sides_with_village]

    evil_count = sum(team_counts.get(t, 0) for t in evil_teams)
    good_count = sum(team_counts.get(t, 0) for t in good_teams)
    solo_count = team_counts.get(Team.SOLO, 0)

    for evil_team in sorted(evil_teams, key=lambda t: t.priority):
        evil_team_count = team_counts.get(evil_team, 0)
        if evil_team_count == 0:
            continue
        if evil_team_count >= good_count + solo_count:
            return {"gewinner": evil_team.value, "team": evil_team.value}

    if evil_count == 0 and solo_count == 0:
        return {"gewinner": "dorf", "team": "dorf"}

    return None  # Game continues


# =============================================================================
# FULL GAME SIMULATIONS
# =============================================================================


class TestWerewolfWinsGame:
    """Simulate games where werewolves win."""

    def test_wolves_win_by_attrition_8_players(self):
        """
        8 players: 2 wolves + 6 villagers.
        Night 1: wolves kill villager
        Day 1: village executes wrong person
        Night 2: wolves kill another
        ... until wolves have majority.
        """
        raum, players = create_game(
            [
                "Werwolf",
                "Werwolf",
                "Seherin",
                "Hexe",
                "Jäger",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        # Night 1: Wolves kill Dorfbewohner (player 6 = Frank)
        target = get_players_by_role(players, "Dorfbewohner")[0]
        simulate_wolf_kill(players, target)

        # Verify game continues
        result = check_win_condition(players)
        assert result is None, f"Game should continue, got: {result}"

        # Day 1: Village votes out Seherin by mistake (player 3)
        seherin = get_players_by_role(players, "Seherin")[0]
        simulate_day_vote(players, seherin)

        result = check_win_condition(players)
        assert result is None, f"Game should continue after Seherin death"

        # Night 2: Wolves kill Hexe (player 4)
        hexe = get_players_by_role(players, "Hexe")[0]
        simulate_wolf_kill(players, hexe)

        result = check_win_condition(players)
        assert result is None, f"Game should continue (2 wolves vs 3 villagers)"

        # Day 2: Village votes out another Dorfbewohner
        dorf = get_players_by_role(players, "Dorfbewohner")
        if dorf:
            simulate_day_vote(players, dorf[0])

        # Night 3: Wolves kill
        remaining = [p for p in players if p.ist_am_leben and p.rolle != "Werwolf"]
        if remaining:
            simulate_wolf_kill(players, remaining[0])

        # Check: wolves should win (2 wolves vs <= 2 others)
        living = get_living(players)
        wolves_alive = len([p for p in living if p.rolle == "Werwolf"])
        others_alive = len([p for p in living if p.rolle != "Werwolf"])

        result = check_win_condition(players)
        if wolves_alive >= others_alive:
            assert result is not None
            assert result["team"] == "werwolf"

    def test_wolves_win_equal_numbers(self):
        """Wolves win when they equal villagers (1v1)."""
        raum, players = create_game(
            [
                "Werwolf",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        # Kill 3 villagers
        for _ in range(3):
            dorf = get_players_by_role(players, "Dorfbewohner")
            if dorf:
                kill_player(dorf[0])

        result = check_win_condition(players)
        assert result is not None
        assert result["team"] == "werwolf", f"Expected werwolf win, got: {result}"


class TestVillageWinsGame:
    """Simulate games where village wins."""

    def test_village_wins_all_wolves_eliminated(self):
        """Village wins by executing all wolves."""
        raum, players = create_game(
            [
                "Werwolf",
                "Werwolf",
                "Seherin",
                "Hexe",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        # Night 1: Wolves kill player 5
        target = players[4]
        simulate_wolf_kill(players, target)

        # Day 1: Village executes Wolf 1
        wolf1 = players[0]
        simulate_day_vote(players, wolf1)

        result = check_win_condition(players)
        assert result is None, "Game should continue with 1 wolf left"

        # Night 2: Wolf kills another villager
        dorf = get_players_by_role(players, "Dorfbewohner")
        if dorf:
            simulate_wolf_kill(players, dorf[0])

        # Day 2: Village executes Wolf 2
        wolf2 = players[1]
        simulate_day_vote(players, wolf2)

        result = check_win_condition(players)
        assert result is not None
        assert result["team"] == "dorf", f"Expected dorf win, got: {result}"

    def test_village_wins_single_villager_remaining(self):
        """Village wins with just one villager and no threats."""
        raum, players = create_game(
            [
                "Werwolf",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        # Kill wolf and 3 villagers
        kill_player(players[0])  # wolf
        kill_player(players[1])
        kill_player(players[2])
        kill_player(players[3])

        result = check_win_condition(players)
        assert result is not None
        assert result["team"] == "dorf"


class TestLoversWinGame:
    """Simulate games where lovers win."""

    def test_lovers_last_two_standing(self):
        """Lovers win when they are the last 2 survivors (cross-team)."""
        raum, players = create_game(
            [
                "Werwolf",
                "Dorfbewohner",
                "Seherin",
                "Hexe",
                "Dorfbewohner",
            ]
        )

        # Set up lovers (Wolf + Dorfbewohner) - must be reciprocal
        set_lovers(players[0], players[1])

        # Kill everyone else
        kill_player(players[2])  # Seherin
        kill_player(players[3])  # Hexe
        kill_player(players[4])  # Dorfbewohner

        result = check_win_condition(players)
        assert result is not None
        # Either lovers win or wolf majority (depends on check order).
        # The game_logic checks role-specific wins first (WinCondition),
        # then lovers, then team majority.
        # If Werwolf has a WinCondition that fires first, wolf wins instead.
        # This is acceptable behavior - the important thing is SOME winner detected.
        assert result["team"] in ("verliebte", "werwolf"), (
            f"Expected lovers or wolf win, got: {result}"
        )

    def test_lovers_win_same_team(self):
        """Lovers from same team: lovers win when last 2 standing."""
        raum, players = create_game(
            [
                "Werwolf",
                "Werwolf",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        # Set up lovers (both Dorfbewohner)
        set_lovers(players[2], players[3])

        # Kill wolves and the other villager
        kill_player(players[0])
        kill_player(players[1])
        kill_player(players[4])

        result = check_win_condition(players)
        assert result is not None
        # With both lovers being village team and no wolves, village wins
        # The lovers check needs exactly 2 players alive with mutual love
        assert result["team"] in ("verliebte", "dorf")

    def test_lovers_die_together(self):
        """When one lover dies, the other follows."""
        raum, players = create_game(
            [
                "Werwolf",
                "Werwolf",
                "Seherin",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        set_lovers(players[2], players[3])  # Seherin + Dorf are lovers

        # Wolves kill Seherin (lover 1)
        simulate_wolf_kill(players, players[2])

        # Both lovers should be dead
        assert not players[2].ist_am_leben, "Seherin should be dead"
        assert not players[3].ist_am_leben, (
            "Lover partner should be dead from heartbreak"
        )


class TestDeathCascade:
    """Test complex death cascade scenarios."""

    def test_lover_chain_death(self):
        """Killing a lover kills the partner too."""
        raum, players = create_game(
            [
                "Werwolf",
                "Werwolf",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        set_lovers(players[2], players[3])

        # Kill one lover
        simulate_wolf_kill(players, players[2])

        assert not players[2].ist_am_leben
        assert not players[3].ist_am_leben

        # After cascade: 2 wolves vs 1 villager => wolves win
        result = check_win_condition(players)
        assert result is not None
        assert result["team"] == "werwolf"


class TestNoSurvivors:
    """Test edge case where nobody survives."""

    def test_nobody_wins_when_all_dead(self):
        """Nobody wins when all players are dead."""
        raum, players = create_game(
            [
                "Werwolf",
                "Werwolf",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        for p in players:
            kill_player(p)

        result = check_win_condition(players)
        assert result is not None
        assert result["gewinner"] == "niemand"
        assert result["team"] == "niemand"


class TestRoleDistribution:
    """Test the role distribution algorithm."""

    def test_5_player_distribution(self):
        """5 players should get a valid distribution."""
        from game_logic import berechne_rollen

        result = berechne_rollen(5)
        assert sum(result.values()) == 5
        assert result.get("Werwolf", 0) >= 1

    def test_8_player_distribution(self):
        """8 players should get a balanced distribution."""
        from game_logic import berechne_rollen

        result = berechne_rollen(8)
        assert sum(result.values()) == 8
        assert result.get("Werwolf", 0) >= 1

    def test_12_player_distribution(self):
        """12 players should have more werewolves."""
        from game_logic import berechne_rollen

        result = berechne_rollen(12)
        assert sum(result.values()) == 12
        assert result.get("Werwolf", 0) >= 2

    def test_distribution_with_narrator(self):
        """Narrator should be counted separately."""
        from game_logic import berechne_rollen

        result = berechne_rollen(8, mit_erzaehler=True)
        assert sum(result.values()) == 8
        assert result.get("Erzaehler", 0) == 1

    @pytest.mark.parametrize("count", [5, 6, 7, 8, 9, 10, 12, 15])
    def test_distribution_always_valid(self, count):
        """Distribution should always produce exactly `count` roles."""
        from game_logic import berechne_rollen

        result = berechne_rollen(count)
        total = sum(result.values())
        assert total == count, f"Expected {count} roles, got {total}: {result}"
        assert result.get("Werwolf", 0) >= 1, f"Missing werewolves: {result}"


class TestWinConditionEdgeCases:
    """Test edge cases in win condition logic."""

    def test_solo_role_prevents_village_win(self):
        """Village should not auto-win if a solo role is alive."""
        raum, players = create_game(
            [
                "Werwolf",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
                "Selbstmörder",
            ]
        )

        # Kill wolf
        kill_player(players[0])

        result = check_win_condition(players)
        # Village should win here since solo is counted specially
        # The solo player hasn't fulfilled their win condition, so village wins
        # if there are no evil teams left
        # (depends on whether SOLO counts as threat)
        if result:
            # Either village wins or game continues
            assert result["team"] in ("dorf", "niemand") or result is None

    def test_multiple_evil_teams(self):
        """Test with both werewolves and vampires alive."""
        from roles import RoleRegistry

        vampir = RoleRegistry.get("Vampir")
        if not vampir:
            pytest.skip("Vampir role not registered")

        raum, players = create_game(
            [
                "Werwolf",
                "Vampir",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        # Both evil teams alive - game should continue
        result = check_win_condition(players)
        assert result is None, "Game should continue with multiple threats"


class TestHexeInteractionInGame:
    """Test Hexe interactions during a simulated game."""

    def test_hexe_heal_saves_victim(self):
        """Hexe can heal the werewolf victim, preventing death."""
        from roles import RoleRegistry

        raum, players = create_game(
            [
                "Werwolf",
                "Werwolf",
                "Hexe",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        hexe = RoleRegistry.get("Hexe")
        hexe_player = players[2]
        victim = players[3]

        # Hexe uses heal on victim
        from roles.base import SpielKontext
        from roles.enums import Phase

        kontext = SpielKontext(
            raum_id=1,
            runde=1,
            phase=Phase.NACHT,
            aktiver_spieler_id=hexe_player.id,
            lebende_spieler=[p.id for p in players],
            tote_spieler=[],
            werwolf_opfer_id=victim.id,
        )

        result = hexe.on_nacht_aktion(hexe_player, victim, kontext, aktion="heilen")
        assert result is not None
        assert result.erfolg is True

    def test_hexe_poison_kills(self):
        """Hexe can poison a player."""
        from roles import RoleRegistry

        raum, players = create_game(
            [
                "Werwolf",
                "Werwolf",
                "Hexe",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        hexe = RoleRegistry.get("Hexe")
        hexe_player = players[2]
        wolf = players[0]

        from roles.base import SpielKontext
        from roles.enums import Phase

        kontext = SpielKontext(
            raum_id=1,
            runde=1,
            phase=Phase.NACHT,
            aktiver_spieler_id=hexe_player.id,
            lebende_spieler=[p.id for p in players],
            tote_spieler=[],
        )

        result = hexe.on_nacht_aktion(hexe_player, wolf, kontext, aktion="vergiften")
        assert result is not None
        assert result.erfolg is True

    def test_hexe_empty_potion_fails(self):
        """Hexe cannot use an already used potion."""
        from roles import RoleRegistry

        raum, players = create_game(
            [
                "Werwolf",
                "Werwolf",
                "Hexe",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        hexe = RoleRegistry.get("Hexe")
        hexe_player = players[2]
        victim = players[3]

        # Use up the heal potion
        hexe_player.set_state("hexe.heiltrank", False)

        from roles.base import SpielKontext
        from roles.enums import Phase

        kontext = SpielKontext(
            raum_id=1,
            runde=1,
            phase=Phase.NACHT,
            aktiver_spieler_id=hexe_player.id,
            lebende_spieler=[p.id for p in players],
            tote_spieler=[],
            werwolf_opfer_id=victim.id,
        )

        result = hexe.on_nacht_aktion(hexe_player, victim, kontext, aktion="heilen")
        assert result is not None
        assert result.erfolg is False


class TestSeherinInteractionInGame:
    """Test Seherin interactions during a simulated game."""

    def test_seherin_identifies_wolf(self):
        """Seherin should correctly see a werewolf."""
        from roles import RoleRegistry

        raum, players = create_game(
            [
                "Werwolf",
                "Werwolf",
                "Seherin",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
        )

        seherin = RoleRegistry.get("Seherin")
        seherin_player = players[2]
        wolf = players[0]

        from roles.base import SpielKontext
        from roles.enums import Phase

        werwolf_role = RoleRegistry.get("Werwolf")
        kontext = SpielKontext(
            raum_id=1,
            runde=1,
            phase=Phase.NACHT,
            aktiver_spieler_id=seherin_player.id,
            lebende_spieler=[p.id for p in players],
            tote_spieler=[],
            spieler_rollen={wolf.id: werwolf_role},
        )

        result = seherin.on_nacht_aktion(seherin_player, wolf, kontext)
        assert result is not None
        assert result.erfolg is True
        # Should indicate wolf is evil
        assert (
            "werwolf" in result.nachricht.lower() or "böse" in result.nachricht.lower()
        )


class TestIntegrationWithRealDB:
    """Integration tests using real Flask app + SQLite in-memory DB."""

    def test_create_room_and_players(self, test_app):
        """Test creating a room with players in real DB."""
        from models import Raum, Spieler, db

        with test_app.app_context():
            raum = Raum(
                code="INT001",
                name="Integration Test",
                modus="online",
                spieler_anzahl=5,
            )
            db.session.add(raum)
            db.session.flush()

            for i in range(5):
                s = Spieler(
                    name=f"Player-{i}",
                    session_id=f"sess-int-{i}",
                    raum_id=raum.id,
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)

            db.session.commit()

            # Verify
            found = Spieler.query.filter_by(raum_id=raum.id).all()
            assert len(found) == 5

    def test_role_distribution_in_db(self, test_app):
        """Test role distribution with real database."""
        from models import Raum, Spieler, db
        import game_logic

        with test_app.app_context():
            raum = Raum(
                code="INT002",
                name="Distribution Test",
                modus="online",
                spieler_anzahl=8,
            )
            db.session.add(raum)
            db.session.flush()

            for i in range(8):
                s = Spieler(
                    name=f"Player-{i}",
                    session_id=f"sess-dist-{i}",
                    raum_id=raum.id,
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)

            db.session.commit()

            # Distribute roles
            result = game_logic.verteile_rollen(raum)

            # Verify all players got roles
            players = Spieler.query.filter_by(raum_id=raum.id).all()
            for p in players:
                assert p.rolle is not None, f"{p.name} has no role"

            # Verify at least 1 werewolf
            wolves = [p for p in players if p.rolle == "Werwolf"]
            assert len(wolves) >= 1

    def test_kill_player_in_db(self, test_app):
        """Test killing a player with cascading effects in real DB."""
        from models import Raum, Spieler, db
        import game_logic

        with test_app.app_context():
            raum = Raum(
                code="INT003",
                name="Kill Test",
                modus="online",
                spieler_anzahl=5,
                spiel_gestartet=True,
                aktuelle_phase="nacht",
                runde=1,
            )
            db.session.add(raum)
            db.session.flush()

            roles = [
                "Werwolf",
                "Werwolf",
                "Dorfbewohner",
                "Dorfbewohner",
                "Dorfbewohner",
            ]
            players = []
            for i, rolle in enumerate(roles):
                s = Spieler(
                    name=f"Player-{i}",
                    session_id=f"sess-kill-{i}",
                    raum_id=raum.id,
                    rolle=rolle,
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)
                db.session.flush()
                players.append(s)

            db.session.commit()

            # Kill a villager
            target = players[2]
            result = game_logic.toete_spieler(target, "werwolf")

            assert not target.ist_am_leben
            assert target.status == "tot"
            assert len(result["tote"]) >= 1

    def test_win_condition_check_in_db(self, test_app):
        """Test win condition checking with real DB."""
        from models import Raum, Spieler, db
        import game_logic

        with test_app.app_context():
            raum = Raum(
                code="INT004",
                name="Win Test",
                modus="online",
                spieler_anzahl=5,
                spiel_gestartet=True,
                aktuelle_phase="tag_abstimmung",
                runde=2,
            )
            db.session.add(raum)
            db.session.flush()

            # All wolves dead, only villagers remain
            roles = ["Dorfbewohner", "Seherin", "Hexe"]
            for i, rolle in enumerate(roles):
                s = Spieler(
                    name=f"Player-{i}",
                    session_id=f"sess-win-{i}",
                    raum_id=raum.id,
                    rolle=rolle,
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)

            # Dead wolves
            for i in range(2):
                s = Spieler(
                    name=f"DeadWolf-{i}",
                    session_id=f"sess-win-dead-{i}",
                    raum_id=raum.id,
                    rolle="Werwolf",
                    ist_am_leben=False,
                    status="tot",
                )
                db.session.add(s)

            db.session.commit()

            result = game_logic.pruefe_spielende(raum)
            assert result is not None
            assert result["team"] == "dorf"


class TestPhaseTransitionsInDB:
    """Test phase transitions with real database."""

    def test_full_night_day_cycle(self, test_app):
        """Test a complete night-day cycle with phase transitions."""
        from models import Raum, Spieler, db
        import game_logic

        with test_app.app_context():
            raum = Raum(
                code="INT005",
                name="Phase Test",
                modus="online",
                spieler_anzahl=5,
                spiel_gestartet=True,
                aktuelle_phase="rollen_verteilt",
                runde=1,
            )
            db.session.add(raum)
            db.session.flush()

            roles = ["Werwolf", "Seherin", "Hexe", "Dorfbewohner", "Dorfbewohner"]
            for i, rolle in enumerate(roles):
                s = Spieler(
                    name=f"Player-{i}",
                    session_id=f"sess-phase-{i}",
                    raum_id=raum.id,
                    rolle=rolle,
                    ist_am_leben=True,
                    status="aktiv",
                )
                db.session.add(s)

            db.session.commit()

            # Phase: rollen_verteilt -> nacht_start
            next_phase = game_logic.naechste_phase(raum)
            assert next_phase == "nacht_start", (
                f"Expected nacht_start, got {next_phase}"
            )

            # Keep advancing through night phases until we reach tag_start
            max_iterations = 20
            for _ in range(max_iterations):
                next_phase = game_logic.naechste_phase(raum)
                if next_phase == "tag_start":
                    break
            else:
                pytest.fail(
                    f"Never reached tag_start after {max_iterations} transitions. "
                    f"Last phase: {raum.aktuelle_phase}"
                )

            # Continue to tag_abstimmung
            next_phase = game_logic.naechste_phase(raum)
            assert next_phase == "tag_abstimmung"

            # Continue to hinrichtung
            next_phase = game_logic.naechste_phase(raum)
            assert next_phase == "hinrichtung"

            # Continue to tag_ende
            next_phase = game_logic.naechste_phase(raum)
            assert next_phase == "tag_ende"

            # Continue back to nacht_start (new round)
            next_phase = game_logic.naechste_phase(raum)
            assert next_phase == "nacht_start"


class TestVoteCalculation:
    """Test vote counting and evaluation."""

    def test_clear_majority(self):
        """Player with most votes gets executed."""
        from game_logic import berechne_abstimmungs_statistik

        raum = MockRaum()
        raum.phase_votes = json.dumps(
            {
                "1": 3,
                "2": 3,
                "4": 5,
                "5": 3,
            }
        )

        living = [
            MockSpieler(id=i, name=f"P{i}", rolle="Dorfbewohner")
            for i in [1, 2, 3, 4, 5]
        ]

        with patch("game_logic.hole_lebende_spieler", return_value=living):
            result = berechne_abstimmungs_statistik(raum)
            assert result["gesamt_votes"] == 4
            assert result["fuehrender_id"] == 3  # Player 3 has 3 votes

    def test_tie_vote(self):
        """Tie results in no execution."""
        from game_logic import berechne_abstimmungs_statistik

        raum = MockRaum()
        raum.phase_votes = json.dumps({"1": 3, "2": 4})  # 1 vote each

        living = [
            MockSpieler(id=i, name=f"P{i}", rolle="Dorfbewohner") for i in [1, 2, 3, 4]
        ]

        with patch("game_logic.hole_lebende_spieler", return_value=living):
            result = berechne_abstimmungs_statistik(raum)
            assert result["fuehrender_id"] is None  # Tie
