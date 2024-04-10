# bot.py
import requests
import json
import datetime
from utils import create_grid, getColumnCharacterToNumber, get_movable_coordinates
from database import get_db_connection
from config import API_ENDPOINT, BEARER_TOKEN

class Bot:
    def __init__(self, cursor, cnx, entity='Bob', personality='', initial_position='A1', api_endpoint='', bearer_token='', bots=[], ability='', action=''):
        self.cursor = cursor
        self.cnx = cnx
        self.entity = entity
        self.ability = ability
        self.action = action
        self.personality = personality
        self.bearer_token = bearer_token
        self.api_endpoint = api_endpoint
        self.position = initial_position
        self.initial_position = initial_position
        self.bots = bots
        self.health_points = 100  # Initialize health points to 100

    def fetch_and_set_initial_position(self):
        time, position, history, health_points, ability = self.fetch_last_data()
        if position in create_grid():
            self.position = position
        else:
            self.position = self.initial_position

    def add_bots(self, bots):
        self.bots = bots

    def generate_bot_data(self, time, position, movable_coordinates, nearby_entities, history, health_points):
            data = {
                "present_time":{
                    "your_name": self.entity,
                    "your_personality": self.personality,
                    "available_ability": self.ability,
                    "health_points": health_points,
                    "time": time,
                    "position": position,
                    "movable_coordinates": movable_coordinates,
                    "nearby_entities": nearby_entities
                },
                "history": history
            }
            return data

    def is_alive(self):
        return self.fetch_last_data()[3] > 0

    def send_to_bot(self, data):
        print(f'Data sent to {self.entity} AI Bot:\n', json.dumps(data, indent=2))
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        try:
            response = requests.post(self.api_endpoint, headers=headers, json={"question": json.dumps(data)})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as error:
            print(f'HTTP Error occured while sending data to {self.entity}:', error)
        except requests.exceptions.ConnectionError as error:
            print(f'Error Connecting while sending data to {self.entity}:', error)
        except requests.exceptions.Timeout as error:
            print(f'Timeout Error occured while sending data to {self.entity}:', error)
        except requests.exceptions.RequestException as error:
            print(f'Error occured while sending data to {self.entity}:', error)

    def insert_data(self, entity, thought, talk, move, position, time, health_points, ability_target):
        query = ("INSERT INTO aiworld "
                "(time, position, entity, thought, talk, move, health_points, ability, timestamp) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)")
        values = (time, position, entity, thought, talk, move, health_points, ability_target, datetime.datetime.now())
        print("Inserting into Database:\n", query)
        self.cursor.execute(query, values)
        self.cnx.commit()

    def fetch_last_data(self):
        self.cursor.execute("SELECT time, position, entity, thought, talk, move, health_points, ability FROM aiworld WHERE entity=%s ORDER BY time DESC LIMIT 1",
                            (self.entity,))
        row = self.cursor.fetchone()
        if row:
            time = row[0] + 1
            position = row[5] if row[5] in create_grid() else row[1]
            health_points = row[6]
            ability = row[7]
            self.cursor.execute("SELECT time, position, entity, thought, talk, move, health_points, ability FROM aiworld WHERE entity=%s ORDER BY time DESC LIMIT 20",
                                (self.entity,))
            all_rows = self.cursor.fetchall()
            history = []
            for a_row in all_rows:
                current_dict = dict(zip(('time', 'position', 'entity', 'thought', 'talk', 'move', 'health_points', 'ability'), a_row))
                history.append(current_dict)
        else:
            time = 1
            position = self.initial_position
            health_points = 100
            ability = ''
            history = []
        self.health_points = health_points  # Update the bot's health_points attribute
        print(f'Fetched Data for {self.entity}:\n', row)
        return time, position, history, health_points, ability
    
    def fetch_nearby_entities_for_history(self):
        history = []
        for a_row in self.history:
            current_dict = a_row
            nearby_entities_from_past = []
            for other_bot in self.bots:
                if other_bot.entity == self.entity:
                    # Update the current bot's action in the same format as nearby entities
                    if current_dict['ability'] and current_dict['ability'] != '0':
                        current_dict['action'] = f"{self.ability}:{current_dict['ability']}"
                    else:
                        current_dict.pop('ability', None)  # Remove the 'ability' field if it's '0' or empty
                    continue
                self.cursor.execute("SELECT position, talk, health_points, ability FROM aiworld WHERE entity=%s AND time<=%s ORDER BY time DESC LIMIT 1", (other_bot.entity, a_row['time']))
                row = self.cursor.fetchone()
                if row:
                    other_bot_position, other_bot_talk, other_bot_health_points, other_bot_ability = row[0], row[1], row[2], row[3]
                    if ':' in other_bot_ability:
                        other_bot_action = other_bot_ability
                    else:
                        other_bot_action = f"{other_bot.ability}:{other_bot_ability}" if other_bot_ability and other_bot_ability != '0' else ''
                    pos_col = getColumnCharacterToNumber(other_bot_position[0])
                    pos_row = int(other_bot_position[1:])
                    self_col = getColumnCharacterToNumber(current_dict['position'][0])
                    self_row = int(current_dict['position'][1:])
                    if max(abs(pos_col - self_col), abs(pos_row - self_row)) <= 2:
                        nearby_entity = {
                            "name": other_bot.entity,
                            "talks": other_bot_talk,
                            "position": other_bot_position,
                            "health_points": other_bot_health_points
                        }
                        if other_bot_action:
                            nearby_entity["action"] = other_bot_action
                        nearby_entities_from_past.append(nearby_entity)
            current_dict["nearby_entities"] = nearby_entities_from_past if nearby_entities_from_past else {"nearby": []}
            history.append(current_dict)
        return history

    def fetch_current_talk_and_position(self, entity):
        self.cursor.execute("SELECT position, talk FROM aiworld WHERE entity=%s ORDER BY time DESC LIMIT 1", (entity,))
        row = self.cursor.fetchone()
        if row:
            position, talk = row[0], row[1]
        else:
            position, talk = self.initial_position, ""
        return position, talk

    def communicate_with_bot(self, bot_data):
        time, position, self.history, health_points, ability = self.fetch_last_data()
        self.position = position
        grid = create_grid()
        movable_coordinates = get_movable_coordinates(position, grid)
        nearby_entities = {}
        col = getColumnCharacterToNumber(self.position[0])
        row = int(self.position[1:])
        for other_bot in self.bots:
            if other_bot.entity == self.entity:
                continue
            other_bot_position, other_bot_talk = other_bot.fetch_current_talk_and_position(other_bot.entity)
            other_bot_health_points, other_bot_ability = other_bot.fetch_last_data()[3], other_bot.fetch_last_data()[4]
            other_bot_action = f"{other_bot.ability}:{other_bot_ability}" if other_bot_ability else ''
            if max(abs(getColumnCharacterToNumber(other_bot_position[0]) - col), abs(int(other_bot_position[1:]) - row)) <= 2:
                if not nearby_entities:
                    nearby_entities = {"nearby": []}
                nearby_entity = {
                    "name": other_bot.entity,
                    "talks": other_bot_talk if other_bot_talk else "",
                    "position": other_bot_position,
                    "health_points": other_bot_health_points
                }
                if other_bot_action and other_bot_action not in ["attack:0", "heal:0"]:
                    nearby_entity["action"] = other_bot_action
                nearby_entities['nearby'].append(nearby_entity)
        updated_history = self.fetch_nearby_entities_for_history()
        bot_info = self.generate_bot_data(time, position, movable_coordinates, nearby_entities, updated_history, health_points)
        response = self.send_to_bot(bot_info)
        print(f"Response from {self.entity} AI Bot:\n", json.dumps(response, indent=2))
        next_position = response['json']['move'] if response and 'json' in response and 'move' in response['json'] and response['json']['move'] in bot_info['present_time']['movable_coordinates'] else position
        ability_target = response['json']['ability'] if response and 'json' in response and 'ability' in response['json'] else '0'
           
        if response and 'json' in response:
            ability_target = response['json']['ability'] if response and 'json' in response and 'ability' in response['json'] else '0'
            
            # Remove any "attack:" or "heal:" prefix from the ability_target
            if ability_target.startswith("attack:") or ability_target.startswith("heal:"):
                ability_target = ability_target.split(":", 1)[1]
            
            self.insert_data(self.entity, response['json']['thought'], response['json']['talk'], next_position, position, time, self.health_points, ability_target)
            
            # Check if the bot used an ability on another bot
            if ability_target != '0':
                target_entity = ability_target
                
                # Fetch the ability of the current bot from the entities table
                query = "SELECT ability FROM entities WHERE name = %s"
                values = (self.entity,)
                self.cursor.execute(query, values)
                result = self.cursor.fetchone()
                
                if result:
                    bot_ability = result[0]
                    
                    # Check if the ability is attack or heal
                    if bot_ability == 'attack':
                        # Reduce the health points of the target bot by 10
                        query = "UPDATE aiworld SET health_points = GREATEST(health_points - 10, 0) WHERE entity = %s ORDER BY time DESC LIMIT 1"
                        values = (target_entity,)
                        self.cursor.execute(query, values)
                        self.cnx.commit()
                    elif bot_ability == 'heal':
                        # Increase the health points of the target bot by 10, capped at 100
                        query = "UPDATE aiworld SET health_points = LEAST(health_points + 10, 100) WHERE entity = %s ORDER BY time DESC LIMIT 1"
                        values = (target_entity,)
                        self.cursor.execute(query, values)
                        self.cnx.commit()
        else:
            print("No valid data received from bot")

        for bdata in bot_data:
            if bdata['entity'] == self.entity:
                bdata['position'] = self.position
                bdata['time'] = self.fetch_last_data()[0]
                bdata['talk'] = self.fetch_current_talk_and_position(self.entity)[1]
                bdata['pos_col'] = getColumnCharacterToNumber(self.position[0])
                bdata['pos_row'] = int(self.position[1:])
                bdata['health_points'] = self.health_points
                bdata['action'] = f"{self.ability}:{ability_target}" if ability_target != '0' else ''