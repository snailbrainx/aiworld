# app.py
from flask import Flask, render_template, jsonify, request
from aiworld import AIWorld
from database import get_db_connection
from multiprocessing import Process, Value
import signal
import sys

app = Flask(__name__)

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

@app.route('/reset', methods=['POST'])
def reset_aiworld():
    stop_process()  # Stop the AIWorld process
    clear_aiworld_table()  # Clear the aiworld table
    return jsonify({"message": "AIWorld has been reset"})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/botData')
def bot_data():
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
            e.ability AS entity_ability
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
            'entity_ability': row[9]
        })

    return jsonify(result)

@app.route('/start', methods=['POST'])
def start_aiworld():
    start_process()
    return jsonify({"message": "AIWorld started"})

@app.route('/stop', methods=['POST'])
def stop_aiworld():
    stop_process()
    return jsonify({"message": "AIWorld stopped"})

@app.route('/pause', methods=['POST'])
def pause_aiworld():
    paused.value = True
    return jsonify({"message": "AIWorld paused"})

@app.route('/resume', methods=['POST'])
def resume_aiworld():
    paused.value = False
    return jsonify({"message": "AIWorld resumed"})

@app.route('/status', methods=['GET'])
def get_status():
    if aiworld_process and aiworld_process.is_alive():
        if paused.value:
            return jsonify({"status": "paused"})
        else:
            return jsonify({"status": "running"})
    return jsonify({"status": "stopped"})

def signal_handler(sig, frame):
    stop_process()
    sys.exit(0)

if __name__ == '__main__':
    from database import initialize_db
    initialize_db()  # Ensure database setup
    signal.signal(signal.SIGINT, signal_handler)
    app.run(debug=False)