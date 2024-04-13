# app.py
from flask import Flask, render_template, jsonify, url_for, request
from aiworld import AIWorld
from database import get_db_connection
from multiprocessing import Process, Value
import signal
import sys

app = Flask(__name__)
game_running = Value('b', True)
paused = Value('b', False)

def run_aiworld(paused):
    aiworld_instance = AIWorld(paused)
    while game_running.value:
        aiworld_instance.run()
    aiworld_instance.stop()
    aiworld_instance.close_db_connection()

def signal_handler(sig, frame):
    print('Keyboard interrupt received. Exiting gracefully...')
    game_running.value = False
    if aiworld_process:
        aiworld_process.join()
    sys.exit(0)

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

@app.route('/pause', methods=['POST'])
def pause_aiworld():
    paused.value = True
    print("Paused AIWorld")
    return jsonify({"message": "AIWorld paused"})

@app.route('/resume', methods=['POST'])
def resume_aiworld():
    paused.value = False
    print("Resumed AIWorld")
    return jsonify({"message": "AIWorld resumed"})

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    aiworld_process = Process(target=run_aiworld, args=(paused,))
    aiworld_process.start()
    app.run(debug=False)