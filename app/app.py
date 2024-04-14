from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from aiworld import AIWorld
from database import get_db_connection
from multiprocessing import Process, Value
import signal
import sys

app = Flask(__name__)
socketio = SocketIO(app)

# Shared memory values to manage state
game_running = Value('b', False)
paused = Value('b', False)
aiworld_process = None

def run_aiworld(paused):
    aiworld_instance = AIWorld(paused)
    aiworld_instance.run()

def start_process():
    global aiworld_process
    game_running.value = True
    paused.value = False  # To activate the run method in AIWorld
    if aiworld_process is None or not aiworld_process.is_alive():
        aiworld_process = Process(target=run_aiworld, args=(paused,))
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

@app.route('/')
def index():
    return render_template('index.html')

def send_bot_data():
    while True:
        if game_running.value:
            cnx = get_db_connection()
            cursor = cnx.cursor()
            sql = """
                SELECT
                    a1.entity,
                    a1.position,
                    a1.id,
                    a1.thought,
                    a1.talk,
                    a1.time,
                    a1.health_points,
                    a1.ability AS ability_target,
                    e.image,
                    e.ability AS entity_ability,
                    e.hp AS max_hp  -- Include the max_hp from the entities table
                FROM
                    aiworld a1
                INNER JOIN
                    (SELECT entity, MAX(time) max_time FROM aiworld GROUP BY entity) a2
                ON
                    (a1.entity = a2.entity AND a1.time = a2.max_time)
                INNER JOIN entities e ON e.name = a1.entity
            """
            cursor.execute(sql)
            data = cursor.fetchall()
            cursor.close()
            cnx.close()
            # Convert the data to a list of dictionaries
            result = []
            for row in data:
                result.append({
                    'entity': row[0],
                    'position': row[1],
                    'id': row[2],
                    'thought': row[3],
                    'talk': row[4],
                    'time': row[5],
                    'health_points': row[6],
                    'ability_target': row[7],
                    'image': row[8],
                    'entity_ability': row[9],
                    'max_hp': row[10]
                })
            socketio.emit('bot_data', result)
        socketio.sleep(2)

def signal_handler(sig, frame):
    stop_process()
    sys.exit(0)

if __name__ == '__main__':
    from database import initialize_db
    initialize_db()  # Ensure database setup
    signal.signal(signal.SIGINT, signal_handler)
    socketio.start_background_task(target=send_bot_data)
    socketio.run(app, debug=False)