import pytest
import json
from app import app, db, Game, Player, Vote, Action, GameLog
from flask import url_for
import random

class TestSpecialRoles:
    """Test the special abilities and actions of different roles."""
    
    def test_werewolf_kill(self, client, game_with_players, socket_clients, app_instance):
        """Test werewolves voting to kill a player during night phase."""
        # Create a game and add players
        game_id, players = game_with_players(num_players=8)
        
        # Connect all players via Socket.IO
        for i, player in enumerate(players):
            socket_clients[i].emit('join_game', {
                'game_id': game_id,
                'token': player['token']
            })
        
        # Find werewolves and a target
        with app_instance.app_context():
            all_players = Player.query.filter_by(game_id=game_id).all()
            werewolves = [p for p in all_players if p.role == 'Werwolf']
            non_werewolves = [p for p in all_players if p.role != 'Werwolf']
            
            assert len(werewolves) >= 2, "Should have at least 2 werewolves"
            
            # Pick a non-werewolf target
            target = random.choice(non_werewolves)
            
            # Map tokens to IDs for easier reference
            player_tokens = {p.id: p.token for p in all_players}
            token_to_index = {p['token']: i for i, p in enumerate(players)}
            
        # Werewolves vote to kill the target
        for werewolf in werewolves:
            werewolf_index = token_to_index[player_tokens[werewolf.id]]
            socket_clients[werewolf_index].emit('vote', {
                'token': player_tokens[werewolf.id],
                'target_id': target.id
            })
        
        # After all werewolves vote, the player should be marked as killed
        with app_instance.app_context():
            # Force vote processing (normally happens when all players vote)
            from app import process_night_actions
            process_night_actions(game_id)
            
            # Refresh the target data
            target = Player.query.get(target.id)
            assert target.status == 'dead', "Target should be killed by werewolves"
            
            # Check for kill logs
            logs = GameLog.query.filter_by(game_id=game_id).all()
            assert any(f"Player {target.name} ({target.role}) was killed by werewolves" in log.message for log in logs)
    
    def test_witch_abilities(self, client, game_with_players, socket_clients, app_instance):
        """Test the witch's ability to kill and heal players."""
        # Create a game and add players
        game_id, players = game_with_players(num_players=8)
        
        # Connect all players via Socket.IO
        for i, player in enumerate(players):
            socket_clients[i].emit('join_game', {
                'game_id': game_id,
                'token': player['token']
            })
        
        # Find the witch and a target to kill
        with app_instance.app_context():
            all_players = Player.query.filter_by(game_id=game_id).all()
            witch = next((p for p in all_players if p.role == 'Hexe'), None)
            assert witch is not None, "Should have a witch"
            
            # Pick a random player to kill
            kill_target = next((p for p in all_players if p.id != witch.id), None)
            
            # Pick a "dead" player to heal (simulate werewolf kill)
            heal_target = next((p for p in all_players if p.id != witch.id and p.id != kill_target.id), None)
            heal_target.status = 'dead'
            game = Game.query.get(game_id)
            game.last_killed = heal_target.id
            db.session.commit()
            
            # Map tokens to IDs for easier reference
            player_tokens = {p.id: p.token for p in all_players}
            token_to_index = {p['token']: i for i, p in enumerate(players)}
        
        # Test witch kill ability
        witch_index = token_to_index[player_tokens[witch.id]]
        socket_clients[witch_index].emit('action', {
            'token': player_tokens[witch.id],
            'action_type': 'kill',
            'target_id': kill_target.id
        })
        
        # Test witch heal ability
        socket_clients[witch_index].emit('action', {
            'token': player_tokens[witch.id],
            'action_type': 'heal',
            'target_id': heal_target.id
        })
        
        # Verify the actions worked
        with app_instance.app_context():
            # Force night action processing
            from app import process_night_actions
            process_night_actions(game_id)
            
            # Refresh player data
            kill_target = Player.query.get(kill_target.id)
            heal_target = Player.query.get(heal_target.id)
            
            assert kill_target.status == 'dead', "Witch's kill target should be dead"
            assert heal_target.status == 'alive', "Witch's heal target should be alive"
            
            # Check logs
            logs = GameLog.query.filter_by(game_id=game_id).order_by(GameLog.timestamp.desc()).all()
            assert any(f"The witch revived {heal_target.name}" in log.message for log in logs)
    
    def test_seer_ability(self, client, game_with_players, socket_clients, app_instance):
        """Test the seer's ability to see other players' roles."""
        # Create a game and add players
        game_id, players = game_with_players(num_players=8)
        
        # Connect all players via Socket.IO
        for i, player in enumerate(players):
            socket_clients[i].emit('join_game', {
                'game_id': game_id,
                'token': player['token']
            })
        
        # Find the seer and a target to investigate
        with app_instance.app_context():
            all_players = Player.query.filter_by(game_id=game_id).all()
            seer = next((p for p in all_players if p.role == 'Seherin'), None)
            assert seer is not None, "Should have a seer"
            
            # Pick a werewolf to investigate
            werewolf = next((p for p in all_players if p.role == 'Werwolf'), None)
            assert werewolf is not None, "Should have a werewolf to investigate"
            
            # Map tokens to IDs for easier reference
            player_tokens = {p.id: p.token for p in all_players}
            token_to_index = {p['token']: i for i, p in enumerate(players)}
        
        # Seer investigates the werewolf
        seer_index = token_to_index[player_tokens[seer.id]]
        socket_clients[seer_index].emit('action', {
            'token': player_tokens[seer.id],
            'action_type': 'see',
            'target_id': werewolf.id
        })
        
        # Check that the seer received the correct information
        received = socket_clients[seer_index].get_received()
        seer_results = [msg for msg in received if msg['name'] == 'seer_result']
        
        assert len(seer_results) > 0, "Seer should receive a result"
        result = seer_results[-1]['args'][0]  # Get the most recent result
        assert result['target_name'] == werewolf.name
        assert result['role'] == 'Werwolf'