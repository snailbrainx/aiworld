# aiworld.py
from bot import Bot
from database import get_db_connection
from config import API_ENDPOINT, BEARER_TOKEN
from utils import getColumnCharacterToNumber

class AIWorld:
    def __init__(self):
        self.cnx = get_db_connection()
        self.cursor = self.cnx.cursor()
        self.bots = self.fetch_and_initialize_bots(self.cursor, self.cnx, API_ENDPOINT, BEARER_TOKEN)

    def fetch_and_initialize_bots(self, cursor, cnx, api_endpoint, bearer_token):
        cursor.execute("SELECT name, personality, start_pos, ability FROM entities")
        entities = cursor.fetchall()
        bots = [Bot(cursor, cnx, entity=entity[0], personality=entity[1], initial_position=entity[2],
                    api_endpoint=api_endpoint, bearer_token=bearer_token, ability=entity[3]) for entity in entities]
        for bot in bots:
            bot.add_bots(bots)
        for bot in bots:
            bot.fetch_and_set_initial_position()
        return bots
    
    def remove_dead_bots(self):
        self.bots = [bot for bot in self.bots if bot.is_alive()]

    def run(self):
        while True:
            self.remove_dead_bots()
            bot_data = [
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
            for bot in self.bots:
                bot.communicate_with_bot(bot_data)

    def __del__(self):
        try:
            self.cursor.close()
            self.cnx.close()
        except ReferenceError:
            pass

if __name__ == "__main__":
    aiworld = AIWorld()
    aiworld.run()