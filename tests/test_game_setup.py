import pytest
import json
from app import app, db, Game, Player, Vote, Action
from flask import url_for

class TestBasicGameSetup:
    """Test basic game setup functionality."""

    def test_create_game(self, client):
        """Test creating a new game."""
        response = client.post('/games', data={'player_count': 8})
        assert response.status_code == 302  # Redirect
        assert '/game/' in response.location

    def test_join_game(self, client, game_with_players):
        """Test joining a game."""
        game_id, _ = game_with_players(num_players=1)  # Create a game with 1 player
        
        # Join another player
        response = client.post(
            f'/api/games/{game_id}/join', 
            data={'name': 'TestPlayer'}
        )
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] == True
        assert json_data['player']['name'] == 'TestPlayer'
        assert 'token' in json_data

    def test_game_starts_when_full(self, client, game_with_players):
        """Test that game starts automatically when all players join."""
        game_id, players = game_with_players(num_players=8)
        
        # Game should be in running status
        response = client.get(f'/api/games/{game_id}')
        game_data = response.get_json()
        assert game_data['status'] == 'running'
        assert game_data['phase'] == 'night'
        
        # Players should have roles assigned
        response = client.get(f'/api/games/{game_id}/players')
        players_data = response.get_json()
        assert len(players_data) == 8
        for player in players_data:
            assert player['role'] is not None