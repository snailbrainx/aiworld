# bot.py
import requests
import json
import datetime
import random
from utils import create_grid, get_movable_coordinates, is_within_sight
from database import get_db_connection
from openai_module import get_openai_response
from abilities import AbilityHandler

class Bot:
    def __init__(self, cursor, cnx, entity='Bob', personality='', initial_x=0, initial_y=0, bots=[], ability='', action='', sight_distance=10, talk=''):
        self.cursor = cursor
        self.cnx = cnx
        self.entity = entity
        self.ability = ability
        self.action = action
        self.personality = personality
        self.x = initial_x
        self.y = initial_y
        self.bots = bots
        self.health_points = 100
        self.ability_handler = AbilityHandler(cursor, cnx)
        self.sight_distance = sight_distance
        self.talk = talk  # Initialize talk attribute

    def use_ability(self, ability_name, target_entity):
        #Uses the specified ability on the target entity if the target is valid.
        if target_entity != '0':
            self.ability_handler.use_ability(self.entity, target_entity)

    def fetch_and_set_initial_position(self):
        # Assuming this method is still needed for some initialization logic
        time, x, y, history, health_points, ability = self.fetch_last_data()
        if (x, y) in create_grid():
            self.x = x
            self.y = y
        else:
            self.x = self.x  # Default to current x
            self.y = self.y  # Default to current y

    def add_bots(self, bots):
        self.bots = bots

    def generate_bot_data(self, time, position, movable_coordinates, nearby_entities, history, health_points):
        data = {
            "present_time": {
                "your_name": self.entity,
                "your_personality": self.personality,
                "available_ability": self.ability,
                "health_points": health_points,
                "time": time,
                "position": position,
                "movable_coordinates": movable_coordinates,  # This now includes directional groups
                "nearby_entities": nearby_entities
            },
            "history": history
        }
        return data

    def is_alive(self):
        return self.fetch_last_data()[4] > 0

    def send_to_bot(self, data):
        # Print the data being sent to the AI Bot
        print(f'Data sent to {self.entity} AI Bot:\n', json.dumps(data, indent=2))
        
        # Assuming valid_entities needs to be passed to get_openai_response
        valid_entities = {bot.entity for bot in self.bots}
        try:
            # Serialize the dictionary to JSON string format
            user_content = json.dumps(data)
            # Getting the raw response from the OpenAI module
            response_json = get_openai_response(user_content, valid_entities)
            
            # Print the raw JSON response from OpenAI
            print(f"Raw JSON response from OpenAI for {self.entity}:\n", response_json)

            # Try parsing the JSON response to the dictionary
            response_dict = json.loads(response_json)
            
            # Print the parsed response after JSON loads
            print(f"Parsed response for {self.entity} after JSON loads:\n", response_dict)

            return response_dict
        except json.JSONDecodeError as e:
            print(f'JSON Decoding error while processing response for {self.entity}:', e)
        except Exception as error:
            print(f'General error occurred while sending data to {self.entity}:', error)
        
        # If we can't parse or if an error occurs, return None or a default response structure
        return None

    def insert_data(self, entity, thought, talk, x, y, time, health_points, ability_target):
        query = ("INSERT INTO aiworld "
                "(time, x, y, entity, thought, talk, move, health_points, ability, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
        values = (time, x, y, entity, thought, talk, f"{x},{y}", health_points, ability_target, datetime.datetime.now())
        print("Inserting into Database:\n", query)
        self.cursor.execute(query, values)
        self.cnx.commit()

    def fetch_last_data(self):
        # Execute the query to fetch the latest record for the current entity
        self.cursor.execute("SELECT e.hp, a.time, a.x, a.y, a.entity, a.thought, a.talk, a.move, a.health_points, a.ability FROM aiworld a JOIN entities e ON a.entity = e.name WHERE a.entity=? ORDER BY a.time DESC LIMIT 1", (self.entity,))
        row = self.cursor.fetchone()
        
        if row:
            max_hp = row[0]
            time = row[1] + 1
            x = row[2]
            y = row[3]
            health_points = row[8]
            ability = row[9]
            
            # Fetch the last 12 records for history
            self.cursor.execute("SELECT time, x, y, entity, thought, talk, move, health_points, ability FROM aiworld WHERE entity=? ORDER BY time DESC LIMIT 12", (self.entity,))
            all_rows = self.cursor.fetchall()
            
            # Initialize history list and populate with data from fetched rows
            history = []
            for a_row in all_rows:
                current_dict = dict(zip(('time', 'x', 'y', 'entity', 'thought', 'talk', 'move', 'health_points', 'ability'), a_row))
                history.append(current_dict)
        else:
            # If no records are found, set default values
            max_hp = self.cursor.execute("SELECT hp FROM entities WHERE name=?", (self.entity,)).fetchone()[0]
            time = 1
            x = self.x  # Use self.x instead of self.initial_position
            y = self.y  # Use self.y instead of self.initial_position
            health_points = max_hp
            ability = ''
            history = []
        
        # Update the bot's health_points attribute
        self.health_points = health_points
        
        # Store the fetched history in self.history for use in other methods
        self.history = history
        
        return time, x, y, history, health_points, ability, max_hp
    
    def fetch_nearby_entities_for_history(self):
        history = []
        # Fetch sight distance for the current bot
        self.cursor.execute("SELECT sight_dist FROM entities WHERE name=?", (self.entity,))
        sight_dist = self.cursor.fetchone()[0]

        for a_row in self.history:
            current_dict = a_row
            nearby_entities_from_past = []
            for other_bot in self.bots:
                if other_bot.entity == self.entity:
                    continue
                self.cursor.execute("SELECT x, y, talk, health_points, ability FROM aiworld WHERE entity=? AND time<=? ORDER BY time DESC LIMIT 1", (other_bot.entity, a_row['time']))
                row = self.cursor.fetchone()
                if row:
                    other_bot_x, other_bot_y, other_bot_talk, other_bot_health_points, other_bot_ability = row[0], row[1], row[2], row[3], row[4]
                    other_bot_action = f"{other_bot.ability}:{other_bot_ability}" if other_bot_ability and other_bot_ability != '0' else ''
                    if max(abs(other_bot_x - current_dict['x']), abs(other_bot_y - current_dict['y'])) <= sight_dist:
                        nearby_entity = {
                            "name": other_bot.entity,
                            "talks": other_bot_talk,
                            "x": other_bot_x,
                            "y": other_bot_y,
                            "health_points": other_bot_health_points,
                            "action": other_bot_action
                        }
                        nearby_entities_from_past.append(nearby_entity)
            current_dict["nearby_entities"] = nearby_entities_from_past if nearby_entities_from_past else {"nearby": []}
            history.append(current_dict)
        return history

    def fetch_current_talk_and_position(self, entity):
        self.cursor.execute("SELECT x, y, talk FROM aiworld WHERE entity=? ORDER BY time DESC LIMIT 1", (entity,))
        row = self.cursor.fetchone()
        if row:
            x, y = row[0], row[1]
            talk = row[2]
        else:
            x, y = self.x, self.y  # Use current x and y if no data is found
            talk = ""
        return (x, y), talk

    def evaluate_nearby_entities(self, position, bots, width, height):
        x, y = position
        nearby_entities = {}
        for bot in bots:
            if bot.entity == self.entity:
                continue
            bot_x, bot_y = bot.x, bot.y
            if is_within_sight(x, y, bot_x, bot_y, self.sight_distance):
                bot_position, bot_talk = self.fetch_current_talk_and_position(bot.entity)
                nearby_entities[bot.entity] = {
                    "position": (bot_x, bot_y),
                    "talk": bot_talk,
                    "health_points": bot.health_points
                }
        return nearby_entities

    def communicate_with_bot(self, bot_data):
        if not self.is_alive():
            print(f"Skipping communication for dead bot {self.entity}")
            return
        time, x, y, self.history, health_points, ability, max_hp = self.fetch_last_data()

        # Create a list of valid positions that the bot can move to on a grid
        grid = create_grid(500, 500)  # Assuming a 500x500 grid
        movable_coordinates = get_movable_coordinates((x, y), 500, 500)

        # Evaluate and collect data on bots within the sight distance
        nearby_entities = self.evaluate_nearby_entities((x, y), self.bots, 500, 500)

        # Fetch and format the history data for nearby entities compared with the current bot
        updated_history = self.fetch_nearby_entities_for_history()
        bot_info = self.generate_bot_data(time, (x, y), movable_coordinates, nearby_entities, updated_history, health_points)

        # Send formatted data to the openai module and receive a response dict
        response = self.send_to_bot(bot_info)
        print(f"Response from {self.entity} AI Bot:\n", json.dumps(response, indent=2))

        # Initialize ability_target to '0' to handle cases where no response is received
        ability_target = '0'

        # Process the received response, check and manipulate data based on the action defined
        if response:
            move_response = response.get('move', f"{x},{y}")
            if move_response == '0':
                next_position = (x, y)  # No movement
            else:
                next_position = tuple(map(int, move_response.split(',')))  # Convert "x,y" to (x, y)
            ability_target = response.get('ability', '0')
            thought = response.get('thought', '')
            talk = response.get('talk', '')
            
            # Check if the next position is valid and among the movable coordinates
            if any(next_position in coords for coords in movable_coordinates.values()):
                x, y = next_position
                self.x, self.y = x, y  # Update the bot's position attributes
            
            # Insert the processed data back into the database
            self.insert_data(self.entity, thought, talk, x, y, time, health_points, ability_target)
            
            # Use the ability if specified
            if ability_target != '0':
                self.use_ability(ability, ability_target)
        else:
            print("No valid data received from bot")

        for bdata in bot_data:
            if bdata['entity'] == self.entity:
                bdata['position'] = (x, y)
                bdata['time'] = self.fetch_last_data()[0]
                bdata['talk'] = self.fetch_current_talk_and_position(self.entity)[1]
                bdata['pos_x'] = x
                bdata['pos_y'] = y
                bdata['health_points'] = self.health_points
                bdata['action'] = f"{self.ability}:{ability_target}" if ability_target != '0' else ''