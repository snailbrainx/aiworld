# actions.py
import random
from utils import create_grid, is_within_sight, get_possible_movements, is_obstacle, get_direction_from_deltas

class ActionHandler:
    def __init__(self, cursor, cnx):
        self.cursor = cursor
        self.cnx = cnx

    def use_action(self, attacker, action, target_entity):
        if action == "move":
            return  # Skip execution for the "move" action
        
        query = "SELECT boss, hp FROM entities WHERE name = ?"
        values = (target_entity,)
        self.cursor.execute(query, values)
        result = self.cursor.fetchone()
        if result:
            is_boss, target_max_hp = result
            # Check if the target is within the action's range
            attacker_x, attacker_y = self.get_entity_position(attacker)
            target_x, target_y = self.get_entity_position(target_entity)
            
            # Check if both attacker and target positions are valid
            if attacker_x is not None and attacker_y is not None and target_x is not None and target_y is not None:
                self.cursor.execute("SELECT range FROM actions WHERE action=?", (action,))
                action_range = self.cursor.fetchone()[0]
                if is_within_sight(attacker_x, attacker_y, target_x, target_y, action_range):
                    if action == 'attack':
                        self.attack(attacker, target_entity, is_boss)
                    elif action == 'heal':
                        self.heal(attacker, target_entity, target_max_hp, is_boss)
            else:
                print(f"Warning: Invalid position for attacker ({attacker}) or target ({target_entity})")

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