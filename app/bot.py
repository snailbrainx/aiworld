# bot.py
import requests
import json
import datetime
import random
from database import get_db_connection
from openai_module import get_openai_response
from abilities import AbilityHandler
from utils import create_grid, is_within_sight, get_possible_movements, is_obstacle, get_direction_from_deltas

# bot.py
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
        self.talk = talk
        self.map_data = set()
        self.max_travel_distance = 5  # Default value
        self.fetch_initial_data()

    def update_map_data(self, new_map_data):
        self.map_data = new_map_data

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

    def fetch_initial_data(self):
        self.cursor.execute("SELECT max_travel_distance FROM entities WHERE name=?", (self.entity,))
        row = self.cursor.fetchone()
        if row:
            self.max_travel_distance = row['max_travel_distance']

    def generate_bot_data(self, time, position, possible_directions, nearby_entities, history, health_points):
        data = {
            "present_time": {
                "your_name": self.entity,
                "your_personality": self.personality,
                "available_ability": self.ability,
                "health_points": health_points,
                "time": time,
                "position": position,
                "possible_directions": possible_directions,  # Include possible directions instead of movable coordinates
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
            return response_json
        except Exception as error:
            print(f'General error occurred while sending data to {self.entity}:', error)
        
        # If an error occurs, return None or a default response structure
        return None

    def insert_data(self, entity, thought, talk, x, y, time, health_points, ability_target, move_direction, move_distance):
        query = ("INSERT INTO aiworld "
                "(time, x, y, entity, thought, talk, move_direction, move_distance, health_points, ability, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
        values = (time, x, y, entity, thought, talk, move_direction, move_distance, health_points, ability_target, datetime.datetime.now())
        print("Inserting into Database:\n", query)
        self.cursor.execute(query, values)
        self.cnx.commit()

    def fetch_last_data(self):
        # Updated SQL query to match the new database schema
        self.cursor.execute("""
            SELECT e.hp, a.time, a.x, a.y, a.entity, a.thought, a.talk, 
                a.move_direction, a.move_distance, a.health_points, a.ability 
            FROM aiworld a 
            JOIN entities e ON a.entity = e.name 
            WHERE a.entity=? 
            ORDER BY a.time DESC 
            LIMIT 1
        """, (self.entity,))
        row = self.cursor.fetchone()
        
        if row:
            max_hp = row[0]
            time = row[1] + 1
            x = row[2]
            y = row[3]
            health_points = row[9]
            ability = row[10]
            
            # Fetch the last 12 records for history
            self.cursor.execute("""
                SELECT time, x, y, entity, thought, talk, move_direction, move_distance, health_points, ability 
                FROM aiworld 
                WHERE entity=? 
                ORDER BY time DESC 
                LIMIT 12
            """, (self.entity,))
            all_rows = self.cursor.fetchall()
            
            # Initialize history list and populate with data from fetched rows
            history = []
            for a_row in all_rows:
                current_dict = dict(zip(('time', 'x', 'y', 'entity', 'thought', 'talk', 'move_direction', 'move_distance', 'health_points', 'ability'), a_row))
                history.append(current_dict)
        else:
            # If no records are found, set default values
            max_hp = self.cursor.execute("SELECT hp FROM entities WHERE name=?", (self.entity,)).fetchone()[0]
            time = 1
            x = self.x
            y = self.y
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
                    if is_within_sight(current_dict['x'], current_dict['y'], other_bot_x, other_bot_y, sight_dist):
                        dx, dy = other_bot_x - current_dict['x'], other_bot_y - current_dict['y']
                        direction, distance = get_direction_from_deltas(dx, dy)
                        nearby_entity = {
                            "name": other_bot.entity,
                            "talks": other_bot_talk,
                            "direction": direction,
                            "distance": distance,
                            "health_points": other_bot_health_points,
                            "action": other_bot_action
                        }
                        nearby_entities_from_past.append(nearby_entity)
            current_dict["nearby_entities"] = nearby_entities_from_past if nearby_entities_from_past else []
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
                dx, dy = bot_x - x, bot_y - y
                direction, distance = get_direction_from_deltas(dx, dy)
                nearby_entities[bot.entity] = {
                    "direction": direction,
                    "distance": distance,
                    "talk": bot_talk,
                    "health_points": bot.health_points
                }
        return nearby_entities

    def communicate_with_bot(self, bot_data):
        if not self.is_alive():
            print(f"Skipping communication for dead bot {self.entity}")
            return

        time, x, y, self.history, health_points, ability, max_hp = self.fetch_last_data()

        # Calculate possible movements using the unified function
        possible_movements = get_possible_movements(self.x, self.y, max_distance=self.max_travel_distance, grid_size=500, is_obstacle_func=lambda x, y: is_obstacle(x, y, self.map_data))

        # Evaluate and collect data on bots within the sight distance
        nearby_entities = self.evaluate_nearby_entities((x, y), self.bots, 500, 500)

        # Fetch and format the history data for nearby entities compared with the current bot
        updated_history = self.fetch_nearby_entities_for_history()

        # Generate bot data with the new possible movements data
        bot_info = self.generate_bot_data(time, (x, y), possible_movements, nearby_entities, updated_history, health_points)

        # Send formatted data to the openai module and receive a response dict
        response = self.send_to_bot(bot_info)
        print(f"Response from {self.entity} AI Bot:\n", json.dumps(response, indent=2))

        # Initialize ability_target to '0' to handle cases where no response is received
        ability_target = '0'

        # Process the received response, check and manipulate data based on the action defined
        if response:
            move_direction = response.get('move', 'N')  # Default to North if not specified
            move_distance = int(response.get('distance', '0'))  # Default to 1 tile if not specified
            move_distance = min(move_distance, self.max_travel_distance)  # Use the max travel distance from the database

            # Calculate new position based on direction and distance
            direction_map = {
                'N': (0, -1), 'NE': (1, -1), 'E': (1, 0), 'SE': (1, 1),
                'S': (0, 1), 'SW': (-1, 1), 'W': (-1, 0), 'NW': (-1, -1)
            }
            dx, dy = direction_map[move_direction]
            new_x, new_y = x + dx * move_distance, y + dy * move_distance

            # Ensure the new position is within bounds
            new_x = max(0, min(new_x, 499))  # Assuming grid width of 500
            new_y = max(0, min(new_y, 499))  # Assuming grid height of 500

            # Update bot's position
            self.x, self.y = new_x, new_y

            ability_target = response.get('ability', '0')
            thought = response.get('thought', '')
            talk = response.get('talk', '')

            # Insert the processed data back into the database
            self.insert_data(self.entity, thought, talk, new_x, new_y, time, health_points, ability_target, move_direction, move_distance)

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