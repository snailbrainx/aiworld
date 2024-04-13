# aiworld.py
from bot import Bot
from database import get_db_connection
from utils import getColumnCharacterToNumber
import time

class AIWorld:
    def __init__(self, paused):
        self.cnx = get_db_connection()
        self.cursor = self.cnx.cursor()
        self.bots = self.fetch_and_initialize_bots()
        self.paused = paused
        self.running = True

    def run(self):
        while self.running:
            if not self.paused.value:
                self.remove_dead_bots()
                bot_data = self.collect_bot_data()
                for i, bot in enumerate(self.bots):
                    bot.communicate_with_bot(bot_data)
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

    def stop(self):
        self.running = False

    def __del__(self):
        try:
            self.cursor.close()
            self.cnx.close()
        except ReferenceError:
            pass

if __name__ == "__main__":
    from multiprocessing import Value
    paused = Value('b', True)
    aiworld = AIWorld(paused)
    aiworld.run()