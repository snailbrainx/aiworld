# bot.py
import json
import requests
from actions import ActionHandler
from utils import (
    get_possible_movements,
    is_obstacle,
    calculate_direction_and_distance,
)
from flowise_module import get_flowise_response
from db_functions import (
    insert_data,
    fetch_last_data,
    fetch_current_talk_and_position,
    fetch_nearby_entities_for_history,
    evaluate_nearby_entities,
    fetch_nearby_items,
    fetch_bot_inventory,
    generate_summary,
    update_summary,
    remove_item_from_world,
)


class Bot:
    def __init__(
        self,
        cursor,
        cnx,
        entity='Bob',
        personality='',
        x=0,
        y=0,
        bots=None,
        action='',
        sight_distance=10,
        talk='',
        talk_distance=11,
        obstacle_data=None,
    ):
        self.cursor = cursor
        self.cnx = cnx
        self.entity = entity
        self.action = action
        self.personality = personality
        self.x = x
        self.y = y
        self.obstacle_data = obstacle_data or []
        print(f"Loaded obstacle data: {self.obstacle_data}")  # Debugging statement
        self.bots = bots or []
        self.health_points = 100
        self.action_handler = ActionHandler(cursor, cnx)
        self.sight_distance = sight_distance
        self.talk = talk
        self.talk_distance = talk_distance
        self.map_data = set()
        self.max_travel_distance = None
        self.model = None
        self.fetch_initial_data()
        self.fetch_last_data()  # Fetch last known data including position

    def update_map_data(self, new_map_data):
        self.map_data = new_map_data

    def use_action(self, action_name, target_entity):
        if target_entity != '0':
            self.action_handler.use_action(self.entity, action_name, target_entity)

    def add_bots(self, bots):
        self.bots = bots

    def fetch_initial_data(self):
        # Fetch max_travel_distance and model type
        self.cursor.execute(
            "SELECT max_travel_distance, model FROM entities WHERE name=?", (self.entity,)
        )
        row = self.cursor.fetchone()
        if row:
            self.max_travel_distance = row['max_travel_distance']
            self.model = row['model']  # Store the model type
        else:
            raise ValueError(f"No data found for entity: {self.entity}")

    def is_alive(self):
        return self.fetch_last_data()[4] > 0

    def fetch_last_data(self):
        (
            time,
            x,
            y,
            history,
            health_points,
            action,
            action_target,
            max_hp,
            summary,
        ) = fetch_last_data(self.cursor, self.entity)

        # Update the bot's health_points attribute
        self.health_points = health_points

        # Store the fetched history in self.history for use in other methods
        self.history = history

        return time, x, y, history, health_points, action, action_target, max_hp, summary

    def fetch_current_talk_and_position(self, entity):
        return fetch_current_talk_and_position(self.cursor, entity)

    def communicate_with_bot(self, bot_data):
        if not self.is_alive():
            print(f"Skipping communication for dead bot {self.entity}")
            return

        (
            time,
            x,
            y,
            self.history,
            health_points,
            action,
            action_target,
            max_hp,
            summary,
        ) = self.fetch_last_data()
        print(f"Fetched coordinates for {self.entity}: x={x}, y={y}")

        if x is None or y is None:
            print(f"Error: Invalid coordinates for {self.entity} (x={x}, y={y})")
            return

        bot_info = self.prepare_bot_info(time, x, y, health_points, max_hp, summary)
        bot_info["historical_summary"] = self.update_summary_if_needed(
            time, bot_info, summary
        )

        response = self.send_to_bot(bot_info)
        print(f"Response from {self.entity} AI Bot:\n", json.dumps(response, indent=2))

        if response:
            print(f"About to process response for {self.entity}")
            self.process_bot_response(
                response, x, y, bot_data, time, health_points, action, action_target
            )
        else:
            print("No valid data received from bot")
            self.update_bot_data(bot_data, x, y, action, action_target)

    def prepare_bot_info(self, time, x, y, health_points, max_hp, summary):
        (
            possible_movements,
            destination_direction,
        ) = self.get_possible_movements_and_direction(x, y)
        nearby_entities = self.get_nearby_entities(x, y)
        updated_history = self.get_updated_history(nearby_entities)
        items_info, self.nearby_items = self.get_items_info(x, y)
        inventory = fetch_bot_inventory(self.cursor, self.entity)

        bot_info = self.generate_bot_data(
            time,
            (x, y),
            possible_movements,
            destination_direction,
            nearby_entities,
            updated_history,
            health_points,
            max_hp,
            items_info,
            inventory,
            summary,
        )
        return bot_info

    def update_summary_if_needed(self, time, bot_info, summary):
        if time % 5 == 0:
            new_summary = generate_summary(self.cursor, bot_info)
            update_summary(self.cursor, self.cnx, self.entity, new_summary, time)
            return new_summary
        else:
            return summary

    def generate_bot_data(
        self,
        time,
        position,
        possible_directions,
        destination_direction,
        nearby_entities,
        history,
        health_points,
        max_hp,
        items_info,
        inventory,
        summary,
    ):
        data = {
            "present_time": {
                "your_name": self.entity,
                "your_personality": self.personality,
                "available_actions": [self.action, "move", "pickup", "consume"],
                "health_points": f"{health_points} / {max_hp}",
                "inventory": inventory,
                "time": time,
                "position": position,
                "possible_directions": possible_directions,
                "items": items_info,
                "destination_direction": destination_direction,
                "nearby_entities": [
                    {
                        **entity_data,
                        "health_points": f"{entity_data['health_points'].split('/')[0].strip()} / {entity_data['health_points'].split('/')[1].strip()}",
                    }
                    for entity_data in nearby_entities
                ],
            },
            "history": history,
            "historical_summary": summary,
        }
        return data

    def send_to_bot(self, data):
        print(f'Data sent to {self.entity} AI Bot:\n', json.dumps(data, indent=2))

        valid_entities = {bot.entity for bot in self.bots}
        valid_items = list(data["present_time"]["items"].keys())  # Extract item names

        try:
            user_content = json.dumps(data)
            if self.model.startswith('flowise_'):
                # Extract the specific model name for flowise_module
                model_name = self.model  # This should match one of the keys in API_URLS
                response_json = get_flowise_response(
                    user_content, valid_entities, valid_items, model_name
                )
            else:
                raise ValueError(f"Unsupported model type: {self.model}")

            print(
                f"Raw JSON response from {self.model} for {self.entity}:\n",
                response_json,
            )
            return response_json
        except Exception as error:
            print(f'General error occurred while sending data to {self.entity}:', error)

        return None

    def process_bot_response(
        self,
        response,
        x,
        y,
        bot_data,
        time,
        health_points,
        action='0',
        action_target='0',
    ):
        print(f"Entering process_bot_response for {self.entity}")
        move_direction, move_distance, new_x, new_y, valid_move = self.get_new_position(
            response, x, y
        )
        action = response.get('action', action)
        action_target = response.get('action_target', action_target)
        thought = response.get('thought', '')
        talk = response.get('talk', '')

        # Include invalid move thought if applicable
        if not valid_move:
            thought += f" {self.invalid_move_thought}"

        print(f"Processing response for {self.entity}: action={action}, target={action_target}")

        if action == 'pickup' and action_target != '0':
            self.process_pickup_action(action_target, x, y)
        elif action == 'consume' and action_target != '0':
            print(f"Attempting to consume {action_target} for {self.entity}")
            self.action_handler.use_action(self.entity, action, action_target)

        insert_data(
            self.cursor,
            self.cnx,
            self.entity,
            thought,
            talk,
            new_x,
            new_y,
            time,
            health_points,
            action,
            action_target,
            move_direction,
            move_distance,
        )

        if action not in ['0', 'pickup', 'consume', 'move'] and action_target != '0':
            print(
                f"Calling use_action for {self.entity} with action={action}, target={action_target}"
            )
            self.action_handler.use_action(self.entity, action, action_target)

        self.update_bot_data(bot_data, new_x, new_y, action, action_target)
        print(f"Exiting process_bot_response for {self.entity}")

    def process_pickup_action(self, action_target, x, y):
        item_name, item_id = action_target.rsplit('_', 1)
        for item, item_x, item_y, item_desc, id in self.nearby_items:
            if (
                item == item_name
                and int(item_id) == id
                and ((item_x - x) ** 2 + (item_y - y) ** 2) ** 0.5 <= 1.5
            ):
                self.action_handler.use_action(self.entity, 'pickup', item_name)
                remove_item_from_world(self.cursor, self.cnx, item_name, item_x, item_y)
                break

    def get_new_position(self, response, x, y):
        move_direction = response.get('direction', 'N')
        move_distance = int(response.get('distance', '0'))
        move_distance = min(move_distance, self.max_travel_distance)
        direction_map = {
            'N': (0, -1), 'NE': (1, -1), 'E': (1, 0), 'SE': (1, 1),
            'S': (0, 1), 'SW': (-1, 1), 'W': (-1, 0), 'NW': (-1, -1),
        }
        dx, dy = direction_map.get(move_direction, (0, 0))
        new_x, new_y = x + dx * move_distance, y + dy * move_distance
        new_x = max(0, min(new_x, 31))
        new_y = max(0, min(new_y, 31))
        if not is_obstacle(new_x, new_y, self.obstacle_data):
            self.x, self.y = new_x, new_y
            valid_move = True
        else:
            print(f"Move to ({new_x}, {new_y}) is invalid due to an obstacle.")
            valid_move = False
            # Log the invalid move in the bot's thought process
            self.invalid_move_thought = f"Tried to move to ({new_x}, {new_y}), but it was blocked."
            new_x, new_y = x, y
        return move_direction, move_distance, new_x, new_y, valid_move


    def update_bot_data(self, bot_data, x, y, action, action_target):
        for bdata in bot_data:
            if bdata['entity'] == self.entity:
                bdata['position'] = (x, y)
                bdata['time'] = self.fetch_last_data()[0]
                bdata['talk'] = self.fetch_current_talk_and_position(self.entity)[1]
                bdata['pos_x'] = x
                bdata['pos_y'] = y
                bdata['health_points'] = self.health_points
                bdata['action'] = f"{action}:{action_target}" if action_target != '0' else ''

    def get_possible_movements_and_direction(self, x, y):
        self.cursor.execute("SELECT name, x, y FROM destinations")
        destinations = {row[0]: (row[1], row[2]) for row in self.cursor.fetchall()}
        possible_movements, destination_direction = get_possible_movements(
            self.x,
            self.y,
            max_distance=self.max_travel_distance,
            grid_width=32,
            grid_height=32,
            obstacle_data=self.obstacle_data,
            destinations=destinations,
        )
        return possible_movements, destination_direction

    def get_nearby_entities(self, x, y):
        return evaluate_nearby_entities(
            self.cursor,
            self.entity,
            x,
            y,
            self.bots,
            self.sight_distance,
            self.talk_distance,
            self.action,
            (32, 32),
            self.obstacle_data,
        )

    def get_updated_history(self, nearby_entities):
        return fetch_nearby_entities_for_history(
            self.cursor, self.entity, self.history, self.bots, self.sight_distance, self.talk_distance
        )

    def get_items_info(self, x, y):
        nearby_items = fetch_nearby_items(self.cursor, x, y, self.sight_distance)
        items_info = {}
        for item_name, item_x, item_y, item_desc, item_id in nearby_items:
            if item_x == x and item_y == y:
                items_info[f"{item_name}_{item_id}"] = {
                    "direction": "Here",
                    "path_distance": 0,
                    "total_distance": 0,
                    "description": item_desc,
                    "in_range_to_pickup": True,
                }
            else:
                direction, distance, total_distance = calculate_direction_and_distance(
                    (x, y), (item_x, item_y), (32, 32), self.obstacle_data
                )
                if direction and distance is not None:
                    items_info[f"{item_name}_{item_id}"] = {
                        "direction": direction,
                        "path_distance": distance,
                        "total_distance": total_distance,
                        "description": item_desc,
                        "in_range_to_pickup": total_distance <= 1,
                    }
        return items_info, nearby_items
