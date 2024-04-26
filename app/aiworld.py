# aiworld.py
from bot import Bot
from database import get_db_connection
import time
from utils import load_obstacle_layer
from db_functions import fetch_and_initialize_bots

class AIWorld:
    def __init__(self, paused, data_queue):
        self.cnx = get_db_connection()
        self.cursor = self.cnx.cursor()
        self.obstacle_data = load_obstacle_layer('dungeon.json')
        self.bots = self.fetch_and_initialize_bots()
        self.paused = paused

        self.running = True
        self.data_queue = data_queue
        self.current_bot_index = 0

    def run(self):
        while self.running:
            if not self.paused.value:
                self.remove_dead_bots()  # Could remove bots potentially changing indices
                bot_data = self.collect_bot_data()

                # Make sure the index is still valid
                if self.current_bot_index >= len(self.bots):
                    self.current_bot_index = 0  # Reset if exceeded the list due to removals
                    
                for i in range(self.current_bot_index, len(self.bots)):
                    bot = self.bots[i]
                    if self.paused.value:
                        self.current_bot_index = i  # Save the next to process
                        break

                    bot.communicate_with_bot(bot_data)
                    self.send_data_callback()  # Send data after each bot is processed

                if not self.paused.value or self.current_bot_index >= len(self.bots):
                    self.current_bot_index = 0  # Reset index after all bots have been processed

            time.sleep(1)  # Sleep time to handle both cases outside of conditioning

    def collect_bot_data(self):
        return [
            {
                "entity": bot.entity,
                "time": bot.fetch_last_data()[0],
                "x": bot.x,
                "y": bot.y,
                "talk": bot.fetch_current_talk_and_position(bot.entity)[1],
                "health_points": bot.fetch_last_data()[3]
            }
            for bot in self.bots
        ]

    def fetch_and_initialize_bots(self):
        entities = fetch_and_initialize_bots(self.cursor)
        bots = [Bot(self.cursor, self.cnx, entity=entity[0], personality=entity[1], x=entity[2], y=entity[3], action=entity[4], sight_distance=entity[5], obstacle_data=self.obstacle_data) for entity in entities]
        for bot in bots:
            bot.add_bots(bots)
        return bots

    def remove_dead_bots(self):
        initial_bot_count = len(self.bots)
        self.bots = [bot for bot in self.bots if bot.is_alive()]
        removed_count = initial_bot_count - len(self.bots)
        
        # Assumption: Bots are not added during the run, only removed.
        if removed_count > 0:
            # Calculate how many bots before current_bot_index were removed
            dead_before_current = sum(1 for bot in self.bots[:self.current_bot_index] if not bot.is_alive())
            self.current_bot_index = max(0, self.current_bot_index - dead_before_current)

    def send_data_callback(self):
        cnx = get_db_connection()
        cursor = cnx.cursor()

        # Fetch bot data
        sql = """
            SELECT
                a1.entity,
                a1.x,
                a1.y,
                a1.id,
                a1.thought,
                a1.talk,
                a1.time,
                a1.health_points,
                a1.action,
                a1.action_target,
                e.image,
                e.hp AS max_hp
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

        # Convert the bot data to a list of dictionaries
        result = []
        for row in data:
            result.append({
                'entity': row[0],
                'x': row[1],
                'y': row[2],
                'id': row[3],
                'thought': row[4],
                'talk': row[5],
                'time': row[6],
                'health_points': row[7],
                'action': row[8],
                'action_target': row[9],
                'image': row[10],
                'max_hp': row[11]
            })

        # Fetch item data
        cursor.execute("""
            SELECT i.name, i.image, wi.x, wi.y
            FROM world_items wi
            JOIN items i ON wi.item_id = i.id
        """)
        item_data = cursor.fetchall()

        # Convert the item data to a list of dictionaries
        items = []
        for row in item_data:
            items.append({
                'name': row[0],
                'image': row[1],
                'x': row[2],
                'y': row[3]
            })

        # Close the cursor and connection after all queries have been executed
        cursor.close()
        cnx.close()

        # Send both bot data and item data
        self.data_queue.put({'bots': result, 'items': items})

        # Convert the item data to a list of dictionaries
        items = []
        for row in item_data:
            items.append({
                'name': row[0],
                'image': row[1],
                'x': row[2],
                'y': row[3]
            })

        # Send both bot data and item data
        self.data_queue.put({'bots': result, 'items': items})

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