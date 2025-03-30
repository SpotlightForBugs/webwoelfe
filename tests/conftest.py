import pytest
import os
import sys
import tempfile

# Add the parent directory to sys.path to find the app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from app module
from app import app, db, socketio
import uuid
from flask_socketio import SocketIOTestClient

@pytest.fixture(scope='session')
def app_instance():
    """Return the Flask app instance."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app

@pytest.fixture
def client(app_instance):
    """A test client for the app."""
    with app_instance.test_client() as client:
        with app_instance.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

@pytest.fixture
def socket_client(app_instance):
    """Socket.IO test client for emulating real-time interaction."""
    with app_instance.app_context():
        db.create_all()
        client = SocketIOTestClient(app_instance, socketio)
        yield client
        db.session.remove()
        db.drop_all()

@pytest.fixture
def game_with_players(client, app_instance):
    """Creates a game with specified number of players."""
    def _create_game_with_players(num_players=8):
        # Create a new game
        response = client.post('/games', data={'player_count': num_players})
        game_id = response.location.split('/')[-1]
        
        # Add players to the game
        players = []
        for i in range(1, num_players + 1):
            name = f"Player{i}"
            response = client.post(
                f'/api/games/{game_id}/join', 
                data={'name': name}
            )
            player_data = response.get_json()
            players.append({
                'name': name,
                'token': player_data['token'],
                'player_id': player_data['player']['id']
            })
        
        return game_id, players
    
    return _create_game_with_players

@pytest.fixture
def socket_clients(app_instance):
    """Create multiple Socket.IO clients to simulate multiple players."""
    clients = []
    
    with app_instance.app_context():
        db.create_all()
        
        # Create several clients
        for _ in range(10):  # Create 10 clients
            client = SocketIOTestClient(app_instance, socketio)
            clients.append(client)
        
        yield clients
        
        db.session.remove()
        db.drop_all()