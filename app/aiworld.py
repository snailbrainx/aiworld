# aiworld.py
from bot import Bot
from database import get_db_connection
from utils import getColumnCharacterToNumber
import time

class AIWorld:
    def __init__(self, paused, data_queue):
        self.cnx = get_db_connection()
        self.cursor = self.cnx.cursor()
        self.bots = self.fetch_and_initialize_bots()
        self.paused = paused
        self.running = True
        self.data_queue = data_queue

    def run(self):
        while self.running:
            if not self.paused.value:
                self.remove_dead_bots()
                bot_data = self.collect_bot_data()
                for i, bot in enumerate(self.bots):
                    bot.communicate_with_bot(bot_data)
                    self.send_data_callback()  # Send data after each bot is processed
                    if self.paused.value:
                        break  # Exit the loop if paused
                while self.paused.value:
                    time.sleep(1)  # Wait if paused
            else:
                time.sleep(1)

    def collect_bot_data(self):
        return [
            {
                "entity": bot.entity,
                "time": bot.fetch_last_data()[0],
                "position": bot.fetch_current_talk_and_position(bot.entity)[0],
                "talk": bot.fetch_current_talk_and_position(bot.entity)[1],
                "pos_col": getColumnCharacterToNumber(bot.position[0]),
                "pos_row": int(bot.position[1:]),
                "health_points": bot.fetch_last_data()[3]
            }
            for bot in self.bots
        ]

    def fetch_and_initialize_bots(self):
        self.cursor.execute("SELECT name, personality, start_pos, ability FROM entities")
        entities = self.cursor.fetchall()
        bots = [Bot(self.cursor, self.cnx, entity=entity[0], personality=entity[1],
                    initial_position=entity[2], ability=entity[3]) for entity in entities]
        # Ensure each bot is aware of the others
        for bot in bots:
            bot.add_bots(bots)
        return bots

    def remove_dead_bots(self):
        self.bots = [bot for bot in self.bots if bot.is_alive()]

    def send_data_callback(self):
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
        self.data_queue.put(result)

    def stop(self):
        self.running = False

    def __del__(self):
        try:
            self.cursor.close()
            self.cnx.close()
        except ReferenceError:
            pass

if __name__ == "__main__":
    from multiprocessing import Value, Queue
    paused = Value('b', True)
    data_queue = Queue()
    aiworld = AIWorld(paused, data_queue)
    aiworld.run()