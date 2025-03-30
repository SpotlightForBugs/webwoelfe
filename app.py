from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime, timezone
import random
import uuid
import json
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

app = Flask(__name__)
app.config['SECRET_KEY'] = 'werewolf-game-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///werewolf.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
socketio = SocketIO(app)

# Configure Sentry
sentry_sdk.init(
    dsn="https://78fe9de58a5847ada071bf5f62f9c214@o1363527.ingest.sentry.io/6678492",
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
)

# Database Models
class Game(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    status = db.Column(db.String(20), default='setup')  # setup, running, ended
    phase = db.Column(db.String(20))  # night, day, voting
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    player_count = db.Column(db.Integer, default=8)
    random_storyteller = db.Column(db.Boolean, default=False)
    last_killed = db.Column(db.String(36), nullable=True)
    players = db.relationship('Player', backref='game', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'phase': self.phase,
            'player_count': self.player_count,
            'random_storyteller': self.random_storyteller,
            'created_at': self.created_at.isoformat()
        }

class Player(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    game_id = db.Column(db.String(36), db.ForeignKey('game.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20))
    status = db.Column(db.String(20), default='alive')  # alive, dead
    token = db.Column(db.String(100))
    state = db.Column(db.String(20), default='awake')  # awake, sleeping
    last_action = db.Column(db.DateTime)
    votes = db.relationship('Vote', backref='voter', lazy=True, foreign_keys='Vote.voter_id')
    votes_received = db.relationship('Vote', backref='target', lazy=True, foreign_keys='Vote.target_id')
    actions = db.relationship('Action', backref='player', lazy=True, foreign_keys='Action.player_id')
    targeted_by = db.relationship('Action', backref='target', lazy=True, foreign_keys='Action.target_id')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'status': self.status,
            'state': self.state
        }

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(36), db.ForeignKey('game.id'), nullable=False)
    voter_id = db.Column(db.String(36), db.ForeignKey('player.id'), nullable=False)
    target_id = db.Column(db.String(36), db.ForeignKey('player.id'), nullable=False)
    phase = db.Column(db.String(20))  # day, night
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(36), db.ForeignKey('game.id'), nullable=False)
    player_id = db.Column(db.String(36), db.ForeignKey('player.id'), nullable=False)
    action_type = db.Column(db.String(20))  # kill, protect, see, heal
    target_id = db.Column(db.String(36), db.ForeignKey('player.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class GameLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(36), db.ForeignKey('game.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# Game Logic Functions
def create_game(player_count, random_storyteller):
    game_id = str(uuid.uuid4())
    game = Game(
        id=game_id,
        status='setup',
        phase='setup',
        player_count=player_count,
        random_storyteller=random_storyteller
    )
    db.session.add(game)
    db.session.commit()
    log_event(game_id, f"New game created with {player_count} players")
    return game

def add_player(game_id, name):
    # Validate name
    name = name.strip()
    if not name:
        return None, "Name cannot be empty"
    
    # Check if name already exists in this game
    existing = Player.query.filter_by(game_id=game_id, name=name).first()
    if existing:
        return None, "Player name already exists"
    
    # Find game
    game = Game.query.get(game_id)
    if not game:
        return None, "Game not found"
    
    # Check if game is full
    player_count = Player.query.filter_by(game_id=game_id).count()
    if player_count >= game.player_count:
        return None, "Game is full"
    
    # Create player
    player_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    player = Player(
        id=player_id,
        game_id=game_id,
        name=name,
        token=token,
        status='alive',
        state='awake'
    )
    db.session.add(player)
    db.session.commit()
    
    log_event(game_id, f"Player {name} joined the game")
    
    # If game is full, assign roles
    if player_count + 1 == game.player_count:
        assign_roles(game_id)
        game.status = 'running'
        game.phase = 'night'
        db.session.commit()
        log_event(game_id, "Game started, roles assigned")
    
    return player, None

def assign_roles(game_id):
    players = Player.query.filter_by(game_id=game_id).all()
    game = Game.query.get(game_id)
    
    # Define roles based on player count
    roles = []
    
    # Basic roles
    roles.append('Erzaehler')  # Storyteller
    roles.extend(['Werwolf'] * 2)  # Werewolves
    roles.append('Seherin')  # Seer
    roles.append('Hexe')  # Witch
    
    # Add more roles based on player count
    if game.player_count >= 10:
        roles.append('Armor')  # Armor
    if game.player_count >= 12:
        roles.append('Jaeger')  # Hunter
    if game.player_count >= 14:
        roles.append('Werwolf')  # Add another werewolf
    
    # Fill remaining slots with villagers
    villager_count = game.player_count - len(roles)
    roles.extend(['Dorfbewohner'] * villager_count)  # Villagers
    
    # Randomize roles
    random.shuffle(roles)
    
    # Assign roles to players
    for i, player in enumerate(players):
        player.role = roles[i]
        log_event(game_id, f"Player {player.name} assigned role: {player.role}")
    
    db.session.commit()

def log_event(game_id, message):
    log = GameLog(game_id=game_id, message=message)
    db.session.add(log)
    db.session.commit()
    
    # Also emit via websocket
    socketio.emit('game_log', {
        'game_id': game_id,
        'message': message,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room=game_id)

def kill_player(game_id, player_id, killer_type):
    player = Player.query.get(player_id)
    if not player or player.status == 'dead':
        return False
    
    player.status = 'dead'
    db.session.commit()
    
    death_message = f"Player {player.name} ({player.role}) was killed"
    if killer_type == 'werewolf':
        death_message += " by werewolves"
    elif killer_type == 'witch':
        death_message += " by the witch"
    elif killer_type == 'vote':
        death_message += " by village vote"
    log_event(game_id, death_message)
    
    # Check if game is over
    check_game_end(game_id)
    
    return True

def check_game_end(game_id):
    game = Game.query.get(game_id)
    werewolves = Player.query.filter_by(game_id=game_id, role='Werwolf', status='alive').count()
    villagers = Player.query.filter_by(game_id=game_id, status='alive').filter(Player.role != 'Werwolf').count()
    
    if werewolves == 0:
        game.status = 'ended'
        game.phase = 'villagers_win'
        log_event(game_id, "Game over! Villagers win!")
        db.session.commit()
        return True
    
    if werewolves >= villagers:
        game.status = 'ended'
        game.phase = 'werewolves_win'
        log_event(game_id, "Game over! Werewolves win!")
        db.session.commit()
        return True
    
    return False

def process_night_actions(game_id):
    game = Game.query.get(game_id)
    
    # Get werewolf targets
    werewolf_votes = Vote.query.filter_by(
        game_id=game_id, 
        phase='night'
    ).join(Player, Vote.voter_id == Player.id).filter(
        Player.role == 'Werwolf',
        Player.status == 'alive'
    ).all()
    
    # Count votes to find target
    vote_counts = {}
    for vote in werewolf_votes:
        if vote.target_id in vote_counts:
            vote_counts[vote.target_id] += 1
        else:
            vote_counts[vote.target_id] = 1
    
    # Find most voted player
    if vote_counts:
        max_votes = max(vote_counts.values())
        targets = [k for k, v in vote_counts.items() if v == max_votes]
        
        # If there's a tie, randomly select
        if targets:
            werewolf_target = random.choice(targets)
            
            # Check if target is protected by armor
            armor_action = Action.query.filter_by(
                game_id=game_id,
                action_type='protect',
                target_id=werewolf_target
            ).filter(
                Action.timestamp > datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
            ).first()
            
            if not armor_action:
                kill_player(game_id, werewolf_target, 'werewolf')
                
                # Store last killed for witch
                game.last_killed = werewolf_target
                db.session.commit()
    
    # Process witch actions
    witch = Player.query.filter_by(game_id=game_id, role='Hexe', status='alive').first()
    if witch:
        witch_kill = Action.query.filter_by(
            game_id=game_id,
            player_id=witch.id,
            action_type='kill'
        ).filter(
            Action.timestamp > datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        ).first()
        
        if witch_kill:
            kill_player(game_id, witch_kill.target_id, 'witch')
        
        witch_heal = Action.query.filter_by(
            game_id=game_id,
            player_id=witch.id,
            action_type='heal'
        ).filter(
            Action.timestamp > datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        ).first()
        
        if witch_heal and game.last_killed:
            # Revive player
            player = Player.query.get(game.last_killed)
            if player:
                player.status = 'alive'
                log_event(game_id, f"The witch revived {player.name}")
                db.session.commit()
    
    # Process seer action
    seer = Player.query.filter_by(game_id=game_id, role='Seherin', status='alive').first()
    if seer:
        seer_action = Action.query.filter_by(
            game_id=game_id,
            player_id=seer.id,
            action_type='see'
        ).filter(
            Action.timestamp > datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        ).first()
        
        if seer_action:
            target = Player.query.get(seer_action.target_id)
            if target:
                # Send private message to seer
                socketio.emit('seer_result', {
                    'target_name': target.name,
                    'role': target.role
                }, room=seer.id)
    
    # Transition to day phase
    game.phase = 'day'
    db.session.commit()
    
    # Notify all players
    socketio.emit('phase_change', {
        'game_id': game_id,
        'phase': 'day'
    }, room=game_id)
    
    return True

def process_day_vote(game_id):
    votes = Vote.query.filter_by(game_id=game_id, phase='day').all()
    
    # Count votes
    vote_counts = {}
    for vote in votes:
        if vote.target_id in vote_counts:
            vote_counts[vote.target_id] += 1
        else:
            vote_counts[vote.target_id] = 1
    
    # Find most voted player
    if vote_counts:
        max_votes = max(vote_counts.values())
        targets = [k for k, v in vote_counts.items() if v == max_votes]
        
        # If there's a tie, randomly select
        if targets:
            target = random.choice(targets)
            kill_player(game_id, target, 'vote')
    
    # Transition to night phase
    game = Game.query.get(game_id)
    game.phase = 'night'
    db.session.commit()
    
    # Reset votes
    Vote.query.filter_by(game_id=game_id, phase='day').delete()
    db.session.commit()
    
    # Notify all players
    socketio.emit('phase_change', {
        'game_id': game_id,
        'phase': 'night'
    }, room=game_id)
    
    return True

# Routes and Socket Handlers
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/games', methods=['POST'])
def create_new_game():
    player_count = request.form.get('player_count', 8, type=int)
    if player_count < 8 or player_count > 18:
        player_count = 8
    
    random_storyteller = bool(request.form.get('random_storyteller', False))
    
    game = create_game(player_count, random_storyteller)
    return redirect(f'/game/{game.id}')

@app.route('/game/<game_id>')
def game_page(game_id):
    game = Game.query.get_or_404(game_id)
    return render_template('game.html', game=game)

@app.route('/api/games/<game_id>', methods=['GET'])
def get_game(game_id):
    game = Game.query.get_or_404(game_id)
    return jsonify(game.to_dict())

@app.route('/api/games/<game_id>/players', methods=['GET'])
def get_players(game_id):
    players = Player.query.filter_by(game_id=game_id).all()
    return jsonify([p.to_dict() for p in players])

@app.route('/api/games/<game_id>/join', methods=['POST'])
def join_game(game_id):
    name = request.form.get('name', '').strip()
    player, error = add_player(game_id, name)
    
    if error:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'player': player.to_dict(),
        'token': player.token
    })

@app.route('/api/player/<token>')
def get_player_by_token(token):
    player = Player.query.filter_by(token=token).first_or_404()
    return jsonify(player.to_dict())

@app.route('/api/games/<game_id>/logs')
def get_game_logs(game_id):
    logs = GameLog.query.filter_by(game_id=game_id).order_by(GameLog.timestamp.desc()).limit(50).all()
    return jsonify([{
        'message': log.message,
        'timestamp': log.timestamp.isoformat()
    } for log in logs])

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_game')
def handle_join_game(data):
    game_id = data.get('game_id')
    player_token = data.get('token')
    
    if not game_id or not player_token:
        return False
    
    player = Player.query.filter_by(token=player_token).first()
    if not player or player.game_id != game_id:
        return False
    
    join_room(game_id)
    join_room(player.id)  # For private messages
    
    emit('joined', {
        'player': player.to_dict(),
        'game_id': game_id
    })
    return True

@socketio.on('vote')
def handle_vote(data):
    player_token = data.get('token')
    target_id = data.get('target_id')
    
    player = Player.query.filter_by(token=player_token).first()
    if not player or player.status != 'alive':
        return False
    
    game = Game.query.get(player.game_id)
    if not game or game.status != 'running':
        return False
    
    # Delete any existing votes from this player for this phase
    Vote.query.filter_by(
        voter_id=player.id, 
        game_id=player.game_id,
        phase=game.phase
    ).delete()
    
    # Create new vote
    vote = Vote(
        game_id=player.game_id,
        voter_id=player.id,
        target_id=target_id,
        phase=game.phase
    )
    db.session.add(vote)
    db.session.commit()
    
    # Check if all players have voted
    alive_players = Player.query.filter_by(
        game_id=player.game_id, 
        status='alive'
    ).count()
    
    current_votes = Vote.query.filter_by(
        game_id=player.game_id,
        phase=game.phase
    ).count()
    
    # If all alive players have voted, process the votes
    if current_votes >= alive_players:
        if game.phase == 'night':
            process_night_actions(player.game_id)
        else:
            process_day_vote(player.game_id)
    
    return True

@socketio.on('action')
def handle_action(data):
    player_token = data.get('token')
    action_type = data.get('action_type')
    target_id = data.get('target_id')
    
    player = Player.query.filter_by(token=player_token).first()
    if not player or player.status != 'alive':
        return False
    
    game = Game.query.get(player.game_id)
    if not game or game.status != 'running' or game.phase != 'night':
        return False
    
    # Validate action based on role
    valid_action = False
    if player.role == 'Hexe' and action_type in ['kill', 'heal']:
        valid_action = True
    elif player.role == 'Seherin' and action_type == 'see':
        valid_action = True
    elif player.role == 'Armor' and action_type == 'protect':
        valid_action = True
    
    if not valid_action:
        return False
    
    # Delete any existing actions of this type from this player today
    Action.query.filter_by(
        player_id=player.id,
        action_type=action_type,
        game_id=player.game_id
    ).filter(
        Action.timestamp > datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    ).delete()
    
    # Create new action
    action = Action(
        game_id=player.game_id,
        player_id=player.id,
        action_type=action_type,
        target_id=target_id
    )
    db.session.add(action)
    db.session.commit()
    
    # For seer, immediately provide result
    if action_type == 'see':
        target = Player.query.get(target_id)
        if target:
            emit('seer_result', {
                'target_name': target.name,
                'role': target.role
            }, room=player.id)
    
    return True

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# Context processors
@app.context_processor
def inject_now():
    return {'now': datetime.now(timezone.utc)}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
