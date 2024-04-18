# abilities.py
import random
from utils import create_grid, is_within_sight, get_possible_movements, is_obstacle, get_direction_from_deltas

class AbilityHandler:
    def __init__(self, cursor, cnx):
        self.cursor = cursor
        self.cnx = cnx

    def use_ability(self, attacker, ability, target_entity):
        query = "SELECT boss, hp FROM entities WHERE name = ?"
        values = (target_entity,)
        self.cursor.execute(query, values)
        result = self.cursor.fetchone()
        if result:
            is_boss, target_max_hp = result
            # Check if the target is within the ability's range
            attacker_x, attacker_y = self.get_entity_position(attacker)
            target_x, target_y = self.get_entity_position(target_entity)
            self.cursor.execute("SELECT range FROM abilities WHERE ability=?", (ability,))
            ability_range = self.cursor.fetchone()[0]
            if is_within_sight(attacker_x, attacker_y, target_x, target_y, ability_range):
                if ability == 'attack':
                    self.attack(attacker, target_entity, is_boss)
                elif ability == 'heal':
                    self.heal(attacker, target_entity, target_max_hp, is_boss)

    def get_entity_position(self, entity):
        self.cursor.execute("SELECT x, y FROM aiworld WHERE entity=? ORDER BY time DESC LIMIT 1", (entity,))
        row = self.cursor.fetchone()
        if row:
            return row[0], row[1]
        return None, None

    def get_ability_values(self, ability, is_boss):
        self.cursor.execute("SELECT min_value, max_value FROM abilities WHERE ability=?", (ability,))
        row = self.cursor.fetchone()
        if row:
            min_value, max_value = row
            if is_boss:
                min_value *= 3
                max_value *= 3
            return min_value, max_value
        return 0, 0

    def attack(self, attacker, target, is_boss):
        min_damage, max_damage = self.get_ability_values('attack', is_boss)
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
        min_healing, max_healing = self.get_ability_values('heal', is_boss)
        healing = random.randint(min_healing, max_healing)
        query = """
        UPDATE aiworld
        SET health_points = CASE WHEN health_points + ? > ? THEN ? ELSE health_points + ? END
        WHERE entity = ? AND time = (SELECT MAX(time) FROM aiworld WHERE entity = ?)
        """
        values = (healing, target_max_hp, target_max_hp, healing, target, target)
        self.cursor.execute(query, values)
        self.cnx.commit()