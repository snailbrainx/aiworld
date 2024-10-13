# actions.py
import random
from utils import is_within_sight
from db_functions import remove_item_from_world, add_item_to_inventory, get_item_location, remove_item_from_inventory

class ActionHandler:
    def __init__(self, cursor, cnx):
        self.cursor = cursor
        self.cnx = cnx

    # Keep this method with print statements for better logging
    def use_action(self, attacker, action, target_entity):
        print(f"Entering use_action: attacker={attacker}, action={action}, target={target_entity}")
        if action == "move":
            return  # Skip execution for the "move" action
        elif action == "pickup":
            self.handle_pickup(attacker, target_entity)
        elif action == "consume":
            self.handle_consume(attacker, target_entity)  # target_entity is the item to consume
        elif action in ["attack", "heal"]:
            self.handle_combat_action(attacker, action, target_entity)
        else:
            print(f"Invalid action: {action}")
        print(f"Exiting use_action for {attacker}")

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

    def handle_consume(self, entity, item_name):
        # Strip the ID suffix from the item name
        item_name = item_name.rsplit('_', 1)[0]
        cursor = self.cursor
        cnx = self.cnx

        print(f"Attempting to consume {item_name} for entity {entity}")

        cursor.execute("""
            SELECT i.effect_value, i.type, inv.id, i.name
            FROM inventory inv
            JOIN items i ON inv.item_id = i.id
            JOIN entities e ON inv.entity_id = e.id
            WHERE e.name = ? AND i.name LIKE ? AND (i.type = 'food' OR i.type = 'health_potion')
            LIMIT 1
        """, (entity, f"{item_name}%"))
        
        result = cursor.fetchone()
        if result:
            effect_value, item_type, inventory_id, actual_item_name = result
            print(f"Found consumable item: {actual_item_name}, effect: {effect_value}, type: {item_type}")
            
            # Apply the healing effect
            cursor.execute("""
                UPDATE aiworld
                SET health_points = MIN(health_points + ?, (SELECT hp FROM entities WHERE name = ?))
                WHERE entity = ? AND time = (SELECT MAX(time) FROM aiworld WHERE entity = ?)
            """, (effect_value, entity, entity, entity))
            
            # Remove the item from inventory
            cursor.execute("DELETE FROM inventory WHERE id = ?", (inventory_id,))
            
            print(f"{entity} consumed {actual_item_name} and healed for {effect_value} points")
            cnx.commit()
        else:
            print(f"{entity} doesn't have {item_name} or it's not consumable")

    def handle_pickup(self, attacker, target_entity):
        # Strip the ID suffix from the item name
        item_name = target_entity.rsplit('_', 1)[0]
        attacker_x, attacker_y = self.get_entity_position(attacker)
        self.pickup_item_in_range(attacker, item_name, attacker_x, attacker_y)


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