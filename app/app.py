# app.py
from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO, emit
from aiworld import AIWorld
from database import get_db_connection, initialize_db
from multiprocessing import Process, Value, Queue
import signal
import sys
import json

app = Flask(__name__)
socketio = SocketIO(app)

# Shared memory values to manage state
game_running = Value('b', False)
paused = Value('b', False)
data_queue = Queue()
aiworld_process = None

def run_aiworld(paused, data_queue):
    aiworld_instance = AIWorld(paused, data_queue)
    aiworld_instance.run()

def start_process():
    global aiworld_process
    game_running.value = True
    paused.value = False  # To activate the run method in AIWorld
    if aiworld_process is None or not aiworld_process.is_alive():
        aiworld_process = Process(target=run_aiworld, args=(paused, data_queue))
        aiworld_process.start()

def stop_process():
    global aiworld_process
    game_running.value = False
    if aiworld_process and aiworld_process.is_alive():
        aiworld_process.terminate()
        aiworld_process.join()
        aiworld_process = None

def insert_initial_positions():
    cnx = get_db_connection()
    cursor = cnx.cursor()
    # Insert initial positions for when reseting
    cursor.execute('''
        INSERT INTO aiworld (time, x, y, entity, health_points, thought, talk, move_direction, move_distance, ability, ability_target, timestamp)
        SELECT 1, start_x, start_y, name, hp, '', '', '', 0, '', '', CURRENT_TIMESTAMP FROM entities;
    ''')
    cnx.commit()
    cursor.close()
    cnx.close()

def clear_aiworld_table():
    cnx = get_db_connection()
    cursor = cnx.cursor()
    cursor.execute("DELETE FROM aiworld")
    cnx.commit()
    cursor.close()
    cnx.close()

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'status': 'running' if game_running.value else 'stopped'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('reset')
def handle_reset():
    stop_process()  # Stop the AIWorld process
    clear_aiworld_table()  # Clear the aiworld table
    insert_initial_positions()  # Reinsert initial positions
    emit('reset_response', {"message": "AIWorld has been reset"}, broadcast=True)
    emit('status', {'status': 'stopped'}, broadcast=True)  # Emit the updated status

@socketio.on('start')
def handle_start():
    start_process()
    emit('status', {'status': 'running'}, broadcast=True)
    emit('start_response', {"message": "AIWorld started"}, broadcast=True)

@socketio.on('stop')
def handle_stop():
    stop_process()
    emit('status', {'status': 'stopped'}, broadcast=True)
    emit('stop_response', {"message": "AIWorld stopped"}, broadcast=True)

@socketio.on('pause')
def handle_pause():
    paused.value = True
    emit('pause_response', {"message": "AIWorld paused"}, broadcast=True)

@socketio.on('resume')
def handle_resume():
    paused.value = False
    emit('resume_response', {"message": "AIWorld resumed"}, broadcast=True)

@app.route('/config')
def config():
    return render_template('config.html')

@app.route('/api/entities', methods=['GET'])
def get_entities():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entities')
    entities = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(entity) for entity in entities])

@app.route('/api/entities/<int:id>', methods=['GET'])
def get_entity(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entities WHERE id = ?', (id,))
    entity = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify(dict(entity))

@app.route('/api/entities', methods=['POST'])
def create_or_update_entity():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    if data.get('id'):
        # Update existing entity
        cursor.execute('''
            UPDATE entities SET name=?, personality=?, start_x=?, start_y=?, image=?, ability=?, boss=?, hp=?, sight_dist=?, max_travel_distance=?
            WHERE id=?
        ''', (
            data['name'], data['personality'], 
            data['start_x'], data['start_y'], 
            data['image'], data['ability'], 
            data['boss'], data['hp'], 
            data['sight_dist'], data['max_travel_distance'],
            data['id']
        ))
    else:
        # Create new entity
        cursor.execute('''
            INSERT INTO entities (name, personality, start_x, start_y, image, ability, boss, hp, sight_dist, max_travel_distance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'], data['personality'], 
            data['start_x'], data['start_y'], 
            data['image'], data['ability'], 
            data['boss'], data['hp'], 
            data['sight_dist'], data['max_travel_distance']
        ))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/entities/<int:id>', methods=['DELETE'])
def delete_entity(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM entities WHERE id = ?', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/output_format', methods=['GET', 'POST'])
def output_format():
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        cursor.execute('''
            UPDATE output_format SET type=?, description=?
            WHERE property=?
        ''', (data['type'], data['description'], data['property']))
        conn.commit()
    cursor.execute('SELECT * FROM output_format')
    formats = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(row) for row in formats])

@app.route('/api/entities/metadata', methods=['GET'])
def get_entities_metadata():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(entities)')
    columns = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([{'name': col['name'], 'type': col['type']} for col in columns])

@app.route('/api/abilities', methods=['GET'])
def get_abilities():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM abilities')
    abilities = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(ability) for ability in abilities])

@app.route('/api/abilities', methods=['POST'])
def create_or_update_ability():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    if data.get('id'):
        # Update existing ability
        cursor.execute('''
            UPDATE abilities SET ability=?, range=?, min_value=?, max_value=?
            WHERE id=?
        ''', (
            data['ability'], data['range'],
            data['min_value'], data['max_value'],
            data['id']
        ))
    else:
        # Create new ability
        cursor.execute('''
            INSERT INTO abilities (ability, range, min_value, max_value)
            VALUES (?, ?, ?, ?)
        ''', (
            data['ability'], data['range'],
            data['min_value'], data['max_value']
        ))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/abilities/<int:id>', methods=['DELETE'])
def delete_ability(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM abilities WHERE id = ?', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/system_prompt', methods=['GET'])
def get_system_prompt():
    with open('system_prompt.txt', 'r') as file:
        content = file.read()
    return jsonify({'content': content})

@app.route('/api/system_prompt', methods=['POST'])
def update_system_prompt():
    data = request.get_json()
    with open('system_prompt.txt', 'w') as file:
        file.write(data['content'])
    return jsonify({'success': True})

@app.route('/')
def index():
    return render_template('index.html')

def send_bot_data():
    while True:
        data = data_queue.get()
        print("Received data to send over socket:", data)
        socketio.emit('bot_data', data)

def signal_handler(sig, frame):
    stop_process()
    sys.exit(0)

if __name__ == '__main__':
    initialize_db()  # Ensure database setup
    signal.signal(signal.SIGINT, signal_handler)
    socketio.start_background_task(target=send_bot_data)
    socketio.run(app, debug=False)