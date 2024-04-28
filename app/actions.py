# actions.py
import random
from utils import is_within_sight
from db_functions import remove_item_from_world, add_item_to_inventory, get_item_location

class ActionHandler:
    def __init__(self, cursor, cnx):
        self.cursor = cursor
        self.cnx = cnx

    def use_action(self, attacker, action, target_entity):
        if action == "move":
            return  # Skip execution for the "move" action
        elif action == "pickup":
            self.handle_pickup(attacker, target_entity)
        else:
            self.handle_combat_action(attacker, action, target_entity)

    def handle_pickup(self, attacker, target_entity):
        attacker_x, attacker_y = self.get_entity_position(attacker)
        self.pickup_item_in_range(attacker, target_entity, attacker_x, attacker_y)

    def pickup_item_in_range(self, entity, item_name, x, y):
        cursor = self.cursor
        cnx = self.cnx

        item_location = get_item_location(cursor, item_name)

        if item_location:
            item_x, item_y = item_location
            if abs(item_x - x) <= 1 and abs(item_y - y) <= 1:
                remove_item_from_world(cursor, cnx, item_name, item_x, item_y)
                add_item_to_inventory(cursor, cnx, entity, item_name)
                print(f"{entity} picked up {item_name}")
            else:
                print(f"{item_name} is not within pickup range of {entity}")
        else:
            print(f"{item_name} not found in the world")

    def handle_combat_action(self, attacker, action, target_entity):
        target_info = self.get_target_info(target_entity)
        if target_info:
            is_boss, target_max_hp = target_info
            self.execute_combat_action(attacker, action, target_entity, is_boss, target_max_hp)

    def get_target_info(self, target_entity):
        query = "SELECT boss, hp FROM entities WHERE name = ?"
        self.cursor.execute(query, (target_entity,))
        return self.cursor.fetchone()

    def execute_combat_action(self, attacker, action, target_entity, is_boss, target_max_hp):
        attacker_x, attacker_y = self.get_entity_position(attacker)
        target_x, target_y = self.get_entity_position(target_entity)
        if self.positions_are_valid(attacker_x, attacker_y, target_x, target_y):
            self.process_combat_action(attacker, action, target_entity, attacker_x, attacker_y, target_x, target_y, is_boss, target_max_hp)

    def positions_are_valid(self, *positions):
        return all(pos is not None for pos in positions)

    def process_combat_action(self, attacker, action, target_entity, attacker_x, attacker_y, target_x, target_y, is_boss, target_max_hp):
        action_range = self.get_action_range(action)
        if is_within_sight(attacker_x, attacker_y, target_x, target_y, action_range):
            if action == 'attack':
                self.attack(attacker, target_entity, is_boss)
            elif action == 'heal':
                self.heal(attacker, target_entity, target_max_hp, is_boss)

    def get_action_range(self, action):
        self.cursor.execute("SELECT range FROM actions WHERE action=?", (action,))
        return self.cursor.fetchone()[0]

    def get_entity_position(self, entity):
        self.cursor.execute("SELECT x, y FROM aiworld WHERE entity=? ORDER BY time DESC LIMIT 1", (entity,))
        row = self.cursor.fetchone()
        if row:
            return row[0], row[1]
        return None, None

    def get_action_values(self, action, is_boss):
        self.cursor.execute("SELECT min_value, max_value FROM actions WHERE action=?", (action,))
        row = self.cursor.fetchone()
        if row:
            min_value, max_value = row
            if is_boss:
                min_value *= 3
                max_value *= 3
            return min_value, max_value
        return 0, 0

    def attack(self, attacker, target, is_boss):
        min_damage, max_damage = self.get_action_values('attack', is_boss)
        damage = random.randint(min_damage, max_damage)
        query = """
        UPDATE aiworld
        SET health_points = CASE WHEN health_points - ? < 0 THEN 0 ELSE health_points - ? END
        WHERE entity = ? AND time = (SELECT MAX(time) FROM aiworld WHERE entity = ?)
        """
        values = (damage, damage, target, target)
        self.cursor.execute(query, values)
        self.cnx.commit()

    def heal(self, healer, target, target_max_hp, is_boss):
        min_healing, max_healing = self.get_action_values('heal', is_boss)
        healing = random.randint(min_healing, max_healing)
        query = """
        UPDATE aiworld
        SET health_points = CASE WHEN health_points + ? > ? THEN ? ELSE health_points + ? END
        WHERE entity = ? AND time = (SELECT MAX(time) FROM aiworld WHERE entity = ?)
        """
        values = (healing, target_max_hp, target_max_hp, healing, target, target)
        self.cursor.execute(query, values)
        self.cnx.commit()