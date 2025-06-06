# Always monkey_patch FIRST before anything else

import random
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from models import db, User, GameHistory
from game_logic import create_deck, calculate_points
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secure-random-secret'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///game.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/game.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
db.init_app(app)

rooms = {}
timers = {}
MAX_PLAYERS = 12

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()

def start_turn_timer(room):
    # Cancel existing timer if any
    if room in timers and timers[room]:
        timers[room].cancel()

    # Start new timer
    timer = threading.Timer(30.0, lambda: skip_turn_due_to_timeout(room))
    timers[room] = timer
    timer.start()

def skip_turn_due_to_timeout(room):
    if room not in rooms:
        return

    current_turn = rooms[room]['current_turn']
    sid = rooms[room]['turn_order'][current_turn]
    username = rooms[room]['players'][sid]['username']

    emit('turn_skipped', {'username': username}, room=room)

    # Move to next turn
    rooms[room]['current_turn'] = (current_turn + 1) % len(rooms[room]['turn_order'])
    next_sid = rooms[room]['turn_order'][rooms[room]['current_turn']]
    emit('your_turn', {'username': rooms[room]['players'][next_sid]['username']}, room=room)

    # Start the next turn timer
    start_turn_timer(room)


@app.route('/')
def index():
    return render_template('index.html', username=session.get('username'))

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username exists'}), 400
    user = User(username=data['username'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Registered successfully'}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and user.check_password(data['password']):
        login_user(user)
        session['username'] = user.username
        return jsonify({'message': 'Login successful'}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/current_user')
@login_required
def current_user_info():
    return jsonify({'username': current_user.username})


@socketio.on('join')
def on_join(data):
    if not current_user.is_authenticated:
        emit('error', {'msg': 'Authentication required'})
        return

    room = data['room']
    username = current_user.username
    sid = request.sid

    join_room(room)

    if room not in rooms:
        rooms[room] = {
            'players': {},
            'deck': create_deck(),
            'started': False,
            'host': sid  # Assign host on first join
        }

    if len(rooms[room]['players']) >= MAX_PLAYERS:
        emit('error', {'msg': 'Room is full'}, room=sid)
        return

    rooms[room]['players'][sid] = {
        'username': username,
        'hand': [],
        'points': 0
    }

    emit('player_joined', {'username': username}, room=room)
    emit('room_info', {
        'host': rooms[room]['players'][rooms[room]['host']]['username'],
        'is_host': rooms[room]['host'] == sid
    }, room=sid)
    emit('room_stats', {
        'players': len(rooms[room]['players']),
        'max_players': MAX_PLAYERS
    }, room=room)


@socketio.on('start_game')
def start_game(data):
    if not current_user.is_authenticated:
        emit('error', {'msg': 'Authentication required'})
        return
    room = data['room']
    if room in rooms:
        deck = rooms[room]['deck']
        random.shuffle(deck)
        player_ids = list(rooms[room]['players'].keys())
        
        for sid in player_ids:
            hand = [deck.pop() for _ in range(5)]
            rooms[room]['players'][sid]['hand'] = hand
            emit('your_cards', hand, room=sid)

        rooms[room]['started'] = True
        rooms[room]['game_over'] = False  # Add this line
        rooms[room]['turn_order'] = player_ids
        rooms[room]['current_turn'] = 0

        first_sid = player_ids[0]
        emit('game_started', room=room)
        emit('your_turn', {'username': rooms[room]['players'][first_sid]['username']}, room=room)
        start_turn_timer(room)

@socketio.on('kick_player')
def kick_player(data):
    room = data['room']
    target_username = data['username']
    if room not in rooms:
        return
    host_sid = rooms[room]['host']
    if request.sid != host_sid:
        emit('error', {'msg': 'Only the host can kick players'})
        return

    for sid, player in list(rooms[room]['players'].items()):
        if player['username'] == target_username:
            del rooms[room]['players'][sid]
            emit('kicked', {}, room=sid)
            leave_room(room, sid=sid)
            emit('player_kicked', {'username': target_username}, room=room)
            break


@socketio.on('discard_card')
def discard_card(data):
    if not current_user.is_authenticated:
        emit('error', {'msg': 'Authentication required'})
        return

    room = data['room']
    card = data['card']
    sid = request.sid

    if room not in rooms or sid != rooms[room]['turn_order'][rooms[room]['current_turn']]:
        emit('error', {'msg': 'Not your turn or invalid room'}, room=sid)
        return

    if rooms[room].get('game_over'):
        emit('error', {'msg': 'Game is over. Please start a new game.'}, room=sid)
        return

    if room in timers and timers[room]:
        timers[room].cancel()

    player = rooms[room]['players'][sid]
    if card in player['hand']:
        player['hand'].remove(card)
        point_gained = calculate_points([card])
        player['points'] += point_gained

        emit('card_discarded', {
            'username': player['username'],
            'card': card,
            'points': player['points']
        }, room=room)

        # ✅ Check win condition
        if player['points'] >= 50:
            rooms[room]['game_over'] = True
            emit('game_won', {
                'username': player['username'],
                'points': player['points']
            }, room=room)
            return

        # ✅ Check if all players have no cards left (deck is also empty)
        all_hands_empty = all(len(p['hand']) == 0 for p in rooms[room]['players'].values())
        deck_empty = len(rooms[room]['deck']) == 0

        if all_hands_empty and deck_empty:
            rooms[room]['game_over'] = True
            emit('game_over_no_winner', {
                'msg': 'Game over. No more cards and no player reached 50 points.'
            }, room=room)
            return

        # ➕ Advance turn
        rooms[room]['current_turn'] = (rooms[room]['current_turn'] + 1) % len(rooms[room]['turn_order'])
        next_sid = rooms[room]['turn_order'][rooms[room]['current_turn']]

        scores = {
            sid: {
                'username': p['username'],
                'points': p['points']
            } for sid, p in rooms[room]['players'].items()
        }
        emit('update_scores', scores, room=room)
        emit('your_turn', {'username': rooms[room]['players'][next_sid]['username']}, room=room)
        start_turn_timer(room)
    else:
        emit('error', {'msg': 'Card not in hand'}, room=sid)



@socketio.on('disconnect')
def on_disconnect():
    for room in list(rooms):
        if request.sid in rooms[room]['players']:
            username = rooms[room]['players'][request.sid]['username']
            del rooms[room]['players'][request.sid]
            leave_room(room)
            emit('player_left', {'username': username}, room=room)
            if not rooms[room]['players']:
                del rooms[room]

@app.route('/leaderboard')
def leaderboard():
    top_scores = GameHistory.query.order_by(GameHistory.points.desc()).limit(10).all()
    return render_template('leaderboard.html', scores=top_scores)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)