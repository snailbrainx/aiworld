from flask import Flask, render_template, jsonify, url_for
from aiworld import AIWorld
from database import get_db_connection
import threading
import signal
import sys

app = Flask(__name__)
aiworld_thread = None
aiworld_instance = None

def run_aiworld():
    global aiworld_instance
    aiworld_instance = AIWorld()
    aiworld_instance.run()

def signal_handler(sig, frame):
    print('Keyboard interrupt received. Exiting gracefully...')
    if aiworld_instance:
        aiworld_instance.stop()
        aiworld_instance.close_db_connection()
    if aiworld_thread:
        aiworld_thread.join()
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

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    aiworld_thread = threading.Thread(target=run_aiworld)
    aiworld_thread.start()
    app.run(debug=True)