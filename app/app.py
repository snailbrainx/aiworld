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
            UPDATE entities SET name=?, personality=?, start_pos=?, image=?, ability=?, boss=?, hp=?
            WHERE id=?
        ''', (data['name'], data['personality'], data['start_pos'], data['image'], data['ability'], data['boss'], data['hp'], data['id']))
    else:
        # Create new entity
        cursor.execute('''
            INSERT INTO entities (name, personality, start_pos, image, ability, boss, hp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['name'], data['personality'], data['start_pos'], data['image'], data['ability'], data['boss'], data['hp']))
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

@app.route('/')
def index():
    return render_template('index.html')

def send_bot_data():
    while True:
        data = data_queue.get()
        socketio.emit('bot_data', data)

def signal_handler(sig, frame):
    stop_process()
    sys.exit(0)

if __name__ == '__main__':
    initialize_db()  # Ensure database setup
    signal.signal(signal.SIGINT, signal_handler)
    socketio.start_background_task(target=send_bot_data)
    socketio.run(app, debug=False)