# bot.py
import requests
import json
import datetime
import random
from utils import create_grid, getColumnCharacterToNumber, get_movable_coordinates
from database import get_db_connection
from openai_module import get_openai_response

class Bot:
    def __init__(self, cursor, cnx, entity='Bob', personality='', initial_position='A1', bots=[], ability='', action=''):
        self.cursor = cursor
        self.cnx = cnx
        self.entity = entity
        self.ability = ability
        self.action = action
        self.personality = personality
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
        try:
            # Serialize the dictionary to JSON string format
            user_content = json.dumps(data)
            # Getting the raw response from the OpenAI module
            response_json = get_openai_response(user_content)
            print(f"Raw JSON response from OpenAI for {self.entity}:\n", response_json)

            # Try parsing the JSON response to the dictionary
            response_dict = json.loads(response_json)
            print(f"Parsed response for {self.entity} after JSON loads:\n", response_dict)

            return response_dict
        except json.JSONDecodeError as e:
            print(f'JSON Decoding error while processing response for {self.entity}:', e)
        except Exception as error:
            print(f'General error occurred while sending data to {self.entity}:', error)
        
        # If we can't parse or if an error occurs, return None or a default response structure
        return None

    def insert_data(self, entity, thought, talk, move, position, time, health_points, ability_target):
        query = ("INSERT INTO aiworld "
              "(time, position, entity, thought, talk, move, health_points, ability, timestamp) "
              "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
        values = (time, position, entity, thought, talk, move, health_points, ability_target, datetime.datetime.now())
        print("Inserting into Database:\n", query)
        self.cursor.execute(query, values)
        self.cnx.commit()

    def fetch_last_data(self):
        self.cursor.execute("SELECT time, position, entity, thought, talk, move, health_points, ability FROM aiworld WHERE entity=? ORDER BY time DESC LIMIT 1", (self.entity,))
        row = self.cursor.fetchone()
        if row:
            time = row[0] + 1
            position = row[5] if row[5] in create_grid() else row[1]
            health_points = row[6]
            ability = row[7]
            self.cursor.execute("SELECT time, position, entity, thought, talk, move, health_points, ability FROM aiworld WHERE entity=? ORDER BY time DESC LIMIT 12",
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
                self.cursor.execute("SELECT position, talk, health_points, ability FROM aiworld WHERE entity=? AND time<=? ORDER BY time DESC LIMIT 1", (other_bot.entity, a_row['time']))
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
        self.cursor.execute("SELECT position, talk FROM aiworld WHERE entity=? ORDER BY time DESC LIMIT 1", (entity,))
        row = self.cursor.fetchone()
        if row:
            position, talk = row[0], row[1]
        else:
            position, talk = self.initial_position, ""
        return position, talk

    def communicate_with_bot(self, bot_data):
        # Fetch the last data stored from the previous communications or initial defaults
        time, position, self.history, health_points, ability = self.fetch_last_data()
        self.position = position

        # Create a list of valid positions that the bot can move to on a grid
        grid = create_grid()
        movable_coordinates = get_movable_coordinates(position, grid)
        nearby_entities = {}

        # Calculate the current position numerically for comparison
        col = getColumnCharacterToNumber(self.position[0])
        row = int(self.position[1:])

        # Evaluate and collect data on bots within a certain distance
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
        
        # Fetch and format the history data for nearby entities compared with the current bot
        updated_history = self.fetch_nearby_entities_for_history()
        bot_info = self.generate_bot_data(time, position, movable_coordinates, nearby_entities, updated_history, health_points)

        # Send formatted data to the openai module and receive a response dict
        response = self.send_to_bot(bot_info)
        print(f"Response from {self.entity} AI Bot:\n", json.dumps(response, indent=2))

        # Process the received response, check and manipulate data based on the action defined
        if response:
            next_position = response.get('move', position)
            ability_target = response.get('ability', '0')
            thought = response.get('thought', '')
            talk = response.get('talk', '')

            # Insert the processed data back into the database
            self.insert_data(self.entity, thought, talk, next_position, position, time, self.health_points, ability_target)

            # Check if the bot used an ability on another bot
            if ability_target != '0':
                target_entity = ability_target

                # Fetch the ability and boss status of the current bot from the entities table
                query = "SELECT ability, boss FROM entities WHERE name = ?"
                values = (self.entity,)
                self.cursor.execute(query, values)
                result = self.cursor.fetchone()

                if result:
                    bot_ability, is_boss = result[0], result[1]

                    if bot_ability == 'attack':
                        damage = random.randint(10, 50) if is_boss else 10
                        query = """
                        UPDATE aiworld 
                        SET health_points = (CASE WHEN health_points - ? < 0 THEN 0 ELSE health_points - ? END) 
                        WHERE entity = ? AND time = (SELECT MAX(time) FROM aiworld WHERE entity = ?)
                        """
                        values = (damage, damage, target_entity, target_entity)
                        self.cursor.execute(query, values)
                        self.cnx.commit()
                    elif bot_ability == 'heal':
                        healing = random.randint(10, 50) if is_boss else 10
                        query = """
                        UPDATE aiworld 
                        SET health_points = (CASE WHEN health_points + ? > 100 THEN 100 ELSE health_points + ? END) 
                        WHERE entity = ? AND time = (SELECT MAX(time) FROM aiworld WHERE entity = ?)
                        """
                        values = (healing, healing, target_entity, target_entity)
                        self.cursor.execute(query, values)
                        self.cnx.commit()

        else:
            print("No valid data received from bot")

        # This loop appears to update the bot_data with results from this specific communication routine.
        for bdata in bot_data:
            if bdata['entity'] == self.entity:
                bdata['position'] = self.position
                bdata['time'] = self.fetch_last_data()[0]
                bdata['talk'] = self.fetch_current_talk_and_position(self.entity)[1]
                bdata['pos_col'] = getColumnCharacterToNumber(self.position[0])
                bdata['pos_row'] = int(self.position[1:])
                bdata['health_points'] = self.health_points
                bdata['action'] = f"{self.ability}:{ability_target}" if ability_target != '0' else ''